"""AuthService: password hashing (Argon2id), DB-backed opaque session
lifecycle, per-email convergence, admin promotion.

Follows 02-RESEARCH.md Pattern 1 (session) and Code Examples (argon2-cffi)
VERBATIM. Never use `passlib` (deprecated/broken with bcrypt>=4.1, Pitfall 2)
— `argon2-cffi` directly, per OWASP 2024+ recommendation.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Response
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User, UserSession

SESSION_COOKIE_NAME = "session_id"
SESSION_TTL = timedelta(days=30)

_ph = PasswordHasher()


class AuthService:
    """Server-side auth logic: hashing, session create/revoke, convergence."""

    @staticmethod
    def hash_password(plain: str) -> str:
        return _ph.hash(plain)

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        try:
            return _ph.verify(hashed, plain)
        except VerifyMismatchError:
            return False

    @staticmethod
    def create_session(session: Session, user: User, response: Response) -> str:
        """Always mints a NEW session id (session fixation mitigation,
        T-02-07) — never reuses a pre-login id."""
        session_id = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + SESSION_TTL
        session.add(UserSession(id=session_id, user_id=user.id, expires_at=expires_at))
        session.commit()
        response.set_cookie(
            SESSION_COOKIE_NAME,
            session_id,
            httponly=True,
            samesite="lax",
            secure=settings.COOKIE_SECURE,
            max_age=int(SESSION_TTL.total_seconds()),
        )
        return session_id

    @staticmethod
    def revoke_session(session: Session, session_id: str, response: Response) -> None:
        session.query(UserSession).filter_by(id=session_id).delete()
        session.commit()
        response.delete_cookie(SESSION_COOKIE_NAME)

    @staticmethod
    def get_or_create_user_by_email(session: Session, email: str, nome: str) -> User:
        """D-05: un solo account per email. Se esiste gia' (via password o
        Google), converge sullo stesso record — nessun doppione."""
        user = session.query(User).filter_by(email=email).one_or_none()
        if user is not None:
            return user
        user = User(email=email, nome=nome, role="user")
        AuthService.promote_admin_if_configured(user)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    @staticmethod
    def promote_admin_if_configured(user: User) -> None:
        """D-03: il primo admin e' promosso via ADMIN_EMAIL."""
        if settings.ADMIN_EMAIL and user.email == settings.ADMIN_EMAIL:
            user.role = "admin"
