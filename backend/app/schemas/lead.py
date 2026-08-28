"""Request/response schemas for POST /api/v1/lead (+ admin dashboard reuse,
04-04-PLAN.md).

Same closed-fields anti-leak pattern as `schemas/stima.py`/`schemas/stima_salvata.py`
(D-22): `LeadCreate` bounds untrusted client input (ASVS V5, T-04-06).
`LeadOut`/`LeadUpdate` are admin-only (used behind `require_admin` in
04-04-PLAN.md) and NEVER reference `coefficiente_impresa`/`base_eur_mq`/any
margin-shaped field — there is no such column on `Lead` (see models/lead.py),
so this is enforced structurally, not just by schema discipline.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class PreferenzaContattoEnum(str, Enum):
    email = "email"
    telefono = "telefono"


class LeadCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=200)
    email: EmailStr
    telefono: str | None = Field(default=None, max_length=50)
    messaggio: str | None = Field(default=None, max_length=2000)
    preferenza_contatto: PreferenzaContattoEnum
    fascia_oraria: str | None = Field(default=None, max_length=32)

    # Snapshot indipendente della stima mostrata al momento del contatto (D-03).
    citta: str = Field(min_length=1, max_length=200)
    mq: int = Field(ge=1, le=2000)
    tipo: str = Field(min_length=1, max_length=32)
    totale_min: Decimal = Field(ge=0)
    totale_max: Decimal = Field(ge=0)


class LeadCreatedOut(BaseModel):
    id: int


class LeadOut(BaseModel):
    """Admin-only (04-04-PLAN.md, `require_admin`). Mai coefficiente/prezzo
    impresa: non esiste nessuna colonna del genere su `Lead` (D-22)."""

    id: int
    nome: str
    email: str
    telefono: str | None
    preferenza_contatto: str
    fascia_oraria: str | None
    messaggio: str | None
    citta: str
    mq: int
    tipo: str
    totale_min: Decimal
    totale_max: Decimal
    referente_id: int | None
    email_inviata: bool
    stato: str
    nota: str | None
    created_at: datetime


class LeadUpdate(BaseModel):
    """Admin PATCH (04-04-PLAN.md) — narrowest possible closed schema."""

    stato: str = Field(min_length=1, max_length=16)
    nota: str | None = Field(default=None, max_length=2000)
