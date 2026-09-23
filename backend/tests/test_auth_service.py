"""Unit tests (RED, TDD) for the auth foundation: password hashing (Argon2id),
DB-backed opaque session (create/validate/revoke), admin guard, per-email
convergence (D-05), and the anti-leak invariant on `UserOut` (mai
"password_hash").

See 02-RESEARCH.md Pattern 1 (session), Code Examples (argon2-cffi),
02-02-PLAN.md <behavior>.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine

from app.db import Base
from tests.session_factory import sessione_di_test


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)
    with testing_session_local() as s:
        yield s


def _make_user(session, email="mario.rossi@example.com", nome="Mario Rossi", role="user"):
    from app.models.user import User
    from app.services.auth_service import AuthService

    user = User(email=email, nome=nome, role=role, password_hash=AuthService.hash_password("Password123"))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


class TestPasswordHashing:
    def test_hash_password_differs_from_plain(self, session):
        from app.services.auth_service import AuthService

        hashed = AuthService.hash_password("Password123")
        assert hashed != "Password123"

    def test_verify_password_correct(self, session):
        from app.services.auth_service import AuthService

        hashed = AuthService.hash_password("Password123")
        assert AuthService.verify_password("Password123", hashed) is True

    def test_verify_password_incorrect(self, session):
        from app.services.auth_service import AuthService

        hashed = AuthService.hash_password("Password123")
        assert AuthService.verify_password("PasswordSbagliata", hashed) is False


class _FakeResponse:
    """Minimal stand-in for fastapi.Response, tracks set_cookie/delete_cookie calls."""

    def __init__(self):
        self.cookies_set = {}
        self.cookies_deleted = []

    def set_cookie(self, key, value, **kwargs):
        self.cookies_set[key] = value

    def delete_cookie(self, key, **kwargs):
        self.cookies_deleted.append(key)


class TestSessionLifecycle:
    def test_create_session_inserts_row_with_high_entropy_id_and_future_expiry(self, session):
        from app.models.user import UserSession
        from app.services.auth_service import AuthService

        user = _make_user(session)
        response = _FakeResponse()

        AuthService.create_session(session, user, response)

        rows = session.query(UserSession).filter_by(user_id=user.id).all()
        assert len(rows) == 1
        row = rows[0]
        assert len(row.id) >= 32
        assert row.expires_at > datetime.now(timezone.utc).replace(tzinfo=None) or row.expires_at > datetime.now(
            timezone.utc
        )
        assert "session_id" in response.cookies_set

    def test_get_current_user_with_valid_cookie_returns_user(self, session):
        from app.dependencies.auth import get_current_user
        from app.services.auth_service import AuthService

        user = _make_user(session)
        response = _FakeResponse()
        AuthService.create_session(session, user, response)
        session_id = response.cookies_set["session_id"]

        resolved = get_current_user(session_id=session_id, db=session)
        assert resolved.id == user.id

    def test_get_current_user_missing_cookie_raises_401(self, session):
        from app.dependencies.auth import get_current_user

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(session_id=None, db=session)
        assert exc_info.value.status_code == 401

    def test_get_current_user_expired_session_raises_401(self, session):
        from app.dependencies.auth import get_current_user
        from app.models.user import UserSession

        user = _make_user(session)
        expired = UserSession(
            id="a" * 43,
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        session.add(expired)
        session.commit()

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(session_id=expired.id, db=session)
        assert exc_info.value.status_code == 401

    def test_revoke_session_deletes_row_then_get_current_user_401(self, session):
        from app.dependencies.auth import get_current_user
        from app.services.auth_service import AuthService

        user = _make_user(session)
        response = _FakeResponse()
        AuthService.create_session(session, user, response)
        session_id = response.cookies_set["session_id"]

        AuthService.revoke_session(session, session_id, response)

        assert "session_id" in response.cookies_deleted
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(session_id=session_id, db=session)
        assert exc_info.value.status_code == 401


class TestAdminGuard:
    def test_require_admin_passes_for_admin_role(self, session):
        from app.dependencies.auth import require_admin

        admin = _make_user(session, email="admin@example.com", role="admin")
        result = require_admin(user=admin)
        assert result.id == admin.id

    def test_require_admin_raises_403_for_user_role(self, session):
        from app.dependencies.auth import require_admin

        user = _make_user(session, email="user@example.com", role="user")
        with pytest.raises(HTTPException) as exc_info:
            require_admin(user=user)
        assert exc_info.value.status_code == 403


class TestEmailConvergence:
    def test_get_or_create_user_by_email_does_not_duplicate(self, session):
        from app.models.user import User
        from app.services.auth_service import AuthService

        first = AuthService.get_or_create_user_by_email(session, email="dup@example.com", nome="Prima")
        second = AuthService.get_or_create_user_by_email(session, email="dup@example.com", nome="Seconda")

        assert first.id == second.id
        count = session.query(User).filter_by(email="dup@example.com").count()
        assert count == 1


def _assert_no_password_hash_key(node) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            assert key != "password_hash", f"forbidden key 'password_hash' found in serialized output"
            _assert_no_password_hash_key(value)
    elif isinstance(node, list):
        for item in node:
            _assert_no_password_hash_key(item)


class TestUserOutAntiLeak:
    def test_user_out_never_contains_password_hash(self, session):
        from app.schemas.auth import UserOut

        user = _make_user(session, email="secreto@example.com")
        assert user.password_hash is not None

        out = UserOut(
            id=user.id, email=user.email, nome=user.nome, role=user.role, pro=False, created_at=user.created_at
        )
        serialized = out.model_dump(mode="json")
        _assert_no_password_hash_key(serialized)
