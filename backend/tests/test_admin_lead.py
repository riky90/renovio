"""E2E tests (RED->GREEN, TDD) per la dashboard lead admin (ADM-04, D-17,
04-04-PLAN.md): GET /admin/lead (list con filtri citta/stato), GET
/admin/lead/{id} (detail), PATCH /admin/lead/{id} (stato/nota).

Copre: 403 su ogni route per non-admin (T-04-15); nessun dato impresa nelle
risposte (T-04-16, D-22); filtri citta/stato (D-17); 404 (non leak) su id
inesistente.

Fino a quando `routers/admin/lead.py` non ha le route implementate, queste
richieste ritornano 404 sulla route stessa (nessuna route registrata) ->
RED come atteso.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db as db_module
from app.config import settings
from app.db import Base
from app.limiter import limiter
from app.main import app

REGISTRAZIONE_URL = "/api/v1/auth/registrati"
LEAD_URL = "/api/v1/admin/lead"

ADMIN_EMAIL = "admin.lead@example.com"

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


@pytest.fixture()
def client(monkeypatch, tmp_path):
    limiter.reset()
    monkeypatch.setattr(settings, "ADMIN_EMAIL", ADMIN_EMAIL)

    db_path = tmp_path / "test_admin_lead.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine)

    monkeypatch.setattr(db_module, "SessionLocal", testing_session_local)

    import app.dependencies.auth as deps_auth_module
    import app.routers.auth as auth_router_module

    monkeypatch.setattr(deps_auth_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(auth_router_module, "SessionLocal", testing_session_local)

    try:
        import app.routers.admin.lead as admin_lead_router_module

        if hasattr(admin_lead_router_module, "SessionLocal"):
            monkeypatch.setattr(admin_lead_router_module, "SessionLocal", testing_session_local)
    except ModuleNotFoundError:
        pass

    return TestClient(app), testing_session_local


def _registra_admin(client, email=ADMIN_EMAIL, nome="Admin Lead"):
    return client.post(REGISTRAZIONE_URL, json={"email": email, "password": "Password123", "nome": nome})


def _registra_user(client, email="utente.normale@example.com", nome="Utente Normale"):
    return client.post(REGISTRAZIONE_URL, json={"email": email, "password": "Password123", "nome": nome})


def _seed_lead(session_factory, *, citta="Reggio Emilia", stato="nuovo", nome="Mario Rossi") -> int:
    from app.models.lead import Lead

    with session_factory() as session:
        lead = Lead(
            user_id=1,
            nome=nome,
            email="mario.rossi@example.com",
            telefono="3331234567",
            preferenza_contatto="email",
            fascia_oraria="mattina",
            messaggio="Vorrei un sopralluogo.",
            citta=citta,
            mq=85,
            tipo="totale",
            totale_min=Decimal("30120.00"),
            totale_max=Decimal("44350.00"),
            stato=stato,
        )
        session.add(lead)
        session.commit()
        session.refresh(lead)
        return lead.id


class TestAdminLeadGuard:
    def test_get_lead_403_per_non_admin(self, client):
        c, _ = client
        _registra_user(c)
        response = c.get(LEAD_URL)
        assert response.status_code == 403

    def test_get_lead_401_senza_sessione(self, client):
        c, _ = client
        response = c.get(LEAD_URL)
        assert response.status_code == 401

    def test_patch_lead_403_per_non_admin(self, client):
        c, session_factory = client
        _registra_user(c)
        lead_id = _seed_lead(session_factory)
        response = c.patch(f"{LEAD_URL}/{lead_id}", json={"stato": "gestito"})
        assert response.status_code == 403


class TestAdminListLeads:
    def test_admin_list_leads(self, client):
        c, session_factory = client
        _registra_admin(c)
        _seed_lead(session_factory, citta="Reggio Emilia")

        response = c.get(LEAD_URL)
        assert response.status_code == 200
        rows = response.json()
        assert len(rows) == 1
        row = rows[0]
        assert row["citta"] == "Reggio Emilia"
        assert row["nome"] == "Mario Rossi"
        assert row["email"] == "mario.rossi@example.com"
        assert row["totale_min"] is not None
        assert row["totale_max"] is not None
        assert row["stato"] == "nuovo"


class TestAdminFilterLeads:
    def test_admin_filter_leads_per_citta(self, client):
        c, session_factory = client
        _registra_admin(c)
        _seed_lead(session_factory, citta="Reggio Emilia")
        _seed_lead(session_factory, citta="Parma")

        response = c.get(LEAD_URL, params={"citta": "Parma"})
        assert response.status_code == 200
        rows = response.json()
        assert len(rows) == 1
        assert rows[0]["citta"] == "Parma"

    def test_admin_filter_leads_per_stato(self, client):
        c, session_factory = client
        _registra_admin(c)
        _seed_lead(session_factory, stato="nuovo")
        _seed_lead(session_factory, stato="gestito")

        response = c.get(LEAD_URL, params={"stato": "nuovo"})
        assert response.status_code == 200
        rows = response.json()
        assert len(rows) == 1
        assert rows[0]["stato"] == "nuovo"


class TestAdminLeadDetail:
    def test_admin_lead_detail(self, client):
        c, session_factory = client
        _registra_admin(c)
        lead_id = _seed_lead(session_factory)

        response = c.get(f"{LEAD_URL}/{lead_id}")
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == lead_id
        assert body["mq"] == 85
        assert body["tipo"] == "totale"
        assert float(body["totale_min"]) == 30120.00
        assert float(body["totale_max"]) == 44350.00

    def test_admin_lead_detail_404_se_inesistente(self, client):
        c, _ = client
        _registra_admin(c)

        response = c.get(f"{LEAD_URL}/999999")
        assert response.status_code == 404


class TestAdminPatchLead:
    def test_admin_patch_lead_stato_e_nota(self, client):
        c, session_factory = client
        _registra_admin(c)
        lead_id = _seed_lead(session_factory)

        response = c.patch(f"{LEAD_URL}/{lead_id}", json={"stato": "gestito", "nota": "Ricontattare lunedi"})
        assert response.status_code == 200
        body = response.json()
        assert body["stato"] == "gestito"
        assert body["nota"] == "Ricontattare lunedi"

        rigetto = c.get(f"{LEAD_URL}/{lead_id}")
        assert rigetto.json()["stato"] == "gestito"
        assert rigetto.json()["nota"] == "Ricontattare lunedi"

    def test_admin_patch_lead_404_se_inesistente(self, client):
        c, _ = client
        _registra_admin(c)

        response = c.patch(f"{LEAD_URL}/999999", json={"stato": "gestito"})
        assert response.status_code == 404


class TestAdminLeadNoImpresaLeak:
    def test_admin_lead_no_impresa_leak(self, client):
        c, session_factory = client
        _registra_admin(c)
        _seed_lead(session_factory)

        list_response = c.get(LEAD_URL)
        _assert_no_forbidden_keys(list_response.json())

        lead_id = list_response.json()[0]["id"]
        detail_response = c.get(f"{LEAD_URL}/{lead_id}")
        _assert_no_forbidden_keys(detail_response.json())
