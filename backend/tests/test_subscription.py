"""Test suite Subscription/paywall (PRO-02, PRO-03, 03-01-PLAN.md).

Task 1: scaffold del modello `Subscription` (fixture SQLite in-memory +
seed idempotente, come `test_estimation.py`) e verifica dei default di
riga. La logica attivo/scaduto (`subscription_is_active`/`require_pro`) e
gli endpoint di attivazione arrivano nei Task 2/3 di questo stesso file,
che estendono questa suite fino a farla diventare interamente verde
(03-01-PLAN.md <verify> Task 3).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import app.db as db_module
from app.db import Base
from app.limiter import limiter
from app.main import app
from app.dependencies.auth import require_pro, subscription_is_active
from app.models.subscription import Subscription
from app.models.user import User
from scripts.seed import load_seed_data, seed
from tests.session_factory import sessione_di_test

REGISTRAZIONE_URL = "/api/v1/auth/registrati"
ME_URL = "/api/v1/auth/me"
ATTIVA_PRO_URL = "/api/v1/me/pro/attiva"
ADMIN_ATTIVA_PRO_URL = "/api/v1/admin/pro/attiva"

FORBIDDEN_SUBSTRINGS = [
    "base_eur_mq",
    "moltiplicatore",
    "coefficiente_impresa",
    "prezzo_impresa",
]


@pytest.fixture()
def session():
    """SQLite in-memory + seed idempotente, come test_estimation.py."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)
    with testing_session_local() as s:
        seed(s, load_seed_data())
        yield s


@pytest.fixture()
def client(monkeypatch, tmp_path):
    # slowapi Limiter e' un singleton di processo (02-03-SUMMARY.md) — reset
    # per non far leakare il rate limit di /me/pro/attiva tra i test.
    limiter.reset()

    db_path = tmp_path / "test_subscription.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)

    monkeypatch.setattr(db_module, "SessionLocal", testing_session_local)

    import app.dependencies.auth as deps_auth_module
    import app.routers.auth as auth_router_module

    monkeypatch.setattr(deps_auth_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(auth_router_module, "SessionLocal", testing_session_local)

    try:
        import app.routers.subscription as subscription_router_module

        if hasattr(subscription_router_module, "SessionLocal"):
            monkeypatch.setattr(subscription_router_module, "SessionLocal", testing_session_local)
    except ModuleNotFoundError:
        pass

    return TestClient(app)


def _registra(client, email="utente.a@example.com", password="Password123", nome="Utente A"):
    return client.post(REGISTRAZIONE_URL, json={"email": email, "password": password, "nome": nome})


class TestSubscriptionModelDefaults:
    """Task 1: il modello Subscription esiste, e' migrabile, e ha i default
    dichiarati in must_haves (stato default 'inattivo')."""

    def test_stato_di_default_inattivo(self, session):
        user = User(email="model.a@example.com", nome="Model A", role="user")
        session.add(user)
        session.flush()

        sub = Subscription(user_id=user.id)
        session.add(sub)
        session.commit()
        session.refresh(sub)

        assert sub.stato == "inattivo"
        assert sub.scaduta_il is None
        assert sub.piano_code is None

    def test_riga_attiva_senza_scadenza_e_rappresentabile(self, session):
        user = User(email="model.b@example.com", nome="Model B", role="user")
        session.add(user)
        session.flush()

        sub = Subscription(user_id=user.id, stato="attivo", scaduta_il=None)
        session.add(sub)
        session.commit()
        session.refresh(sub)

        assert sub.stato == "attivo"
        assert sub.scaduta_il is None

    def test_riga_attiva_con_scadenza_passata_e_rappresentabile(self, session):
        user = User(email="model.c@example.com", nome="Model C", role="user")
        session.add(user)
        session.flush()

        scaduta = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
        sub = Subscription(user_id=user.id, stato="attivo", scaduta_il=scaduta)
        session.add(sub)
        session.commit()
        session.refresh(sub)

        assert sub.stato == "attivo"
        assert sub.scaduta_il == scaduta


class TestSubscriptionIsActive:
    """Task 2: subscription_is_active(session, user) — attivo/scaduto/assente."""

    def test_attivo_senza_scadenza_e_true(self, session):
        user = User(email="active.a@example.com", nome="Active A", role="user")
        session.add(user)
        session.flush()
        session.add(Subscription(user_id=user.id, stato="attivo", scaduta_il=None))
        session.commit()

        assert subscription_is_active(session, user) is True

    def test_scaduto_e_false(self, session):
        user = User(email="active.b@example.com", nome="Active B", role="user")
        session.add(user)
        session.flush()
        scaduta = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
        session.add(Subscription(user_id=user.id, stato="attivo", scaduta_il=scaduta))
        session.commit()

        assert subscription_is_active(session, user) is False

    def test_attivo_con_scadenza_futura_e_true(self, session):
        user = User(email="active.c@example.com", nome="Active C", role="user")
        session.add(user)
        session.flush()
        scaduta = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30)
        session.add(Subscription(user_id=user.id, stato="attivo", scaduta_il=scaduta))
        session.commit()

        assert subscription_is_active(session, user) is True

    def test_assente_e_false(self, session):
        user = User(email="active.d@example.com", nome="Active D", role="user")
        session.add(user)
        session.commit()

        assert subscription_is_active(session, user) is False

    def test_stato_inattivo_e_false_anche_senza_scadenza(self, session):
        user = User(email="active.e@example.com", nome="Active E", role="user")
        session.add(user)
        session.flush()
        session.add(Subscription(user_id=user.id, stato="inattivo", scaduta_il=None))
        session.commit()

        assert subscription_is_active(session, user) is False


class TestRequirePro:
    """Task 2: require_pro solleva 403 con messaggio esatto se non attivo."""

    def test_require_pro_403_se_non_attivo(self, session):
        user = User(email="pro.a@example.com", nome="Pro A", role="user")
        session.add(user)
        session.commit()

        with pytest.raises(Exception) as exc_info:
            require_pro(user=user, db=session)

        assert getattr(exc_info.value, "status_code", None) == 403
        assert getattr(exc_info.value, "detail", None) == "Funzione riservata agli utenti Pro"

    def test_require_pro_ok_se_attivo(self, session):
        user = User(email="pro.b@example.com", nome="Pro B", role="user")
        session.add(user)
        session.flush()
        session.add(Subscription(user_id=user.id, stato="attivo", scaduta_il=None))
        session.commit()

        result = require_pro(user=user, db=session)

        assert result is user


class TestAttivazioneProEndToEnd:
    """Task 3: /me/pro/attiva (stub) + /admin/pro/attiva + UserOut.pro
    riflesso su /auth/me."""

    def test_me_ritorna_pro_false_senza_tessera(self, client):
        _registra(client)

        response = client.get(ME_URL)

        assert response.status_code == 200
        assert response.json()["pro"] is False

    def test_attiva_pro_ritorna_200_e_me_diventa_pro_true(self, client):
        _registra(client)

        attiva = client.post(ATTIVA_PRO_URL)
        assert attiva.status_code == 200
        assert attiva.json()["pro"] is True

        me = client.get(ME_URL)
        assert me.status_code == 200
        assert me.json()["pro"] is True

    def test_attiva_pro_e_idempotente_una_sola_riga(self, client):
        _registra(client)

        client.post(ATTIVA_PRO_URL)
        second = client.post(ATTIVA_PRO_URL)
        assert second.status_code == 200

        with db_module.SessionLocal() as s:
            count = s.query(Subscription).count()
        assert count == 1

    def test_attiva_pro_senza_sessione_ritorna_401(self, client):
        response = client.post(ATTIVA_PRO_URL)

        assert response.status_code == 401

    def test_admin_attiva_pro_dietro_require_admin_403_per_non_admin(self, client):
        _registra(client)

        response = client.post(ADMIN_ATTIVA_PRO_URL, json={"user_id": 1})

        assert response.status_code == 403

    def test_dettaglio_salvato_non_contiene_dati_impresa_su_attiva_pro(self, client):
        _registra(client)

        response = client.post(ATTIVA_PRO_URL)
        raw_text = response.text

        for forbidden in FORBIDDEN_SUBSTRINGS:
            assert forbidden not in raw_text, f"forbidden substring '{forbidden}' leaked in attiva-pro response"
