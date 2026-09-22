"""Upload Excel listino a due passi (ADM-01, D-18/D-19/D-20): `POST /preview`
(parse + diff, NIENTE scritture) e `POST /confirm` (upsert idempotente,
mai distruttivo, D-24), con destinazione discriminata (listino esistente O
nuova città, D-13). Round-trip stateless (04-RESEARCH.md Pattern 4): il
client re-invia a `/confirm` il payload diff completo ricevuto da
`/preview`, nessuna cache/sessione server per il pending upload.

Ogni route ha `Depends(require_admin)` (T-04-22/D-22).

Non toccare `routers/admin/__init__.py`: questo file resta il solo punto
di estensione per le route di questa sezione (04-02-PLAN.md Task 1).
"""

from __future__ import annotations

import io

import openpyxl
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from openpyxl.utils.exceptions import InvalidFileException
from pydantic import TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from app.dependencies.auth import get_db, require_admin
from app.schemas.admin_upload import (
    DiffConfirmIn,
    DiffPreviewOut,
    ImportResultOut,
    UploadTarget,
)
from app.services.import_excel.flat import e_formato_piatto, leggi_timestamp_export
from app.services.listino_upload_service import (
    UploadValidationError,
    apply_diff_idempotent,
    compute_diff,
    parse_computo,
    parse_flat_listino,
    resolve_destinazione,
    validate_upload,
    zip_error_types,
)

router = APIRouter(prefix="/upload-listino", tags=["admin-upload-listino"])

_target_adapter: TypeAdapter = TypeAdapter(UploadTarget)


@router.post("/preview", response_model=DiffPreviewOut)
async def preview_upload(
    file: UploadFile,
    target: str = Form(...),
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> DiffPreviewOut:
    """Parse + diff contro lo stato DB reale — NIENTE scritture (nemmeno
    per il ramo nuova città, che confronta contro un set vuoto, T-04-42)."""
    try:
        target_obj = _target_adapter.validate_json(target)
    except ValidationError as exc:
        raise HTTPException(400, f"Destinazione non valida: {exc}") from exc

    content = await file.read()
    try:
        validate_upload(file.filename, len(content))
    except UploadValidationError as exc:
        raise HTTPException(400, str(exc)) from exc

    try:
        listino, target_descr = resolve_destinazione(db, target_obj)
    except UploadValidationError as exc:
        raise HTTPException(404, str(exc)) from exc

    # Il workbook si carica UNA sola volta per decidere il formato (D-01):
    # il computo originale non ha mai il foglio ISTRUZIONI, il formato
    # piatto di 08-01 lo ha sempre. Nessuna seconda route, nessun parametro
    # nuovo in richiesta — il client esistente non cambia di una riga.
    try:
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    except (InvalidFileException, KeyError, OSError, *zip_error_types()) as exc:
        raise HTTPException(400, f"File .xlsx non leggibile: {exc}") from exc

    generato_il = leggi_timestamp_export(wb)
    try:
        if e_formato_piatto(wb):
            righe, scarti = parse_flat_listino(content)
        else:
            righe, scarti = parse_computo(content)
    except UploadValidationError as exc:
        raise HTTPException(400, str(exc)) from exc

    nuove, modificate, scarti_diff = compute_diff(db, righe, listino, generato_il)
    return DiffPreviewOut(
        nuove=nuove, modificate=modificate, scarti=[*scarti, *scarti_diff],
        target_descr=target_descr, generato_il=generato_il,
    )


@router.post("/confirm", response_model=ImportResultOut)
def confirm_upload(
    payload: DiffConfirmIn,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> ImportResultOut:
    """Applica l'upsert idempotente (mai un DELETE implicito, D-24). Ramo
    nuova città: crea Listino + ComuneListino PRIMA dell'upsert voci
    (D-13)."""
    try:
        listino_id, righe_importate = apply_diff_idempotent(
            db, payload.target, payload.nuove, payload.modificate, payload.comuni_extra
        )
    except UploadValidationError as exc:
        raise HTTPException(404, str(exc)) from exc

    db.commit()
    return ImportResultOut(righe_importate=righe_importate, listino_id=listino_id)
