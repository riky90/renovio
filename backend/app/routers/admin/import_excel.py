"""Endpoint generico di import Excel per risorsa (piano 08-06, CUR-01).

`POST /import-excel/{risorsa}/preview` (parse + diff, NIENTE scritture) e
`POST /import-excel/{risorsa}/confirm` (apply, round-trip stateless — il
client re-invia le righe proposte in preview). Il dispatch sulla risorsa
passa SEMPRE da `risolvi_handler` (registro di `services/import_excel/
registry.py`): una `{risorsa}` non registrata risponde 404 con messaggio
esplicito, mai una costruzione dinamica di nome modulo/`getattr` su input
utente (T-08-52).

Ogni route ha `Depends(require_admin)` (T-08-53). Il file caricato passa
prima da `validate_upload` (10MB, `.xlsx`, D-20) e poi da `zip_error_types()`
per gli archivi corrotti — entrambi PRIMA di `load_workbook`, stesso
ordine di `upload_listino.py`. Il file del computo originale (senza il
foglio `ISTRUZIONI`) e' rifiutato con 400 descritto: ha il suo endpoint
dedicato (`/admin/upload-listino`), non questo generico (D-01).
"""

from __future__ import annotations

import io

import openpyxl
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from openpyxl.utils.exceptions import InvalidFileException
from sqlalchemy.orm import Session

from app.dependencies.auth import get_db, require_admin
from app.schemas.admin_import import ConfirmPiattoIn, DiffPiattoOut
from app.services.import_excel.flat import e_formato_piatto, leggi_timestamp_export
from app.services.import_excel.registry import RisorsaImportSconosciuta, risolvi_handler
from app.services.listino_upload_service import UploadValidationError, validate_upload, zip_error_types

# Import per side-effect: registra la risorsa "parametri" in HANDLER (piano
# 08-06). Ogni risorsa futura (08-07, 08-08) aggiunge qui la sua riga
# — mai una route nuova (T-08-52).
import app.services.import_excel.parametri  # noqa: F401

router = APIRouter(prefix="/import-excel", tags=["admin-import-excel"])


@router.post("/{risorsa}/preview", response_model=DiffPiattoOut)
async def preview_import(
    risorsa: str,
    file: UploadFile,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> DiffPiattoOut:
    try:
        handler = risolvi_handler(risorsa)
    except RisorsaImportSconosciuta as exc:
        raise HTTPException(404, str(exc)) from exc

    content = await file.read()
    try:
        validate_upload(file.filename, len(content))
    except UploadValidationError as exc:
        raise HTTPException(400, str(exc)) from exc

    try:
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    except (InvalidFileException, KeyError, OSError, *zip_error_types()) as exc:
        raise HTTPException(400, f"File .xlsx non leggibile: {exc}") from exc

    if not e_formato_piatto(wb):
        raise HTTPException(400, "Il file non e' nel formato piatto di import: sembra il computo originale, che ha il suo endpoint dedicato (/admin/upload-listino)")

    righe, scarti_parse = handler.parse(wb)
    nuove, modificate, scarti_diff = handler.diff(db, righe)

    return DiffPiattoOut(
        risorsa=risorsa,
        nuove=nuove,
        modificate=modificate,
        scarti=[*scarti_parse, *scarti_diff],
        generato_il=leggi_timestamp_export(wb),
    )


@router.post("/{risorsa}/confirm")
def confirm_import(
    risorsa: str,
    payload: ConfirmPiattoIn,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    try:
        handler = risolvi_handler(risorsa)
    except RisorsaImportSconosciuta as exc:
        raise HTTPException(404, str(exc)) from exc

    righe_applicate = handler.apply(db, payload.nuove, payload.modificate, is_admin=True)
    db.commit()
    return {"righe_applicate": righe_applicate}
