"""Schemi CRUD per le voci di dettaglio Pro (Sottocategoria/Voce).

Anti-leak (D-10): `Voce` non ha per costruzione NESSUNA colonna di margine/
prezzo impresa, quindi questi schemi non possono esporre `coefficiente_impresa`
o simili. Solo `prezzo_unitario_cliente` (prezzo mostrato al cliente).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

Famiglia = Literal["gerarchica", "catalogo"]


# --- Sottocategoria --------------------------------------------------------


class SottocategoriaIn(BaseModel):
    listino_id: int
    categoria_code: str = Field(min_length=1, max_length=32)
    codice: str | None = Field(default=None, max_length=16)
    nome: str = Field(min_length=1, max_length=200)
    famiglia: Famiglia = "gerarchica"
    ordine: int = Field(default=0, ge=0)


class SottocategoriaUpdate(BaseModel):
    categoria_code: str | None = Field(default=None, min_length=1, max_length=32)
    codice: str | None = Field(default=None, max_length=16)
    nome: str | None = Field(default=None, min_length=1, max_length=200)
    famiglia: Famiglia | None = None
    ordine: int | None = Field(default=None, ge=0)


class SottocategoriaOut(BaseModel):
    id: int
    listino_id: int
    categoria_code: str
    codice: str | None
    nome: str
    famiglia: str
    ordine: int


# --- Voce ------------------------------------------------------------------


class VoceIn(BaseModel):
    sottocategoria_id: int
    codice: str | None = Field(default=None, max_length=16)
    descrizione: str = Field(min_length=1, max_length=300)
    um: str = Field(min_length=1, max_length=16)
    prezzo_unitario_cliente: Decimal = Field(gt=0)
    ordine: int = Field(default=0, ge=0)


class VoceUpdate(BaseModel):
    codice: str | None = Field(default=None, max_length=16)
    descrizione: str | None = Field(default=None, min_length=1, max_length=300)
    um: str | None = Field(default=None, min_length=1, max_length=16)
    prezzo_unitario_cliente: Decimal | None = Field(default=None, gt=0)
    ordine: int | None = Field(default=None, ge=0)


class VoceOut(BaseModel):
    id: int
    sottocategoria_id: int
    codice: str | None
    descrizione: str
    um: str
    prezzo_unitario_cliente: Decimal
    ordine: int
