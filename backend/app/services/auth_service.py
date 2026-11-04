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
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User, UserSession

SESSION_COOKIE_NAME = "session_id"
SESSION_TTL = timedelta(days=30)

_ph = PasswordHasher()

# Hash di una password casuale e mai usata: il login di un'email inesistente
# verifica contro questo, cosi' impiega lo stesso tempo di un'email vera e il
# tempo di risposta non dice quali email sono registrate.
_DUMMY_HASH = _ph.hash(secrets.token_urlsafe(32))


def normalizza_email(email: str) -> str:
    """Le email si confrontano e si salvano in minuscolo: `Mario@x.it` e
    `mario@x.it` sono la stessa casella, quindi lo stesso account."""
    return email.strip().lower()


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
    def verify_password_or_dummy(plain: str, hashed: str | None) -> bool:
        """Come `verify_password`, ma senza hash (utente inesistente o solo
        Google) verifica comunque contro un hash fittizio e ritorna False:
        tempo costante, nessuna enumerazione via timing."""
        if hashed is None:
            AuthService.verify_password(plain, _DUMMY_HASH)
            return False
        return AuthService.verify_password(plain, hashed)

    @staticmethod
    def find_user_by_email(session: Session, email: str) -> User | None:
        return (
            session.query(User)
            .filter(func.lower(User.email) == normalizza_email(email))
            .one_or_none()
        )

    @staticmethod
    def revoke_all_sessions(session: Session, user_id: int) -> None:
        """Chiude ogni sessione dell'utente: dopo un cambio password o una
        presa di possesso dell'account via Google, chi aveva un cookie
        valido resta fuori."""
        session.query(UserSession).filter_by(user_id=user_id).delete()

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
            # In prod (COOKIE_SECURE=True, HTTPS) frontend e backend stanno su
            # domini diversi (Vercel vs Render): serve SameSite=None perche' il
            # cookie viaggi sulle fetch cross-site, e None richiede Secure=True.
            # In dev locale (http, COOKIE_SECURE=False) None+non-Secure verrebbe
            # rifiutato dal browser, quindi si resta su Lax.
            samesite="none" if settings.COOKIE_SECURE else "lax",
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
        Google), converge sullo stesso record — nessun doppione.

        Si chiama SOLO con un'email verificata dal provider (Google
        `email_verified`). Se l'account esistente non aveva mai dimostrato di
        possedere la casella e ha una password, quella password puo' essere
        di chiunque l'abbia registrato prima (pre-hijacking): si azzera e si
        chiudono le sessioni aperte. Il proprietario vero entra con Google o
        si rifa' la password dal reset."""
        user = AuthService.find_user_by_email(session, email)
        if user is not None:
            if not user.email_verificata:
                if user.password_hash is not None:
                    user.password_hash = None
                    AuthService.revoke_all_sessions(session, user.id)
                user.email_verificata = True
            AuthService.promote_admin_if_configured(user)
            session.commit()
            session.refresh(user)
            return user
        user = User(email=normalizza_email(email), nome=nome, role="user", email_verificata=True)
        AuthService.promote_admin_if_configured(user)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    @staticmethod
    def promote_admin_if_configured(user: User) -> None:
        """D-03: il primo admin e' promosso via ADMIN_EMAIL, ma solo quando la
        casella e' dimostrata (login Google verificato o reset password):
        altrimenti chiunque si registri per primo con quell'indirizzo
        diventerebbe admin. `ADMIN_PROMUOVI_SENZA_VERIFICA` esiste per i test
        e lo sviluppo locale, mai in produzione."""
        if not settings.ADMIN_EMAIL:
            return
        if normalizza_email(user.email) != normalizza_email(settings.ADMIN_EMAIL):
            return
        if user.email_verificata or settings.ADMIN_PROMUOVI_SENZA_VERIFICA:
            user.role = "admin"
