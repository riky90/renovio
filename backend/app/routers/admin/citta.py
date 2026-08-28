"""CRUD citta/mappature/tipi (ADM-03): ComuneListino (list/create/patch/
delete) + TipoRistrutturazione (list/patch nome/ordine/range_pct).

Ogni route ha `Depends(require_admin)` (T-04-11): righe mancanti -> 404
(stesso pattern di `routers/admin/listini.py`). Su create/patch di
ComuneListino il `comune_slug` e' SEMPRE ricalcolato server-side con lo
stesso `slugify` usato da `services/city_resolver.resolve_listino`, cosi'
la mappatura creata/modificata dall'admin risolve coerentemente da
POST /api/v1/stima (T-04-12). Upsert idempotente per `comune_slug` unico:
una seconda POST sullo stesso comune aggiorna invece di duplicare (D-24).
DELETE elimina SOLO la riga indicata, non tocca le stime salvate (D-11) —
snapshot congelato, invariato da un edit successivo della mappatura.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from slugify import slugify
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies.auth import get_db, require_admin
from app.models.catalogo import ComuneListino, TipoRistrutturazione
from app.schemas.admin_citta import (
    ComuneListinoAdminIn,
    ComuneListinoAdminOut,
    ComuneListinoPatchIn,
    TipoRistrutturazioneAdminOut,
    TipoRistrutturazionePatchIn,
)

router = APIRouter(prefix="/citta", tags=["admin-citta"])


def _to_comune_out(row: ComuneListino) -> ComuneListinoAdminOut:
    return ComuneListinoAdminOut(
        id=row.id,
        comune_nome=row.comune_nome,
        comune_slug=row.comune_slug,
        codice_istat=row.codice_istat,
        listino_id=row.listino_id,
    )


def _to_tipo_out(row: TipoRistrutturazione) -> TipoRistrutturazioneAdminOut:
    return TipoRistrutturazioneAdminOut(code=row.code, nome=row.nome, ordine=row.ordine, range_pct=row.range_pct)


@router.get("", response_model=list[ComuneListinoAdminOut])
def lista_citta(user=Depends(require_admin), db: Session = Depends(get_db)) -> list[ComuneListinoAdminOut]:
    rows = db.execute(select(ComuneListino).order_by(ComuneListino.comune_nome)).scalars().all()
    return [_to_comune_out(row) for row in rows]


@router.post("", response_model=ComuneListinoAdminOut, status_code=201)
def crea_o_aggiorna_citta(
    payload: ComuneListinoAdminIn,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> ComuneListinoAdminOut:
    """Upsert per `comune_slug` (chiave naturale unica, D-24): una seconda
    POST dello stesso comune aggiorna invece di duplicare."""
    slug = slugify(payload.comune_nome)
    row = db.query(ComuneListino).filter_by(comune_slug=slug).one_or_none()
    if row is None:
        row = ComuneListino(
            comune_nome=payload.comune_nome,
            comune_slug=slug,
            codice_istat=payload.codice_istat,
            listino_id=payload.listino_id,
        )
        db.add(row)
    else:
        row.comune_nome = payload.comune_nome
        row.codice_istat = payload.codice_istat
        row.listino_id = payload.listino_id

    db.commit()
    db.refresh(row)
    return _to_comune_out(row)


@router.patch("/{comune_id}", response_model=ComuneListinoAdminOut)
def modifica_citta(
    comune_id: int,
    payload: ComuneListinoPatchIn,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> ComuneListinoAdminOut:
    row = db.get(ComuneListino, comune_id)
    if row is None:
        raise HTTPException(404, "Mappatura citta non trovata")

    if payload.comune_nome is not None:
        row.comune_nome = payload.comune_nome
        row.comune_slug = slugify(payload.comune_nome)
    if payload.codice_istat is not None:
        row.codice_istat = payload.codice_istat
    if payload.listino_id is not None:
        row.listino_id = payload.listino_id

    db.commit()
    db.refresh(row)
    return _to_comune_out(row)


@router.delete("/{comune_id}", status_code=204)
def elimina_citta(
    comune_id: int,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    """Elimina SOLO la mappatura indicata (D-24). Non tocca le stime
    salvate (D-11, snapshot congelato) — la citta torna semplicemente a
    risolvere in fallback dopo la delete."""
    row = db.get(ComuneListino, comune_id)
    if row is None:
        raise HTTPException(404, "Mappatura citta non trovata")

    db.delete(row)
    db.commit()


@router.get("/tipi", response_model=list[TipoRistrutturazioneAdminOut])
def lista_tipi(user=Depends(require_admin), db: Session = Depends(get_db)) -> list[TipoRistrutturazioneAdminOut]:
    rows = db.execute(select(TipoRistrutturazione).order_by(TipoRistrutturazione.ordine)).scalars().all()
    return [_to_tipo_out(row) for row in rows]


@router.patch("/tipi/{code}", response_model=TipoRistrutturazioneAdminOut)
def modifica_tipo(
    code: str,
    payload: TipoRistrutturazionePatchIn,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> TipoRistrutturazioneAdminOut:
    row = db.get(TipoRistrutturazione, code)
    if row is None:
        raise HTTPException(404, "Tipo ristrutturazione non trovato")

    if payload.nome is not None:
        row.nome = payload.nome
    if payload.ordine is not None:
        row.ordine = payload.ordine
    if payload.range_pct is not None:
        row.range_pct = payload.range_pct

    db.commit()
    db.refresh(row)
    return _to_tipo_out(row)
