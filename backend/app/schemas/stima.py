"""Request/response schemas for POST /api/v1/stima.

`StimaRequest` bounds untrusted input (ASVS V5, T-03-02). The response
models (`CategoriaOut`, `ExtraOut`, `TotaleOut`, `StimaResponse`) declare
ONLY the fields in the API contract from 01-RESEARCH.md — no
`base_eur_mq`, `moltiplicatore`, `coefficiente_impresa`, or
`prezzo_impresa` anywhere in this module (T-03-01, EST-05).
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class TipoEnum(str, Enum):
    leggera = "leggera"
    moderata = "moderata"
    totale = "totale"


class DestinazioneEnum(str, Enum):
    """Abitazione principale vs altri immobili: e' cio' che separa il 50% dal
    36% sul bonus ristrutturazione."""

    prima_casa = "prima_casa"
    altro = "altro"


class StimaRequest(BaseModel):
    citta: str = Field(min_length=1, max_length=100)
    mq: int = Field(ge=1, le=2000)
    tipo: TipoEnum
    # DEFAULT OBBLIGATORIO: decine di test e i client esistenti postano
    # {citta, mq, tipo}. Senza default questo campo sarebbe un breaking change
    # dell'API pubblica.
    destinazione: DestinazioneEnum = DestinazioneEnum.prima_casa


class StimaInputEcho(BaseModel):
    citta: str
    mq: int
    tipo: TipoEnum
    # Anche qui con default: gli snapshot v1 congelati non hanno questa chiave
    # e devono restare ricostruibili (`StimaInputEcho(**snapshot["input"])`).
    destinazione: DestinazioneEnum = DestinazioneEnum.prima_casa


class CategoriaOut(BaseModel):
    code: str
    nome: str
    imponibile_min: Decimal
    imponibile_max: Decimal
    iva_pct: Decimal
    iva_min: Decimal
    iva_max: Decimal
    totale_min: Decimal
    totale_max: Decimal


class ExtraOut(BaseModel):
    """Fixed single values — no min/max range on extras (D-13/01-02 rule)."""

    code: str
    nome: str
    importo: Decimal
    iva_pct: Decimal


class TotaleOut(BaseModel):
    imponibile_min: Decimal
    imponibile_max: Decimal
    iva_min: Decimal
    iva_max: Decimal
    totale_min: Decimal
    totale_max: Decimal


class BonusDettaglioOut(BaseModel):
    code: str
    nome: str
    descrizione: str | None
    base_min: Decimal
    base_max: Decimal
    aliquota_pct: Decimal
    tetto_spesa_eur: Decimal | None
    tetto_modalita: str | None
    tetto_raggiunto: bool
    rate_annuali: int
    detrazione_min: Decimal
    detrazione_max: Decimal
    rata_annua_min: Decimal
    rata_annua_max: Decimal


class BonusOut(BaseModel):
    """Il disclaimer viaggia QUI DENTRO, non accanto: cosi' finisce nello
    snapshot congelato e nel PDF, e non e' rimovibile dal client. E' materia
    fiscale — la stima e' commerciale, non consulenza."""

    bonus: list[BonusDettaglioOut]
    detrazione_min: Decimal
    detrazione_max: Decimal
    rata_annua_min: Decimal
    rata_annua_max: Decimal
    disclaimer: str


class StimaResponse(BaseModel):
    input: StimaInputEcho
    fallback: bool
    disclaimer: str | None
    valuta: str
    categorie: list[CategoriaOut]
    extra: list[ExtraOut]
    totale: TotaleOut
    # None = nessun bonus applicabile (o snapshot v1 salvato prima di questa
    # feature). Mai una sezione a zero.
    bonus: BonusOut | None = None
