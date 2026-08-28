"""Domain-guard test (D-10/D-22, 04-02-PLAN.md): gli endpoint NON-admin
(/api/v1/stima) continuano a non esporre coefficiente_impresa/base_eur_mq,
mentre gli endpoint /admin/listini (dietro require_admin) li espongono
DELIBERATAMENTE (D-10 — l'admin e' l'unica eccezione all'anti-leak).

Complementare a `test_no_leak.py` (Fase 1, solo lato pubblico): questo
file prova ENTRAMBI i lati del fork di schema (04-RESEARCH.md Pattern 1).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db as db_module
from app.config import settings
from app.db import Base
from app.limiter import limiter
from app.main import app
from scripts.seed import load_seed_data, seed

REGISTRAZIONE_URL = "/api/v1/auth/registrati"
STIMA_URL = "/api/v1/stima"
LISTINI_URL = "/api/v1/admin/listini"

ADMIN_EMAIL = "admin.noleak@example.com"

FORBIDDEN_SUBSTRINGS = [
    "moltiplicatore",
    "prezzo_impresa",
]


@pytest.fixture()
def client(monkeypatch, tmp_path):
    limiter.reset()
    monkeypatch.setattr(settings, "ADMIN_EMAIL", ADMIN_EMAIL)

    db_path = tmp_path / "test_no_leak_admin.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine)

    with testing_session_local() as s:
        seed(s, load_seed_data())

    monkeypatch.setattr(db_module, "SessionLocal", testing_session_local)

    import app.dependencies.auth as deps_auth_module
    import app.routers.auth as auth_router_module
    import app.routers.stima as stima_router_module

    monkeypatch.setattr(deps_auth_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(auth_router_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(stima_router_module, "SessionLocal", testing_session_local)

    return TestClient(app)


def _registra_admin(client, email=ADMIN_EMAIL, nome="Admin NoLeak"):
    return client.post(REGISTRAZIONE_URL, json={"email": email, "password": "Password123", "nome": nome})


def test_endpoint_pubblico_non_espone_coefficiente_impresa(client):
    response = client.post(STIMA_URL, json={"citta": "Reggio Emilia", "mq": 85, "tipo": "totale"})
    assert response.status_code == 200

    raw_text = response.text
    assert "coefficiente_impresa" not in raw_text
    assert "base_eur_mq" not in raw_text
    for forbidden in FORBIDDEN_SUBSTRINGS:
        assert forbidden not in raw_text


def test_endpoint_admin_espone_deliberatamente_coefficiente_impresa(client):
    _registra_admin(client)
    listini = client.get(LISTINI_URL).json()
    listino_id = next(r["id"] for r in listini if r["citta_riferimento"] == "Reggio Emilia")

    response = client.get(f"{LISTINI_URL}/{listino_id}/categorie")
    assert response.status_code == 200

    raw_text = response.text
    assert "coefficiente_impresa" in raw_text
    assert "base_eur_mq" in raw_text
