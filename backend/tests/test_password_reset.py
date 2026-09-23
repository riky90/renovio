"""Tests (RED, TDD) for password reset (D-04, 02-06-PLAN.md): token
firmato/scadenza (`itsdangerous`), endpoint richiesta/conferma con
anti-enumeration (T-06-01) e uso singolo (T-06-03), email transazionale
astratta riusabile in Fase 4.

`email_service.send_email` is monkeypatched on the router module so the
test never attempts a real SMTP delivery (SMTP_HOST is empty by default in
this environment anyway, which already triggers the dev log-only fallback
in `email_service.py` — the monkeypatch additionally lets us capture the
reset link/token to drive the confirm step, without depending on log
output parsing).

Until `app/services/email_service.py`/`app/services/reset_token.py` and the
two new `/auth/password-dimenticata`/`/auth/reimposta-password` endpoints
exist, this file fails to even import or the endpoints 404 -> RED as
expected.
"""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import app.db as db_module
from app.db import Base
from app.limiter import limiter
from app.main import app
from app.services.reset_token import read_reset_token
from tests.session_factory import sessione_di_test

REGISTRAZIONE_URL = "/api/v1/auth/registrati"
LOGIN_URL = "/api/v1/auth/login"
PASSWORD_DIMENTICATA_URL = "/api/v1/auth/password-dimenticata"
REIMPOSTA_PASSWORD_URL = "/api/v1/auth/reimposta-password"

TOKEN_RE = re.compile(r"token=([^\"&\s]+)")


@pytest.fixture()
def sent_emails(monkeypatch):
    """Captures every `send_email` call made by `routers/auth.py`, and
    guarantees no real SMTP delivery is attempted from this test."""
    calls: list[dict] = []

    import app.routers.auth as auth_router_module

    async def fake_send_email(to: str, subject: str, html_body: str) -> None:
        calls.append({"to": to, "subject": subject, "html_body": html_body})

    monkeypatch.setattr(auth_router_module, "send_email", fake_send_email)
    return calls


@pytest.fixture()
def client(monkeypatch, tmp_path, sent_emails):
    # slowapi Limiter is a process-wide singleton (see 02-03-SUMMARY.md) —
    # reset it so the 5/minute cap on the new endpoints doesn't leak
    # between test functions.
    limiter.reset()

    db_path = tmp_path / "test_password_reset.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)

    monkeypatch.setattr(db_module, "SessionLocal", testing_session_local)

    import app.dependencies.auth as deps_auth_module
    import app.routers.auth as auth_router_module

    monkeypatch.setattr(deps_auth_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(auth_router_module, "SessionLocal", testing_session_local)

    return TestClient(app)


def _registra(client, email="utente.reset@example.com", password="Password123", nome="Utente Reset"):
    return client.post(REGISTRAZIONE_URL, json={"email": email, "password": password, "nome": nome})


def _extract_token(html_body: str) -> str:
    match = TOKEN_RE.search(html_body)
    assert match is not None, f"nessun token trovato nel corpo email: {html_body}"
    return match.group(1)


class TestResetTokenUnit:
    def test_token_valido_ritorna_user_id(self):
        from app.services.reset_token import make_reset_token

        token = make_reset_token(user_id=42)
        assert read_reset_token(token) == 42

    def test_token_scaduto_ritorna_none(self):
        from app.services.reset_token import make_reset_token

        token = make_reset_token(user_id=42)
        # max_age negativo forza la scadenza immediata, senza sleep.
        assert read_reset_token(token, max_age_seconds=-1) is None

    def test_token_manomesso_ritorna_none(self):
        from app.services.reset_token import make_reset_token

        token = make_reset_token(user_id=42)
        tampered = token[:-1] + ("a" if token[-1] != "a" else "b")
        assert read_reset_token(tampered) is None


class TestPasswordDimenticataAntiEnumeration:
    def test_risposta_identica_per_email_esistente_e_inesistente(self, client, sent_emails):
        _registra(client, email="esiste@example.com")

        risposta_esistente = client.post(PASSWORD_DIMENTICATA_URL, json={"email": "esiste@example.com"})
        risposta_inesistente = client.post(
            PASSWORD_DIMENTICATA_URL, json={"email": "non.esiste@example.com"}
        )

        assert risposta_esistente.status_code == 200
        assert risposta_inesistente.status_code == 200
        assert risposta_esistente.json() == risposta_inesistente.json()

        # L'email transazionale parte SOLO per l'utente che esiste davvero.
        assert len(sent_emails) == 1
        assert sent_emails[0]["to"] == "esiste@example.com"


class TestReimpostaPasswordFlow:
    def test_token_valido_aggiorna_password_e_permette_login(self, client, sent_emails):
        _registra(client, email="flusso@example.com", password="VecchiaPassword1")

        client.post(PASSWORD_DIMENTICATA_URL, json={"email": "flusso@example.com"})
        token = _extract_token(sent_emails[0]["html_body"])

        risposta = client.post(
            REIMPOSTA_PASSWORD_URL, json={"token": token, "password": "NuovaPassword1"}
        )
        assert risposta.status_code == 200

        login_vecchia = client.post(
            LOGIN_URL, json={"email": "flusso@example.com", "password": "VecchiaPassword1"}
        )
        assert login_vecchia.status_code == 401

        login_nuova = client.post(
            LOGIN_URL, json={"email": "flusso@example.com", "password": "NuovaPassword1"}
        )
        assert login_nuova.status_code == 200

    def test_riutilizzo_dello_stesso_token_ritorna_400(self, client, sent_emails):
        _registra(client, email="replay@example.com", password="VecchiaPassword1")

        client.post(PASSWORD_DIMENTICATA_URL, json={"email": "replay@example.com"})
        token = _extract_token(sent_emails[0]["html_body"])

        prima = client.post(REIMPOSTA_PASSWORD_URL, json={"token": token, "password": "NuovaPassword1"})
        assert prima.status_code == 200

        seconda = client.post(
            REIMPOSTA_PASSWORD_URL, json={"token": token, "password": "AltraPassword1"}
        )
        assert seconda.status_code == 400

    def test_token_invalido_ritorna_400(self, client):
        risposta = client.post(
            REIMPOSTA_PASSWORD_URL, json={"token": "token-completamente-invalido", "password": "NuovaPassword1"}
        )
        assert risposta.status_code == 400

    def test_password_troppo_corta_ritorna_422(self, client, sent_emails):
        _registra(client, email="corta@example.com")
        client.post(PASSWORD_DIMENTICATA_URL, json={"email": "corta@example.com"})
        token = _extract_token(sent_emails[0]["html_body"])

        risposta = client.post(REIMPOSTA_PASSWORD_URL, json={"token": token, "password": "corta"})
        assert risposta.status_code == 422
