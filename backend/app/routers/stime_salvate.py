"""/api/v1/me/stime — save/list/detail of the current user's estimates.

Every endpoint sits behind `Depends(get_current_user)` (T-07-04, 401
without a session). POST freezes the client-supplied `StimaResponse`-shaped
payload as-is into `risultato_json` (+ `schema_version`) — it NEVER calls
`EstimationService` (D-09/Pitfall 5, no recompute). GET list/detail are
filtered by `user_id == current_user.id`; detail returns 404 (not 403) when
the row belongs to another user or doesn't exist, so ownership is never
leaked (T-07-01, anti-IDOR, ASVS V4).
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.dependencies.auth import get_current_user
from app.models.stima_salvata import StimaSalvata
from app.models.user import User
from app.schemas.stima import CategoriaOut, ExtraOut, StimaInputEcho, TotaleOut
from app.schemas.stima_salvata import (
    StimaSalvataCreate,
    StimaSalvataListItem,
    StimaSalvataOut,
)

router = APIRouter(prefix="/me", tags=["stime"])

SCHEMA_VERSION = 1


class StimaSalvataCreatedOut(BaseModel):
    id: int
    created_at: datetime


@router.post("/stime", response_model=StimaSalvataCreatedOut, status_code=201)
def salva_stima(
    payload: StimaSalvataCreate,
    current_user: User = Depends(get_current_user),
) -> StimaSalvataCreatedOut:
    with SessionLocal() as session:
        risultato_json = payload.model_dump(mode="json")
        risultato_json["schema_version"] = SCHEMA_VERSION

        row = StimaSalvata(
            user_id=current_user.id,
            citta=payload.input.citta,
            mq=payload.input.mq,
            tipo=payload.input.tipo.value,
            totale_min=payload.totale.totale_min,
            totale_max=payload.totale.totale_max,
            fallback=payload.fallback,
            risultato_json=risultato_json,
        )
        session.add(row)
        session.commit()
        session.refresh(row)

        return StimaSalvataCreatedOut(id=row.id, created_at=row.created_at)


@router.get("/stime", response_model=list[StimaSalvataListItem])
def lista_stime(current_user: User = Depends(get_current_user)) -> list[StimaSalvataListItem]:
    with SessionLocal() as session:
        stmt = (
            select(StimaSalvata)
            .where(StimaSalvata.user_id == current_user.id)
            .order_by(StimaSalvata.created_at.desc())
        )
        rows = session.execute(stmt).scalars().all()

        return [
            StimaSalvataListItem(
                id=row.id,
                citta=row.citta,
                mq=row.mq,
                tipo=row.tipo,
                totale_min=row.totale_min,
                totale_max=row.totale_max,
                created_at=row.created_at,
            )
            for row in rows
        ]


@router.get("/stime/{stima_id}", response_model=StimaSalvataOut)
def dettaglio_stima(
    stima_id: int,
    current_user: User = Depends(get_current_user),
) -> StimaSalvataOut:
    with SessionLocal() as session:
        stmt = select(StimaSalvata).where(
            StimaSalvata.id == stima_id,
            StimaSalvata.user_id == current_user.id,
        )
        row = session.execute(stmt).scalar_one_or_none()
        if row is None:
            raise HTTPException(404, "Stima non trovata")

        snapshot = row.risultato_json

        return StimaSalvataOut(
            id=row.id,
            created_at=row.created_at,
            input=StimaInputEcho(**snapshot["input"]),
            fallback=snapshot["fallback"],
            disclaimer=snapshot["disclaimer"],
            valuta=snapshot["valuta"],
            categorie=[CategoriaOut(**c) for c in snapshot["categorie"]],
            extra=[ExtraOut(**e) for e in snapshot["extra"]],
            totale=TotaleOut(**snapshot["totale"]),
        )
