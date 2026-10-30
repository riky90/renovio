"""Schemi admin per ComuneListino/TipoRistrutturazione (ADM-03): campi
chiusi, uso esclusivo in `routers/admin/citta.py` dietro
`Depends(require_admin)`.

`comune_slug` non e' mai accettato in input: viene ricalcolato server-side
con lo stesso `slugify` usato da `city_resolver.resolve_listino`, cosi' la
mappatura creata/modificata dall'admin resta coerente con la risoluzione
del motore (04-03-PLAN.md Task 2).
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class ComuneListinoAdminIn(BaseModel):
    comune_nome: str = Field(min_length=1, max_length=200)
    codice_istat: str | None = Field(default=None, max_length=20)
    listino_id: int


class ComuneListinoPatchIn(BaseModel):
    comune_nome: str | None = Field(default=None, min_length=1, max_length=200)
    codice_istat: str | None = Field(default=None, max_length=20)
    listino_id: int | None = None


class ComuneListinoAdminOut(BaseModel):
    id: int
    comune_nome: str
    comune_slug: str
    codice_istat: str | None
    listino_id: int


class TipoRistrutturazioneAdminOut(BaseModel):
    code: str
    nome: str
    ordine: int
    range_pct: Decimal
    range_pct_sotto: Decimal | None = None


class TipoRistrutturazionePatchIn(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=100)
    ordine: int | None = None
    range_pct: Decimal | None = Field(default=None, gt=0, le=1)
    range_pct_sotto: Decimal | None = Field(default=None, gt=0, le=1)
