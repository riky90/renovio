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

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, UploadFile, status
from fastapi.responses import RedirectResponse

from app.config import settings
from app.db import SessionLocal
from app.dependencies.auth import get_current_user, subscription_is_active
from app.limiter import limiter
from app.oauth import oauth
from app.schemas.auth import (
    LoginRequest,
    PasswordDimenticataRequest,
    ProfiloUpdateRequest,
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
STORAGE_OFF_DETAIL = "Caricamento immagini non disponibile: storage non configurato."


def _hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _to_user_out(session, user) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        nome=user.nome,
        cognome=user.cognome,
        telefono=user.telefono,
        citta=user.citta,
        avatar_url=user.avatar_url,
        role=user.role,
        pro=subscription_is_active(session, user),
        created_at=user.created_at,
    )


def _blank_to_none(value: str | None) -> str | None:
    """Normalizza i campi opzionali: stringa vuota/spazi -> None."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


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


@router.patch("/me", response_model=UserOut)
def aggiorna_profilo(payload: ProfiloUpdateRequest, user=Depends(get_current_user)) -> UserOut:
    """Aggiorna i dati profilo dell'utente corrente (nome/cognome/telefono/
    citta). email/role/pro non sono toccati: l'identità di login e lo stato
    abbonamento non passano mai da qui."""
    from app.models.user import User

    with SessionLocal() as session:
        db_user = session.get(User, user.id)
        if db_user is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Utente non trovato")

        db_user.nome = payload.nome.strip()
        db_user.cognome = _blank_to_none(payload.cognome)
        db_user.telefono = _blank_to_none(payload.telefono)
        db_user.citta = _blank_to_none(payload.citta)
        session.commit()
        session.refresh(db_user)

        return _to_user_out(session, db_user)


@router.post("/me/avatar", response_model=UserOut)
@limiter.limit("5/minute")
async def carica_avatar(request: Request, file: UploadFile, user=Depends(get_current_user)) -> UserOut:
    """Carica l'avatar dell'utente corrente su R2 e ne salva l'URL.

    L'ordine conta: si valida e normalizza l'immagine PRIMA di parlare con lo
    storage, e si scrive in DB solo dopo che l'oggetto e' davvero sul bucket.
    Il vecchio oggetto si cancella per ultimo, best-effort: un orfano nel
    bucket non deve far fallire un upload gia' riuscito.

    Rate limit 5/minute come registrazione e login: un upload e' l'endpoint
    piu' costoso dell'app (banda + decodifica immagine).
    """
    from app.models.user import User
    from app.services.avatar_service import AvatarValidationError, process_avatar
    from app.services.storage_service import (
        StorageError,
        StorageNotConfigured,
        avatar_key,
        delete_avatar,
        key_from_url,
        upload_avatar,
    )

    content = await file.read()
    try:
        webp = process_avatar(content)
    except AvatarValidationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    with SessionLocal() as session:
        db_user = session.get(User, user.id)
        if db_user is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Utente non trovato")

        vecchia_key = key_from_url(db_user.avatar_url)
        try:
            url = upload_avatar(avatar_key(db_user.id), webp)
        except StorageNotConfigured as exc:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, STORAGE_OFF_DETAIL) from exc
        except StorageError as exc:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

        db_user.avatar_url = url
        session.commit()
        session.refresh(db_user)

        if vecchia_key:
            try:
                delete_avatar(vecchia_key)
            except (StorageError, StorageNotConfigured):
                pass

        return _to_user_out(session, db_user)


@router.delete("/me/avatar", response_model=UserOut)
def rimuovi_avatar(user=Depends(get_current_user)) -> UserOut:
    """Azzera `avatar_url` e cancella l'oggetto. La colonna si azzera anche se
    la cancellazione remota fallisce: l'utente ha chiesto di non vedere piu'
    quella foto, e un oggetto orfano su R2 non e' una ragione per dirgli di
    no."""
    from app.models.user import User
    from app.services.storage_service import (
        StorageError,
        StorageNotConfigured,
        delete_avatar,
        key_from_url,
    )

    with SessionLocal() as session:
        db_user = session.get(User, user.id)
        if db_user is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Utente non trovato")

        key = key_from_url(db_user.avatar_url)
        db_user.avatar_url = None
        session.commit()
        session.refresh(db_user)

        if key:
            try:
                delete_avatar(key)
            except (StorageError, StorageNotConfigured):
                pass

        return _to_user_out(session, db_user)


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
