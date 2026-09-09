"""Schemi CRUD dei bonus fiscali (0011).

Nessun dato riservato all'impresa passa da qui: i bonus vivono sui totali
CLIENTE. La materia sensibile e' un'altra — aliquote, tetti e date sono cio'
che l'utente vedra' come "recuperi X euro", quindi ogni campo e' vincolato in
ingresso (aliquota in [0,1], tetto positivo, rate >= 1) invece di fidarsi del
pannello.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

Destinazione = str


# --- Bonus -----------------------------------------------------------------


class BonusIn(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    nome: str = Field(min_length=1, max_length=100)
    descrizione: str | None = Field(default=None, max_length=500)
    ordine: int = Field(default=0, ge=0)
    attivo: bool = True


class BonusUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=100)
    descrizione: str | None = Field(default=None, max_length=500)
    ordine: int | None = Field(default=None, ge=0)
    attivo: bool | None = None


class BonusOut(BaseModel):
    code: str
    nome: str
    descrizione: str | None
    ordine: int
    attivo: bool


# --- Aliquote --------------------------------------------------------------


class AliquotaIn(BaseModel):
    bonus_code: str = Field(min_length=1, max_length=32)
    destinazione: Destinazione = Field(min_length=1, max_length=32)
    # Frazione, non percentuale: 0.50 = 50%. Stessa convenzione di `iva_pct`.
    aliquota_pct: Decimal = Field(ge=0, le=1)
    tetto_spesa_eur: Decimal | None = Field(default=None, gt=0)
    tetto_modalita: str | None = Field(default=None, max_length=32)
    rate_annuali: int = Field(default=10, ge=1, le=20)
    valido_dal: date
    valido_al: date | None = None
    note: str | None = Field(default=None, max_length=500)


class AliquotaUpdate(BaseModel):
    aliquota_pct: Decimal | None = Field(default=None, ge=0, le=1)
    tetto_spesa_eur: Decimal | None = Field(default=None, gt=0)
    tetto_modalita: str | None = Field(default=None, max_length=32)
    rate_annuali: int | None = Field(default=None, ge=1, le=20)
    valido_dal: date | None = None
    valido_al: date | None = None
    note: str | None = Field(default=None, max_length=500)


class AliquotaOut(BaseModel):
    id: int
    bonus_code: str
    destinazione: str
    aliquota_pct: Decimal
    tetto_spesa_eur: Decimal | None
    tetto_modalita: str | None
    rate_annuali: int
    valido_dal: date
    valido_al: date | None
    note: str | None


# --- Mapping categoria -> bonus --------------------------------------------


class BonusCategoriaIn(BaseModel):
    bonus_code: str = Field(min_length=1, max_length=32)
    categoria_code: str = Field(min_length=1, max_length=32)
    quota_ammissibile_pct: Decimal = Field(default=Decimal("1"), gt=0, le=1)


class BonusCategoriaUpdate(BaseModel):
    quota_ammissibile_pct: Decimal | None = Field(default=None, gt=0, le=1)


class BonusCategoriaOut(BaseModel):
    id: int
    bonus_code: str
    categoria_code: str
    quota_ammissibile_pct: Decimal


# --- Mapping extra -> bonus ------------------------------------------------


class BonusExtraIn(BaseModel):
    bonus_code: str = Field(min_length=1, max_length=32)
    extra_code: str = Field(min_length=1, max_length=32)
    quota_ammissibile_pct: Decimal = Field(default=Decimal("1"), gt=0, le=1)


class BonusExtraUpdate(BaseModel):
    quota_ammissibile_pct: Decimal | None = Field(default=None, gt=0, le=1)


class BonusExtraOut(BaseModel):
    id: int
    bonus_code: str
    extra_code: str
    quota_ammissibile_pct: Decimal
