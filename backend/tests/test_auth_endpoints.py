"""E2E tests (RED, TDD) for the auth HTTP slice: registrazione/login/me/logout
+ admin guard, over real cookie-jar HTTP calls (`TestClient`).

Covers AUTH-01/03/04 end-to-end (02-03-PLAN.md <must_haves>): httpOnly
session cookie on register/login, server-side revoke on logout, generic
error message on login failure (no user enumeration, T-03-02), duplicate
email on register (T-03-02), admin route 200/403 (T-03-03, AUTH-04).

Until `app/routers/auth.py`/`app/routers/admin.py` exist this file fails to
even import (`ModuleNotFoundError` via `app.main` -> RED as expected).
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

REGISTRAZIONE_URL = "/api/v1/auth/registrati"
LOGIN_URL = "/api/v1/auth/login"
LOGOUT_URL = "/api/v1/auth/logout"
ME_URL = "/api/v1/auth/me"
ADMIN_PING_URL = "/api/v1/admin/ping"


@pytest.fixture()
def client(monkeypatch, tmp_path):
    # `Limiter` state is a module-level singleton shared across the whole
    # test process (see `app/limiter.py`): without a reset, the 5/minute
    # cap on /registrati and /login (T-03-01) leaks between test functions
    # and spuriously 429s later tests (Rule 3 - blocking issue, not in plan
    # text but required for test isolation).
    limiter.reset()

    db_path = tmp_path / "test_auth_endpoints.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine)

    monkeypatch.setattr(db_module, "SessionLocal", testing_session_local)

    import app.dependencies.auth as deps_auth_module
    import app.routers.auth as auth_router_module

    monkeypatch.setattr(deps_auth_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(auth_router_module, "SessionLocal", testing_session_local)

    try:
        import app.routers.admin as admin_router_module

        if hasattr(admin_router_module, "SessionLocal"):
            monkeypatch.setattr(admin_router_module, "SessionLocal", testing_session_local)
    except ModuleNotFoundError:
        pass

    return TestClient(app)


def _registra(client, email="mario.rossi@example.com", password="Password123", nome="Mario Rossi"):
    return client.post(REGISTRAZIONE_URL, json={"email": email, "password": password, "nome": nome})


class TestRegistrazione:
    def test_registrazione_ritorna_201_con_cookie_httponly_e_userout_senza_hash(self, client):
        response = _registra(client)

        assert response.status_code == 201

        set_cookie_header = response.headers.get("set-cookie", "")
        assert "session_id=" in set_cookie_header
        assert "httponly" in set_cookie_header.lower()

        body = response.json()
        assert body["email"] == "mario.rossi@example.com"
        assert body["nome"] == "Mario Rossi"
        assert "password_hash" not in body
        assert "password" not in body

    def test_registrazione_email_duplicata_ritorna_errore(self, client):
        first = _registra(client, email="duplicato@example.com")
        assert first.status_code == 201

        second = _registra(client, email="duplicato@example.com")
        assert second.status_code in (409, 400)


class TestLoginLogoutMe:
    def test_me_con_cookie_valido_ritorna_utente_corrente(self, client):
        _registra(client, email="utente.me@example.com")

        response = client.get(ME_URL)

        assert response.status_code == 200
        assert response.json()["email"] == "utente.me@example.com"

    def test_me_senza_cookie_ritorna_401(self, client):
        response = client.get(ME_URL)
        assert response.status_code == 401

    def test_logout_poi_me_ritorna_401(self, client):
        _registra(client, email="logout@example.com")

        logout_response = client.post(LOGOUT_URL)
        assert logout_response.status_code == 204

        me_response = client.get(ME_URL)
        assert me_response.status_code == 401

    def test_login_credenziali_corrette_ritorna_200_e_nuovo_cookie(self, client):
        _registra(client, email="login.ok@example.com", password="Password123")
        client.post(LOGOUT_URL)

        response = client.post(LOGIN_URL, json={"email": "login.ok@example.com", "password": "Password123"})

        assert response.status_code == 200
        set_cookie_header = response.headers.get("set-cookie", "")
        assert "session_id=" in set_cookie_header

    def test_login_password_errata_ritorna_401_messaggio_generico(self, client):
        _registra(client, email="login.bad.pwd@example.com", password="Password123")
        client.post(LOGOUT_URL)

        response = client.post(LOGIN_URL, json={"email": "login.bad.pwd@example.com", "password": "PasswordSbagliata"})

        assert response.status_code == 401
        assert response.json()["detail"] == "Email o password non corretti"

    def test_login_email_inesistente_ritorna_401_stesso_messaggio_generico(self, client):
        response = client.post(LOGIN_URL, json={"email": "non.esiste@example.com", "password": "Password123"})

        assert response.status_code == 401
        assert response.json()["detail"] == "Email o password non corretti"


class TestAdminGuard:
    def test_admin_ping_200_per_admin_403_per_utente_normale(self, client, monkeypatch):
        monkeypatch.setattr(settings, "ADMIN_EMAIL", "admin@example.com")

        admin_client = client
        admin_response = _registra(admin_client, email="admin@example.com", nome="Admin")
        assert admin_response.status_code == 201
        assert admin_response.json()["role"] == "admin"

        ping_as_admin = admin_client.get(ADMIN_PING_URL)
        assert ping_as_admin.status_code == 200

        admin_client.post(LOGOUT_URL)
        _registra(admin_client, email="utente.normale@example.com", nome="Utente Normale")

        ping_as_user = admin_client.get(ADMIN_PING_URL)
        assert ping_as_user.status_code == 403
