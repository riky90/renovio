"""Auth entities: `User`, `UserSession`, `PasswordResetToken`.

`password_hash` is the CAMPO SEGRETO of this module: an Argon2id hash,
mapped on the ORM entity only, NEVER serialized by any Pydantic response
schema (same convention as `coefficiente_impresa` in models/listino.py —
see 01-RESEARCH.md Pattern 1 / 02-RESEARCH.md Pattern 1). `password_hash`
is nullable because a user who signs up via Google-only (D-05 convergence)
has no local password until they explicitly set one.

`UserSession` is a DB-backed opaque session (02-RESEARCH.md Pattern 1): the
primary key is the high-entropy `secrets.token_urlsafe(32)` session id set
in the httpOnly cookie, NOT an autoincrement integer — this makes cookie ->
row lookup a direct PK read and server-side revocation (logout) a plain
DELETE, honoring D-02 ("logout server-side pulito", no JWT blocklist).

`PasswordResetToken` exists here only so the table is created by migration
0002; the reset-password flow logic itself lands in Plan 06 (D-04).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    # SEGRETO: hash Argon2id. Mai serializzato in nessuna risposta Pydantic.
    # Nullable: un utente arrivato via Google-only (D-05) non ha password locale.
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    # Campi profilo (D-profilo): opzionali, compilati dall'utente in Impostazioni.
    # Nullable perché registrazione/Google non li raccolgono.
    cognome: Mapped[str | None] = mapped_column(String(200), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(40), nullable=True)
    citta: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # URL pubblico dell'avatar su R2. Scritto SOLO dall'endpoint di upload
    # (mai da `ProfiloUpdateRequest`): una stringa arbitraria dal client
    # aprirebbe a SSRF e hotlinking.
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="user", server_default="user")
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user")


class UserSession(Base):
    """Sessione applicativa opaca DB-backed (02-RESEARCH.md Pattern 1).

    `id` e' il session_id ad alta entropia (secrets.token_urlsafe(32)) messo
    nel cookie httpOnly — PK diretta, non autoincrement, per un lookup
    cookie -> riga senza indice secondario.
    """

    __tablename__ = "user_session"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="sessions")


class PasswordResetToken(Base):
    """Tabella minima per il reset password (D-04). Creata qui per far
    esistere lo schema in migrazione 0002; la logica del flusso arriva nel
    Plan 06."""

    __tablename__ = "password_reset_token"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
