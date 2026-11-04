"""Caldaia a gas e pompa di calore sono due interventi diversi.

Fino alla 0032 la pompa di calore accendeva le voci della caldaia a GAS
(allaccio gas, posa caldaia, fornitura caldaia). Qui si dimostra che:

  1. la caldaia a condensazione porta le tre voci del gas e nient'altro;
  2. la pompa di calore porta le sue voci (macchina, bollitore, accumulo,
     posa, linea elettrica, contatore, assistenza muraria, smontaggio della
     vecchia caldaia) e NESSUNA voce del gas;
  3. dall'efficientamento e dalla domanda lavori si arriva allo stesso
     risultato, e scegliere la pompa in entrambi i posti non la conta due volte;
  4. la pompa sostituisce la caldaia anche quando il preset della
     ristrutturazione totale dice "caldaia";
  5. la migrazione 0033 porta un DB seminato prima di questa modifica alla
     forma nuova, torna indietro, e non tocca cio' che l'admin ha cambiato.
"""

from __future__ import annotations

import importlib.util
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from app.db import Base
from app.services.city_resolver import resolve_listino
from app.services.computo import computo_free
from scripts.seed import load_seed_data, seed
from tests.session_factory import sessione_di_test

VOCI_GAS = {"A.8.8", "A.10.3", "D.1.7"}
VOCI_POMPA = {"A.1.17", "A.8.23", "A.8.24", "A.9.7", "A.10.14", "A.10.15", "D.1.11", "D.1.12", "D.1.13"}


@pytest.fixture(scope="module")
def engine():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    with sessione_di_test(engine)() as s:
        seed(s, load_seed_data())
        s.commit()
    return engine


def _voci(engine, risposte, tipo="moderata"):
    with sessione_di_test(engine)() as s:
        listino, _ = resolve_listino(s, "Reggio Emilia")
        return {v.codice: v for v in computo_free(s, listino, mq=85, tipo=tipo, risposte=risposte).voci}


def test_nessun_intervento_nessuna_voce(engine):
    voci = _voci(engine, {"interv_caldaia": "no"})
    assert not (VOCI_GAS | VOCI_POMPA) & set(voci)


def test_caldaia_a_condensazione_solo_voci_gas(engine):
    voci = _voci(engine, {"interv_caldaia": "si"})
    assert VOCI_GAS <= set(voci)
    assert not VOCI_POMPA & set(voci)


def test_pompa_di_calore_senza_voci_gas(engine):
    voci = _voci(engine, {"interv_caldaia": "pompa_calore"})
    assert VOCI_POMPA <= set(voci)
    assert not VOCI_GAS & set(voci)
    assert all(voci[c].quantita == 1 for c in VOCI_POMPA)


def test_pompa_di_calore_costa_piu_della_caldaia(engine):
    """Imponibile delle sole voci dell'intervento, prezzi cliente."""
    gas = sum(v.importo for c, v in _voci(engine, {"interv_caldaia": "si"}).items() if c in VOCI_GAS)
    pompa = sum(
        v.importo for c, v in _voci(engine, {"interv_caldaia": "pompa_calore"}).items() if c in VOCI_POMPA
    )
    assert gas == Decimal("2200")
    # Indagine di mercato 2026: 8-15 mila euro IVA inclusa chiavi in mano per
    # un appartamento. L'imponibile del seed deve starci dentro.
    assert Decimal("8000") <= pompa * Decimal("1.10") <= Decimal("15000")


@pytest.mark.parametrize(
    "risposte",
    [
        {"efficientamento": "si", "interventi_efficientamento": ["pompa_calore"]},
        {
            "interv_caldaia": "pompa_calore",
            "efficientamento": "si",
            "interventi_efficientamento": ["pompa_calore"],
        },
    ],
)
def test_pompa_dall_efficientamento_contata_una_volta(engine, risposte):
    voci = _voci(engine, risposte)
    assert VOCI_POMPA <= set(voci)
    assert all(voci[c].quantita == 1 for c in VOCI_POMPA)
    assert not VOCI_GAS & set(voci)


def test_caldaia_dall_efficientamento(engine):
    voci = _voci(engine, {"efficientamento": "si", "interventi_efficientamento": ["cambio_caldaia"]})
    assert VOCI_GAS <= set(voci)
    assert not VOCI_POMPA & set(voci)


def test_pompa_sostituisce_la_caldaia_del_preset_totale(engine):
    """Nella totale il preset mette `interv_caldaia = si`: se l'utente sceglie la
    pompa dall'efficientamento, la caldaia a gas esce."""
    preset = _voci(engine, {}, tipo="totale")
    assert VOCI_GAS <= set(preset)

    con_pompa = _voci(
        engine,
        {"efficientamento": "si", "interventi_efficientamento": ["pompa_calore"]},
        tipo="totale",
    )
    assert VOCI_POMPA <= set(con_pompa)
    assert not VOCI_GAS & set(con_pompa)


def test_le_voci_nuove_non_entrano_senza_regola(engine):
    """Le voci della pompa non hanno coefficienti v2: senza la grandezza
    restano a zero anche nella ristrutturazione totale."""
    voci = _voci(engine, {}, tipo="totale")
    assert not VOCI_POMPA & set(voci)


# --- migrazione 0033 ------------------------------------------------------------


def _migrazione():
    percorso = (
        Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0033_caldaia_e_pompa_di_calore.py"
    )
    spec = importlib.util.spec_from_file_location("migrazione_0033", percorso)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _istantanea(conn) -> dict:
    return {
        "domanda": conn.execute(
            text("SELECT testo, tipo_controllo, help FROM domanda WHERE code = 'interv_caldaia'")
        ).one(),
        "opzioni": sorted(
            tuple(r)
            for r in conn.execute(
                text(
                    "SELECT domanda_code, code, etichetta, descrizione FROM opzione_domanda"
                    " WHERE (domanda_code = 'interv_caldaia' AND code = 'si')"
                    " OR (domanda_code = 'interventi_efficientamento' AND code = 'cambio_caldaia')"
                )
            )
        ),
        "regole": dict(
            conn.execute(
                text(
                    "SELECT voce_codice, grandezza_code FROM regola_voce"
                    " WHERE voce_codice IN ('A.8.8', 'A.10.3', 'D.1.7')"
                )
            ).all()
        ),
        "grandezza": conn.execute(
            text("SELECT descrizione FROM grandezza WHERE code = 'caldaia_nuova'")
        ).scalar_one(),
    }


def _db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    with sessione_di_test(engine)() as s:
        seed(s, load_seed_data())
        s.commit()
    return engine


def test_migrazione_0033_va_e_torna(monkeypatch):
    m = _migrazione()
    with _db().begin() as conn:
        monkeypatch.setattr(m.op, "get_bind", lambda: conn, raising=False)
        nuovo = _istantanea(conn)
        assert nuovo["domanda"][1] == "scelta_singola"
        assert set(nuovo["regole"].values()) == {"caldaia_gas"}

        m.downgrade()
        vecchio = _istantanea(conn)
        assert vecchio["domanda"][:2] == ("Sostituisci la caldaia?", "toggle")
        assert set(vecchio["regole"].values()) == {"caldaia_nuova"}
        assert ("interventi_efficientamento", "cambio_caldaia", "Cambio caldaia o pompa di calore",
                "Costo una tantum: una caldaia costa quel che costa, non 45 euro al metro quadro.") in vecchio["opzioni"]

        m.upgrade()
        assert _istantanea(conn) == nuovo


def test_migrazione_0033_non_tocca_la_curatela(monkeypatch):
    m = _migrazione()
    with _db().begin() as conn:
        monkeypatch.setattr(m.op, "get_bind", lambda: conn, raising=False)
        m.downgrade()
        conn.execute(text("UPDATE domanda SET testo = 'Caldaia nuova?' WHERE code = 'interv_caldaia'"))
        conn.execute(text("UPDATE regola_voce SET grandezza_code = 'cucina' WHERE voce_codice = 'A.8.8'"))
        m.upgrade()
        testo = conn.execute(text("SELECT testo FROM domanda WHERE code = 'interv_caldaia'")).scalar_one()
        a88 = conn.execute(
            text("SELECT grandezza_code FROM regola_voce WHERE voce_codice = 'A.8.8'")
        ).scalar_one()
        a103 = conn.execute(
            text("SELECT grandezza_code FROM regola_voce WHERE voce_codice = 'A.10.3'")
        ).scalar_one()
    assert testo == "Caldaia nuova?"
    assert a88 == "cucina"
    assert a103 == "caldaia_gas"


def test_seed_su_db_vecchio_aggiunge_le_opzioni(engine):
    """Le opzioni `pompa_calore` le crea il seed anche su un catalogo gia'
    esistente (create-if-missing)."""
    with engine.connect() as conn:
        opzioni = {
            tuple(r)
            for r in conn.execute(
                text("SELECT domanda_code, code FROM opzione_domanda WHERE code = 'pompa_calore'")
            )
        }
    assert opzioni == {("interv_caldaia", "pompa_calore"), ("interventi_efficientamento", "pompa_calore")}
