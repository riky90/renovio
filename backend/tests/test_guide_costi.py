"""GET /api/v1/guide/costi — le cifre delle guide pubbliche.

Tre cose vanno dimostrate:

  1. LE CIFRE SONO RANGE COERENTI: min <= max, crescono con i metri quadri e
     con il tipo di ristrutturazione, come la stima che le genera.
  2. OGNI GUIDA HA I SUOI SCENARI, con l'etichetta leggibile del livello.
  3. NIENTE PREZZO IMPRESA: l'endpoint e' pubblico, la risposta non deve
     contenere coefficienti ne' prezzi impresa nemmeno nei nomi delle chiavi.
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import app.db as db_module
from app.db import Base
from app.main import app
from app.services import guide_costi
from scripts.seed import load_seed_data, seed
from tests.session_factory import sessione_di_test


@pytest.fixture(autouse=True, scope="module")
def _seeded_db(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db") / "test_guide_costi.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)

    with testing_session_local() as s:
        seed(s, load_seed_data())
        s.commit()

    import app.routers.guide as guide_router

    original_session_local = db_module.SessionLocal
    db_module.SessionLocal = testing_session_local
    guide_router.SessionLocal = testing_session_local
    guide_costi._CACHE.clear()

    yield testing_session_local

    guide_costi._CACHE.clear()
    db_module.SessionLocal = original_session_local
    guide_router.SessionLocal = original_session_local


@pytest.fixture(scope="module")
def dati():
    response = TestClient(app).get("/api/v1/guide/costi")
    assert response.status_code == 200, response.text
    assert "max-age" in response.headers["cache-control"]
    return response.json()


def test_fasce_per_tipo_sono_range_crescenti(dati):
    assert dati["citta_listino"]
    for tipo in ("leggera", "moderata", "totale"):
        fasce = dati["per_tipo"][tipo]
        assert [f["mq"] for f in fasce] == list(guide_costi.MQ_TABELLA)
        for f in fasce:
            assert 0 < f["min"] <= f["max"]
            assert f["min"] % 100 == 0 and f["max"] % 100 == 0
        assert [f["min"] for f in fasce] == sorted(f["min"] for f in fasce)

    def a_85(tipo):
        return next(f for f in dati["per_tipo"][tipo] if f["mq"] == 85)

    assert a_85("leggera")["max"] < a_85("moderata")["max"] < a_85("totale")["max"]


def test_ogni_guida_ha_scenari_con_etichette_leggibili(dati):
    for guida in guide_costi.GUIDE:
        scenari = dati["guide"][guida.code]
        assert scenari, guida.code
        for s in scenari:
            assert 0 < s["min"] <= s["max"]
            assert "medio" not in s["etichetta"].split()
    bagno = {s["etichetta"] for s in dati["guide"]["bagno"]}
    assert "Finiture medie" in bagno


def test_risposta_senza_prezzo_impresa(dati):
    testo = json.dumps(dati).lower()
    assert "impresa" not in testo
    assert "coefficiente" not in testo
