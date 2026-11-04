"""Caldaia a gas, pompa di calore e sistema ibrido sono tre interventi diversi.

Fino alla 0032 la pompa di calore accendeva le voci della caldaia a GAS
(allaccio gas, posa caldaia, fornitura caldaia). Qui si dimostra che:

  1. la caldaia a condensazione porta le tre voci del gas e lo smontaggio
     della vecchia caldaia;
  2. la pompa di calore porta le sue voci (macchina, bollitore, accumulo,
     posa, linea elettrica, contatore, assistenza muraria, smontaggio) e
     NESSUNA voce del gas;
  3. la TAGLIA della pompa e del bollitore segue i m2: 6 kW fino a 80, 8 kW
     fino a 120, 12 kW (e bollitore 300 l) oltre;
  4. con la pompa sui RADIATORI ESISTENTI circa uno su tre diventa un
     ventilradiatore; con radiatori nuovi, pavimento radiante o ibrido no;
  5. il SISTEMA IBRIDO porta caldaia a gas + modulo pompa 4 kW, linea
     elettrica e assistenza muraria, senza bollitore, puffer, contatore;
  6. efficientamento e domanda lavori danno lo stesso risultato, nessuna
     voce e' contata due volte, e la pompa pura vince su caldaia e ibrido;
  7. le migrazioni 0033 e 0034 vanno e tornano e non toccano la curatela.
"""

from __future__ import annotations

import importlib.util
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import bindparam, create_engine, text

from app.db import Base
from app.services.city_resolver import resolve_listino
from app.services.computo import computo_free
from scripts.seed import load_seed_data, seed
from tests.session_factory import sessione_di_test

VOCI_GAS = {"A.8.8", "A.10.3", "D.1.7"}
SMONTAGGIO = {"A.1.17"}
#: Pompa pura a 85 m² (taglia 8 kW, bollitore 200 l).
VOCI_POMPA = {"A.8.23", "A.8.24", "A.9.7", "A.10.14", "A.10.15", "D.1.11", "D.1.12", "D.1.13"}
TAGLIE = {"D.1.11", "D.1.14", "D.1.15", "D.1.12", "D.1.16"}
VOCI_RADIATORI = {"D.1.18", "A.10.17"}
VOCI_IBRIDO = {"D.1.17", "A.10.16"}
#: Solo della pompa pura: l'ibrido non le ha.
SOLO_POMPA = {"A.8.24", "A.10.14", "A.10.15", "D.1.13"} | TAGLIE
TUTTE = VOCI_GAS | SMONTAGGIO | VOCI_POMPA | TAGLIE | VOCI_RADIATORI | VOCI_IBRIDO


@pytest.fixture(scope="module")
def engine():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    with sessione_di_test(engine)() as s:
        seed(s, load_seed_data())
        s.commit()
    return engine


def _voci(engine, risposte, tipo="moderata", mq=85):
    with sessione_di_test(engine)() as s:
        listino, _ = resolve_listino(s, "Reggio Emilia")
        return {v.codice: v for v in computo_free(s, listino, mq=mq, tipo=tipo, risposte=risposte).voci}


def _importo(voci, codici):
    return sum((v.importo for c, v in voci.items() if c in codici), Decimal("0"))


# --- 1-2. caldaia e pompa ---------------------------------------------------------


def test_nessun_intervento_nessuna_voce(engine):
    voci = _voci(engine, {"interv_caldaia": "no"})
    assert not TUTTE & set(voci)


def test_caldaia_a_condensazione_voci_gas_e_smontaggio(engine):
    voci = _voci(engine, {"interv_caldaia": "si"})
    assert VOCI_GAS | SMONTAGGIO <= set(voci)
    assert not (VOCI_POMPA | TAGLIE | VOCI_RADIATORI | VOCI_IBRIDO) & set(voci)
    assert voci["A.1.17"].quantita == 1


def test_pompa_di_calore_senza_voci_gas(engine):
    voci = _voci(engine, {"interv_caldaia": "pompa_calore"})
    assert VOCI_POMPA | SMONTAGGIO <= set(voci)
    assert not (VOCI_GAS | VOCI_IBRIDO) & set(voci)
    assert all(voci[c].quantita == 1 for c in VOCI_POMPA | SMONTAGGIO)


def test_pompa_di_calore_costa_piu_della_caldaia(engine):
    """Imponibile delle sole voci dell'intervento, prezzi cliente, 85 m²."""
    gas = _importo(_voci(engine, {"interv_caldaia": "si"}), VOCI_GAS)
    pompa = _importo(
        _voci(engine, {"interv_caldaia": "pompa_calore", "interv_riscaldamento": "radiatori"}),
        VOCI_POMPA | SMONTAGGIO,
    )
    assert gas == Decimal("2200")
    # Indagine di mercato 2026: 8-15 mila euro IVA inclusa chiavi in mano per
    # un appartamento. L'imponibile del seed deve starci dentro.
    assert Decimal("8000") <= pompa * Decimal("1.10") <= Decimal("15000")


# --- 3. taglie ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mq,attese",
    [
        (60, {"D.1.14", "D.1.12"}),
        (80, {"D.1.14", "D.1.12"}),
        (81, {"D.1.11", "D.1.12"}),
        (120, {"D.1.11", "D.1.12"}),
        (150, {"D.1.15", "D.1.16"}),
    ],
)
def test_taglia_segue_i_metri_quadri(engine, mq, attese):
    voci = _voci(engine, {"interv_caldaia": "pompa_calore"}, mq=mq)
    assert TAGLIE & set(voci) == attese
    assert all(voci[c].quantita == 1 for c in attese)


def test_taglie_spente_senza_pompa(engine):
    for mq in (60, 100, 150):
        assert not TAGLIE & set(_voci(engine, {"interv_caldaia": "si"}, mq=mq))


# --- 4. radiatori esistenti -------------------------------------------------------------


@pytest.mark.parametrize("riscaldamento", ["nessuno", "smonta_rimonta"])
def test_pompa_sui_radiatori_esistenti_adegua_un_terzo(engine, riscaldamento):
    voci = _voci(engine, {"interv_caldaia": "pompa_calore", "interv_riscaldamento": riscaldamento})
    # 85 m²: 3 locali + 1 bagno + 1 = 5 radiatori, un terzo arrotondato in su = 2.
    assert voci["D.1.18"].quantita == 2
    assert voci["A.10.17"].quantita == 2


@pytest.mark.parametrize("riscaldamento", ["radiatori", "pavimento"])
def test_terminali_nuovi_niente_adeguamento(engine, riscaldamento):
    voci = _voci(
        engine,
        {"interv_caldaia": "pompa_calore", "interv_riscaldamento": riscaldamento, "interv_pavimenti": "rifai"},
    )
    assert not VOCI_RADIATORI & set(voci)


def test_adeguamento_cresce_con_la_casa(engine):
    piccola = _voci(engine, {"interv_caldaia": "pompa_calore"}, mq=50)["D.1.18"].quantita
    grande = _voci(engine, {"interv_caldaia": "pompa_calore"}, mq=150)["D.1.18"].quantita
    assert 1 <= piccola < grande


# --- 5. sistema ibrido ----------------------------------------------------------------


@pytest.mark.parametrize(
    "risposte",
    [
        {"interv_caldaia": "ibrido"},
        {"efficientamento": "si", "interventi_efficientamento": ["ibrido"]},
        {"interv_caldaia": "ibrido", "efficientamento": "si", "interventi_efficientamento": ["ibrido"]},
        {"interv_caldaia": "si", "efficientamento": "si", "interventi_efficientamento": ["ibrido"]},
    ],
)
def test_ibrido_caldaia_piu_modulo_pompa(engine, risposte):
    voci = _voci(engine, risposte)
    assert VOCI_GAS | VOCI_IBRIDO | SMONTAGGIO | {"A.8.23", "A.9.7"} <= set(voci)
    assert not (SOLO_POMPA | VOCI_RADIATORI) & set(voci)
    assert all(voci[c].quantita == 1 for c in VOCI_GAS | VOCI_IBRIDO | SMONTAGGIO | {"A.8.23", "A.9.7"})


def test_ibrido_costa_fra_caldaia_e_pompa(engine):
    gas = _importo(_voci(engine, {"interv_caldaia": "si"}), TUTTE)
    ibrido = _importo(_voci(engine, {"interv_caldaia": "ibrido"}), TUTTE)
    pompa = _importo(_voci(engine, {"interv_caldaia": "pompa_calore"}), TUTTE)
    assert gas < ibrido < pompa


def test_pompa_pura_vince_sull_ibrido(engine):
    voci = _voci(
        engine,
        {"interv_caldaia": "pompa_calore", "efficientamento": "si", "interventi_efficientamento": ["ibrido"]},
    )
    assert VOCI_POMPA <= set(voci)
    assert not (VOCI_GAS | VOCI_IBRIDO) & set(voci)
    assert all(voci[c].quantita == 1 for c in {"A.8.23", "A.9.7", "A.1.17"})


# --- 6. efficientamento, preset, doppi conteggi -----------------------------------------


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
    assert all(voci[c].quantita == 1 for c in VOCI_POMPA | SMONTAGGIO)
    assert not VOCI_GAS & set(voci)


def test_caldaia_dall_efficientamento(engine):
    voci = _voci(engine, {"efficientamento": "si", "interventi_efficientamento": ["cambio_caldaia"]})
    assert VOCI_GAS | SMONTAGGIO <= set(voci)
    assert not (VOCI_POMPA | VOCI_IBRIDO) & set(voci)


def test_pompa_sostituisce_la_caldaia_del_preset_totale(engine):
    """Nella totale il preset mette `interv_caldaia = si`: se l'utente sceglie la
    pompa dall'efficientamento, la caldaia a gas esce."""
    preset = _voci(engine, {}, tipo="totale")
    assert VOCI_GAS | SMONTAGGIO <= set(preset)

    con_pompa = _voci(
        engine,
        {"efficientamento": "si", "interventi_efficientamento": ["pompa_calore"]},
        tipo="totale",
    )
    assert VOCI_POMPA <= set(con_pompa)
    assert not VOCI_GAS & set(con_pompa)
    assert con_pompa["A.1.17"].quantita == 1


def test_le_voci_della_pompa_non_entrano_senza_scelta(engine):
    """Le voci nuove hanno coefficienti v2 a zero: senza la grandezza restano
    fuori anche nella ristrutturazione totale (che ha solo la caldaia)."""
    voci = _voci(engine, {}, tipo="totale")
    assert not (VOCI_POMPA | TAGLIE | VOCI_RADIATORI | VOCI_IBRIDO) & set(voci)


def test_seed_crea_le_opzioni(engine):
    with engine.connect() as conn:
        opzioni = {
            tuple(r)
            for r in conn.execute(
                text(
                    "SELECT domanda_code, code FROM opzione_domanda"
                    " WHERE code IN ('pompa_calore', 'ibrido')"
                )
            )
        }
    assert opzioni == {
        ("interv_caldaia", "pompa_calore"),
        ("interventi_efficientamento", "pompa_calore"),
        ("interv_caldaia", "ibrido"),
        ("interventi_efficientamento", "ibrido"),
    }


# --- 7. migrazioni 0033 e 0034 ------------------------------------------------------------


def _migrazione(nome):
    percorso = Path(__file__).resolve().parents[1] / "alembic" / "versions" / f"{nome}.py"
    spec = importlib.util.spec_from_file_location(f"migrazione_{nome}", percorso)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


M0033 = "0033_caldaia_e_pompa_di_calore"
M0034 = "0034_pompa_taglie_radiatori_ibrido"
VOCI_MIGRATE = ("A.8.8", "A.10.3", "D.1.7", "A.1.17", "A.8.23", "A.9.7", "D.1.11", "D.1.12")


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
                    " WHERE code IN ('si', 'cambio_caldaia', 'pompa_calore')"
                    " AND domanda_code IN ('interv_caldaia', 'interventi_efficientamento')"
                )
            )
        ),
        "regole": sorted(
            tuple(r)
            for r in conn.execute(
                text(
                    "SELECT voce_codice, tipo_regola, grandezza_code, condizione_grandezza_code, nota"
                    " FROM regola_voce WHERE voce_codice IN :voci"
                ).bindparams(bindparam("voci", expanding=True)),
                {"voci": list(VOCI_MIGRATE)},
            )
        ),
        "grandezza": conn.execute(
            text("SELECT descrizione FROM grandezza WHERE code = 'caldaia_nuova'")
        ).scalar_one(),
        "scaglioni": sorted(
            (r[0], str(r[1]), str(r[2]))
            for r in conn.execute(
                text(
                    "SELECT voce_codice, fino_a, valore FROM scaglione_regola"
                    " WHERE voce_codice IN ('D.1.11', 'D.1.12')"
                )
            )
        ),
    }


def _db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    with sessione_di_test(engine)() as s:
        seed(s, load_seed_data())
        s.commit()
    return engine


def _con(conn, monkeypatch, *migrazioni):
    for m in migrazioni:
        monkeypatch.setattr(m.op, "get_bind", lambda: conn, raising=False)
    return migrazioni


def _regola(conn, voce):
    return conn.execute(
        text(
            "SELECT tipo_regola, grandezza_code, condizione_grandezza_code FROM regola_voce"
            " WHERE voce_codice = :v"
        ),
        {"v": voce},
    ).one()


def test_migrazioni_vanno_e_tornano(monkeypatch):
    with _db().begin() as conn:
        m33, m34 = _con(conn, monkeypatch, _migrazione(M0033), _migrazione(M0034))
        nuovo = _istantanea(conn)
        assert nuovo["domanda"][1] == "scelta_singola"
        assert _regola(conn, "D.1.11") == ("scaglioni", "mq", "pompa_calore")
        assert _regola(conn, "A.1.17")[1] == "generatore_nuovo"

        m34.downgrade()
        dopo_0033 = _istantanea(conn)
        assert _regola(conn, "D.1.11") == ("grandezza", "pompa_calore", None)
        assert {_regola(conn, v)[1] for v in ("A.1.17", "A.8.23", "A.9.7")} == {"pompa_calore"}

        m33.downgrade()
        vecchio = _istantanea(conn)
        assert vecchio["domanda"][:2] == ("Sostituisci la caldaia?", "toggle")
        assert {_regola(conn, v)[1] for v in ("A.8.8", "A.10.3", "D.1.7")} == {"caldaia_nuova"}
        assert (
            "interventi_efficientamento", "cambio_caldaia", "Cambio caldaia o pompa di calore",
            "Costo una tantum: una caldaia costa quel che costa, non 45 euro al metro quadro.",
        ) in vecchio["opzioni"]

        m33.upgrade()
        assert _istantanea(conn) == dopo_0033
        m34.upgrade()
        assert _istantanea(conn) == nuovo


def test_0034_aggiunge_gli_scaglioni_mancanti(monkeypatch):
    """Un DB alla 0033 ha D.1.11 e D.1.12 senza scaglioni: la 0034 li crea."""
    with _db().begin() as conn:
        (m34,) = _con(conn, monkeypatch, _migrazione(M0034))
        attesi = _istantanea(conn)["scaglioni"]
        m34.downgrade()
        conn.execute(text("DELETE FROM scaglione_regola WHERE voce_codice IN ('D.1.11', 'D.1.12')"))
        m34.upgrade()
        assert _istantanea(conn)["scaglioni"] == attesi
        assert len(attesi) == 5
        m34.upgrade()  # una seconda volta non duplica
        assert _istantanea(conn)["scaglioni"] == attesi


def test_migrazioni_non_toccano_la_curatela(monkeypatch):
    with _db().begin() as conn:
        m33, m34 = _con(conn, monkeypatch, _migrazione(M0033), _migrazione(M0034))
        m34.downgrade()
        m33.downgrade()
        conn.execute(text("UPDATE domanda SET testo = 'Caldaia nuova?' WHERE code = 'interv_caldaia'"))
        conn.execute(text("UPDATE regola_voce SET grandezza_code = 'cucina' WHERE voce_codice = 'A.8.8'"))
        m33.upgrade()
        conn.execute(text("UPDATE regola_voce SET grandezza_code = 'cucina' WHERE voce_codice = 'A.8.23'"))
        conn.execute(text("UPDATE regola_voce SET grandezza_code = 'mq' WHERE voce_codice = 'D.1.11'"))
        m34.upgrade()
        testo = conn.execute(text("SELECT testo FROM domanda WHERE code = 'interv_caldaia'")).scalar_one()
        assert testo == "Caldaia nuova?"
        assert _regola(conn, "A.8.8")[1] == "cucina"
        assert _regola(conn, "A.10.3")[1] == "caldaia_gas"
        assert _regola(conn, "A.8.23")[1] == "cucina"
        assert _regola(conn, "A.9.7")[1] == "pdc_esterna"
        assert _regola(conn, "D.1.11") == ("grandezza", "mq", None)
