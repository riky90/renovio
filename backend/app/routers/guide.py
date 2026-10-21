"""GET /api/v1/guide/costi — le cifre delle guide pubbliche ai costi.

Pubblico e di sola lettura come `POST /stima`: le guide del sito sono aperte a
tutti, e i loro numeri vengono dallo stesso motore della stima
(`services/guide_costi.py`). Il frontend le prerenderizza al build con una
copia di questi dati e li aggiorna dal vivo nel browser.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, Response

from app.db import SessionLocal
from app.limiter import limiter
from app.services.guide_costi import dati_guide_in_cache

router = APIRouter(prefix="/guide", tags=["guide"])


@router.get("/costi")
@limiter.limit("60/minute")
def costi(request: Request, response: Response) -> dict[str, Any]:
    response.headers["Cache-Control"] = "public, max-age=600"
    with SessionLocal() as session:
        return dati_guide_in_cache(session)
