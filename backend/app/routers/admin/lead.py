"""Dashboard lead (ADM-04, D-17, 04-04-PLAN.md): list con filtri
citta/stato, detail, PATCH stato/nota. Ogni route dietro `require_staff`
(admin O consulente, T-04-15). Risponde con `LeadOut` (04-01), chiuso a campi: nessun dato
impresa esposto (D-22, T-04-16) — struttura invariata da `models/lead.py`,
che non ha nessuna colonna coefficiente/prezzo impresa.

Non toccare `routers/admin/__init__.py`: questo file resta il solo punto
di estensione per le route di questa sezione (04-02-PLAN.md Task 1).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.db import SessionLocal
from app.dependencies.auth import require_staff
from app.models.lead import Lead
from app.models.user import User
from app.schemas.lead import LeadOut, LeadUpdate

router = APIRouter(prefix="/lead", tags=["admin-lead"])


@router.get("", response_model=list[LeadOut])
def lista_lead(
    citta: str | None = None,
    stato: str | None = None,
    _staff: User = Depends(require_staff),
) -> list[LeadOut]:
    with SessionLocal() as session:
        stmt = select(Lead)
        if citta is not None:
            stmt = stmt.where(Lead.citta == citta)
        if stato is not None:
            stmt = stmt.where(Lead.stato == stato)
        stmt = stmt.order_by(Lead.created_at.desc())

        rows = session.execute(stmt).scalars().all()
        return [LeadOut.model_validate(row, from_attributes=True) for row in rows]


@router.get("/{lead_id}", response_model=LeadOut)
def dettaglio_lead(lead_id: int, _staff: User = Depends(require_staff)) -> LeadOut:
    with SessionLocal() as session:
        row = session.get(Lead, lead_id)
        if row is None:
            raise HTTPException(404, "Lead non trovato")
        return LeadOut.model_validate(row, from_attributes=True)


@router.patch("/{lead_id}", response_model=LeadOut)
def aggiorna_lead(
    lead_id: int,
    payload: LeadUpdate,
    _staff: User = Depends(require_staff),
) -> LeadOut:
    with SessionLocal() as session:
        row = session.get(Lead, lead_id)
        if row is None:
            raise HTTPException(404, "Lead non trovato")

        row.stato = payload.stato
        row.nota = payload.nota
        session.commit()
        session.refresh(row)

        return LeadOut.model_validate(row, from_attributes=True)
