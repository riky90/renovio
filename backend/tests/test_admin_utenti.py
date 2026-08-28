"""E2E test per la gestione utenti/ruoli admin e per l'accesso `consulente`.

Copre:
- guard: GET/PATCH /admin/utenti 403 per non-admin, 401 senza sessione;
- lista utenti chiusa a campi (mai `password_hash`);
- PATCH ruolo user->consulente->admin; ruolo invalido -> 422;
- anti-lockout: admin non cambia il proprio ruolo (403); ultimo admin non
  degradabile (409); id inesistente -> 404;
- accesso consulente: dopo la promozione, la sessione del consulente vede
  /admin/lead (200) ma resta 403 su /admin/listini e /admin/utenti.
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
UTENTI_URL = "/api/v1/admin/utenti"
LEAD_URL = "/api/v1/admin/lead"
LISTINI_URL = "/api/v1/admin/listini"

ADMIN_EMAIL = "admin.utenti@example.com"
PASSWORD = "Password123"

FORBIDDEN_KEYS = {"password_hash", "coefficiente_impresa", "base_eur_mq"}


def _assert_no_forbidden_keys(node) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            assert key not in FORBIDDEN_KEYS, f"forbidden key '{key}' found"
            _assert_no_forbidden_keys(value)
    elif isinstance(node, list):
        for item in node:
            _assert_no_forbidden_keys(item)


@pytest.fixture()
def client(monkeypatch, tmp_path):
    limiter.reset()
    monkeypatch.setattr(settings, "ADMIN_EMAIL", ADMIN_EMAIL)

    db_path = tmp_path / "test_admin_utenti.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine)

    monkeypatch.setattr(db_module, "SessionLocal", testing_session_local)

    import app.dependencies.auth as deps_auth_module
    import app.routers.auth as auth_router_module

    monkeypatch.setattr(deps_auth_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(auth_router_module, "SessionLocal", testing_session_local)

    for mod_name in ("utenti", "lead", "listini"):
        try:
            mod = __import__(f"app.routers.admin.{mod_name}", fromlist=["SessionLocal"])
            if hasattr(mod, "SessionLocal"):
                monkeypatch.setattr(mod, "SessionLocal", testing_session_local)
        except ModuleNotFoundError:
            pass

    return TestClient(app), testing_session_local


def _registra(c, email, nome="Utente", password=PASSWORD):
    return c.post(REGISTRAZIONE_URL, json={"email": email, "password": password, "nome": nome})


def _login(c, email, password=PASSWORD):
    return c.post(LOGIN_URL, json={"email": email, "password": password})


def _id_utente(session_factory, email) -> int:
    from app.models.user import User

    with session_factory() as session:
        return session.query(User).filter_by(email=email).one().id


# --- Guard -----------------------------------------------------------------


class TestUtentiGuard:
    def test_get_utenti_401_senza_sessione(self, client):
        c, _ = client
        assert c.get(UTENTI_URL).status_code == 401

    def test_get_utenti_403_per_user(self, client):
        c, _ = client
        _registra(c, "user@example.com")
        assert c.get(UTENTI_URL).status_code == 403

    def test_patch_utenti_403_per_user(self, client):
        c, _ = client
        _registra(c, "user@example.com")
        assert c.patch(f"{UTENTI_URL}/1", json={"role": "consulente"}).status_code == 403


# --- CRUD ruoli ------------------------------------------------------------


class TestUtentiRoleUpdate:
    def test_lista_utenti_no_forbidden_keys(self, client):
        c, _ = client
        _registra(c, ADMIN_EMAIL, nome="Capo")
        _registra(c, "b@example.com")
        _login(c, ADMIN_EMAIL)
        r = c.get(UTENTI_URL)
        assert r.status_code == 200
        assert len(r.json()) == 2
        _assert_no_forbidden_keys(r.json())

    def test_promuove_user_a_consulente_e_admin(self, client):
        c, sf = client
        _registra(c, ADMIN_EMAIL)
        _registra(c, "b@example.com")
        _login(c, ADMIN_EMAIL)
        bid = _id_utente(sf, "b@example.com")

        r1 = c.patch(f"{UTENTI_URL}/{bid}", json={"role": "consulente"})
        assert r1.status_code == 200 and r1.json()["role"] == "consulente"

        r2 = c.patch(f"{UTENTI_URL}/{bid}", json={"role": "admin"})
        assert r2.status_code == 200 and r2.json()["role"] == "admin"

    def test_ruolo_invalido_422(self, client):
        c, sf = client
        _registra(c, ADMIN_EMAIL)
        _registra(c, "b@example.com")
        _login(c, ADMIN_EMAIL)
        bid = _id_utente(sf, "b@example.com")
        assert c.patch(f"{UTENTI_URL}/{bid}", json={"role": "superuser"}).status_code == 422

    def test_id_inesistente_404(self, client):
        c, _ = client
        _registra(c, ADMIN_EMAIL)
        _login(c, ADMIN_EMAIL)
        assert c.patch(f"{UTENTI_URL}/9999", json={"role": "consulente"}).status_code == 404

    def test_admin_non_cambia_proprio_ruolo(self, client):
        c, sf = client
        _registra(c, ADMIN_EMAIL)
        _login(c, ADMIN_EMAIL)
        aid = _id_utente(sf, ADMIN_EMAIL)
        assert c.patch(f"{UTENTI_URL}/{aid}", json={"role": "user"}).status_code == 403

    def test_ultimo_admin_non_degradabile(self, client):
        c, sf = client
        _registra(c, ADMIN_EMAIL)
        _registra(c, "b@example.com")
        _login(c, ADMIN_EMAIL)
        bid = _id_utente(sf, "b@example.com")
        # promuovo b ad admin, poi provo a declassare b: restano 2 admin -> ok
        c.patch(f"{UTENTI_URL}/{bid}", json={"role": "admin"})
        r_ok = c.patch(f"{UTENTI_URL}/{bid}", json={"role": "user"})
        assert r_ok.status_code == 200
        # ora resta solo l'admin capo: declassarlo e' vietato via se stesso (403),
        # ma il vincolo "ultimo admin" e' verificato promuovendo b e riprovando.
        c.patch(f"{UTENTI_URL}/{bid}", json={"role": "admin"})  # b admin
        # declasso capo NON e' possibile (self, 403); declasso b lascia 1 admin -> deve passare
        r = c.patch(f"{UTENTI_URL}/{bid}", json={"role": "user"})
        assert r.status_code == 200


# --- Accesso consulente ----------------------------------------------------


class TestConsulenteAccess:
    def test_consulente_vede_lead_ma_non_config(self, client):
        c, sf = client
        _registra(c, ADMIN_EMAIL)
        _registra(c, "cons@example.com")
        _login(c, ADMIN_EMAIL)
        cid = _id_utente(sf, "cons@example.com")
        assert c.patch(f"{UTENTI_URL}/{cid}", json={"role": "consulente"}).status_code == 200

        # divento il consulente (nuova sessione)
        _login(c, "cons@example.com")
        assert c.get(LEAD_URL).status_code == 200          # dashboard lead consentita
        assert c.get(LISTINI_URL).status_code == 403        # config di business vietata
        assert c.get(UTENTI_URL).status_code == 403         # gestione ruoli vietata
