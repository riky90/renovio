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
    assert revisione == ("0026",)


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
    `effetto_opzione`, `voce.livello` e `domanda_mirata_key` invariati.

    WR-02 (review 09-08 e 09-14): il downgrade e' un no-op documentato. Non
    cancella `domanda`/`opzione_domanda` di `finitura` ne' gli effetti,
    perche' non puo' distinguere le righe scritte dall'upgrade da quelle del
    seed o della curatela a mano con la stessa chiave naturale."""
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
        ).fetchone() is not None  # WR-02: la domanda non viene piu' cancellata
        assert connessione.execute(
            "SELECT COUNT(*) FROM opzione_domanda WHERE domanda_code = 'finitura'"
        ).fetchone()[0] == 3  # idem per le opzioni base/medio/alto
        assert connessione.execute(
            "SELECT COUNT(*) FROM effetto_opzione"
        ).fetchone()[0] == conteggio_prima  # WR-02 (09-14): nemmeno gli effetti
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


def test_downgrade_0021_preserva_finitura_preesistente_e_effetto_curato_a_mano(tmp_path, monkeypatch):
    """WR-02 (09-14): se `finitura` preesisteva PRIMA di 0021 (come fa il
    seed su un DB nuovo) e ha un effetto `includi` curato a mano su una voce
    SENZA livello, il downgrade lascia domanda, opzioni e quell'effetto —
    rimuove solo gli `includi` il cui bersaglio ha `voce.livello` uguale al
    code dell'opzione (quelli che la sezione (A) dell'upgrade crea)."""
    db_path = tmp_path / "finitura_preesistente.db"
    config = _alembic_config(db_path, monkeypatch)
    command.upgrade(config, "0020")

    connessione = sqlite3.connect(db_path)
    try:
        id_ = _semina_curatela_09_04(connessione)

        # finitura preesistente (come la crea il seed su un DB nuovo, D-41)
        connessione.execute(
            "INSERT INTO domanda (code, testo, tipo_controllo, gruppo, ordine, tier_minimo)"
            " VALUES ('finitura', 'Livello di finitura', 'scelta_singola', 'configuratore_pro', 200, 'pro')"
        )
        cursore = connessione.execute(
            "INSERT INTO opzione_domanda (domanda_code, code, etichetta, is_default, ordine)"
            " VALUES ('finitura', 'medio', 'Medio', 1, 2)"
        )
        opzione_medio_id = cursore.lastrowid

        # effetto includi curato a mano su una voce SENZA livello: l'upgrade
        # (sezione A) non lo crea e non lo tocca, quindi il downgrade non
        # deve toccarlo nemmeno lui.
        connessione.execute(
            "INSERT INTO effetto_opzione (opzione_id, tipo_effetto, target_voce_id, attivo)"
            " VALUES (?, 'includi', ?, 1)",
            (opzione_medio_id, id_["voce_senza_livello"]),
        )
        connessione.commit()
    finally:
        connessione.close()

    command.upgrade(config, "0021")

    connessione = sqlite3.connect(db_path)
    try:
        # l'upgrade non duplica l'opzione 'medio' gia' presente, ne crea
        # 'base'/'alto' e i loro includi sulle voci livellate
        opzioni = connessione.execute(
            "SELECT code FROM opzione_domanda WHERE domanda_code = 'finitura' ORDER BY code"
        ).fetchall()
        assert opzioni == [("alto",), ("base",), ("medio",)]
    finally:
        connessione.close()

    command.downgrade(config, "0020")

    connessione = sqlite3.connect(db_path)
    try:
        # domanda e opzioni restano TUTTE (WR-02), non solo quella preesistente
        assert connessione.execute(
            "SELECT code FROM domanda WHERE code = 'finitura'"
        ).fetchone() is not None
        assert connessione.execute(
            "SELECT COUNT(*) FROM opzione_domanda WHERE domanda_code = 'finitura'"
        ).fetchone()[0] == 3

        # l'effetto curato a mano su una voce SENZA livello sopravvive
        curato_superstite = connessione.execute(
            "SELECT COUNT(*) FROM effetto_opzione WHERE opzione_id = ? AND tipo_effetto = 'includi'"
            " AND target_voce_id = ?",
            (opzione_medio_id, id_["voce_senza_livello"]),
        ).fetchone()[0]
        assert curato_superstite == 1

        # WR-02 (09-14): il downgrade e' un no-op, restano anche i 3 includi
        # delle voci livellate (non distinguibili da quelli del seed)
        totale_includi = connessione.execute(
            "SELECT COUNT(*) FROM effetto_opzione WHERE tipo_effetto = 'includi'"
        ).fetchone()[0]
        assert totale_includi == 4

        assert connessione.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connessione.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    finally:
        connessione.close()


def test_downgrade_0021_non_cancella_includi_preesistente_su_voce_livellata(tmp_path, monkeypatch):
    """WR-02 (review 09-14): un `includi` di `finitura` che esisteva PRIMA
    della 0021 sulla stessa coppia (opzione, voce livellata) che l'upgrade
    avrebbe prodotto — per esempio creato dal seed — l'upgrade lo salta e il
    downgrade non deve cancellarlo. Vale anche per il `quantita_per_unita`
    preesistente sulla voce con chiave mirata."""
    db_path = tmp_path / "includi_preesistente_livellata.db"
    config = _alembic_config(db_path, monkeypatch)
    command.upgrade(config, "0020")

    connessione = sqlite3.connect(db_path)
    try:
        id_ = _semina_curatela_09_04(connessione)
        connessione.execute(
            "INSERT INTO domanda (code, testo, tipo_controllo, gruppo, ordine, tier_minimo)"
            " VALUES ('finitura', 'Livello di finitura', 'scelta_singola', 'configuratore_pro', 200, 'pro')"
        )
        cursore = connessione.execute(
            "INSERT INTO opzione_domanda (domanda_code, code, etichetta, is_default, ordine)"
            " VALUES ('finitura', 'medio', 'Medio', 1, 2)"
        )
        opzione_medio_id = cursore.lastrowid
        connessione.execute(
            "INSERT INTO effetto_opzione (opzione_id, tipo_effetto, target_voce_id, attivo)"
            " VALUES (?, 'includi', ?, 1)",
            (opzione_medio_id, id_["voce_medio"]),
        )
        (opzione_bagni_id,) = connessione.execute(
            "SELECT id FROM opzione_domanda WHERE domanda_code = 'bagni' AND code = 'valore'"
        ).fetchone()
        connessione.execute(
            "INSERT INTO effetto_opzione (opzione_id, tipo_effetto, target_voce_id, valore, attivo)"
            " VALUES (?, 'quantita_per_unita', ?, 1, 1)",
            (opzione_bagni_id, id_["voce_bagni"]),
        )
        connessione.commit()
    finally:
        connessione.close()

    command.upgrade(config, "0021")
    command.downgrade(config, "0020")

    connessione = sqlite3.connect(db_path)
    try:
        assert connessione.execute(
            "SELECT COUNT(*) FROM effetto_opzione WHERE opzione_id = ? AND tipo_effetto = 'includi'"
            " AND target_voce_id = ?",
            (opzione_medio_id, id_["voce_medio"]),
        ).fetchone()[0] == 1
        assert connessione.execute(
            "SELECT COUNT(*) FROM effetto_opzione WHERE opzione_id = ?"
            " AND tipo_effetto = 'quantita_per_unita' AND target_voce_id = ?",
            (opzione_bagni_id, id_["voce_bagni"]),
        ).fetchone()[0] == 1
    finally:
        connessione.close()


def test_downgrade_0021_e_poi_upgrade_non_crea_doppioni_su_finitura_preesistente(tmp_path, monkeypatch):
    """upgrade -> downgrade 0020 -> upgrade su una `finitura` preesistente non
    crea doppioni: stessi conteggi di `effetto_opzione` prima e dopo il
    round-trip."""
    db_path = tmp_path / "finitura_preesistente_roundtrip.db"
    config = _alembic_config(db_path, monkeypatch)
    command.upgrade(config, "0020")

    connessione = sqlite3.connect(db_path)
    try:
        _semina_curatela_09_04(connessione)
        connessione.execute(
            "INSERT INTO domanda (code, testo, tipo_controllo, gruppo, ordine, tier_minimo)"
            " VALUES ('finitura', 'Livello di finitura', 'scelta_singola', 'configuratore_pro', 200, 'pro')"
        )
        connessione.execute(
            "INSERT INTO opzione_domanda (domanda_code, code, etichetta, is_default, ordine)"
            " VALUES ('finitura', 'medio', 'Medio', 1, 2)"
        )
        connessione.commit()
    finally:
        connessione.close()

    command.upgrade(config, "0021")
    conteggio_prima = _conta_effetti(db_path)

    command.downgrade(config, "0020")
    command.upgrade(config, "0021")
    conteggio_dopo = _conta_effetti(db_path)

    assert conteggio_dopo == conteggio_prima

    connessione = sqlite3.connect(db_path)
    try:
        opzioni = connessione.execute(
            "SELECT COUNT(*) FROM opzione_domanda WHERE domanda_code = 'finitura'"
        ).fetchone()[0]
    finally:
        connessione.close()
    assert opzioni == 3  # nessun doppione sulle opzioni neanche in questo scenario


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


def test_0022_risolve_le_voci_solo_sul_listino_predefinito(tmp_path, monkeypatch):
    """WR-03 (review 09): con un secondo listino che ha gli stessi codici, la
    migrazione risolve la voce sul listino PREDEFINITO, come il seed, e non
    sulla prima sottocategoria che capita (qui quella del listino 1, non piu'
    predefinito e con id piu' basso)."""
    db_path = tmp_path / "due_listini.db"
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
        connessione.execute("UPDATE listino SET is_default = 0 WHERE id = 1")
        connessione.execute(
            "INSERT INTO listino (id, nome, citta_riferimento, valuta, is_default, attivo)"
            " VALUES (2, 'Listino Parma', 'Parma', 'EUR', 1, 1)"
        )
        connessione.execute(
            "INSERT INTO sottocategoria (id, listino_id, categoria_code, nome, famiglia, ordine)"
            " VALUES (2, 2, 'finiture', 'GRES', 'catalogo', 1)"
        )
        cursore = connessione.execute(
            "INSERT INTO voce (sottocategoria_id, descrizione, um, prezzo_unitario_cliente, ordine)"
            " VALUES (2, 'Voce coefficiente', 'mq', 40.00, 1)"
        )
        voce_default_id = cursore.lastrowid
        connessione.execute(
            "INSERT INTO coefficiente_qta_voce (voce_id, tipo_code, coefficiente_qta_per_mq)"
            " VALUES (?, 'totale', 0.6)",
            (voce_default_id,),
        )
        connessione.commit()
    finally:
        connessione.close()

    command.upgrade(config, "0022")

    connessione = sqlite3.connect(db_path)
    try:
        (valore_default,) = connessione.execute(
            "SELECT coefficiente_qta_per_mq FROM coefficiente_qta_voce WHERE voce_id = ? AND tipo_code = 'totale'",
            (voce_default_id,),
        ).fetchone()
        (valore_altro,) = connessione.execute(
            "SELECT coefficiente_qta_per_mq FROM coefficiente_qta_voce WHERE voce_id = ? AND tipo_code = 'totale'",
            (id_["voce_coeff"],),
        ).fetchone()
    finally:
        connessione.close()

    assert valore_default == pytest.approx(0.85)
    assert valore_altro == pytest.approx(0.6)  # listino non predefinito: intatto


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


# ---------------------------------------------------------------------------
# 0023 — pavimenti alternativi + A.6 intera governata (gap G1/G2, piano 09-14)
# ---------------------------------------------------------------------------
#
# A differenza della 0022 (che aggiorna righe gia' esistenti al valore di
# bozza), la 0023 CREA righe assenti dalla base (opzioni + effetti a
# bersaglio naturale), create-if-missing come il seed. I test seminano il
# catalogo REALE (`scripts.seed.seed`) su un DB a 0022, non curatela
# sintetica: il rischio che questa migrazione deve coprire e' un mojibake o
# un drift del catalogo VERO, non un caso di laboratorio.


def _importa_modulo_0023():
    """Importa `0023_pavimenti_alternativi.py` con `importlib` (il nome del
    file comincia per cifra, non e' un percorso puntato valido) per leggere
    le sue costanti `_OPZIONI_NUOVE`/`_EFFETTI_AGGIUNTI`/`_EFFETTI_RIMOSSI`
    senza duplicarle a mano nel test."""
    import importlib.util

    percorso = BACKEND_DIR / "alembic" / "versions" / "0023_pavimenti_alternativi.py"
    spec = importlib.util.spec_from_file_location("_migrazione_0023", percorso)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _semina_catalogo_reale(db_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Porta un DB vergine a 0022 e ci semina sopra il catalogo reale
    (`backend/seed_data/seed-domande.json` + il resto di `scripts.seed.seed`)
    — lo stesso file che gira in produzione, non una fixture di laboratorio.

    Sessione legata a un engine dedicato su `db_path` (non `app.db.SessionLocal`,
    che e' un singleton di modulo creato alla prima import e resta legato al
    `DATABASE_URL` di quel momento: il `monkeypatch` su `settings.DATABASE_URL`
    non lo riconfigura mai una volta importato)."""
    import app.models  # noqa: F401 — registra le entita' su Base.metadata
    from scripts.seed import seed as seed_reale
    from tests.session_factory import sessione_di_test

    config = _alembic_config(db_path, monkeypatch)
    command.upgrade(config, "0022")
    engine_dedicato = create_engine(f"sqlite:///{db_path}")
    Sessione = sessione_di_test(engine_dedicato)
    session = Sessione()
    try:
        seed_reale(session)
        session.commit()
    finally:
        session.close()
        engine_dedicato.dispose()


def _conta_effetti(db_path: Path) -> int:
    connessione = sqlite3.connect(db_path)
    try:
        return connessione.execute("SELECT COUNT(*) FROM effetto_opzione").fetchone()[0]
    finally:
        connessione.close()


def _rimuovi_effetti_e_opzioni_0023(db_path: Path, modulo) -> None:
    """Cancella dal DB esattamente le righe che `_OPZIONI_NUOVE`/
    `_EFFETTI_AGGIUNTI` della 0023 dovrebbero ricreare, per simulare un DB
    fermo alla base 0022 (seed di ieri) pur avendo il catalogo reale
    intorno."""
    connessione = sqlite3.connect(db_path)
    try:
        opzioni_nuove_codici = [oc for _dc, oc, *_ in modulo._OPZIONI_NUOVE]
        segnaposto = ", ".join("?" for _ in opzioni_nuove_codici)
        connessione.execute(
            f"DELETE FROM effetto_opzione WHERE opzione_id IN"
            f" (SELECT id FROM opzione_domanda WHERE domanda_code = 'tipo_pavimento' AND code IN ({segnaposto}))",
            opzioni_nuove_codici,
        )
        connessione.execute(
            f"DELETE FROM opzione_domanda WHERE domanda_code = 'tipo_pavimento' AND code IN ({segnaposto})",
            opzioni_nuove_codici,
        )
        for (
            domanda_code,
            opzione_code,
            tipo_effetto,
            categoria_code,
            sottocategoria_key,
            voce_key,
            tipo_code,
            _valore,
        ) in modulo._EFFETTI_AGGIUNTI:
            if opzione_code in opzioni_nuove_codici:
                continue  # gia' rimosso sopra insieme all'opzione
            righe_voce = connessione.execute(
                "SELECT v.id FROM voce v JOIN sottocategoria s ON s.id = v.sottocategoria_id"
                # Per nome/descrizione anche con un codice: dalla 0025 B/C/D
                # hanno codici stabili e il seed v3 li scrive gia'.
                " WHERE s.categoria_code = ? AND (s.codice = ? OR s.nome = ?)"
                " AND (v.codice = ? OR v.descrizione = ?)",
                (categoria_code, sottocategoria_key, sottocategoria_key, voce_key, voce_key),
            ).fetchall()
            for (voce_id,) in righe_voce:
                connessione.execute(
                    "DELETE FROM effetto_opzione WHERE opzione_id ="
                    " (SELECT id FROM opzione_domanda WHERE domanda_code = ? AND code = ?)"
                    " AND tipo_effetto = ? AND target_voce_id = ?"
                    " AND (tipo_code = ? OR (tipo_code IS NULL AND ? IS NULL))",
                    (domanda_code, opzione_code, tipo_effetto, voce_id, tipo_code, tipo_code),
                )
        connessione.commit()
    finally:
        connessione.close()


def test_0023_tutte_le_chiavi_di_effetti_aggiunti_si_risolvono_sul_catalogo_reale(tmp_path, monkeypatch):
    """Un mojibake o un drift nelle costanti generate dal diff deve rompere
    la suite, non il deploy: su un DB appena seminato con il catalogo reale,
    OGNI chiave naturale di `_EFFETTI_AGGIUNTI` risolve una voce e
    un'opzione (gia' presente o fra le `_OPZIONI_NUOVE`)."""
    modulo = _importa_modulo_0023()
    db_path = tmp_path / "chiavi_reali.db"
    _semina_catalogo_reale(db_path, monkeypatch)

    opzioni_nuove_chiavi = {(dc, oc) for dc, oc, *_ in modulo._OPZIONI_NUOVE}
    domanda, opzione, sottocategoria, voce, effetto = modulo._tabelle()
    engine = create_engine(f"sqlite:///{db_path}")
    bind = engine.connect()
    try:
        non_risolte = []
        for (
            domanda_code,
            opzione_code,
            _tipo_effetto,
            categoria_code,
            sottocategoria_key,
            voce_key,
            _tipo_code,
            _valore,
        ) in modulo._EFFETTI_AGGIUNTI:
            voce_id = modulo._risolvi_voce_id(bind, sottocategoria, voce, categoria_code, sottocategoria_key, voce_key)
            opzione_id = modulo._opzione_id(bind, opzione, domanda_code, opzione_code)
            opzione_pendente = opzione_id is None and (domanda_code, opzione_code) in opzioni_nuove_chiavi
            if voce_id is None or (opzione_id is None and not opzione_pendente):
                non_risolte.append((domanda_code, opzione_code, categoria_code, sottocategoria_key, voce_key))
        assert non_risolte == [], f"chiavi non risolte sul catalogo reale: {non_risolte}"
    finally:
        bind.close()
        engine.dispose()


def test_0023_ricrea_le_righe_rimosse_dalla_base_senza_doppioni(tmp_path, monkeypatch):
    """Su un DB seminato col catalogo reale e poi riportato allo stato 'base'
    (le righe che la 0023 porterebbe rimosse a mano), l'upgrade ricrea
    esattamente 3 opzioni e N effetti (N = len(_EFFETTI_AGGIUNTI)), nessun
    doppione."""
    modulo = _importa_modulo_0023()
    db_path = tmp_path / "ricostruzione.db"
    monkeypatch_config = monkeypatch
    _semina_catalogo_reale(db_path, monkeypatch_config)

    effetti_dopo_seed = _conta_effetti(db_path)
    _rimuovi_effetti_e_opzioni_0023(db_path, modulo)
    effetti_dopo_rimozione = _conta_effetti(db_path)
    assert effetti_dopo_rimozione == effetti_dopo_seed - len(modulo._EFFETTI_AGGIUNTI)

    connessione = sqlite3.connect(db_path)
    try:
        opzioni_residue = connessione.execute(
            "SELECT COUNT(*) FROM opzione_domanda WHERE domanda_code = 'tipo_pavimento'"
            " AND code IN ('laminato', 'vinilico_lvt', 'moquette')"
        ).fetchone()[0]
    finally:
        connessione.close()
    assert opzioni_residue == 0

    config = _alembic_config(db_path, monkeypatch)
    command.upgrade(config, "0023")

    effetti_dopo_upgrade = _conta_effetti(db_path)
    assert effetti_dopo_upgrade == effetti_dopo_seed

    connessione = sqlite3.connect(db_path)
    try:
        opzioni_ricreate = connessione.execute(
            "SELECT COUNT(*) FROM opzione_domanda WHERE domanda_code = 'tipo_pavimento'"
            " AND code IN ('laminato', 'vinilico_lvt', 'moquette')"
        ).fetchone()[0]
        assert opzioni_ricreate == 3

        # nessun doppione fra gli effetti a bersaglio voce (quelli che la 0023
        # crea): la coppia (opzione_id, tipo_effetto, target_voce_id, tipo_code)
        # e' unica. Scoped a target_voce_id NOT NULL: altri effetti del
        # catalogo (es. moltiplicatore_categoria) condividono legittimamente
        # opzione/tipo con target NULL su piu' righe (tipo_code diverso non
        # incluso nella GROUP BY qui sotto darebbe un falso positivo).
        doppioni = connessione.execute(
            "SELECT opzione_id, tipo_effetto, target_voce_id, tipo_code, COUNT(*) AS n"
            " FROM effetto_opzione WHERE target_voce_id IS NOT NULL"
            " GROUP BY opzione_id, tipo_effetto, target_voce_id, tipo_code HAVING n > 1"
        ).fetchall()
    finally:
        connessione.close()
    assert doppioni == []


def test_0023_e_idempotente_su_un_secondo_upgrade(tmp_path, monkeypatch):
    """Un secondo `upgrade` immediato (stato gia' a testa) non crea doppioni:
    stesso conteggio di effetti prima e dopo."""
    modulo = _importa_modulo_0023()
    db_path = tmp_path / "idempotenza.db"
    _semina_catalogo_reale(db_path, monkeypatch)
    _rimuovi_effetti_e_opzioni_0023(db_path, modulo)

    config = _alembic_config(db_path, monkeypatch)
    command.upgrade(config, "0023")
    dopo_primo = _conta_effetti(db_path)

    command.upgrade(config, "0023")
    dopo_secondo = _conta_effetti(db_path)

    assert dopo_secondo == dopo_primo


def test_0023_su_db_con_seed_gia_passato_non_crea_doppioni(tmp_path, monkeypatch):
    """Un DB dove il seed nuovo e' gia' girato (ha gia' tutto quello che la
    0023 porterebbe) non guadagna righe in piu' dopo l'upgrade."""
    db_path = tmp_path / "gia_seminato_0023.db"
    _semina_catalogo_reale(db_path, monkeypatch)

    prima = _conta_effetti(db_path)
    config = _alembic_config(db_path, monkeypatch)
    command.upgrade(config, "0023")
    dopo = _conta_effetti(db_path)

    assert dopo == prima


def test_0023_fallisce_rumorosamente_su_una_voce_bersaglio_alterata(tmp_path, monkeypatch):
    """Con il catalogo presente, se una voce bersaglio citata da
    `_EFFETTI_AGGIUNTI` ha la descrizione alterata (mojibake/drift), l'upgrade
    solleva `RuntimeError` con risolte/totale e la chiave non risolta — e non
    scrive nulla (conteggi invariati)."""
    modulo = _importa_modulo_0023()
    db_path = tmp_path / "voce_alterata.db"
    _semina_catalogo_reale(db_path, monkeypatch)
    _rimuovi_effetti_e_opzioni_0023(db_path, modulo)

    connessione = sqlite3.connect(db_path)
    try:
        connessione.execute("UPDATE voce SET codice = 'A.6.3-alterata' WHERE codice = 'A.6.3'")
        connessione.commit()
    finally:
        connessione.close()

    prima = _conta_effetti(db_path)
    config = _alembic_config(db_path, monkeypatch)
    with pytest.raises(RuntimeError) as errore:
        command.upgrade(config, "0023")
    assert "risolte" in str(errore.value)
    assert "0023" in str(errore.value)

    dopo = _conta_effetti(db_path)
    assert dopo == prima  # nessuna scrittura prima della guardia


def test_0023_downgrade_toglie_solo_cio_che_upgrade_ha_scritto(tmp_path, monkeypatch):
    """Il downgrade rimuove gli effetti aggiunti e cancella le tre opzioni
    nuove (senza effetti residui): i conteggi tornano esattamente a quelli
    precedenti l'upgrade."""
    modulo = _importa_modulo_0023()
    db_path = tmp_path / "downgrade_0023.db"
    _semina_catalogo_reale(db_path, monkeypatch)
    _rimuovi_effetti_e_opzioni_0023(db_path, modulo)

    prima_upgrade = _conta_effetti(db_path)
    config = _alembic_config(db_path, monkeypatch)
    command.upgrade(config, "0023")
    dopo_upgrade = _conta_effetti(db_path)
    assert dopo_upgrade == prima_upgrade + len(modulo._EFFETTI_AGGIUNTI)

    command.downgrade(config, "0022")
    dopo_downgrade = _conta_effetti(db_path)
    assert dopo_downgrade == prima_upgrade

    connessione = sqlite3.connect(db_path)
    try:
        opzioni_residue = connessione.execute(
            "SELECT COUNT(*) FROM opzione_domanda WHERE domanda_code = 'tipo_pavimento'"
            " AND code IN ('laminato', 'vinilico_lvt', 'moquette')"
        ).fetchone()[0]
        assert connessione.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connessione.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    finally:
        connessione.close()
    assert opzioni_residue == 0

    command.upgrade(config, "0023")
    dopo_riupgrade = _conta_effetti(db_path)
    assert dopo_riupgrade == dopo_upgrade


def test_0023_downgrade_dopo_seed_conserva_effetti_ritarati_o_disattivati(tmp_path, monkeypatch):
    """WR-04 (review 09): seed gia' passato -> upgrade (no-op) -> taratura a
    mano -> downgrade. Un `fattore_quantita` ritarato e un effetto
    disattivato dall'admin restano; le righe identiche alle costanti (qui
    create dal seed, non dall'upgrade) tornano allo stato 0022."""
    modulo = _importa_modulo_0023()
    db_path = tmp_path / "downgrade_dopo_seed_0023.db"
    _semina_catalogo_reale(db_path, monkeypatch)

    config = _alembic_config(db_path, monkeypatch)
    prima_upgrade = _conta_effetti(db_path)
    command.upgrade(config, "0023")
    assert _conta_effetti(db_path) == prima_upgrade  # seed gia' passato: no-op

    def _id_effetto(connessione, riga) -> int:
        domanda_code, opzione_code, tipo_effetto, categoria_code, sotto_key, voce_key, tipo_code, _v = riga
        risultato = connessione.execute(
            "SELECT e.id FROM effetto_opzione e"
            " JOIN opzione_domanda o ON o.id = e.opzione_id"
            " JOIN voce v ON v.id = e.target_voce_id"
            " JOIN sottocategoria s ON s.id = v.sottocategoria_id"
            " JOIN listino l ON l.id = s.listino_id AND l.is_default = 1"
            " WHERE o.domanda_code = ? AND o.code = ? AND e.tipo_effetto = ?"
            " AND s.categoria_code = ? AND (s.codice = ? OR (s.codice IS NULL AND s.nome = ?))"
            " AND (v.codice = ? OR (v.codice IS NULL AND v.descrizione = ?))"
            " AND (e.tipo_code = ? OR (e.tipo_code IS NULL AND ? IS NULL))",
            (
                domanda_code,
                opzione_code,
                tipo_effetto,
                categoria_code,
                sotto_key,
                sotto_key,
                voce_key,
                voce_key,
                tipo_code,
                tipo_code,
            ),
        ).fetchall()
        assert len(risultato) == 1, riga
        return risultato[0][0]

    riga_ritarata = next(r for r in modulo._EFFETTI_AGGIUNTI if r[2] == "fattore_quantita")
    riga_disattivata = next(r for r in modulo._EFFETTI_AGGIUNTI if r[7] is None)
    connessione = sqlite3.connect(db_path)
    try:
        id_ritarato = _id_effetto(connessione, riga_ritarata)
        id_disattivato = _id_effetto(connessione, riga_disattivata)
        connessione.execute(
            "UPDATE effetto_opzione SET valore = ? WHERE id = ?",
            (float(riga_ritarata[7]) + 0.03, id_ritarato),
        )
        connessione.execute("UPDATE effetto_opzione SET attivo = 0 WHERE id = ?", (id_disattivato,))
        connessione.commit()
    finally:
        connessione.close()

    command.downgrade(config, "0022")

    connessione = sqlite3.connect(db_path)
    try:
        superstiti = {
            riga[0]
            for riga in connessione.execute(
                "SELECT id FROM effetto_opzione WHERE id IN (?, ?)", (id_ritarato, id_disattivato)
            ).fetchall()
        }
        assert connessione.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        connessione.close()

    assert superstiti == {id_ritarato, id_disattivato}
    assert _conta_effetti(db_path) == prima_upgrade - len(modulo._EFFETTI_AGGIUNTI) + 2
