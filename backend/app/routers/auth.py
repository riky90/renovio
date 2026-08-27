"""POST /api/v1/auth/registrati|login|logout, GET /api/v1/auth/me.

Wires `AuthService` + `get_current_user` (02-02) into HTTP endpoints.
Response is built explicitly field-by-field from `User` into `UserOut` —
never validated straight off the ORM entity — so `password_hash` never
reaches the wire (same anti-leak convention as `routers/stima.py`, T-03-05).

Rate limit 5/minute on `/registrati` and `/login` (T-03-01, brute-force
mitigation, reuses the shared `app.limiter` instance). Login failure and
unknown-email both raise the SAME generic 401 message — no user
enumeration (T-03-02).
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

from app.config import settings
from app.db import SessionLocal
from app.dependencies.auth import get_current_user, subscription_is_active
from app.limiter import limiter
from app.oauth import oauth
from app.schemas.auth import (
    LoginRequest,
    PasswordDimenticataRequest,
    RegistrazioneRequest,
    ReimpostaPasswordRequest,
    UserOut,
)
from app.services.auth_service import SESSION_COOKIE_NAME, AuthService
from app.services.email_service import send_email
from app.services.reset_token import RESET_TOKEN_MAX_AGE_SECONDS, make_reset_token, read_reset_token

router = APIRouter(prefix="/auth", tags=["auth"])

LOGIN_ERROR_DETAIL = "Email o password non corretti"
RESET_REQUEST_MESSAGE = "Ti abbiamo inviato un'email con le istruzioni per reimpostare la password."
RESET_INVALID_MESSAGE = "Il link non e' piu' valido."


def _hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _to_user_out(session, user) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        nome=user.nome,
        role=user.role,
        pro=subscription_is_active(session, user),
        created_at=user.created_at,
    )


@router.post("/registrati", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def registrati(payload: RegistrazioneRequest, request: Request, response: Response) -> UserOut:
    from app.models.user import User

    with SessionLocal() as session:
        existing = session.query(User).filter_by(email=payload.email).one_or_none()
        if existing is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Email gia' registrata")

        user = User(
            email=payload.email,
            nome=payload.nome,
            role="user",
            password_hash=AuthService.hash_password(payload.password),
        )
        AuthService.promote_admin_if_configured(user)
        session.add(user)
        session.commit()
        session.refresh(user)

        AuthService.create_session(session, user, response)

        return _to_user_out(session, user)


@router.post("/login", response_model=UserOut)
@limiter.limit("5/minute")
def login(payload: LoginRequest, request: Request, response: Response) -> UserOut:
    from app.models.user import User

    with SessionLocal() as session:
        user = session.query(User).filter_by(email=payload.email).one_or_none()
        if user is None or user.password_hash is None or not AuthService.verify_password(
            payload.password, user.password_hash
        ):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, LOGIN_ERROR_DETAIL)

        AuthService.create_session(session, user, response)

        return _to_user_out(session, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> None:
    if session_id:
        with SessionLocal() as session:
            AuthService.revoke_session(session, session_id, response)
    else:
        response.delete_cookie(SESSION_COOKIE_NAME)


@router.get("/me", response_model=UserOut)
def me(user=Depends(get_current_user)) -> UserOut:
    with SessionLocal() as session:
        return _to_user_out(session, user)


@router.post("/password-dimenticata")
@limiter.limit("5/minute")
async def password_dimenticata(payload: PasswordDimenticataRequest, request: Request) -> dict:
    """D-04: SEMPRE la stessa risposta 200, indipendentemente dal fatto che
    l'email esista o meno (T-06-01, no user-enumeration) — la generazione
    del token e l'invio dell'email avvengono solo se l'utente esiste, ma il
    ramo non e' mai osservabile dal client."""
    from app.models.user import PasswordResetToken, User

    with SessionLocal() as session:
        user = session.query(User).filter_by(email=payload.email).one_or_none()
        if user is not None:
            token = make_reset_token(user.id)
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=RESET_TOKEN_MAX_AGE_SECONDS)
            session.add(
                PasswordResetToken(
                    user_id=user.id,
                    token_hash=_hash_reset_token(token),
                    expires_at=expires_at,
                )
            )
            session.commit()

            reset_link = f"{settings.FRONTEND_URL}/reimposta-password?token={token}"
            await send_email(
                to=user.email,
                subject="Reimposta la tua password",
                html_body=(
                    f"<p>Clicca il link per reimpostare la password: "
                    f'<a href="{reset_link}">{reset_link}</a></p>'
                    f"<p>Il link scade tra un'ora.</p>"
                ),
            )

    return {"detail": RESET_REQUEST_MESSAGE}


@router.post("/reimposta-password")
@limiter.limit("5/minute")
def reimposta_password(payload: ReimpostaPasswordRequest, request: Request) -> dict:
    """Token invalido/scaduto/gia' usato -> 400 generico (T-06-02/03/04):
    stesso messaggio in tutti i casi, nessuna distinzione osservabile."""
    from app.models.user import PasswordResetToken, User

    user_id = read_reset_token(payload.token)
    if user_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, RESET_INVALID_MESSAGE)

    token_hash = _hash_reset_token(payload.token)

    with SessionLocal() as session:
        row = (
            session.query(PasswordResetToken)
            .filter_by(user_id=user_id, token_hash=token_hash, used=False)
            .one_or_none()
        )
        if row is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, RESET_INVALID_MESSAGE)

        expires_at = row.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, RESET_INVALID_MESSAGE)

        user = session.get(User, user_id)
        if user is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, RESET_INVALID_MESSAGE)

        user.password_hash = AuthService.hash_password(payload.password)
        row.used = True
        session.commit()

    return {"detail": "Password aggiornata."}


@router.get("/google/login")
async def google_login(request: Request):
    """Reindirizza a Google. Lo `state` anti-CSRF e' generato e verificato
    da Authlib (T-05-01), tenuto nel cookie `SessionMiddleware` isolato
    (Pitfall 1) — mai nel cookie applicativo `session_id`."""
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback", name="google_callback")
async def google_callback(request: Request):
    """Verifica il token (Authlib), converge sull'unico account per email
    (D-05, email GIA' verificata da Google) e crea la stessa sessione
    applicativa del flusso email/password (Plan 02). Su errore di scambio,
    redirect al frontend con un flag generico — nessun dettaglio tecnico
    esposto (T-05-04)."""
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}?google_auth=errore")

    userinfo = token.get("userinfo") or {}
    email = userinfo.get("email")
    if not email:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}?google_auth=errore")

    with SessionLocal() as session:
        user = AuthService.get_or_create_user_by_email(
            session, email=email, nome=userinfo.get("given_name", "")
        )
        response = RedirectResponse(url=settings.FRONTEND_URL)
        AuthService.create_session(session, user, response)
        return response
