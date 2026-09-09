"""Request/response schemas for auth endpoints (registrazione/login/UserOut).

`UserOut` declares ONLY the fields safe for the client — never the secret
password hash field on `User` (T-02-06, ASVS V2.4/V4). Same closed-schema
anti-leak convention as `schemas/stima.py` — never `model_validate` a raw
`User` ORM entity, always build these explicitly.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegistrazioneRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    nome: str = Field(min_length=1, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    nome: str
    cognome: str | None = None
    telefono: str | None = None
    citta: str | None = None
    # Sola lettura: si cambia con POST/DELETE /auth/me/avatar, mai come campo
    # di `ProfiloUpdateRequest`.
    avatar_url: str | None = None
    role: str
    pro: bool
    created_at: datetime


class ProfiloUpdateRequest(BaseModel):
    """Aggiornamento profilo dell'utente corrente. NON include email (identità
    di login), role o pro: quei campi non sono mai scrivibili dal client."""

    nome: str = Field(min_length=1, max_length=200)
    cognome: str | None = Field(default=None, max_length=200)
    telefono: str | None = Field(default=None, max_length=40)
    citta: str | None = Field(default=None, max_length=200)


class PasswordDimenticataRequest(BaseModel):
    email: EmailStr


class ReimpostaPasswordRequest(BaseModel):
    token: str
    password: str = Field(min_length=8)
