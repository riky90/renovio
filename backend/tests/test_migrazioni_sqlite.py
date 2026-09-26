"""La catena Alembic deve girare davvero su SQLite, e lo schema che produce
deve coincidere con quello che costruisce `Base.metadata.create_all`.

Perche' questo file esiste (CR-03 della review di fase 08): tutti gli altri
test costruiscono lo schema da `create_all`, cioe' dai modelli ORM, e non
eseguono mai le migrazioni. Una migrazione puo' quindi essere verde per
l'intera suite e non applicarsi su nessun database reale. E' successo con la
`0019`, che usava `add_column(..., server_default=func.now(), nullable=False)`:
SQLite rifiuta `ALTER TABLE ... ADD COLUMN ... DEFAULT CURRENT_TIMESTAMP`
(`Cannot add a column with non-constant default`), e siccome `DATABASE_URL`
vale `sqlite:///./dev.db` di default quella e' la configurazione di ogni
sviluppatore: il database locale restava a `0018` e le nove colonne
`updated_at` esistevano solo nello schema dei test.

I test qui sotto chiudono quel buco su tre fronti:

* la catena completa `base -> head` gira su un file SQLite usa-e-getta;
* lo schema migrato e quello da `create_all` hanno le stesse colonne, con
  gli stessi tipi, la stessa nullability e lo stesso default lato server;
* la `0019` in particolare fa il backfill delle righe preesistenti, lascia
  un `server_default` funzionante per gli INSERT successivi ed e'
  reversibile.
"""

from __future__ import annotations

import datetime as _dt
import shutil
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

from app.config import settings
from app.db import Base
from scripts.applica_taratura import _TEMPLATE_MIGRAZIONE

# Importare `app.models` registra TUTTE le entita' su `Base.metadata` — da
# WR-05 anche `Lead` e `Testo`, che il package prima taceva e che questo
# file doveva quindi importare a mano (`lead` e' una delle nove tabelle
# toccate dalla 0019, il confronto con lo schema migrato sarebbe stato
# cieco proprio li'). Che il package resti completo lo presidia
# `tests/test_modelli_registrati.py`.
import app.models  # noqa: F401

BACKEND_DIR = Path(__file__).resolve().parents[1]

# Le nove tabelle a cui la 0019 aggiunge `updated_at` (guardia di staleness D-11).
TABELLE_CURATE = (
    "sottocategoria",
    "voce",
    "coefficiente_qta_voce",
    "moltiplicatore",
    "extra",
    "categoria",
    "listino_categoria",
    "forfait_arredo",
    "lead",
)

# Le cinque tabelle del catalogo domande a cui la 0020 aggiunge `updated_at`
# (D-11); le stesse su cui il modello/migrazione devono coincidere.
TABELLE_CATALOGO = (
    "domanda",
    "opzione_domanda",
    "effetto_opzione",
    "attesa_immobile",
    "derivazione_risposta",
)


def _alembic_config(db_path: Path, monkeypatch: pytest.MonkeyPatch) -> Config:
    """Config Alembic puntata a un file SQLite usa-e-getta.

    Si costruisce la `Config` senza file .ini: `env.py` chiama `fileConfig()`
    solo quando `config_file_name` e' valorizzato, e riconfigurare il logging
    globale in mezzo a una suite pytest zittisce i logger degli altri test.
    L'URL non si passa qui perche' `env.py` lo sovrascrive sempre con
    `settings.DATABASE_URL`: e' quello che va spostato.
    """
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{db_path}")
    config = Config()
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return config


def _colonne(db_path: Path) -> dict[str, dict[str, tuple[str, bool, str | None]]]:
    """Schema di un database SQLite come {tabella: {colonna: (tipo, nullable, default)}}."""
    engine = create_engine(f"sqlite:///{db_path}")
    try:
        ispettore = inspect(engine)
        return {
            tabella: {
                colonna["name"]: (
                    str(colonna["type"]),
                    colonna["nullable"],
                    colonna.get("default"),
                )
                for colonna in ispettore.get_columns(tabella)
            }
            for tabella in ispettore.get_table_names()
            if tabella != "alembic_version"
        }
    finally:
        engine.dispose()


def _valore_fittizio(tipo_dichiarato: str) -> object:
    """Un valore qualsiasi ma del tipo giusto, per riempire una colonna NOT NULL."""
    tipo = tipo_dichiarato.upper()
    if "BOOL" in tipo:
        return 0
    if "INT" in tipo:
        return 1
    if "NUMERIC" in tipo or "DECIMAL" in tipo or "REAL" in tipo or "FLOAT" in tipo:
        return 1
    if "BLOB" in tipo:
        return b"x"
    if "DATE" in tipo or "TIME" in tipo:
        return "2020-01-01 00:00:00"
    return "x"


def _popola_ogni_tabella(db_path: Path) -> list[str]:
    """Inserisce una riga fittizia in ogni tabella del database.

    Serve perche' il vincolo SQLite che ha rotto la 0019 scatta **solo su
    tabelle non vuote**: `ALTER TABLE ... ADD COLUMN ... DEFAULT
    CURRENT_TIMESTAMP NOT NULL` passa senza un fiato su una tabella a zero
    righe e fallisce appena ce n'e' una. Una catena di migrazioni eseguita su
    un database vergine e' quindi cieca proprio all'errore da intercettare:
    va popolato prima.

    Le foreign key non vengono imposte (SQLite ha `PRAGMA foreign_keys=OFF`
    di default), quindi i riferimenti possono restare fittizi: qui interessa
    solo che le tabelle non siano vuote.
    """
    connessione = sqlite3.connect(db_path)
    popolate: list[str] = []
    try:
        tabelle = [
            riga[0]
            for riga in connessione.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
                " AND name NOT LIKE 'sqlite_%' AND name <> 'alembic_version'"
            )
        ]
        for tabella in tabelle:
            colonne = list(connessione.execute(f"PRAGMA table_info({tabella})"))
            nomi: list[str] = []
            valori: list[object] = []
            for _, nome, tipo, notnull, default, pk in colonne:
                if default is not None and not pk:
                    continue
                if notnull or pk:
                    nomi.append(nome)
                    valori.append(_valore_fittizio(tipo))
            segnaposto = ", ".join("?" for _ in nomi)
            elenco = ", ".join(f'"{n}"' for n in nomi)
            connessione.execute(
                f'INSERT INTO "{tabella}" ({elenco}) VALUES ({segnaposto})', valori
            )
            popolate.append(tabella)
        connessione.commit()
    finally:
        connessione.close()
    return popolate


def test_upgrade_head_gira_su_sqlite_vergine(tmp_path, monkeypatch):
    """`alembic upgrade head` deve arrivare in fondo su un SQLite vuoto."""
    db_path = tmp_path / "catena.db"
    command.upgrade(_alembic_config(db_path, monkeypatch), "head")

    assert db_path.exists()
    connessione = sqlite3.connect(db_path)
    try:
        revisione = connessione.execute("SELECT version_num FROM alembic_version").fetchone()
    finally:
        connessione.close()
    assert revisione == ("0022",)


def test_upgrade_all_ultima_revisione_gira_su_un_database_popolato(tmp_path, monkeypatch):
    """La migrazione di testa deve applicarsi a un database che contiene dati.

    E' questo il test che intercetta la 0019 rotta, e non quello sul database
    vergine: con le tabelle vuote SQLite accetta senza obiezioni
    `ADD COLUMN ... DEFAULT CURRENT_TIMESTAMP NOT NULL`, e si rifiuta solo
    quando c'e' almeno una riga da riempire —

        sqlite3.OperationalError: Cannot add a column with non-constant default
        [SQL: ALTER TABLE sottocategoria ADD COLUMN updated_at DATETIME
         DEFAULT CURRENT_TIMESTAMP NOT NULL]

    Il test e' scritto in forma generica (penultima revisione -> popola tutto
    -> testa) proprio per continuare a valere sulla prossima migrazione, non
    solo sulla 0019.
    """
    db_path = tmp_path / "popolato.db"
    config = _alembic_config(db_path, monkeypatch)

    script = ScriptDirectory.from_config(config)
    testa = script.get_current_head()
    assert testa is not None
    penultima = script.get_revision(testa).down_revision
    assert isinstance(penultima, str), "la catena di migrazioni deve essere lineare"

    command.upgrade(config, penultima)
    popolate = _popola_ogni_tabella(db_path)
    assert set(TABELLE_CURATE) <= set(popolate), (
        "le nove tabelle curate devono essere popolate prima di applicare la migrazione di testa"
    )

    command.upgrade(config, testa)

    connessione = sqlite3.connect(db_path)
    try:
        assert connessione.execute("SELECT version_num FROM alembic_version").fetchone() == (testa,)
        for tabella in TABELLE_CURATE:
            (righe, valorizzate) = connessione.execute(
                f"SELECT COUNT(*), COUNT(updated_at) FROM {tabella}"
            ).fetchone()
            assert righe > 0
            assert righe == valorizzate, f"{tabella}.updated_at non e' stata backfillata"
    finally:
        connessione.close()


def test_schema_migrato_coincide_con_create_all(tmp_path, monkeypatch):
    """Lo schema prodotto dalle migrazioni e quello dai modelli non devono divergere.

    E' la divergenza — non il singolo errore SQL — il difetto vero di CR-03:
    finche' i test costruiscono lo schema da `create_all`, una colonna puo'
    esistere nei test e mancare in ogni database migrato.
    """
    db_migrato = tmp_path / "migrato.db"
    command.upgrade(_alembic_config(db_migrato, monkeypatch), "head")

    db_metadata = tmp_path / "metadata.db"
    engine = create_engine(f"sqlite:///{db_metadata}")
    try:
        Base.metadata.create_all(engine)
    finally:
        engine.dispose()

    colonne_migrate = _colonne(db_migrato)
    colonne_metadata = _colonne(db_metadata)

    assert set(colonne_migrate) == set(colonne_metadata)
    for tabella in sorted(colonne_metadata):
        assert colonne_migrate[tabella] == colonne_metadata[tabella], (
            f"schema divergente sulla tabella {tabella}"
        )


def test_0019_aggiunge_updated_at_alle_nove_tabelle(tmp_path, monkeypatch):
    """Le nove colonne devono esistere NOT NULL e con default lato server.

    Il `server_default` e' la parte che si dimentica: i modelli ORM non hanno
    un default Python per `updated_at`, quindi un INSERT che non la valorizza
    dipende interamente dal default del database.
    """
    db_path = tmp_path / "colonne.db"
    command.upgrade(_alembic_config(db_path, monkeypatch), "head")

    connessione = sqlite3.connect(db_path)
    try:
        for tabella in TABELLE_CURATE:
            colonne = {
                riga[1]: {"tipo": riga[2], "notnull": riga[3], "default": riga[4]}
                for riga in connessione.execute(f"PRAGMA table_info({tabella})")
            }
            assert "updated_at" in colonne, f"{tabella} non ha updated_at dopo la 0019"
            assert colonne["updated_at"]["notnull"] == 1, f"{tabella}.updated_at deve essere NOT NULL"
            assert "CURRENT_TIMESTAMP" in (colonne["updated_at"]["default"] or ""), (
                f"{tabella}.updated_at deve avere un server_default"
            )
    finally:
        connessione.close()


def test_0019_backfilla_le_righe_preesistenti(tmp_path, monkeypatch):
    """Le righe gia' presenti a revisione 0018 devono ricevere un `updated_at`.

    E devono riceverne uno *anteriore* a qualunque export generato dopo la
    migrazione: e' la proprieta' su cui si regge la guardia di staleness
    (il primo re-import non deve marcare tutto come superato).
    """
    db_path = tmp_path / "backfill.db"
    config = _alembic_config(db_path, monkeypatch)
    command.upgrade(config, "0018")

    prima_della_migrazione = datetime.now(timezone.utc).replace(tzinfo=None)

    connessione = sqlite3.connect(db_path)
    try:
        connessione.execute(
            "INSERT INTO categoria (code, nome, ordine, iva_pct, livello_selezionabile, nel_totale_lavori)"
            " VALUES ('edile', 'Edile', 1, 0.10, 0, 1)"
        )
        connessione.execute(
            "INSERT INTO listino (id, nome, citta_riferimento, valuta, is_default, attivo)"
            " VALUES (1, 'Listino RE', 'Reggio Emilia', 'EUR', 1, 1)"
        )
        connessione.execute(
            "INSERT INTO sottocategoria (id, listino_id, categoria_code, nome, famiglia, ordine)"
            " VALUES (1, 1, 'edile', 'Demolizioni', 'a.1', 1)"
        )
        connessione.commit()
    finally:
        connessione.close()

    command.upgrade(config, "0019")

    connessione = sqlite3.connect(db_path)
    try:
        (valore,) = connessione.execute("SELECT updated_at FROM sottocategoria WHERE id = 1").fetchone()
    finally:
        connessione.close()

    assert valore is not None, "il backfill della 0019 ha lasciato updated_at a NULL"
    backfillato = datetime.fromisoformat(valore)
    dopo_la_migrazione = datetime.now(timezone.utc).replace(tzinfo=None)
    # Tolleranza di un minuto: la migrazione scrive UTC, la finestra e' larga
    # abbastanza da non dipendere dalla durata del test.
    assert prima_della_migrazione - timedelta(minutes=1) <= backfillato <= dopo_la_migrazione + timedelta(minutes=1)


def test_insert_senza_updated_at_funziona_su_db_migrato(tmp_path, monkeypatch):
    """Su un database migrato, un INSERT che non valorizza `updated_at` deve passare.

    E' il modo in cui l'import crea le righe nuove: se la 0019 aggiungesse la
    colonna NOT NULL senza default, ogni riga nuova esploderebbe con una
    violazione di NOT NULL solo in produzione, mai nei test.
    """
    db_path = tmp_path / "insert.db"
    command.upgrade(_alembic_config(db_path, monkeypatch), "head")

    connessione = sqlite3.connect(db_path)
    try:
        connessione.execute(
            "INSERT INTO categoria (code, nome, ordine, iva_pct, livello_selezionabile, nel_totale_lavori)"
            " VALUES ('edile', 'Edile', 1, 0.10, 0, 1)"
        )
        connessione.commit()
        (valore,) = connessione.execute("SELECT updated_at FROM categoria WHERE code = 'edile'").fetchone()
    finally:
        connessione.close()

    assert valore is not None


def test_downgrade_0019_e_poi_upgrade_e_reversibile(tmp_path, monkeypatch):
    """Il downgrade deve togliere le nove colonne senza rompere lo schema, e
    l'upgrade successivo deve poterle rimettere."""
    db_path = tmp_path / "reversibile.db"
    config = _alembic_config(db_path, monkeypatch)
    command.upgrade(config, "head")
    command.downgrade(config, "0018")

    connessione = sqlite3.connect(db_path)
    try:
        for tabella in TABELLE_CURATE:
            colonne = [riga[1] for riga in connessione.execute(f"PRAGMA table_info({tabella})")]
            assert "updated_at" not in colonne, f"{tabella}.updated_at sopravvive al downgrade"
        assert connessione.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connessione.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    finally:
        connessione.close()

    command.upgrade(config, "0019")

    connessione = sqlite3.connect(db_path)
    try:
        for tabella in TABELLE_CURATE:
            colonne = [riga[1] for riga in connessione.execute(f"PRAGMA table_info({tabella})")]
            assert "updated_at" in colonne
        assert connessione.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        connessione.close()


def test_la_ricostruzione_batch_non_perde_chiavi_e_vincoli(tmp_path, monkeypatch):
    """`batch_alter_table` su SQLite ricrea la tabella: le foreign key e i
    vincoli di unicita' devono sopravvivere alla ricostruzione.

    E' il rischio specifico di questa forma di migrazione, e non lo coprirebbe
    nessun confronto di sole colonne.
    """
    db_path = tmp_path / "vincoli.db"
    command.upgrade(_alembic_config(db_path, monkeypatch), "head")

    engine = create_engine(f"sqlite:///{db_path}")
    try:
        ispettore = inspect(engine)
        fk_sottocategoria = {
            (fk["referred_table"], tuple(fk["constrained_columns"]))
            for fk in ispettore.get_foreign_keys("sottocategoria")
        }
        assert ("listino", ("listino_id",)) in fk_sottocategoria
        assert ("categoria", ("categoria_code",)) in fk_sottocategoria

        assert {fk["referred_table"] for fk in ispettore.get_foreign_keys("voce")} == {"sottocategoria"}

        vincoli_unici = {
            tuple(vincolo["column_names"])
            for vincolo in ispettore.get_unique_constraints("listino_categoria")
        }
        assert ("listino_id", "categoria_code") in vincoli_unici
    finally:
        engine.dispose()

    connessione = sqlite3.connect(db_path)
    try:
        assert connessione.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connessione.execute(
            "SELECT name FROM sqlite_master WHERE name LIKE '_alembic_tmp%'"
        ).fetchall() == []
    finally:
        connessione.close()


def test_0020_aggiunge_attiva_e_updated_at(tmp_path, monkeypatch):
    """`attiva` su opzione_domanda/attesa_immobile e `updated_at` sulle cinque
    tabelle del catalogo devono esistere dopo `upgrade head` (D-27, D-40, D-11).
    """
    db_path = tmp_path / "catalogo_colonne.db"
    command.upgrade(_alembic_config(db_path, monkeypatch), "head")

    connessione = sqlite3.connect(db_path)
    try:
        for tabella in TABELLE_CATALOGO:
            colonne = {
                riga[1]: {"tipo": riga[2], "notnull": riga[3], "default": riga[4]}
                for riga in connessione.execute(f"PRAGMA table_info({tabella})")
            }
            assert "updated_at" in colonne, f"{tabella} non ha updated_at dopo la 0020"
            assert colonne["updated_at"]["notnull"] == 1, f"{tabella}.updated_at deve essere NOT NULL"
            assert "CURRENT_TIMESTAMP" in (colonne["updated_at"]["default"] or ""), (
                f"{tabella}.updated_at deve avere un server_default"
            )

        for tabella in ("opzione_domanda", "attesa_immobile"):
            colonne = {
                riga[1]: {"notnull": riga[3], "default": riga[4]}
                for riga in connessione.execute(f"PRAGMA table_info({tabella})")
            }
            assert "attiva" in colonne, f"{tabella} non ha attiva dopo la 0020"
            assert colonne["attiva"]["notnull"] == 1, f"{tabella}.attiva deve essere NOT NULL"
    finally:
        connessione.close()


def test_0020_backfilla_le_righe_preesistenti(tmp_path, monkeypatch):
    """Righe gia' presenti a revisione 0019 ricevono `attiva=1` e un
    `updated_at` non nullo dopo la 0020 (stessa proprieta' di staleness della
    0019: il backfill precede qualunque export generato dopo la migrazione).
    """
    db_path = tmp_path / "catalogo_backfill.db"
    config = _alembic_config(db_path, monkeypatch)
    command.upgrade(config, "0019")

    connessione = sqlite3.connect(db_path)
    try:
        connessione.execute(
            "INSERT INTO domanda (code, testo, tipo_controllo) VALUES ('anno_costruzione', 'Anno di costruzione', 'stepper')"
        )
        connessione.execute(
            "INSERT INTO opzione_domanda (domanda_code, code, etichetta) VALUES ('anno_costruzione', 'valore', 'Valore')"
        )
        connessione.execute(
            "INSERT INTO attesa_immobile (attributo_code, fascia_mq_min, fascia_mq_max, valore_atteso)"
            " VALUES ('bagni', 0, 120, 2)"
        )
        connessione.commit()
    finally:
        connessione.close()

    command.upgrade(config, "0020")

    connessione = sqlite3.connect(db_path)
    try:
        (attiva_opzione, updated_at_opzione) = connessione.execute(
            "SELECT attiva, updated_at FROM opzione_domanda WHERE code = 'valore'"
        ).fetchone()
        (attiva_attesa, updated_at_attesa) = connessione.execute(
            "SELECT attiva, updated_at FROM attesa_immobile WHERE attributo_code = 'bagni'"
        ).fetchone()
        (updated_at_domanda,) = connessione.execute(
            "SELECT updated_at FROM domanda WHERE code = 'anno_costruzione'"
        ).fetchone()
    finally:
        connessione.close()

    assert attiva_opzione == 1
    assert attiva_attesa == 1
    assert updated_at_opzione is not None
    assert updated_at_attesa is not None
    assert updated_at_domanda is not None


def test_downgrade_0020_e_poi_upgrade_e_reversibile(tmp_path, monkeypatch):
    """Il downgrade della 0020 toglie `attiva` e `updated_at` dal catalogo
    senza rompere lo schema, e l'upgrade successivo le rimette."""
    db_path = tmp_path / "catalogo_reversibile.db"
    config = _alembic_config(db_path, monkeypatch)
    command.upgrade(config, "head")
    command.downgrade(config, "0019")

    connessione = sqlite3.connect(db_path)
    try:
        for tabella in TABELLE_CATALOGO:
            colonne = [riga[1] for riga in connessione.execute(f"PRAGMA table_info({tabella})")]
            assert "updated_at" not in colonne, f"{tabella}.updated_at sopravvive al downgrade"
        for tabella in ("opzione_domanda", "attesa_immobile"):
            colonne = [riga[1] for riga in connessione.execute(f"PRAGMA table_info({tabella})")]
            assert "attiva" not in colonne, f"{tabella}.attiva sopravvive al downgrade"
        assert connessione.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connessione.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    finally:
        connessione.close()

    command.upgrade(config, "0020")

    connessione = sqlite3.connect(db_path)
    try:
        for tabella in TABELLE_CATALOGO:
            colonne = [riga[1] for riga in connessione.execute(f"PRAGMA table_info({tabella})")]
            assert "updated_at" in colonne
        for tabella in ("opzione_domanda", "attesa_immobile"):
            colonne = [riga[1] for riga in connessione.execute(f"PRAGMA table_info({tabella})")]
            assert "attiva" in colonne
        assert connessione.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        connessione.close()


# ---------------------------------------------------------------------------
# 0021 — asse finitura da voce.livello + quantita_per_unita da domanda_mirata_key
# ---------------------------------------------------------------------------


def _semina_curatela_09_04(connessione: sqlite3.Connection) -> dict[str, int]:
    """Popola a mano, su un DB a revisione 0020, la curatela minima che la
    0021 deve leggere: 3 voci livellate (base/medio/alto), 1 voce senza
    livello, la domanda stepper `bagni` con opzione `valore`, e righe
    `coefficiente_qta_voce` con `domanda_mirata_key='bagni'` sui 3 tipi per
    quella quarta voce. Ritorna gli id utili al test.
    """
    connessione.execute(
        "INSERT INTO categoria (code, nome, ordine, iva_pct, livello_selezionabile, nel_totale_lavori)"
        " VALUES ('finiture', 'Finiture', 1, 0.22, 1, 1)"
    )
    connessione.execute(
        "INSERT INTO listino (id, nome, citta_riferimento, valuta, is_default, attivo)"
        " VALUES (1, 'Listino RE', 'Reggio Emilia', 'EUR', 1, 1)"
    )
    connessione.execute(
        "INSERT INTO sottocategoria (id, listino_id, categoria_code, nome, famiglia, ordine)"
        " VALUES (1, 1, 'finiture', 'Gres', 'catalogo', 1)"
    )
    for codice, nome, ordine in (
        ("leggera", "Leggera", 1),
        ("moderata", "Moderata", 2),
        ("totale", "Totale", 3),
    ):
        connessione.execute(
            "INSERT INTO tipo_ristrutturazione (code, nome, ordine, range_pct) VALUES (?, ?, ?, 0.15)",
            (codice, nome, ordine),
        )

    id_per_livello: dict[str, int] = {}
    for livello in ("base", "medio", "alto"):
        cursore = connessione.execute(
            "INSERT INTO voce (sottocategoria_id, descrizione, um, prezzo_unitario_cliente, ordine, livello)"
            " VALUES (1, ?, 'mq', 50.00, 1, ?)",
            (f"Voce {livello}", livello),
        )
        id_per_livello[livello] = cursore.lastrowid

    cursore = connessione.execute(
        "INSERT INTO voce (sottocategoria_id, descrizione, um, prezzo_unitario_cliente, ordine, livello)"
        " VALUES (1, 'Voce senza livello', 'mq', 30.00, 4, NULL)"
    )
    id_senza_livello = cursore.lastrowid

    cursore = connessione.execute(
        "INSERT INTO voce (sottocategoria_id, descrizione, um, prezzo_unitario_cliente, ordine, livello)"
        " VALUES (1, 'Sanitari per bagno', 'cad', 400.00, 5, NULL)"
    )
    id_voce_bagni = cursore.lastrowid

    connessione.execute(
        "INSERT INTO domanda (code, testo, tipo_controllo) VALUES ('bagni', 'Numero di bagni', 'stepper')"
    )
    connessione.execute(
        "INSERT INTO opzione_domanda (domanda_code, code, etichetta) VALUES ('bagni', 'valore', 'Valore')"
    )
    for tipo_code in ("leggera", "moderata", "totale"):
        connessione.execute(
            "INSERT INTO coefficiente_qta_voce (voce_id, tipo_code, domanda_mirata_key)"
            " VALUES (?, ?, 'bagni')",
            (id_voce_bagni, tipo_code),
        )

    connessione.commit()
    return {
        "voce_base": id_per_livello["base"],
        "voce_medio": id_per_livello["medio"],
        "voce_alto": id_per_livello["alto"],
        "voce_senza_livello": id_senza_livello,
        "voce_bagni": id_voce_bagni,
    }


def test_0021_crea_asse_finitura_e_quantita_dalle_chiavi(tmp_path, monkeypatch):
    """Su curatela reale (3 voci livellate + chiavi mirate bagni), la 0021
    crea la domanda finitura con 3 opzioni (medio default), 3 effetti
    `includi` sulle voci giuste e 1 effetto `quantita_per_unita` (valore 1,
    tipo_code NULL: la chiave copre tutti e 3 i tipi) sull'opzione valore di
    bagni verso la quarta voce."""
    db_path = tmp_path / "curatela.db"
    config = _alembic_config(db_path, monkeypatch)
    command.upgrade(config, "0020")

    connessione = sqlite3.connect(db_path)
    try:
        id_ = _semina_curatela_09_04(connessione)
    finally:
        connessione.close()

    command.upgrade(config, "0021")

    connessione = sqlite3.connect(db_path)
    try:
        assert connessione.execute(
            "SELECT code FROM domanda WHERE code = 'finitura'"
        ).fetchone() is not None

        opzioni = connessione.execute(
            "SELECT code, is_default FROM opzione_domanda WHERE domanda_code = 'finitura' ORDER BY code"
        ).fetchall()
        assert opzioni == [("alto", 0), ("base", 0), ("medio", 1)]

        opzione_id_per_livello = dict(
            connessione.execute(
                "SELECT code, id FROM opzione_domanda WHERE domanda_code = 'finitura'"
            ).fetchall()
        )

        effetti_includi = connessione.execute(
            "SELECT opzione_id, target_voce_id, tipo_code, valore FROM effetto_opzione"
            " WHERE tipo_effetto = 'includi' AND opzione_id IN"
            " (SELECT id FROM opzione_domanda WHERE domanda_code = 'finitura')"
        ).fetchall()
        assert len(effetti_includi) == 3
        bersagli = {(opzione_id_per_livello[liv], id_[f"voce_{liv}"]) for liv in ("base", "medio", "alto")}
        assert {(riga[0], riga[1]) for riga in effetti_includi} == bersagli
        for _, _, tipo_code, valore in effetti_includi:
            assert tipo_code is None
            assert valore is None

        opzione_bagni_valore = connessione.execute(
            "SELECT id FROM opzione_domanda WHERE domanda_code = 'bagni' AND code = 'valore'"
        ).fetchone()[0]
        effetti_quantita = connessione.execute(
            "SELECT target_voce_id, tipo_code, valore FROM effetto_opzione"
            " WHERE tipo_effetto = 'quantita_per_unita' AND opzione_id = ?",
            (opzione_bagni_valore,),
        ).fetchall()
        assert effetti_quantita == [(id_["voce_bagni"], None, 1)]
    finally:
        connessione.close()


def test_0021_non_duplica_effetti_gia_seminati(tmp_path, monkeypatch):
    """Se il seed (o una run precedente della migrazione) ha gia' creato la
    domanda finitura con un effetto sulla voce base, la 0021 non lo duplica:
    dopo l'upgrade restano 3 effetti includi in totale, non 4."""
    db_path = tmp_path / "gia_seminato.db"
    config = _alembic_config(db_path, monkeypatch)
    command.upgrade(config, "0020")

    connessione = sqlite3.connect(db_path)
    try:
        id_ = _semina_curatela_09_04(connessione)

        adesso = "2026-09-26 00:00:00"
        connessione.execute(
            "INSERT INTO domanda (code, testo, tipo_controllo, gruppo, ordine, tier_minimo, updated_at)"
            " VALUES ('finitura', 'Livello di finitura', 'scelta_singola', 'configuratore_pro', 200, 'pro', ?)",
            (adesso,),
        )
        cursore = connessione.execute(
            "INSERT INTO opzione_domanda (domanda_code, code, etichetta, is_default, ordine, updated_at)"
            " VALUES ('finitura', 'base', 'Entry level', 0, 1, ?)",
            (adesso,),
        )
        opzione_base_id = cursore.lastrowid
        connessione.execute(
            "INSERT INTO effetto_opzione (opzione_id, tipo_effetto, target_voce_id, attivo, updated_at)"
            " VALUES (?, 'includi', ?, 1, ?)",
            (opzione_base_id, id_["voce_base"], adesso),
        )
        connessione.commit()
    finally:
        connessione.close()

    command.upgrade(config, "0021")

    connessione = sqlite3.connect(db_path)
    try:
        totale_effetti_includi = connessione.execute(
            "SELECT COUNT(*) FROM effetto_opzione"
            " WHERE tipo_effetto = 'includi' AND opzione_id IN"
            " (SELECT id FROM opzione_domanda WHERE domanda_code = 'finitura')"
        ).fetchone()[0]
        assert totale_effetti_includi == 3

        totale_opzioni_base = connessione.execute(
            "SELECT COUNT(*) FROM opzione_domanda WHERE domanda_code = 'finitura' AND code = 'base'"
        ).fetchone()[0]
        assert totale_opzioni_base == 1
    finally:
        connessione.close()


def test_0021_ignora_valori_sconosciuti(tmp_path, monkeypatch):
    """`voce.livello` fuori da base/medio/alto e `domanda_mirata_key` senza
    domanda corrispondente vengono saltati senza errore e senza creare nulla."""
    db_path = tmp_path / "sconosciuti.db"
    config = _alembic_config(db_path, monkeypatch)
    command.upgrade(config, "0020")

    connessione = sqlite3.connect(db_path)
    try:
        connessione.execute(
            "INSERT INTO categoria (code, nome, ordine, iva_pct, livello_selezionabile, nel_totale_lavori)"
            " VALUES ('finiture', 'Finiture', 1, 0.22, 1, 1)"
        )
        connessione.execute(
            "INSERT INTO listino (id, nome, citta_riferimento, valuta, is_default, attivo)"
            " VALUES (1, 'Listino RE', 'Reggio Emilia', 'EUR', 1, 1)"
        )
        connessione.execute(
            "INSERT INTO sottocategoria (id, listino_id, categoria_code, nome, famiglia, ordine)"
            " VALUES (1, 1, 'finiture', 'Gres', 'catalogo', 1)"
        )
        connessione.execute(
            "INSERT INTO tipo_ristrutturazione (code, nome, ordine, range_pct)"
            " VALUES ('leggera', 'Leggera', 1, 0.15)"
        )
        connessione.execute(
            "INSERT INTO voce (sottocategoria_id, descrizione, um, prezzo_unitario_cliente, ordine, livello)"
            " VALUES (1, 'Voce livello sconosciuto', 'mq', 10.00, 1, 'xyz')"
        )
        cursore = connessione.execute(
            "INSERT INTO voce (sottocategoria_id, descrizione, um, prezzo_unitario_cliente, ordine)"
            " VALUES (1, 'Voce chiave sconosciuta', 'mq', 10.00, 2)"
        )
        voce_chiave_id = cursore.lastrowid
        connessione.execute(
            "INSERT INTO coefficiente_qta_voce (voce_id, tipo_code, domanda_mirata_key)"
            " VALUES (?, 'leggera', 'foo')",
            (voce_chiave_id,),
        )
        connessione.commit()
    finally:
        connessione.close()

    # Non deve alzare nessuna eccezione.
    command.upgrade(config, "0021")

    connessione = sqlite3.connect(db_path)
    try:
        assert connessione.execute(
            "SELECT code FROM domanda WHERE code = 'finitura'"
        ).fetchone() is None
        assert connessione.execute("SELECT COUNT(*) FROM effetto_opzione").fetchone()[0] == 0
    finally:
        connessione.close()


def test_0021_non_tocca_livello_ne_chiavi(tmp_path, monkeypatch):
    """Dopo l'upgrade, `voce.livello` e `coefficiente_qta_voce.domanda_mirata_key`
    sono identici a prima: nessun UPDATE, solo nuove righe in altre tabelle."""
    db_path = tmp_path / "invariati.db"
    config = _alembic_config(db_path, monkeypatch)
    command.upgrade(config, "0020")

    connessione = sqlite3.connect(db_path)
    try:
        _semina_curatela_09_04(connessione)
        prima_livelli = connessione.execute(
            "SELECT id, livello FROM voce ORDER BY id"
        ).fetchall()
        prima_chiavi = connessione.execute(
            "SELECT voce_id, tipo_code, domanda_mirata_key FROM coefficiente_qta_voce ORDER BY voce_id, tipo_code"
        ).fetchall()
    finally:
        connessione.close()

    command.upgrade(config, "0021")

    connessione = sqlite3.connect(db_path)
    try:
        dopo_livelli = connessione.execute("SELECT id, livello FROM voce ORDER BY id").fetchall()
        dopo_chiavi = connessione.execute(
            "SELECT voce_id, tipo_code, domanda_mirata_key FROM coefficiente_qta_voce ORDER BY voce_id, tipo_code"
        ).fetchall()
    finally:
        connessione.close()

    assert prima_livelli == dopo_livelli
    assert prima_chiavi == dopo_chiavi


def test_downgrade_0021_e_poi_upgrade_e_reversibile(tmp_path, monkeypatch):
    """upgrade head -> downgrade 0020 -> upgrade head: stessi conteggi di
    `effetto_opzione`, `voce.livello` e `domanda_mirata_key` invariati."""
    db_path = tmp_path / "reversibile_0021.db"
    config = _alembic_config(db_path, monkeypatch)
    command.upgrade(config, "0020")

    connessione = sqlite3.connect(db_path)
    try:
        _semina_curatela_09_04(connessione)
    finally:
        connessione.close()

    command.upgrade(config, "0021")

    connessione = sqlite3.connect(db_path)
    try:
        conteggio_prima = connessione.execute("SELECT COUNT(*) FROM effetto_opzione").fetchone()[0]
        livelli_prima = connessione.execute("SELECT id, livello FROM voce ORDER BY id").fetchall()
        chiavi_prima = connessione.execute(
            "SELECT voce_id, tipo_code, domanda_mirata_key FROM coefficiente_qta_voce ORDER BY voce_id, tipo_code"
        ).fetchall()
        assert conteggio_prima == 4  # 3 includi + 1 quantita_per_unita
    finally:
        connessione.close()

    command.downgrade(config, "0020")

    connessione = sqlite3.connect(db_path)
    try:
        assert connessione.execute(
            "SELECT code FROM domanda WHERE code = 'finitura'"
        ).fetchone() is None
        assert connessione.execute(
            "SELECT COUNT(*) FROM opzione_domanda WHERE domanda_code = 'finitura'"
        ).fetchone()[0] == 0
        assert connessione.execute(
            "SELECT COUNT(*) FROM effetto_opzione WHERE tipo_effetto IN ('includi', 'quantita_per_unita')"
        ).fetchone()[0] == 0
        livelli_dopo_downgrade = connessione.execute("SELECT id, livello FROM voce ORDER BY id").fetchall()
        chiavi_dopo_downgrade = connessione.execute(
            "SELECT voce_id, tipo_code, domanda_mirata_key FROM coefficiente_qta_voce ORDER BY voce_id, tipo_code"
        ).fetchall()
        assert livelli_dopo_downgrade == livelli_prima
        assert chiavi_dopo_downgrade == chiavi_prima
        assert connessione.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connessione.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    finally:
        connessione.close()

    command.upgrade(config, "0021")

    connessione = sqlite3.connect(db_path)
    try:
        conteggio_dopo = connessione.execute("SELECT COUNT(*) FROM effetto_opzione").fetchone()[0]
        livelli_dopo = connessione.execute("SELECT id, livello FROM voce ORDER BY id").fetchall()
        chiavi_dopo = connessione.execute(
            "SELECT voce_id, tipo_code, domanda_mirata_key FROM coefficiente_qta_voce ORDER BY voce_id, tipo_code"
        ).fetchall()
        assert conteggio_dopo == conteggio_prima
        assert livelli_dopo == livelli_prima
        assert chiavi_dopo == chiavi_prima
    finally:
        connessione.close()


# ---------------------------------------------------------------------------
# 0022 — taratura approvata (D-03/D-08, piano 09-06): coefficienti + effetti
# ---------------------------------------------------------------------------
#
# La 0022 reale (generata da `scripts/applica_taratura.py --migrazione` sulla
# bozza accettata) ha `_VALORI_EFFETTO`/`_INCLUDI_SPOSTATI` vuote (nessun
# valore di stepper o asse spostato tra la base 09-02 e la bozza corrente).
# Per provare TUTTI i quattro rami del template, questi test scrivono una
# 0022 SINTETICA (stesso `_TEMPLATE_MIGRAZIONE` del modulo, stesse
# revision/down_revision "0022"/"0021") con costanti scelte ad hoc, dentro una
# copia temporanea di `alembic/` — mai il file reale, mai `backend/dev.db`.

CHIAVE_A = ("finiture", "GRES", "Voce coefficiente")
CHIAVE_B = ("finiture", "GRES", "Voce quantita")


def _scrivi_0022_sintetica(
    versions_dir: Path,
    *,
    coefficienti: tuple = (),
    valori_effetto: tuple = (),
    includi_spostati: tuple = (),
    effetti_rimossi: tuple = (),
) -> None:
    contenuto = _TEMPLATE_MIGRAZIONE.format(
        revision="0022",
        down_revision="0021",
        create_date=_dt.datetime.now().isoformat(),
        coefficienti=tuple(coefficienti),
        valori_effetto=tuple(valori_effetto),
        includi_spostati=tuple(includi_spostati),
        effetti_rimossi=tuple(effetti_rimossi),
    )
    (versions_dir / "0022_taratura_pro_approvata.py").write_text(contenuto, encoding="utf-8")


def _alembic_config_0022_sintetica(db_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **costanti) -> Config:
    """Config Alembic su una copia temporanea di `alembic/` con la 0022 reale
    sostituita da una sintetica (stesse revision/down_revision, costanti a
    scelta) — la catena 0001..0021 resta quella vera, invariata."""
    versions_tmp_root = tmp_path / "alembic_0022_sintetica"
    shutil.copytree(BACKEND_DIR / "alembic", versions_tmp_root)
    _scrivi_0022_sintetica(versions_tmp_root / "versions", **costanti)
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{db_path}")
    config = Config()
    config.set_main_option("script_location", str(versions_tmp_root))
    return config


def _semina_curatela_09_06(connessione: sqlite3.Connection) -> dict[str, int]:
    """Curatela minima su un DB a revisione 0021: una sottocategoria/due voci
    con coefficiente_qta_voce (una 'in bozza' al valore vecchio, una 'curata a
    mano' a un valore diverso), la domanda `finitura` con opzioni medio/alto,
    la domanda `bagni` con opzione `valore`."""
    connessione.execute(
        "INSERT INTO categoria (code, nome, ordine, iva_pct, livello_selezionabile, nel_totale_lavori)"
        " VALUES ('finiture', 'Finiture', 1, 0.22, 1, 1)"
    )
    connessione.execute(
        "INSERT INTO listino (id, nome, citta_riferimento, valuta, is_default, attivo)"
        " VALUES (1, 'Listino RE', 'Reggio Emilia', 'EUR', 1, 1)"
    )
    connessione.execute(
        "INSERT INTO sottocategoria (id, listino_id, categoria_code, nome, famiglia, ordine)"
        " VALUES (1, 1, 'finiture', 'GRES', 'catalogo', 1)"
    )
    connessione.execute(
        "INSERT INTO tipo_ristrutturazione (code, nome, ordine, range_pct) VALUES ('totale', 'Totale', 1, 0.15)"
    )

    cursore = connessione.execute(
        "INSERT INTO voce (sottocategoria_id, descrizione, um, prezzo_unitario_cliente, ordine)"
        " VALUES (1, 'Voce coefficiente', 'mq', 40.00, 1)"
    )
    voce_coeff_id = cursore.lastrowid
    connessione.execute(
        "INSERT INTO coefficiente_qta_voce (voce_id, tipo_code, coefficiente_qta_per_mq) VALUES (?, 'totale', 0.6)",
        (voce_coeff_id,),
    )

    cursore = connessione.execute(
        "INSERT INTO voce (sottocategoria_id, descrizione, um, prezzo_unitario_cliente, ordine)"
        " VALUES (1, 'Voce curata', 'mq', 40.00, 2)"
    )
    voce_curata_id = cursore.lastrowid
    connessione.execute(
        "INSERT INTO coefficiente_qta_voce (voce_id, tipo_code, coefficiente_qta_per_mq) VALUES (?, 'totale', 1.23)",
        (voce_curata_id,),
    )

    cursore = connessione.execute(
        "INSERT INTO voce (sottocategoria_id, descrizione, um, prezzo_unitario_cliente, ordine)"
        " VALUES (1, 'Voce quantita', 'cad', 50.00, 3)"
    )
    voce_quantita_id = cursore.lastrowid

    connessione.execute(
        "INSERT INTO domanda (code, testo, tipo_controllo) VALUES ('finitura', 'Livello di finitura', 'scelta_singola')"
    )
    connessione.execute(
        "INSERT INTO opzione_domanda (domanda_code, code, etichetta) VALUES ('finitura', 'medio', 'Medio')"
    )
    connessione.execute(
        "INSERT INTO opzione_domanda (domanda_code, code, etichetta) VALUES ('finitura', 'alto', 'Alto')"
    )
    connessione.execute(
        "INSERT INTO domanda (code, testo, tipo_controllo) VALUES ('bagni', 'Numero di bagni', 'stepper')"
    )
    connessione.execute(
        "INSERT INTO opzione_domanda (domanda_code, code, etichetta) VALUES ('bagni', 'valore', 'Valore')"
    )
    connessione.commit()

    return {
        "voce_coeff": voce_coeff_id,
        "voce_curata": voce_curata_id,
        "voce_quantita": voce_quantita_id,
    }


def test_0022_aggiorna_solo_le_righe_in_bozza(tmp_path, monkeypatch):
    """DB a 0021 con una riga coefficiente al valore di bozza e una riga
    curata a mano: dopo upgrade 0022 la prima ha il valore nuovo, la seconda
    e' invariata."""
    db_path = tmp_path / "coeff.db"
    config = _alembic_config_0022_sintetica(
        db_path,
        tmp_path,
        monkeypatch,
        coefficienti=((CHIAVE_A[0], CHIAVE_A[1], CHIAVE_A[2], "totale", "coefficiente_qta_per_mq", 0.6, 0.85),),
    )
    command.upgrade(config, "0021")

    connessione = sqlite3.connect(db_path)
    try:
        id_ = _semina_curatela_09_06(connessione)
    finally:
        connessione.close()

    command.upgrade(config, "0022")

    connessione = sqlite3.connect(db_path)
    try:
        (valore_bozza,) = connessione.execute(
            "SELECT coefficiente_qta_per_mq FROM coefficiente_qta_voce WHERE voce_id = ? AND tipo_code = 'totale'",
            (id_["voce_coeff"],),
        ).fetchone()
        (valore_curato,) = connessione.execute(
            "SELECT coefficiente_qta_per_mq FROM coefficiente_qta_voce WHERE voce_id = ? AND tipo_code = 'totale'",
            (id_["voce_curata"],),
        ).fetchone()
    finally:
        connessione.close()

    assert valore_bozza == pytest.approx(0.85)
    assert valore_curato == pytest.approx(1.23)  # invariata: non era al valore di bozza (0.6)


def test_0022_aggiorna_valori_effetto_ancora_alla_base(tmp_path, monkeypatch):
    """Un effetto `quantita_per_unita` viene aggiornato solo se vale ancora
    il valore base; una riga gia' curata a un valore diverso resta
    invariata."""
    db_path = tmp_path / "valori.db"
    config = _alembic_config_0022_sintetica(
        db_path,
        tmp_path,
        monkeypatch,
        valori_effetto=(("bagni", "valore", "quantita_per_unita", CHIAVE_B, None, 1.0, 2.0),),
    )
    command.upgrade(config, "0021")

    connessione = sqlite3.connect(db_path)
    try:
        id_ = _semina_curatela_09_06(connessione)
        opzione_id = connessione.execute(
            "SELECT id FROM opzione_domanda WHERE domanda_code = 'bagni' AND code = 'valore'"
        ).fetchone()[0]
        connessione.execute(
            "INSERT INTO effetto_opzione (opzione_id, tipo_effetto, target_voce_id, valore, attivo)"
            " VALUES (?, 'quantita_per_unita', ?, 1.0, 1)",
            (opzione_id, id_["voce_quantita"]),
        )
        connessione.commit()
    finally:
        connessione.close()

    command.upgrade(config, "0022")

    connessione = sqlite3.connect(db_path)
    try:
        (valore,) = connessione.execute(
            "SELECT valore FROM effetto_opzione WHERE tipo_effetto = 'quantita_per_unita' AND target_voce_id = ?",
            (id_["voce_quantita"],),
        ).fetchone()
    finally:
        connessione.close()
    assert valore == pytest.approx(2.0)


def test_0022_sposta_la_finitura_senza_doppioni(tmp_path, monkeypatch):
    """L'effetto `includi` di una voce del gres passa dall'opzione vecchia
    alla nuova senza doppioni; se la nuova ha gia' un includi identico, quello
    sulla vecchia viene rimosso invece di duplicare."""
    db_path = tmp_path / "includi.db"
    config = _alembic_config_0022_sintetica(
        db_path,
        tmp_path,
        monkeypatch,
        includi_spostati=(("finitura", CHIAVE_A, "medio", "alto"),),
    )
    command.upgrade(config, "0021")

    connessione = sqlite3.connect(db_path)
    try:
        id_ = _semina_curatela_09_06(connessione)
        opzione_medio_id = connessione.execute(
            "SELECT id FROM opzione_domanda WHERE domanda_code = 'finitura' AND code = 'medio'"
        ).fetchone()[0]
        connessione.execute(
            "INSERT INTO effetto_opzione (opzione_id, tipo_effetto, target_voce_id, attivo)"
            " VALUES (?, 'includi', ?, 1)",
            (opzione_medio_id, id_["voce_coeff"]),
        )
        connessione.commit()
    finally:
        connessione.close()

    command.upgrade(config, "0022")

    connessione = sqlite3.connect(db_path)
    try:
        righe = connessione.execute(
            "SELECT od.code FROM effetto_opzione eo JOIN opzione_domanda od ON od.id = eo.opzione_id"
            " WHERE eo.tipo_effetto = 'includi' AND eo.target_voce_id = ?",
            (id_["voce_coeff"],),
        ).fetchall()
    finally:
        connessione.close()
    assert righe == [("alto",)]  # una sola riga, mai un doppione


def test_0022_sposta_la_finitura_non_duplica_se_gia_presente_sulla_nuova(tmp_path, monkeypatch):
    """Se l'opzione nuova ha GIA' un includi identico (curatela concorrente),
    l'upgrade rimuove quello sulla vecchia invece di crearne un secondo."""
    db_path = tmp_path / "includi_doppio.db"
    config = _alembic_config_0022_sintetica(
        db_path,
        tmp_path,
        monkeypatch,
        includi_spostati=(("finitura", CHIAVE_A, "medio", "alto"),),
    )
    command.upgrade(config, "0021")

    connessione = sqlite3.connect(db_path)
    try:
        id_ = _semina_curatela_09_06(connessione)
        opzione_medio_id = connessione.execute(
            "SELECT id FROM opzione_domanda WHERE domanda_code = 'finitura' AND code = 'medio'"
        ).fetchone()[0]
        opzione_alto_id = connessione.execute(
            "SELECT id FROM opzione_domanda WHERE domanda_code = 'finitura' AND code = 'alto'"
        ).fetchone()[0]
        for opzione_id in (opzione_medio_id, opzione_alto_id):
            connessione.execute(
                "INSERT INTO effetto_opzione (opzione_id, tipo_effetto, target_voce_id, attivo)"
                " VALUES (?, 'includi', ?, 1)",
                (opzione_id, id_["voce_coeff"]),
            )
        connessione.commit()
    finally:
        connessione.close()

    command.upgrade(config, "0022")

    connessione = sqlite3.connect(db_path)
    try:
        righe = connessione.execute(
            "SELECT od.code FROM effetto_opzione eo JOIN opzione_domanda od ON od.id = eo.opzione_id"
            " WHERE eo.tipo_effetto = 'includi' AND eo.target_voce_id = ?",
            (id_["voce_coeff"],),
        ).fetchall()
    finally:
        connessione.close()
    assert righe == [("alto",)]


def test_0022_rimuove_solo_effetti_identici(tmp_path, monkeypatch):
    """Un effetto con bersaglio naturale presente nella base e assente nel
    nuovo (assegnazione respinta) viene cancellato solo se esiste ancora
    identico; una riga gia' cambiata (valore diverso da quello base) resta."""
    db_path = tmp_path / "rimossi.db"
    config = _alembic_config_0022_sintetica(
        db_path,
        tmp_path,
        monkeypatch,
        effetti_rimossi=(("bagni", "valore", "quantita_per_unita", CHIAVE_B, None, 1.0),),
    )
    command.upgrade(config, "0021")

    connessione = sqlite3.connect(db_path)
    try:
        id_ = _semina_curatela_09_06(connessione)
        opzione_id = connessione.execute(
            "SELECT id FROM opzione_domanda WHERE domanda_code = 'bagni' AND code = 'valore'"
        ).fetchone()[0]
        connessione.execute(
            "INSERT INTO effetto_opzione (opzione_id, tipo_effetto, target_voce_id, valore, attivo)"
            " VALUES (?, 'quantita_per_unita', ?, 1.0, 1)",
            (opzione_id, id_["voce_quantita"]),
        )
        connessione.commit()
    finally:
        connessione.close()

    command.upgrade(config, "0022")

    connessione = sqlite3.connect(db_path)
    try:
        righe = connessione.execute(
            "SELECT COUNT(*) FROM effetto_opzione WHERE tipo_effetto = 'quantita_per_unita' AND target_voce_id = ?",
            (id_["voce_quantita"],),
        ).fetchone()[0]
    finally:
        connessione.close()
    assert righe == 0


def test_0022_non_rimuove_un_effetto_gia_cambiato(tmp_path, monkeypatch):
    db_path = tmp_path / "rimossi_cambiati.db"
    config = _alembic_config_0022_sintetica(
        db_path,
        tmp_path,
        monkeypatch,
        effetti_rimossi=(("bagni", "valore", "quantita_per_unita", CHIAVE_B, None, 1.0),),
    )
    command.upgrade(config, "0021")

    connessione = sqlite3.connect(db_path)
    try:
        id_ = _semina_curatela_09_06(connessione)
        opzione_id = connessione.execute(
            "SELECT id FROM opzione_domanda WHERE domanda_code = 'bagni' AND code = 'valore'"
        ).fetchone()[0]
        connessione.execute(
            "INSERT INTO effetto_opzione (opzione_id, tipo_effetto, target_voce_id, valore, attivo)"
            " VALUES (?, 'quantita_per_unita', ?, 9.0, 1)",  # curato a mano, non piu' al valore base 1.0
            (opzione_id, id_["voce_quantita"]),
        )
        connessione.commit()
    finally:
        connessione.close()

    command.upgrade(config, "0022")

    connessione = sqlite3.connect(db_path)
    try:
        righe = connessione.execute(
            "SELECT valore FROM effetto_opzione WHERE tipo_effetto = 'quantita_per_unita' AND target_voce_id = ?",
            (id_["voce_quantita"],),
        ).fetchall()
    finally:
        connessione.close()
    assert righe == [(9.0,)]  # invariata: non era piu' al valore base


def test_downgrade_0022_e_poi_upgrade_e_reversibile(tmp_path, monkeypatch):
    """upgrade head -> downgrade 0021 -> upgrade head e' stabile: il
    coefficiente torna al valore base al downgrade e al nuovo al successivo
    upgrade."""
    db_path = tmp_path / "reversibile_0022.db"
    config = _alembic_config_0022_sintetica(
        db_path,
        tmp_path,
        monkeypatch,
        coefficienti=((CHIAVE_A[0], CHIAVE_A[1], CHIAVE_A[2], "totale", "coefficiente_qta_per_mq", 0.6, 0.85),),
    )
    command.upgrade(config, "0021")

    connessione = sqlite3.connect(db_path)
    try:
        id_ = _semina_curatela_09_06(connessione)
    finally:
        connessione.close()

    command.upgrade(config, "0022")
    connessione = sqlite3.connect(db_path)
    try:
        (dopo_upgrade,) = connessione.execute(
            "SELECT coefficiente_qta_per_mq FROM coefficiente_qta_voce WHERE voce_id = ? AND tipo_code = 'totale'",
            (id_["voce_coeff"],),
        ).fetchone()
    finally:
        connessione.close()
    assert dopo_upgrade == pytest.approx(0.85)

    command.downgrade(config, "0021")
    connessione = sqlite3.connect(db_path)
    try:
        (dopo_downgrade,) = connessione.execute(
            "SELECT coefficiente_qta_per_mq FROM coefficiente_qta_voce WHERE voce_id = ? AND tipo_code = 'totale'",
            (id_["voce_coeff"],),
        ).fetchone()
        assert connessione.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connessione.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    finally:
        connessione.close()
    assert dopo_downgrade == pytest.approx(0.6)

    command.upgrade(config, "0022")
    connessione = sqlite3.connect(db_path)
    try:
        (dopo_riupgrade,) = connessione.execute(
            "SELECT coefficiente_qta_per_mq FROM coefficiente_qta_voce WHERE voce_id = ? AND tipo_code = 'totale'",
            (id_["voce_coeff"],),
        ).fetchone()
    finally:
        connessione.close()
    assert dopo_riupgrade == pytest.approx(0.85)
