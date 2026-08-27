"""FastAPI auth dependencies: `get_current_user`, `require_admin`, `require_pro`.

Own module (pattern `app/limiter.py`) — imports `SessionLocal` from
`app.db`, never from `app.main`, to avoid a circular import when routers
depend on these. Uses the DB-backed opaque session cookie (02-RESEARCH.md
Pattern 1): reads the `session_id` cookie, looks up `UserSession`, joins to
`User`, 401 if absent/expired. `require_admin` layers a server-side role
check (403) on top — the client role is never trusted (ASVS V4, AUTH-04).

`require_pro` (03-01-PLAN.md, D-08) layers the Pro paywall the same way:
401 if anonymous (via `get_current_user`), 403 if authenticated but the
account has no active `Subscription` tessera. `subscription_is_active`
centralizes the attivo/scaduto check (same naive->aware datetime guard as
`get_current_user` above) so it can be reused by `UserOut.pro` without
duplicating the comparison logic.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.subscription import Subscription
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


def subscription_is_active(session: Session, user: User) -> bool:
    """True se `user` ha una `Subscription` con `stato == 'attivo'` e
    `scaduta_il` None (nessuna scadenza) oppure futura (D-06). Stesso guard
    naive->aware di `get_current_user` sopra: SQLite puo' restituire
    `scaduta_il` come naive anche se e' stato scritto come UTC-aware."""
    sub = session.query(Subscription).filter_by(user_id=user.id).one_or_none()
    if sub is None or sub.stato != "attivo":
        return False
    if sub.scaduta_il is None:
        return True
    scaduta_il = sub.scaduta_il
    if scaduta_il.tzinfo is None:
        scaduta_il = scaduta_il.replace(tzinfo=timezone.utc)
    return scaduta_il > datetime.now(timezone.utc)


def require_pro(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    if not subscription_is_active(db, user):
        raise HTTPException(403, "Funzione riservata agli utenti Pro")
    return user
