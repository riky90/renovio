"""Paywall + anti-IDOR + anti-leak matrix for GET/POST
/me/stime/{id}/dettaglio-pro (03-03-PLAN.md Task 2, PRO-01/PRO-02).

Fixture: engine-swap + client pattern of `test_subscription.py`/
`test_stime_salvate.py`, MA con il seed reale caricato (serve
`Sottocategoria`/`Voce`/`CoefficienteQuantitaVoce` popolate perche' il
dettaglio Pro calcola on-demand dal listino, non da uno snapshot).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import app.db as db_module
from app.db import Base
from app.limiter import limiter
from app.main import app
from scripts.seed import load_seed_data, seed
from tests.session_factory import sessione_di_test

REGISTRAZIONE_URL = "/api/v1/auth/registrati"
LOGOUT_URL = "/api/v1/auth/logout"
STIME_URL = "/api/v1/me/stime"
ATTIVA_PRO_URL = "/api/v1/me/pro/attiva"

FORBIDDEN_SUBSTRINGS = [
    "base_eur_mq",
    "moltiplicatore",
    "coefficiente_impresa",
    "prezzo_impresa",
]

FORBIDDEN_KEYS = {
    "base_eur_mq",
    "moltiplicatore",
    "coefficiente_impresa",
    "prezzo_impresa",
}


def _assert_no_forbidden_keys(node) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            assert key not in FORBIDDEN_KEYS, f"forbidden key '{key}' found in response"
            _assert_no_forbidden_keys(value)
    elif isinstance(node, list):
        for item in node:
            _assert_no_forbidden_keys(item)


def _stima_payload() -> dict:
    """A StimaResponse-shaped payload (same shape as test_stime_salvate.py),
    con citta/mq/tipo reali che risolvono sul listino RE seedato."""
    return {
        "input": {"citta": "Reggio Emilia", "mq": 85, "tipo": "totale"},
        "fallback": False,
        "disclaimer": None,
        "valuta": "EUR",
        "categorie": [
            {
                "code": "edile",
                "nome": "Edile",
                "imponibile_min": "10000.00",
                "imponibile_max": "15000.00",
                "iva_pct": "0.10",
                "iva_min": "1000.00",
                "iva_max": "1500.00",
                "totale_min": "11000.00",
                "totale_max": "16500.00",
            },
        ],
        "extra": [],
        "totale": {
            "imponibile_min": "10000.00",
            "imponibile_max": "15000.00",
            "iva_min": "1000.00",
            "iva_max": "1500.00",
            "totale_min": "11000.00",
            "totale_max": "16500.00",
        },
    }


@pytest.fixture()
def client(monkeypatch, tmp_path):
    limiter.reset()

    db_path = tmp_path / "test_dettaglio_pro_paywall.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)

    with testing_session_local() as s:
        seed(s, load_seed_data())
        s.commit()

    monkeypatch.setattr(db_module, "SessionLocal", testing_session_local)

    import app.dependencies.auth as deps_auth_module
    import app.routers.auth as auth_router_module
    import app.routers.dettaglio_pro as dettaglio_pro_router_module
    import app.routers.stime_salvate as stime_salvate_router_module
    import app.routers.subscription as subscription_router_module

    monkeypatch.setattr(deps_auth_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(auth_router_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(dettaglio_pro_router_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(stime_salvate_router_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(subscription_router_module, "SessionLocal", testing_session_local)

    return TestClient(app)


def _registra(client, email="utente.a@example.com", password="Password123", nome="Utente A"):
    return client.post(REGISTRAZIONE_URL, json={"email": email, "password": password, "nome": nome})


def _crea_stima_pro(client) -> int:
    """Registra un utente Pro e crea una stima salvata; ritorna lo stima_id."""
    _registra(client)
    client.post(ATTIVA_PRO_URL)
    created = client.post(STIME_URL, json=_stima_payload())
    return created.json()["id"]


class TestPaywallMatrix:
    def test_anonimo_401(self, client):
        response = client.get(f"{STIME_URL}/1/dettaglio-pro")
        assert response.status_code == 401

    def test_free_autenticato_403(self, client):
        _registra(client)
        created = client.post(STIME_URL, json=_stima_payload())
        stima_id = created.json()["id"]

        response = client.get(f"{STIME_URL}/{stima_id}/dettaglio-pro")

        assert response.status_code == 403
        assert response.json()["detail"] == "Funzione riservata agli utenti Pro"

    def test_pro_200_con_dettaglio(self, client):
        stima_id = _crea_stima_pro(client)

        response = client.get(f"{STIME_URL}/{stima_id}/dettaglio-pro")

        assert response.status_code == 200
        body = response.json()
        assert len(body["categorie"]) == 4
        edile = next(c for c in body["categorie"] if c["code"] == "A-EDILE")
        assert len(edile["sottocategorie"]) > 0

    def test_post_risposte_anonimo_401(self, client):
        response = client.post(
            f"{STIME_URL}/1/dettaglio-pro/risposte",
            json={"bagni": 1, "porte": 1, "condizionatori": 1},
        )
        assert response.status_code == 401

    def test_post_risposte_free_403(self, client):
        _registra(client)
        created = client.post(STIME_URL, json=_stima_payload())
        stima_id = created.json()["id"]

        response = client.post(
            f"{STIME_URL}/{stima_id}/dettaglio-pro/risposte",
            json={"bagni": 1, "porte": 1, "condizionatori": 1},
        )

        assert response.status_code == 403


class TestAntiIdor:
    def test_get_dettaglio_pro_stima_altrui_404(self, client):
        stima_id = _crea_stima_pro(client)
        client.post(LOGOUT_URL)

        _registra(client, email="utente.b@example.com")
        client.post(ATTIVA_PRO_URL)

        response = client.get(f"{STIME_URL}/{stima_id}/dettaglio-pro")

        assert response.status_code == 404

    def test_post_risposte_stima_altrui_404(self, client):
        stima_id = _crea_stima_pro(client)
        client.post(LOGOUT_URL)

        _registra(client, email="utente.b2@example.com")
        client.post(ATTIVA_PRO_URL)

        response = client.post(
            f"{STIME_URL}/{stima_id}/dettaglio-pro/risposte",
            json={"bagni": 1, "porte": 1, "condizionatori": 1},
        )

        assert response.status_code == 404


class TestAntiLeak:
    def test_dettaglio_pro_non_contiene_dati_impresa(self, client):
        stima_id = _crea_stima_pro(client)

        response = client.get(f"{STIME_URL}/{stima_id}/dettaglio-pro")
        raw_text = response.text

        for forbidden in FORBIDDEN_SUBSTRINGS:
            assert forbidden not in raw_text, f"forbidden substring '{forbidden}' leaked"

        _assert_no_forbidden_keys(response.json())
