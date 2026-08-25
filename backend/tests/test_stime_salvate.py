"""E2E tests (RED, TDD) for the saved-estimate slice: POST/GET /me/stime,
GET /me/stime/{id}, over real cookie-jar HTTP calls (`TestClient`).

Covers AUTH-03 (02-07-PLAN.md <must_haves>): snapshot save (never
recomputed, D-09/Pitfall 5), per-user history list, immutable detail,
anti-IDOR (404 not 403, T-07-01), anti-leak of the impresa secret in the
saved snapshot (T-07-02), and 401 without a session (T-07-04).

Until `app/routers/stime_salvate.py` exists, `app.main` fails to include it
and these requests 404 on `/api/v1/me/stime` -> RED as expected.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db as db_module
from app.db import Base
from app.limiter import limiter
from app.main import app

REGISTRAZIONE_URL = "/api/v1/auth/registrati"
LOGOUT_URL = "/api/v1/auth/logout"
STIME_URL = "/api/v1/me/stime"

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


def _stima_payload() -> dict:
    """A StimaResponse-shaped payload, as returned by POST /api/v1/stima."""
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
            {
                "code": "finiture",
                "nome": "Finiture",
                "imponibile_min": "8000.00",
                "imponibile_max": "12000.00",
                "iva_pct": "0.22",
                "iva_min": "1760.00",
                "iva_max": "2640.00",
                "totale_min": "9760.00",
                "totale_max": "14640.00",
            },
            {
                "code": "serramenti",
                "nome": "Serramenti",
                "imponibile_min": "5000.00",
                "imponibile_max": "7000.00",
                "iva_pct": "0.10",
                "iva_min": "500.00",
                "iva_max": "700.00",
                "totale_min": "5500.00",
                "totale_max": "7700.00",
            },
            {
                "code": "prodotti",
                "nome": "Prodotti",
                "imponibile_min": "3000.00",
                "imponibile_max": "4500.00",
                "iva_pct": "0.10",
                "iva_min": "300.00",
                "iva_max": "450.00",
                "totale_min": "3300.00",
                "totale_max": "4950.00",
            },
        ],
        "extra": [
            {"code": "cse", "nome": "CSE/CSP", "importo": "1500.00", "iva_pct": "0.22"},
            {"code": "pratiche", "nome": "Pratiche", "importo": "800.00", "iva_pct": "0.22"},
        ],
        "totale": {
            "imponibile_min": "26000.00",
            "imponibile_max": "38500.00",
            "iva_min": "4120.00",
            "iva_max": "5850.00",
            "totale_min": "30120.00",
            "totale_max": "44350.00",
        },
    }


def _assert_no_forbidden_keys(node) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            assert key not in FORBIDDEN_KEYS, f"forbidden key '{key}' found in response"
            _assert_no_forbidden_keys(value)
    elif isinstance(node, list):
        for item in node:
            _assert_no_forbidden_keys(item)


@pytest.fixture()
def client(monkeypatch, tmp_path):
    # slowapi Limiter is a process-wide singleton (see 02-03-SUMMARY.md) —
    # reset it so /registrati's 5/minute cap doesn't leak between tests.
    limiter.reset()

    db_path = tmp_path / "test_stime_salvate.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine)

    monkeypatch.setattr(db_module, "SessionLocal", testing_session_local)

    import app.dependencies.auth as deps_auth_module
    import app.routers.auth as auth_router_module

    monkeypatch.setattr(deps_auth_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(auth_router_module, "SessionLocal", testing_session_local)

    try:
        import app.routers.stime_salvate as stime_salvate_router_module

        if hasattr(stime_salvate_router_module, "SessionLocal"):
            monkeypatch.setattr(stime_salvate_router_module, "SessionLocal", testing_session_local)
    except ModuleNotFoundError:
        pass

    return TestClient(app)


def _registra(client, email="utente.a@example.com", password="Password123", nome="Utente A"):
    return client.post(REGISTRAZIONE_URL, json={"email": email, "password": password, "nome": nome})


class TestSalvaListaDettaglio:
    def test_post_stime_salva_e_ritorna_201_con_id(self, client):
        _registra(client)

        response = client.post(STIME_URL, json=_stima_payload())

        assert response.status_code == 201
        body = response.json()
        assert "id" in body

    def test_get_stime_lista_le_stime_utente(self, client):
        _registra(client)
        client.post(STIME_URL, json=_stima_payload())

        response = client.get(STIME_URL)

        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)
        assert len(body) == 1
        row = body[0]
        assert row["citta"] == "Reggio Emilia"
        assert row["mq"] == 85
        assert row["tipo"] == "totale"
        assert "created_at" in row
        assert row["totale_min"] is not None
        assert row["totale_max"] is not None

    def test_get_stima_dettaglio_ritorna_snapshot_completo(self, client):
        _registra(client)
        created = client.post(STIME_URL, json=_stima_payload())
        stima_id = created.json()["id"]

        response = client.get(f"{STIME_URL}/{stima_id}")

        assert response.status_code == 200
        body = response.json()
        assert body["input"]["citta"] == "Reggio Emilia"
        assert len(body["categorie"]) == 4
        assert body["totale"]["totale_min"] is not None
        assert body["totale"]["totale_max"] is not None

    def test_dettaglio_salvato_non_contiene_dati_impresa(self, client):
        _registra(client)
        created = client.post(STIME_URL, json=_stima_payload())
        stima_id = created.json()["id"]

        response = client.get(f"{STIME_URL}/{stima_id}")
        raw_text = response.text

        for forbidden in FORBIDDEN_SUBSTRINGS:
            assert forbidden not in raw_text, f"forbidden substring '{forbidden}' leaked in saved snapshot"

        _assert_no_forbidden_keys(response.json())


class TestAntiIdorEAntiSpoofing:
    def test_utente_b_non_puo_leggere_stima_di_utente_a(self, client):
        _registra(client, email="utente.a2@example.com")
        created = client.post(STIME_URL, json=_stima_payload())
        stima_id = created.json()["id"]
        client.post(LOGOUT_URL)

        _registra(client, email="utente.b@example.com")
        response = client.get(f"{STIME_URL}/{stima_id}")

        assert response.status_code == 404

    def test_post_stime_senza_sessione_ritorna_401(self, client):
        response = client.post(STIME_URL, json=_stima_payload())

        assert response.status_code == 401
