"""API del computo parametrico (Fase 11): preset nel catalogo `/domande`
(INT-03) e route admin `/admin/computo/*` (CUR3-01, RGL-05).

  - il catalogo con `?tipo=` restituisce i default del preset di quel tipo, e
    uno stepper senza fascia di attesa prende il default della sua grandezza;
  - le route admin sono riservate all'admin;
  - export -> import a vuoto non cambia nulla; un file con errori non scrive;
  - l'anteprima porta grandezze e traccia per voce, e niente coefficiente
    impresa.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import app.db as db_module
from app.config import settings
from app.db import Base
from app.limiter import limiter
from app.main import app
from scripts.seed import load_seed_data, seed
from tests.session_factory import sessione_di_test

REGISTRAZIONE_URL = "/api/v1/auth/registrati"
COMPUTO_URL = "/api/v1/admin/computo"
DOMANDE_URL = "/api/v1/domande"
ADMIN_EMAIL = "admin.computo@example.com"


@pytest.fixture()
def client(monkeypatch, tmp_path):
    limiter.reset()
    monkeypatch.setattr(settings, "ADMIN_EMAIL", ADMIN_EMAIL)

    engine = create_engine(
        f"sqlite:///{tmp_path / 'test_computo_api.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)
    with testing_session_local() as s:
        seed(s, load_seed_data())

    monkeypatch.setattr(db_module, "SessionLocal", testing_session_local)
    import app.dependencies.auth as deps_auth_module
    import app.routers.auth as auth_router_module
    import app.routers.domande as domande_router_module

    monkeypatch.setattr(deps_auth_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(auth_router_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(domande_router_module, "SessionLocal", testing_session_local)
    return TestClient(app)


def _registra(client, email):
    risposta = client.post(
        REGISTRAZIONE_URL, json={"email": email, "password": "Password123", "nome": "Computo"}
    )
    assert risposta.status_code in (200, 201), risposta.text


def _default(catalogo, code):
    return next(d for d in catalogo["domande"] if d["code"] == code)["valore_default"]


def test_catalogo_applica_il_preset_del_tipo(client):
    leggera = client.get(DOMANDE_URL, params={"mq": 85, "tipo": "leggera"}).json()
    totale = client.get(DOMANDE_URL, params={"mq": 85, "tipo": "totale"}).json()
    assert _default(leggera, "interv_bagni") == "nessuno"
    assert _default(totale, "interv_bagni") == "tutti"
    assert _default(leggera, "interv_serramenti") == "mantieni"
    assert _default(totale, "interv_serramenti") == "sostituisci"


def test_catalogo_tipo_sconosciuto_si_ignora(client):
    risposta = client.get(DOMANDE_URL, params={"mq": 85, "tipo": "inventato"})
    assert risposta.status_code == 200
    assert _default(risposta.json(), "interv_bagni") == "uno"  # is_default


def test_stepper_senza_attesa_prende_il_default_della_grandezza(client):
    catalogo = client.get(DOMANDE_URL, params={"mq": 85, "tipo": "totale"}).json()
    # Decimal serializzato come stringa, come le attese: il client fa Number().
    assert float(_default(catalogo, "controsoffitti_mq")) == 0


def test_route_admin_riservate(client):
    _registra(client, "utente.computo@example.com")
    assert client.get(f"{COMPUTO_URL}/export.xlsx").status_code == 403
    assert client.get(f"{COMPUTO_URL}/validazione").status_code == 403
    assert (
        client.post(f"{COMPUTO_URL}/anteprima", json={"mq": 85, "tipo": "totale"}).status_code == 403
    )


def test_export_import_a_vuoto_e_validazione(client):
    _registra(client, ADMIN_EMAIL)
    assert client.get(f"{COMPUTO_URL}/validazione").json() == {"errori": []}
    file_bytes = client.get(f"{COMPUTO_URL}/export.xlsx").content
    risposta = client.post(
        f"{COMPUTO_URL}/import",
        params={"applica": "false"},
        files={"file": ("computo.xlsx", file_bytes, "application/octet-stream")},
    )
    assert risposta.status_code == 200, risposta.text
    corpo = risposta.json()
    assert corpo["errori"] == [] and corpo["applicato"] is False
    assert corpo["conteggi"]["regole"] > 100


def test_anteprima_traccia_e_niente_impresa(client):
    _registra(client, ADMIN_EMAIL)
    risposta = client.post(f"{COMPUTO_URL}/anteprima", json={"mq": 85, "tipo": "totale"})
    assert risposta.status_code == 200, risposta.text
    corpo = risposta.json()
    assert corpo["usa_computo"] is True
    smaltimento = next(v for v in corpo["voci"] if v["codice"] == "A.9.6")
    assert "20%" in smaltimento["traccia"]
    assert "impresa" not in risposta.text.lower()


def test_anteprima_tipo_sconosciuto_400(client):
    _registra(client, ADMIN_EMAIL)
    risposta = client.post(f"{COMPUTO_URL}/anteprima", json={"mq": 85, "tipo": "inventato"})
    assert risposta.status_code == 400


def test_post_stima_usa_il_computo(client, monkeypatch):
    """`POST /stima` passa dal computo: il tipo sceglie cosa si fa, e una
    leggera costa molto meno di una totale (prima i tre tipi differivano solo
    per un moltiplicatore)."""
    import app.routers.stima as stima_router_module

    monkeypatch.setattr(stima_router_module, "SessionLocal", db_module.SessionLocal)
    totali = {}
    for tipo in ("leggera", "totale"):
        risposta = client.post(
            "/api/v1/stima", json={"citta": "Reggio Emilia", "mq": 85, "tipo": tipo, "risposte": {}}
        )
        assert risposta.status_code == 200, risposta.text
        totali[tipo] = float(risposta.json()["totale"]["totale_max"])
    assert totali["leggera"] * 2 < totali["totale"]
