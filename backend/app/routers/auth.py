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

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status

from app.db import SessionLocal
from app.dependencies.auth import get_current_user
from app.limiter import limiter
from app.schemas.auth import LoginRequest, RegistrazioneRequest, UserOut
from app.services.auth_service import SESSION_COOKIE_NAME, AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

LOGIN_ERROR_DETAIL = "Email o password non corretti"


def _to_user_out(user) -> UserOut:
    return UserOut(id=user.id, email=user.email, nome=user.nome, role=user.role, created_at=user.created_at)


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

        return _to_user_out(user)


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

        return _to_user_out(user)


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
    return _to_user_out(user)
