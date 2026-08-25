"""Request/response schemas for /api/v1/me/stime.

Same closed-fields anti-leak pattern as `schemas/stima.py` (T-07-02, D-13):
`StimaSalvataCreate` mirrors `StimaResponse` exactly (it IS the payload the
client already received from `POST /api/v1/stima`, to be frozen as-is —
D-09/Pitfall 5, never recomputed here). `StimaSalvataListItem` exposes only
the scalar history columns. `StimaSalvataOut` rebuilds the full snapshot
shape (`id`/`created_at` + the frozen `StimaResponse` fields) from
`risultato_json`. None of the internal margin/cost fields (the impresa
secret family — see `models/listino.py` docstring) appear anywhere in this
module.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.stima import CategoriaOut, ExtraOut, StimaInputEcho, TotaleOut


class StimaSalvataCreate(BaseModel):
    """Mirrors `StimaResponse` (schemas/stima.py) — the already-computed
    payload the client received a moment earlier from `POST /api/v1/stima`.
    Frozen as-is into `risultato_json`; never re-derived server-side."""

    input: StimaInputEcho
    fallback: bool
    disclaimer: str | None = None
    valuta: str
    categorie: list[CategoriaOut]
    extra: list[ExtraOut]
    totale: TotaleOut


class StimaSalvataListItem(BaseModel):
    id: int
    citta: str
    mq: int
    tipo: str
    totale_min: Decimal
    totale_max: Decimal
    created_at: datetime


class StimaSalvataOut(BaseModel):
    id: int
    created_at: datetime
    input: StimaInputEcho
    fallback: bool
    disclaimer: str | None
    valuta: str
    categorie: list[CategoriaOut]
    extra: list[ExtraOut]
    totale: TotaleOut
