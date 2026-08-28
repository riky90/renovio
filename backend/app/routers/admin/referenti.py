"""CRUD referenti (ADM-04, D-15/D-16, 04-04-PLAN.md): create/list/patch
(attivo/priorita)/delete, dietro `require_admin` (T-04-15). V1: nessun
vincolo di unicita sul referente attivo per citta (convenzione operativa,
non enforced a schema) — la risoluzione lead (04-01, `resolve_referente`)
prende il primo attivo per priorita, coerente con questo CRUD.

Non toccare `routers/admin/__init__.py`: questo file resta il solo punto
di estensione per le route di questa sezione (04-02-PLAN.md Task 1).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.db import SessionLocal
from app.dependencies.auth import require_admin
from app.models.catalogo import Referente
from app.models.user import User
from app.schemas.admin_referenti import ReferenteAdminIn, ReferenteAdminOut, ReferenteAdminUpdate

router = APIRouter(prefix="/referenti", tags=["admin-referenti"])


@router.get("", response_model=list[ReferenteAdminOut])
def lista_referenti(_admin: User = Depends(require_admin)) -> list[ReferenteAdminOut]:
    with SessionLocal() as session:
        rows = session.execute(select(Referente).order_by(Referente.id)).scalars().all()
        return [ReferenteAdminOut.model_validate(row, from_attributes=True) for row in rows]


@router.post("", response_model=ReferenteAdminOut, status_code=201)
def crea_referente(
    payload: ReferenteAdminIn,
    _admin: User = Depends(require_admin),
) -> ReferenteAdminOut:
    with SessionLocal() as session:
        row = Referente(
            listino_id=payload.listino_id,
            nome=payload.nome,
            email=payload.email,
            telefono=payload.telefono,
            attivo=payload.attivo,
            priorita=payload.priorita,
        )
        session.add(row)
        session.commit()
        session.refresh(row)

        return ReferenteAdminOut.model_validate(row, from_attributes=True)


@router.patch("/{referente_id}", response_model=ReferenteAdminOut)
def aggiorna_referente(
    referente_id: int,
    payload: ReferenteAdminUpdate,
    _admin: User = Depends(require_admin),
) -> ReferenteAdminOut:
    with SessionLocal() as session:
        row = session.get(Referente, referente_id)
        if row is None:
            raise HTTPException(404, "Referente non trovato")

        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(row, field, value)

        session.commit()
        session.refresh(row)

        return ReferenteAdminOut.model_validate(row, from_attributes=True)


@router.delete("/{referente_id}", status_code=204)
def elimina_referente(referente_id: int, _admin: User = Depends(require_admin)) -> None:
    with SessionLocal() as session:
        row = session.get(Referente, referente_id)
        if row is None:
            raise HTTPException(404, "Referente non trovato")

        session.delete(row)
        session.commit()
