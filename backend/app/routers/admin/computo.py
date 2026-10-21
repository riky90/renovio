"""Admin del computo parametrico (Fase 11): Excel e anteprima con traccia.

- `GET  /admin/computo/export.xlsx` — grandezze, termini, regole, valori delle
  opzioni e preset in un file (CUR3-01).
- `POST /admin/computo/import?applica=false|true` — anteprima o applicazione
  del file: tutto o niente, con gli errori di curatela per foglio e riga.
- `GET  /admin/computo/validazione` — gli errori di curatela del computo a DB.
- `POST /admin/computo/anteprima` — il computo di una stima con il valore di
  ogni grandezza e la traccia di ogni voce (RGL-05): lo strumento con cui si
  tara.

Tutte le route sono `require_admin`. Nessuna espone il coefficiente impresa:
l'anteprima porta solo quantita' e importi cliente.
"""

from __future__ import annotations

import io
from decimal import Decimal
from typing import Any

import openpyxl
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from openpyxl.utils.exceptions import InvalidFileException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.dependencies.auth import get_db, require_admin
from app.models.catalogo import TipoRistrutturazione
from app.models.export_log import ExportLog
from app.services.city_resolver import resolve_listino
from app.services.computo import computo_free, valida_computo
from app.services.computo_excel import esporta_computo, importa_computo
from app.services.export_excel.workbook import MIME_XLSX, build_filename
from app.services.listino_upload_service import (
    UploadValidationError,
    validate_upload,
    zip_error_types,
)

router = APIRouter(prefix="/computo", tags=["admin-computo"])


class EsitoImportOut(BaseModel):
    applicato: bool
    errori: list[str]
    conteggi: dict[str, int]


class ValidazioneOut(BaseModel):
    errori: list[str]


class AnteprimaComputoIn(BaseModel):
    citta: str = Field(default="Reggio Emilia", max_length=200)
    mq: int = Field(ge=1, le=10_000)
    tipo: str = Field(max_length=32)
    risposte: dict[str, Any] = Field(default_factory=dict)


class GrandezzaOut(BaseModel):
    code: str
    nome: str
    um: str
    valore: Decimal
    origine: str


class VoceComputoOut(BaseModel):
    codice: str | None
    descrizione: str
    um: str
    categoria_code: str
    quantita: Decimal
    importo: Decimal
    traccia: str


class AnteprimaComputoOut(BaseModel):
    usa_computo: bool
    grandezze: list[GrandezzaOut]
    voci: list[VoceComputoOut]
    per_categoria: dict[str, Decimal]


@router.get("/export.xlsx")
def esporta(user=Depends(require_admin), db: Session = Depends(get_db)) -> StreamingResponse:
    file_bytes, righe = esporta_computo(db)
    db.add(ExportLog(user_id=user.id, risorsa="computo", righe=righe, include_margine=False))
    db.commit()
    return StreamingResponse(
        iter([file_bytes]),
        media_type=MIME_XLSX,
        headers={
            "Content-Disposition": f'attachment; filename="{build_filename("computo-parametrico")}"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/import", response_model=EsitoImportOut)
async def importa(
    file: UploadFile,
    applica: bool = False,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> EsitoImportOut:
    content = await file.read()
    try:
        validate_upload(file.filename, len(content))
    except UploadValidationError as exc:
        raise HTTPException(400, str(exc)) from exc
    try:
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    except (InvalidFileException, KeyError, OSError, *zip_error_types()) as exc:
        raise HTTPException(400, f"File .xlsx non leggibile: {exc}") from exc
    esito = importa_computo(db, wb, applica=applica)
    return EsitoImportOut(applicato=esito.applicato, errori=esito.errori, conteggi=esito.conteggi)


@router.get("/validazione", response_model=ValidazioneOut)
def validazione(user=Depends(require_admin), db: Session = Depends(get_db)) -> ValidazioneOut:
    return ValidazioneOut(errori=valida_computo(db))


@router.post("/anteprima", response_model=AnteprimaComputoOut)
def anteprima(
    payload: AnteprimaComputoIn,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> AnteprimaComputoOut:
    if db.get(TipoRistrutturazione, payload.tipo) is None:
        raise HTTPException(400, f"Tipo di ristrutturazione '{payload.tipo}' inesistente")
    listino, _fallback = resolve_listino(db, payload.citta)
    risultato = computo_free(db, listino, mq=payload.mq, tipo=payload.tipo, risposte=payload.risposte)
    if risultato is None:
        return AnteprimaComputoOut(usa_computo=False, grandezze=[], voci=[], per_categoria={})
    return AnteprimaComputoOut(
        usa_computo=True,
        grandezze=[
            GrandezzaOut(code=g.code, nome=g.nome, um=g.um, valore=g.valore, origine=g.origine)
            for g in risultato.grandezze.values()
        ],
        voci=[
            VoceComputoOut(
                codice=v.codice,
                descrizione=v.descrizione,
                um=v.um,
                categoria_code=v.categoria_code,
                quantita=v.quantita.quantize(Decimal("0.01")),
                importo=v.importo.quantize(Decimal("1")),
                traccia=v.traccia,
            )
            for v in risultato.voci
        ],
        per_categoria={k: v.quantize(Decimal("1")) for k, v in risultato.per_categoria.items()},
    )
