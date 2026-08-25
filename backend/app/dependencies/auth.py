"""FastAPI auth dependencies: `get_current_user`, `require_admin`.

Own module (pattern `app/limiter.py`) — imports `SessionLocal` from
`app.db`, never from `app.main`, to avoid a circular import when routers
depend on these. Uses the DB-backed opaque session cookie (02-RESEARCH.md
Pattern 1): reads the `session_id` cookie, looks up `UserSession`, joins to
`User`, 401 if absent/expired. `require_admin` layers a server-side role
check (403) on top — the client role is never trusted (ASVS V4, AUTH-04).
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.user import User, UserSession
from app.services.auth_service import SESSION_COOKIE_NAME


def get_db() -> Session:
    with SessionLocal() as session:
        yield session


def get_current_user(
    session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> User:
    if not session_id:
        raise HTTPException(401, "Non autenticato")
    row = db.query(UserSession).filter_by(id=session_id).one_or_none()
    if row is None:
        raise HTTPException(401, "Sessione scaduta")
    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(401, "Sessione scaduta")
    return row.user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Accesso riservato")
    return user
