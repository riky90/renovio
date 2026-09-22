"""CRUD listini/prezzi (ADM-01, D-09/D-10/D-13): creazione Listino per
citta nuova + mappatura ComuneListino, CRUD categoria (base_eur_mq/
coefficiente_impresa), CRUD voce a livello line-item (prezzo/UM, chiave
naturale stabile — D-09 "ritocchi puntuali su voci").

Ogni route ha `Depends(require_admin)` (T-04-07/D-10/D-22): questa e'
l'unica sede in cui `coefficiente_impresa`/`base_eur_mq` sono esposti.
Righe mancanti -> 404 (nessun ownership check, solo il gate require_admin,
04-RESEARCH.md Code Examples). Nessun edit/upsert azzera righe assenti dal
payload (D-24): DELETE elimina sempre e solo la riga esplicita indicata.

Le stime gia' salvate NON leggono queste tabelle (snapshot congelato,
D-11) — un edit qui ha effetto solo sulle stime calcolate DOPO l'edit.

`PATCH /voci/{id}` aggiorna DELIBERATAMENTE solo prezzo_cliente/um — la
descrizione/il codice non sono editabili via CRUD (stabilita' della chiave
naturale `(sottocategoria_id, codice-o-descrizione)` per le voci senza
codice, famiglie B/C/D catalogo: un successivo upload Excel deve poter
ri-matchare la riga per chiave anziche' duplicarla, Pitfall 2/Blocker #2,
limite noto v1 risolto lato prodotto — non un oversight).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from slugify import slugify
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies.auth import get_db, require_admin
from app.models.catalogo import ComuneListino
from app.models.dettaglio_pro import Voce
from app.models.export_log import ExportLog
from app.models.listino import Listino, ListinoCategoria
from app.schemas.admin_listino import (
    ListinoAdminIn,
    ListinoAdminOut,
    ListinoCategoriaAdminIn,
    ListinoCategoriaAdminOut,
    ListinoCategoriaPatchIn,
    ListinoPatchIn,
    VoceAdminIn,
    VoceAdminOut,
)
from app.services.export_excel.listino import build_workbook_listino
from app.services.export_excel.workbook import MIME_XLSX, build_filename

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


def _to_voce_out(row: Voce) -> VoceAdminOut:
    return VoceAdminOut(
        id=row.id,
        sottocategoria_id=row.sottocategoria_id,
        codice=row.codice,
        descrizione=row.descrizione,
        um=row.um,
        prezzo_cliente=row.prezzo_unitario_cliente,
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


@router.get("/{listino_id}/export.xlsx")
def esporta_listino(
    listino_id: int,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Export piatto del listino (D-01/D-03/D-09/D-11/D-12/D-15): un
    workbook con foglio `ISTRUZIONI` + foglio `voci`, una riga per `Voce`,
    nessuna colonna di margine. Ogni download riuscito scrive una riga in
    `export_log` PRIMA di restituire la risposta — se la scrittura del log
    fallisce l'eccezione propaga (nessun try/except che lasci passare il
    file senza traccia, CUR-04)."""
    listino = db.get(Listino, listino_id)
    if listino is None:
        raise HTTPException(404, "Listino non trovato")

    file_bytes, righe = build_workbook_listino(db, listino_id)
    filename = build_filename("listino")

    db.add(ExportLog(user_id=user.id, risorsa="listino", righe=righe, include_margine=False))
    db.commit()

    return StreamingResponse(
        iter([file_bytes]),
        media_type=MIME_XLSX,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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


@router.get("/categorie/{listino_categoria_id}/voci", response_model=list[VoceAdminOut])
def lista_voci_per_sottocategoria(
    listino_categoria_id: int,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[VoceAdminOut]:
    """Elenca le Voce della sottocategoria indicata dall'id nel path (l'id
    e' quello di `Sottocategoria`, coerente con `Voce.sottocategoria_id`;
    il segmento resta `categorie/{id}/voci` per allinearsi al raggruppamento
    categoria->sottocategoria->voce del computo, senza esporre un router
    dedicato alle sottocategorie in questo piano)."""
    rows = (
        db.execute(
            select(Voce)
            .where(Voce.sottocategoria_id == listino_categoria_id)
            .order_by(Voce.ordine, Voce.id)
        )
        .scalars()
        .all()
    )
    return [_to_voce_out(row) for row in rows]


@router.patch("/voci/{voce_id}", response_model=VoceAdminOut)
def modifica_voce(
    voce_id: int,
    payload: VoceAdminIn,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> VoceAdminOut:
    """Aggiorna SOLO prezzo_cliente/um — MAI descrizione/codice, vedi
    docstring di modulo (Pitfall 2/Blocker #2)."""
    voce = db.get(Voce, voce_id)
    if voce is None:
        raise HTTPException(404, "Voce non trovata")

    voce.prezzo_unitario_cliente = payload.prezzo_cliente
    voce.um = payload.um

    db.commit()
    db.refresh(voce)
    return _to_voce_out(voce)


@router.delete("/voci/{voce_id}", status_code=204)
def elimina_voce(
    voce_id: int,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    """Azione esplicita, mai side-effect di bulk (D-24)."""
    voce = db.get(Voce, voce_id)
    if voce is None:
        raise HTTPException(404, "Voce non trovata")

    db.delete(voce)
    db.commit()
