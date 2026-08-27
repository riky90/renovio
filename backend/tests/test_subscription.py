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
from sqlalchemy.orm import sessionmaker

import app.db as db_module
from app.db import Base
from app.limiter import limiter
from app.main import app
from app.models.subscription import Subscription
from app.models.user import User
from scripts.seed import load_seed_data, seed

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
    testing_session_local = sessionmaker(bind=engine)
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
    testing_session_local = sessionmaker(bind=engine)

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
