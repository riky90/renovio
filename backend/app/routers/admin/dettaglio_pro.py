"""CRUD manuale delle voci di dettaglio Pro (Sottocategoria/Voce), oltre
all'upload Excel: consente all'admin di aggiungere/modificare/eliminare a
mano le voci che fanno da base al preventivo di dettaglio Pro.

Tutte le route dietro `require_admin`. Anti-leak (D-10): `Voce` non ha
colonne di margine impresa per costruzione — nessun dato riservato può
uscire da qui. Delete di una sottocategoria con voci: bloccato (409, mai
distruttivo implicito, coerente con D-24) — vanno eliminate prima le voci.

Non toccare `routers/admin/__init__.py` per la logica: questo file resta il
solo punto di estensione delle route di questa sezione.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.db import SessionLocal
from app.dependencies.auth import require_admin
from app.models.dettaglio_pro import Sottocategoria, Voce
from app.models.listino import Listino
from app.schemas.admin_dettaglio_pro import (
    SottocategoriaIn,
    SottocategoriaOut,
    SottocategoriaUpdate,
    VoceIn,
    VoceOut,
    VoceUpdate,
)

router = APIRouter(prefix="/dettaglio-pro", tags=["admin-dettaglio-pro"])


# --- Sottocategorie --------------------------------------------------------


@router.get("/sottocategorie", response_model=list[SottocategoriaOut])
def lista_sottocategorie(
    listino_id: int | None = None,
    categoria_code: str | None = None,
    _admin=Depends(require_admin),
) -> list[SottocategoriaOut]:
    with SessionLocal() as session:
        stmt = select(Sottocategoria)
        if listino_id is not None:
            stmt = stmt.where(Sottocategoria.listino_id == listino_id)
        if categoria_code is not None:
            stmt = stmt.where(Sottocategoria.categoria_code == categoria_code)
        stmt = stmt.order_by(Sottocategoria.ordine, Sottocategoria.id)
        rows = session.execute(stmt).scalars().all()
        return [SottocategoriaOut.model_validate(r, from_attributes=True) for r in rows]


@router.post("/sottocategorie", response_model=SottocategoriaOut, status_code=201)
def crea_sottocategoria(payload: SottocategoriaIn, _admin=Depends(require_admin)) -> SottocategoriaOut:
    with SessionLocal() as session:
        if session.get(Listino, payload.listino_id) is None:
            raise HTTPException(404, "Listino non trovato")
        row = Sottocategoria(
            listino_id=payload.listino_id,
            categoria_code=payload.categoria_code,
            codice=payload.codice,
            nome=payload.nome,
            famiglia=payload.famiglia,
            ordine=payload.ordine,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return SottocategoriaOut.model_validate(row, from_attributes=True)


@router.patch("/sottocategorie/{sotto_id}", response_model=SottocategoriaOut)
def aggiorna_sottocategoria(
    sotto_id: int, payload: SottocategoriaUpdate, _admin=Depends(require_admin)
) -> SottocategoriaOut:
    with SessionLocal() as session:
        row = session.get(Sottocategoria, sotto_id)
        if row is None:
            raise HTTPException(404, "Sottocategoria non trovata")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(row, field, value)
        session.commit()
        session.refresh(row)
        return SottocategoriaOut.model_validate(row, from_attributes=True)


@router.delete("/sottocategorie/{sotto_id}", status_code=204)
def elimina_sottocategoria(sotto_id: int, _admin=Depends(require_admin)) -> None:
    with SessionLocal() as session:
        row = session.get(Sottocategoria, sotto_id)
        if row is None:
            raise HTTPException(404, "Sottocategoria non trovata")
        has_voci = session.execute(
            select(Voce.id).where(Voce.sottocategoria_id == sotto_id).limit(1)
        ).first()
        if has_voci is not None:
            raise HTTPException(409, "Elimina prima le voci di questa sottocategoria")
        session.delete(row)
        session.commit()


# --- Voci ------------------------------------------------------------------


@router.get("/voci", response_model=list[VoceOut])
def lista_voci(sottocategoria_id: int, _admin=Depends(require_admin)) -> list[VoceOut]:
    with SessionLocal() as session:
        stmt = (
            select(Voce)
            .where(Voce.sottocategoria_id == sottocategoria_id)
            .order_by(Voce.ordine, Voce.id)
        )
        rows = session.execute(stmt).scalars().all()
        return [VoceOut.model_validate(r, from_attributes=True) for r in rows]


@router.post("/voci", response_model=VoceOut, status_code=201)
def crea_voce(payload: VoceIn, _admin=Depends(require_admin)) -> VoceOut:
    with SessionLocal() as session:
        if session.get(Sottocategoria, payload.sottocategoria_id) is None:
            raise HTTPException(404, "Sottocategoria non trovata")
        row = Voce(
            sottocategoria_id=payload.sottocategoria_id,
            codice=payload.codice,
            descrizione=payload.descrizione,
            um=payload.um,
            prezzo_unitario_cliente=payload.prezzo_unitario_cliente,
            ordine=payload.ordine,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return VoceOut.model_validate(row, from_attributes=True)


@router.patch("/voci/{voce_id}", response_model=VoceOut)
def aggiorna_voce(voce_id: int, payload: VoceUpdate, _admin=Depends(require_admin)) -> VoceOut:
    with SessionLocal() as session:
        row = session.get(Voce, voce_id)
        if row is None:
            raise HTTPException(404, "Voce non trovata")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(row, field, value)
        session.commit()
        session.refresh(row)
        return VoceOut.model_validate(row, from_attributes=True)


@router.delete("/voci/{voce_id}", status_code=204)
def elimina_voce(voce_id: int, _admin=Depends(require_admin)) -> None:
    with SessionLocal() as session:
        row = session.get(Voce, voce_id)
        if row is None:
            raise HTTPException(404, "Voce non trovata")
        session.delete(row)
        session.commit()
