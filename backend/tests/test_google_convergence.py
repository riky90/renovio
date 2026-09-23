"""Test convergenza per-email (D-05, TDD RED->GREEN).

Verifica che `AuthService.get_or_create_user_by_email` (gia' esistente dal
Plan 02, riusata dal callback Google in `routers/auth.py`) converga sempre
sull'unico account per email, senza rete verso Google: si testa
direttamente la funzione di convergenza, stesso pattern DB in-memory di
`test_auth_service.py`.

Casi (02-05-PLAN.md <behavior>):
- Uno User gia' creato via password con email X: `get_or_create_user_by_email`
  ritorna lo STESSO user (stesso id), non ne crea uno nuovo.
- Nessun user con email Y: la prima chiamata crea uno user col nome dal
  parametro; la seconda chiamata ritorna lo stesso id.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine

from app.db import Base

# Import a livello di modulo (non dentro le funzioni di test): registra
# User/UserSession su Base.metadata PRIMA che la fixture chiami create_all
# — altrimenti, eseguendo questo file in isolamento (nessun altro file di
# test ha ancora importato app.services.auth_service nello stesso processo
# pytest), create_all crea uno schema vuoto e ogni INSERT fallisce con
# "no such table: user".
from app.models.user import User
from app.services.auth_service import AuthService
from tests.session_factory import sessione_di_test


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)
    with testing_session_local() as s:
        yield s


class TestGoogleConvergence:
    def test_existing_password_user_converges_no_duplicate(self, session):
        existing = User(
            email="mario.rossi@example.com",
            nome="Mario Rossi",
            role="user",
            password_hash=AuthService.hash_password("Password123"),
        )
        session.add(existing)
        session.commit()
        session.refresh(existing)

        converged = AuthService.get_or_create_user_by_email(
            session, email="mario.rossi@example.com", nome="Mario (da Google)"
        )

        assert converged.id == existing.id
        count = session.query(User).filter_by(email="mario.rossi@example.com").count()
        assert count == 1
        # Il nome dell'utente gia' esistente non viene sovrascritto dal
        # parametro passato alla convergenza (D-05: converge, non aggiorna).
        assert converged.nome == "Mario Rossi"

    def test_new_email_creates_then_second_call_converges(self, session):
        first = AuthService.get_or_create_user_by_email(
            session, email="nuovo.utente@example.com", nome="Nuovo Utente"
        )
        assert first.id is not None
        assert first.nome == "Nuovo Utente"

        second = AuthService.get_or_create_user_by_email(
            session, email="nuovo.utente@example.com", nome="Ignorato"
        )

        assert second.id == first.id
        count = session.query(User).filter_by(email="nuovo.utente@example.com").count()
        assert count == 1
