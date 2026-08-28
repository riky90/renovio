"""Request/response schemas for CRUD referenti (04-04-PLAN.md, ADM-04,
D-15/D-16). Chiuso a campi come `LeadOut`/`ReferenteAdminOut`: nessun campo
impresa qui — `Referente` (models/catalogo.py) non ha nessuna colonna del
genere.
"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class ReferenteAdminIn(BaseModel):
    listino_id: int
    nome: str = Field(min_length=1, max_length=200)
    email: EmailStr
    telefono: str | None = Field(default=None, max_length=50)
    attivo: bool = True
    priorita: int = Field(default=0, ge=0)


class ReferenteAdminUpdate(BaseModel):
    """PATCH parziale: tutti i campi opzionali."""

    listino_id: int | None = None
    nome: str | None = Field(default=None, min_length=1, max_length=200)
    email: EmailStr | None = None
    telefono: str | None = Field(default=None, max_length=50)
    attivo: bool | None = None
    priorita: int | None = Field(default=None, ge=0)


class ReferenteAdminOut(BaseModel):
    id: int
    listino_id: int
    nome: str
    email: str
    telefono: str | None
    attivo: bool
    priorita: int
