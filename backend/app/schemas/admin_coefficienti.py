"""Schemi admin (D-12, ADM-02) per le 4 famiglie di coefficienti del
modello che l'admin può editare in v1: moltiplicatori tipo×categoria, IVA
per categoria, extra (CSE/CSP, pratiche), coefficienti quantità-per-m² del
motore Pro. Stesso fork deliberato di `schemas/admin_listino.py`: le
classi *AdminOut* qui sono usate SOLO nelle route `routers/admin/
coefficienti.py`, tutte dietro `Depends(require_admin)`, e non sono mai la
stessa classe usata dagli schemi pubblici (`schemas/stima.py`,
`schemas/dettaglio_pro.py`).

`BaseEurMqAdminOut` espone in sola lettura `ListinoCategoria.base_eur_mq`
per la UI Coefficienti (04-08): la scrittura di quel campo resta sul CRUD
di `/admin/listini` (04-02), qui non c'è alcun endpoint di scrittura per
non duplicare il percorso di editing. Il margine interno riservato
all'impresa (il valore corrispondente a `coefficiente_impresa` su
`ListinoCategoria`) NON compare in nessuno schema di questo modulo.

Bound numerici (ASVS V5, T-04-39): moltiplicatore/coeff-pro > 0 o >= 0 a
seconda del dominio, percentuali IVA in [0, 1).
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class MoltiplicatoreAdminOut(BaseModel):
    id: int
    tipo_code: str
    categoria_code: str
    valore: Decimal


class MoltiplicatoreAdminIn(BaseModel):
    valore: Decimal = Field(gt=0)


class CategoriaIvaAdminOut(BaseModel):
    code: str
    nome: str
    iva_pct: Decimal


class IvaAdminIn(BaseModel):
    iva_pct: Decimal = Field(ge=0, lt=1)


class ExtraAdminOut(BaseModel):
    code: str
    nome: str
    importo: Decimal
    iva_pct: Decimal
    tipo_calcolo: str
    attivo: bool


class ExtraAdminCreateIn(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    nome: str = Field(min_length=1, max_length=100)
    importo: Decimal = Field(ge=0)
    iva_pct: Decimal = Field(ge=0, lt=1)
    tipo_calcolo: str = Field(default="fisso", min_length=1, max_length=32)
    attivo: bool = True


class ExtraAdminIn(BaseModel):
    """PATCH parziale: solo i campi presenti nel payload vengono modificati
    (D-24 — nessun campo obbligatorio, non azzera nulla non inviato)."""

    nome: str | None = Field(default=None, min_length=1, max_length=100)
    importo: Decimal | None = Field(default=None, ge=0)
    iva_pct: Decimal | None = Field(default=None, ge=0, lt=1)
    attivo: bool | None = None


class CoeffProAdminOut(BaseModel):
    id: int
    voce_id: int
    tipo_code: str
    valore: Decimal | None
    domanda_mirata_key: str | None
    default_conteggio: int | None


class CoeffProAdminIn(BaseModel):
    valore: Decimal = Field(ge=0)


class BaseEurMqAdminOut(BaseModel):
    """Sola lettura (D-12): la scrittura resta su /admin/listini (04-02)."""

    id: int
    listino_id: int
    categoria_code: str
    base_eur_mq: Decimal
