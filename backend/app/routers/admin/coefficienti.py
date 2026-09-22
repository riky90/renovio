"""CRUD dei coefficienti del modello (ADM-02, D-12): tutte le famiglie che
l'admin può editare in v1 — moltiplicatori tipo×categoria, IVA per
categoria, extra (CSE/CSP, pratiche), coefficienti quantità-per-m² del
motore Pro — più `GET /base` in sola lettura di `ListinoCategoria.
base_eur_mq` per la UI Coefficienti (la scrittura di `base_eur_mq` resta
sul CRUD `/admin/listini`, 04-02, per non duplicare il percorso di
editing).

Ogni route ha `Depends(require_admin)` (T-04-38). Nessun edit azzera righe
non toccate: PATCH è sempre per singola riga via id/code, DELETE elimina
solo la riga indicata (D-24). `EstimationService.compute()` rilegge queste
tabelle ad ogni chiamata — nessuna cache — quindi un edit qui ha effetto
immediato sulla PROSSIMA stima calcolata (D-11); le stime già salvate non
sono toccate (snapshot congelato, invariante D-11 già valido da 04-02).

Non toccare `routers/admin/__init__.py`: resta l'unico punto di
aggregazione dei subrouter admin (04-02-PLAN.md Task 1).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies.auth import get_db, require_admin
from app.models.catalogo import Categoria, Extra, Moltiplicatore
from app.models.dettaglio_pro import CoefficienteQuantitaVoce
from app.models.export_log import ExportLog
from app.models.listino import ListinoCategoria
from app.schemas.admin_coefficienti import (
    BaseEurMqAdminOut,
    CategoriaIvaAdminOut,
    CoeffProAdminIn,
    CoeffProAdminOut,
    ExtraAdminCreateIn,
    ExtraAdminIn,
    ExtraAdminOut,
    IvaAdminIn,
    MoltiplicatoreAdminIn,
    MoltiplicatoreAdminOut,
)
from app.services.export_excel.parametri import build_workbook_parametri
from app.services.export_excel.workbook import MIME_XLSX, build_filename

router = APIRouter(prefix="/coefficienti", tags=["admin-coefficienti"])


def _to_moltiplicatore_out(row: Moltiplicatore) -> MoltiplicatoreAdminOut:
    return MoltiplicatoreAdminOut(
        id=row.id, tipo_code=row.tipo_code, categoria_code=row.categoria_code, valore=row.valore
    )


def _to_iva_out(row: Categoria) -> CategoriaIvaAdminOut:
    return CategoriaIvaAdminOut(code=row.code, nome=row.nome, iva_pct=row.iva_pct)


def _to_extra_out(row: Extra) -> ExtraAdminOut:
    return ExtraAdminOut(
        code=row.code,
        nome=row.nome,
        importo=row.importo,
        iva_pct=row.iva_pct,
        tipo_calcolo=row.tipo_calcolo,
        attivo=row.attivo,
    )


def _to_coeff_pro_out(row: CoefficienteQuantitaVoce) -> CoeffProAdminOut:
    return CoeffProAdminOut(
        id=row.id,
        voce_id=row.voce_id,
        tipo_code=row.tipo_code,
        valore=row.coefficiente_qta_per_mq,
        domanda_mirata_key=row.domanda_mirata_key,
        default_conteggio=row.default_conteggio,
    )


def _to_base_out(row: ListinoCategoria) -> BaseEurMqAdminOut:
    return BaseEurMqAdminOut(
        id=row.id, listino_id=row.listino_id, categoria_code=row.categoria_code, base_eur_mq=row.base_eur_mq
    )


# --- Export parametri motore (CUR-03, D-08, D-13) --------------------------


@router.get("/export.xlsx")
def esporta_parametri(
    margine: bool = False,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Workbook a cinque fogli dei parametri del motore. Di default
    (`margine=False`) il file NON contiene `coefficiente_impresa`: nessun
    foglio AVVISO, nome file senza marcatore. `?margine=true` produce la
    variante opt-in — marcata nel nome (`build_filename(con_margine=True)`),
    con foglio `AVVISO` in prima posizione — riservata comunque al ruolo
    admin (stesso `require_admin` di entrambe le varianti, T-08-31): il
    consulente non scarica nemmeno quella senza margine, perché
    `/admin/coefficienti` è già una pagina da cui è escluso (D-26).

    Ogni download riuscito scrive una riga in `export_log` PRIMA di
    restituire la risposta, distinguendo la variante presa
    (`include_margine`) — CUR-04, T-08-33."""
    file_bytes, righe = build_workbook_parametri(db, con_margine=margine)
    filename = build_filename("parametri-motore", con_margine=margine)

    db.add(ExportLog(user_id=user.id, risorsa="parametri", righe=righe, include_margine=margine))
    db.commit()

    return StreamingResponse(
        iter([file_bytes]),
        media_type=MIME_XLSX,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


# --- Moltiplicatori tipo x categoria ---------------------------------------


@router.get("/moltiplicatori", response_model=list[MoltiplicatoreAdminOut])
def lista_moltiplicatori(
    user=Depends(require_admin), db: Session = Depends(get_db)
) -> list[MoltiplicatoreAdminOut]:
    rows = db.execute(select(Moltiplicatore).order_by(Moltiplicatore.id)).scalars().all()
    return [_to_moltiplicatore_out(row) for row in rows]


@router.patch("/moltiplicatori/{moltiplicatore_id}", response_model=MoltiplicatoreAdminOut)
def modifica_moltiplicatore(
    moltiplicatore_id: int,
    payload: MoltiplicatoreAdminIn,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> MoltiplicatoreAdminOut:
    riga = db.get(Moltiplicatore, moltiplicatore_id)
    if riga is None:
        raise HTTPException(404, "Moltiplicatore non trovato")

    riga.valore = payload.valore

    db.commit()
    db.refresh(riga)
    return _to_moltiplicatore_out(riga)


# --- IVA per categoria -------------------------------------------------------


@router.get("/iva", response_model=list[CategoriaIvaAdminOut])
def lista_iva(user=Depends(require_admin), db: Session = Depends(get_db)) -> list[CategoriaIvaAdminOut]:
    rows = db.execute(select(Categoria).order_by(Categoria.ordine)).scalars().all()
    return [_to_iva_out(row) for row in rows]


@router.patch("/iva/{categoria_code}", response_model=CategoriaIvaAdminOut)
def modifica_iva(
    categoria_code: str,
    payload: IvaAdminIn,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> CategoriaIvaAdminOut:
    riga = db.get(Categoria, categoria_code)
    if riga is None:
        raise HTTPException(404, "Categoria non trovata")

    riga.iva_pct = payload.iva_pct

    db.commit()
    db.refresh(riga)
    return _to_iva_out(riga)


# --- Extra (CSE/CSP, pratiche) ----------------------------------------------


@router.get("/extra", response_model=list[ExtraAdminOut])
def lista_extra(user=Depends(require_admin), db: Session = Depends(get_db)) -> list[ExtraAdminOut]:
    rows = db.execute(select(Extra).order_by(Extra.code)).scalars().all()
    return [_to_extra_out(row) for row in rows]


@router.post("/extra", response_model=ExtraAdminOut, status_code=201)
def crea_extra(
    payload: ExtraAdminCreateIn,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> ExtraAdminOut:
    """Upsert per chiave naturale `code`: una seconda POST con lo stesso
    code aggiorna invece di duplicare (D-24, stesso pattern di
    `upsert_categoria` in 04-02)."""
    riga = db.get(Extra, payload.code)
    if riga is None:
        riga = Extra(
            code=payload.code,
            nome=payload.nome,
            importo=payload.importo,
            iva_pct=payload.iva_pct,
            tipo_calcolo=payload.tipo_calcolo,
            attivo=payload.attivo,
        )
        db.add(riga)
    else:
        riga.nome = payload.nome
        riga.importo = payload.importo
        riga.iva_pct = payload.iva_pct
        riga.tipo_calcolo = payload.tipo_calcolo
        riga.attivo = payload.attivo

    db.commit()
    db.refresh(riga)
    return _to_extra_out(riga)


@router.patch("/extra/{code}", response_model=ExtraAdminOut)
def modifica_extra(
    code: str,
    payload: ExtraAdminIn,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> ExtraAdminOut:
    riga = db.get(Extra, code)
    if riga is None:
        raise HTTPException(404, "Extra non trovato")

    if payload.nome is not None:
        riga.nome = payload.nome
    if payload.importo is not None:
        riga.importo = payload.importo
    if payload.iva_pct is not None:
        riga.iva_pct = payload.iva_pct
    if payload.attivo is not None:
        riga.attivo = payload.attivo

    db.commit()
    db.refresh(riga)
    return _to_extra_out(riga)


@router.delete("/extra/{code}", status_code=204)
def elimina_extra(
    code: str,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    """Elimina SOLO la riga indicata — mai un side-effect di bulk (D-24)."""
    riga = db.get(Extra, code)
    if riga is None:
        raise HTTPException(404, "Extra non trovato")

    db.delete(riga)
    db.commit()


# --- Coefficienti quantita-per-m2 Pro ---------------------------------------


@router.get("/coeff-pro", response_model=list[CoeffProAdminOut])
def lista_coeff_pro(user=Depends(require_admin), db: Session = Depends(get_db)) -> list[CoeffProAdminOut]:
    rows = db.execute(select(CoefficienteQuantitaVoce).order_by(CoefficienteQuantitaVoce.id)).scalars().all()
    return [_to_coeff_pro_out(row) for row in rows]


@router.patch("/coeff-pro/{coeff_id}", response_model=CoeffProAdminOut)
def modifica_coeff_pro(
    coeff_id: int,
    payload: CoeffProAdminIn,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> CoeffProAdminOut:
    riga = db.get(CoefficienteQuantitaVoce, coeff_id)
    if riga is None:
        raise HTTPException(404, "Coefficiente quantita-per-m2 non trovato")

    riga.coefficiente_qta_per_mq = payload.valore

    db.commit()
    db.refresh(riga)
    return _to_coeff_pro_out(riga)


# --- Base €/m² (sola lettura, la scrittura resta su /admin/listini) --------


@router.get("/base", response_model=list[BaseEurMqAdminOut])
def lista_base_eur_mq(user=Depends(require_admin), db: Session = Depends(get_db)) -> list[BaseEurMqAdminOut]:
    rows = db.execute(select(ListinoCategoria).order_by(ListinoCategoria.listino_id, ListinoCategoria.id)).scalars().all()
    return [_to_base_out(row) for row in rows]
