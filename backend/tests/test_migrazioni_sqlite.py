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
    assert revisione == ("0019",)


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
