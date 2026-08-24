"""Request/response schemas for POST /api/v1/stima.

`StimaRequest` bounds untrusted input (ASVS V5, T-03-02). The response
models (`CategoriaOut`, `ExtraOut`, `TotaleOut`, `StimaResponse`) declare
ONLY the fields in the API contract from 01-RESEARCH.md — no
`base_eur_mq`, `moltiplicatore`, `coefficiente_impresa`, or
`prezzo_impresa` anywhere in this module (T-03-01, EST-05).
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class TipoEnum(str, Enum):
    leggera = "leggera"
    moderata = "moderata"
    totale = "totale"


class StimaRequest(BaseModel):
    citta: str = Field(min_length=1, max_length=100)
    mq: int = Field(ge=1, le=2000)
    tipo: TipoEnum


class StimaInputEcho(BaseModel):
    citta: str
    mq: int
    tipo: TipoEnum


class CategoriaOut(BaseModel):
    code: str
    nome: str
    imponibile_min: Decimal
    imponibile_max: Decimal
    iva_pct: Decimal
    iva_min: Decimal
    iva_max: Decimal
    totale_min: Decimal
    totale_max: Decimal


class ExtraOut(BaseModel):
    """Fixed single values — no min/max range on extras (D-13/01-02 rule)."""

    code: str
    nome: str
    importo: Decimal
    iva_pct: Decimal


class TotaleOut(BaseModel):
    imponibile_min: Decimal
    imponibile_max: Decimal
    iva_min: Decimal
    iva_max: Decimal
    totale_min: Decimal
    totale_max: Decimal


class StimaResponse(BaseModel):
    input: StimaInputEcho
    fallback: bool
    disclaimer: str | None
    valuta: str
    categorie: list[CategoriaOut]
    extra: list[ExtraOut]
    totale: TotaleOut
