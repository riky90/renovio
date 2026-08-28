"""CRUD listini/prezzi (ADM-01, D-09/D-10/D-13): creazione Listino per
citta nuova + mappatura ComuneListino, CRUD categoria (base_eur_mq/
coefficiente_impresa). Il CRUD voce (prezzo/UM) e' aggiunto dal Task 3 di
questo stesso piano.

Ogni route ha `Depends(require_admin)` (T-04-07/D-10/D-22): questa e'
l'unica sede in cui `coefficiente_impresa`/`base_eur_mq` sono esposti.
Righe mancanti -> 404 (nessun ownership check, solo il gate require_admin,
04-RESEARCH.md Code Examples). Nessun edit/upsert azzera righe assenti dal
payload (D-24): DELETE elimina sempre e solo la riga esplicita indicata.

Le stime gia' salvate NON leggono queste tabelle (snapshot congelato,
D-11) — un edit qui ha effetto solo sulle stime calcolate DOPO l'edit.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from slugify import slugify
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies.auth import get_db, require_admin
from app.models.catalogo import ComuneListino
from app.models.listino import Listino, ListinoCategoria
from app.schemas.admin_listino import (
    ListinoAdminIn,
    ListinoAdminOut,
    ListinoCategoriaAdminIn,
    ListinoCategoriaAdminOut,
    ListinoCategoriaPatchIn,
    ListinoPatchIn,
)

router = APIRouter(prefix="/listini", tags=["admin-listini"])


def _to_listino_out(row: Listino) -> ListinoAdminOut:
    return ListinoAdminOut(
        id=row.id,
        nome=row.nome,
        citta_riferimento=row.citta_riferimento,
        is_default=row.is_default,
        attivo=row.attivo,
    )


def _to_categoria_out(row: ListinoCategoria) -> ListinoCategoriaAdminOut:
    return ListinoCategoriaAdminOut(
        id=row.id,
        listino_id=row.listino_id,
        categoria_code=row.categoria_code,
        base_eur_mq=row.base_eur_mq,
        coefficiente_impresa=row.coefficiente_impresa,
    )


@router.get("", response_model=list[ListinoAdminOut])
def lista_listini(user=Depends(require_admin), db: Session = Depends(get_db)) -> list[ListinoAdminOut]:
    rows = db.execute(select(Listino).order_by(Listino.id)).scalars().all()
    return [_to_listino_out(row) for row in rows]


@router.post("", response_model=ListinoAdminOut, status_code=201)
def crea_listino(
    payload: ListinoAdminIn,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> ListinoAdminOut:
    """Crea un nuovo Listino e, nella stessa transazione, la mappatura
    ComuneListino per la citta indicata (D-13, Success Criterion #3) — una
    citta nuova diventa subito risolvibile da /api/v1/stima senza
    fallback. Upsert idempotente sulla mappatura per comune_slug: non
    azzera/duplica mappature esistenti (D-24)."""
    listino = Listino(
        nome=payload.nome,
        citta_riferimento=payload.citta_riferimento,
        is_default=payload.is_default,
    )
    db.add(listino)
    db.flush()

    slug = slugify(payload.citta_riferimento)
    comune = db.query(ComuneListino).filter_by(comune_slug=slug).one_or_none()
    if comune is None:
        comune = ComuneListino(
            comune_nome=payload.citta_riferimento,
            comune_slug=slug,
            listino_id=listino.id,
        )
        db.add(comune)
    else:
        comune.comune_nome = payload.citta_riferimento
        comune.listino_id = listino.id

    db.commit()
    db.refresh(listino)
    return _to_listino_out(listino)


@router.patch("/{listino_id}", response_model=ListinoAdminOut)
def modifica_listino(
    listino_id: int,
    payload: ListinoPatchIn,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> ListinoAdminOut:
    listino = db.get(Listino, listino_id)
    if listino is None:
        raise HTTPException(404, "Listino non trovato")

    if payload.nome is not None:
        listino.nome = payload.nome
    if payload.is_default is not None:
        listino.is_default = payload.is_default
    if payload.attivo is not None:
        listino.attivo = payload.attivo

    db.commit()
    db.refresh(listino)
    return _to_listino_out(listino)


@router.get("/{listino_id}/categorie", response_model=list[ListinoCategoriaAdminOut])
def lista_categorie(
    listino_id: int,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[ListinoCategoriaAdminOut]:
    rows = (
        db.execute(
            select(ListinoCategoria)
            .where(ListinoCategoria.listino_id == listino_id)
            .order_by(ListinoCategoria.id)
        )
        .scalars()
        .all()
    )
    return [_to_categoria_out(row) for row in rows]


@router.post("/{listino_id}/categorie", response_model=ListinoCategoriaAdminOut, status_code=201)
def upsert_categoria(
    listino_id: int,
    payload: ListinoCategoriaAdminIn,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> ListinoCategoriaAdminOut:
    """Upsert per chiave naturale (listino_id, categoria_code): una seconda
    POST della stessa categoria aggiorna invece di duplicare (D-24)."""
    listino = db.get(Listino, listino_id)
    if listino is None:
        raise HTTPException(404, "Listino non trovato")

    riga = (
        db.query(ListinoCategoria)
        .filter_by(listino_id=listino_id, categoria_code=payload.categoria_code)
        .one_or_none()
    )
    if riga is None:
        riga = ListinoCategoria(
            listino_id=listino_id,
            categoria_code=payload.categoria_code,
            base_eur_mq=payload.base_eur_mq,
            coefficiente_impresa=payload.coefficiente_impresa,
        )
        db.add(riga)
    else:
        riga.base_eur_mq = payload.base_eur_mq
        riga.coefficiente_impresa = payload.coefficiente_impresa

    db.commit()
    db.refresh(riga)
    return _to_categoria_out(riga)


@router.patch("/categorie/{categoria_id}", response_model=ListinoCategoriaAdminOut)
def modifica_categoria(
    categoria_id: int,
    payload: ListinoCategoriaPatchIn,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> ListinoCategoriaAdminOut:
    riga = db.get(ListinoCategoria, categoria_id)
    if riga is None:
        raise HTTPException(404, "Categoria listino non trovata")

    if payload.base_eur_mq is not None:
        riga.base_eur_mq = payload.base_eur_mq
    if payload.coefficiente_impresa is not None:
        riga.coefficiente_impresa = payload.coefficiente_impresa

    db.commit()
    db.refresh(riga)
    return _to_categoria_out(riga)


@router.delete("/categorie/{categoria_id}", status_code=204)
def elimina_categoria(
    categoria_id: int,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    """Elimina SOLO la riga indicata — mai un side-effect di bulk (D-24)."""
    riga = db.get(ListinoCategoria, categoria_id)
    if riga is None:
        raise HTTPException(404, "Categoria listino non trovata")

    db.delete(riga)
    db.commit()
