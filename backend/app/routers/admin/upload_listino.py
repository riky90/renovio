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

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from pydantic import TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from app.dependencies.auth import get_db, require_admin
from app.schemas.admin_upload import (
    DiffConfirmIn,
    DiffPreviewOut,
    ImportResultOut,
    UploadTarget,
)
from app.services.listino_upload_service import (
    UploadValidationError,
    apply_diff_idempotent,
    compute_diff,
    parse_computo,
    resolve_destinazione,
    validate_upload,
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

    try:
        righe, scarti = parse_computo(content)
    except UploadValidationError as exc:
        raise HTTPException(400, str(exc)) from exc

    nuove, modificate = compute_diff(db, righe, listino)
    return DiffPreviewOut(nuove=nuove, modificate=modificate, scarti=scarti, target_descr=target_descr)


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
        listino_id, righe_importate = apply_diff_idempotent(db, payload.target, payload.nuove, payload.modificate)
    except UploadValidationError as exc:
        raise HTTPException(404, str(exc)) from exc

    db.commit()
    return ImportResultOut(righe_importate=righe_importate, listino_id=listino_id)
