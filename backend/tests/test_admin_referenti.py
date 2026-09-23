"""E2E tests (RED->GREEN, TDD) per il CRUD referenti admin (ADM-04, D-15/D-16,
04-04-PLAN.md): GET/POST /admin/referenti, PATCH/DELETE /admin/referenti/{id}.

Copre: 403 su ogni route per non-admin (T-04-15); nessun dato impresa nelle
risposte referenti (T-04-16); 404 su id inesistente; integrazione con la
risoluzione destinatario lead (04-01, priorita).

Fino a quando `routers/admin/referenti.py` non ha le route implementate,
queste richieste ritornano 404 sulla route stessa -> RED come atteso.
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
from tests.session_factory import sessione_di_test

REGISTRAZIONE_URL = "/api/v1/auth/registrati"
REFERENTI_URL = "/api/v1/admin/referenti"

ADMIN_EMAIL = "admin.referenti@example.com"

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

    db_path = tmp_path / "test_admin_referenti.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)

    monkeypatch.setattr(db_module, "SessionLocal", testing_session_local)

    import app.dependencies.auth as deps_auth_module
    import app.routers.auth as auth_router_module

    monkeypatch.setattr(deps_auth_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(auth_router_module, "SessionLocal", testing_session_local)

    try:
        import app.routers.admin.referenti as admin_referenti_router_module

        if hasattr(admin_referenti_router_module, "SessionLocal"):
            monkeypatch.setattr(admin_referenti_router_module, "SessionLocal", testing_session_local)
    except ModuleNotFoundError:
        pass

    return TestClient(app), testing_session_local


def _registra_admin(client, email=ADMIN_EMAIL, nome="Admin Referenti"):
    return client.post(REGISTRAZIONE_URL, json={"email": email, "password": "Password123", "nome": nome})


def _registra_user(client, email="utente.normale@example.com", nome="Utente Normale"):
    return client.post(REGISTRAZIONE_URL, json={"email": email, "password": "Password123", "nome": nome})


def _seed_listino(session_factory, *, nome="Listino Parma", citta="Parma", is_default=False) -> int:
    from app.models.listino import Listino

    with session_factory() as session:
        listino = Listino(nome=nome, citta_riferimento=citta, is_default=is_default)
        session.add(listino)
        session.commit()
        session.refresh(listino)
        return listino.id


def _referente_payload(listino_id: int, **overrides) -> dict:
    payload = {
        "listino_id": listino_id,
        "nome": "Mario Referente",
        "email": "mario.referente@example.com",
        "telefono": "3339876543",
        "attivo": True,
        "priorita": 0,
    }
    payload.update(overrides)
    return payload


class TestAdminReferentiGuard:
    def test_get_referenti_403_per_non_admin(self, client):
        c, _ = client
        _registra_user(c)
        response = c.get(REFERENTI_URL)
        assert response.status_code == 403

    def test_get_referenti_401_senza_sessione(self, client):
        c, _ = client
        response = c.get(REFERENTI_URL)
        assert response.status_code == 401

    def test_post_referenti_403_per_non_admin(self, client):
        c, session_factory = client
        _registra_user(c)
        listino_id = _seed_listino(session_factory)
        response = c.post(REFERENTI_URL, json=_referente_payload(listino_id))
        assert response.status_code == 403

    def test_patch_referenti_403_per_non_admin(self, client):
        c, _ = client
        _registra_user(c)
        response = c.patch(f"{REFERENTI_URL}/1", json={"attivo": False})
        assert response.status_code == 403

    def test_delete_referenti_403_per_non_admin(self, client):
        c, _ = client
        _registra_user(c)
        response = c.delete(f"{REFERENTI_URL}/1")
        assert response.status_code == 403


class TestAdminReferentiCrud:
    def test_create_list_patch_delete_referente(self, client):
        c, session_factory = client
        _registra_admin(c)
        listino_id = _seed_listino(session_factory)

        create_response = c.post(REFERENTI_URL, json=_referente_payload(listino_id))
        assert create_response.status_code in (200, 201)
        created = create_response.json()
        assert "id" in created
        assert created["email"] == "mario.referente@example.com"
        assert created["attivo"] is True
        assert created["priorita"] == 0

        list_response = c.get(REFERENTI_URL)
        assert list_response.status_code == 200
        emails = [r["email"] for r in list_response.json()]
        assert "mario.referente@example.com" in emails

        patch_response = c.patch(
            f"{REFERENTI_URL}/{created['id']}",
            json={"attivo": False, "priorita": 5},
        )
        assert patch_response.status_code == 200
        patched = patch_response.json()
        assert patched["attivo"] is False
        assert patched["priorita"] == 5

        delete_response = c.delete(f"{REFERENTI_URL}/{created['id']}")
        assert delete_response.status_code in (200, 204)

        after_delete = c.get(REFERENTI_URL).json()
        assert all(r["id"] != created["id"] for r in after_delete)

    def test_patch_referente_404_se_inesistente(self, client):
        c, _ = client
        _registra_admin(c)

        response = c.patch(f"{REFERENTI_URL}/999999", json={"attivo": False})
        assert response.status_code == 404

    def test_delete_referente_404_se_inesistente(self, client):
        c, _ = client
        _registra_admin(c)

        response = c.delete(f"{REFERENTI_URL}/999999")
        assert response.status_code == 404


class TestAdminReferentiNoImpresaLeak:
    def test_admin_referenti_no_impresa_leak(self, client):
        c, session_factory = client
        _registra_admin(c)
        listino_id = _seed_listino(session_factory)
        c.post(REFERENTI_URL, json=_referente_payload(listino_id))

        response = c.get(REFERENTI_URL)
        _assert_no_forbidden_keys(response.json())


class TestAdminReferentiIntegrazioneLead:
    def test_referente_creato_da_admin_e_risolto_dal_flusso_lead(self, client):
        """Un Referente attivo creato via CRUD admin viene risolto da
        `resolve_referente` (04-01) per la citta del suo listino, coerente
        con l'invio email del lead."""
        c, session_factory = client
        _registra_admin(c)
        listino_id = _seed_listino(session_factory, nome="Listino Torino", citta="Torino")

        from app.models.catalogo import ComuneListino
        from slugify import slugify

        with session_factory() as session:
            comune = ComuneListino(
                comune_nome="Torino",
                comune_slug=slugify("Torino"),
                listino_id=listino_id,
            )
            session.add(comune)
            session.commit()

        create_response = c.post(REFERENTI_URL, json=_referente_payload(listino_id, priorita=0))
        assert create_response.status_code in (200, 201)
        created = create_response.json()

        from app.services.lead_service import resolve_referente

        with session_factory() as session:
            referente = resolve_referente(session, "Torino")
            assert referente is not None
            assert referente.id == created["id"]
            assert referente.email == "mario.referente@example.com"
