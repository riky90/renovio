"""E2E tests (RED->GREEN, TDD) per la migrazione dei testi/disclaimer a DB
(D-14, 04-03-PLAN.md Task 1). I test per /api/v1/admin/testi (Task 2) sono
aggiunti in coda a questo stesso file dal Task 2.

Task 1 copre: il disclaimer EST-06 restituito da POST /api/v1/stima in
fallback proviene dalla tabella Testo (modificando la riga cambia il
disclaimer), e il seed e' idempotente (rieseguirlo non duplica righe).

Nessun test qui introduce un messaggio utente per il fallback referente
(D-05, Pitfall 5) — quello resta fuori scope per costruzione (nessuna
chiave Testo per lui esiste nel seed).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.db as db_module
from app.config import settings
from app.db import Base
from app.limiter import limiter
from app.main import app
from app.models.testo import Testo
from scripts.seed import load_seed_data, seed

REGISTRAZIONE_URL = "/api/v1/auth/registrati"
STIMA_URL = "/api/v1/stima"

ADMIN_EMAIL = "admin.testi@example.com"

CITTA_SENZA_LISTINO = "Vattelapesca Inesistente"


@pytest.fixture()
def client(monkeypatch, tmp_path):
    limiter.reset()
    monkeypatch.setattr(settings, "ADMIN_EMAIL", ADMIN_EMAIL)

    db_path = tmp_path / "test_admin_testi.db"
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

    tc = TestClient(app)
    tc._session_local = testing_session_local  # accesso diretto al DB di test
    return tc


def _registra_admin(client, email=ADMIN_EMAIL, nome="Admin Testi"):
    return client.post(REGISTRAZIONE_URL, json={"email": email, "password": "Password123", "nome": nome})


def _registra_user(client, email="utente.normale.testi@example.com", nome="Utente Normale"):
    return client.post(REGISTRAZIONE_URL, json={"email": email, "password": "Password123", "nome": nome})


class TestDisclaimerReadThrough:
    """Task 1: il disclaimer EST-06 proviene da Testo, non da una costante."""

    def test_disclaimer_fallback_letto_da_testo(self, client):
        response = client.post(STIMA_URL, json={"citta": CITTA_SENZA_LISTINO, "mq": 85, "tipo": "totale"})
        assert response.status_code == 200
        body = response.json()
        assert body["fallback"] is True
        assert body["disclaimer"] == (
            f"Stima basata sul listino di Reggio Emilia, non ancora tarata su {CITTA_SENZA_LISTINO}."
        )

    def test_modificando_testo_cambia_il_disclaimer(self, client):
        with client._session_local() as session:
            row = session.get(Testo, "disclaimer_fallback_citta")
            row.valore = "Disclaimer di test personalizzato per {citta}."
            session.commit()

        response = client.post(STIMA_URL, json={"citta": CITTA_SENZA_LISTINO, "mq": 85, "tipo": "totale"})
        assert response.status_code == 200
        assert response.json()["disclaimer"] == (
            f"Disclaimer di test personalizzato per {CITTA_SENZA_LISTINO}."
        )

    def test_nessun_messaggio_utente_per_fallback_referente(self, client):
        """Pitfall 5: nessuna chiave Testo esiste per il fallback referente
        D-05 — silenzioso by construction (nessuna chiave nel seed)."""
        with client._session_local() as session:
            chiavi = {row.chiave for row in session.execute(select(Testo)).scalars().all()}
        assert not any("referente" in chiave for chiave in chiavi)


class TestSeedIdempotente:
    """Task 1: rieseguire seed() non duplica le righe Testo."""

    def test_seed_testi_idempotente(self, client):
        with client._session_local() as session:
            seed(session, load_seed_data())
            seed(session, load_seed_data())
            righe = session.execute(select(Testo)).scalars().all()
            chiavi = [r.chiave for r in righe]
            assert len(chiavi) == len(set(chiavi))
            assert "disclaimer_fallback_citta" in chiavi
