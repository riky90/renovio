"""Schemi per l'upload Excel listino a due passi (ADM-01, D-18/D-19/D-20).

Round-trip stateless (04-RESEARCH.md Pattern 4, Q2 RESOLVED): `POST /preview`
non scrive nulla e ritorna l'intero diff al client; `POST /confirm` si
aspetta che il client re-invii lo stesso payload (righe nuove/modificate)
insieme alla destinazione — nessuna cache/sessione server per il pending
upload.

`UploadTarget` e' discriminato su `kind`: `"esistente"` (listino_id gia'
presente) oppure `"nuova_citta"` (crea Listino+ComuneListino SOLO in
confirm, mai in preview — D-13, T-04-42).

Anti-leak (D-22): nessun campo qui espone `coefficiente_impresa`/
`base_eur_mq` — l'upload tocca solo Sottocategoria/Voce (dettaglio Pro,
D-10: Voce non ha colonne di margine per costruzione).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class UploadTargetEsistente(BaseModel):
    kind: Literal["esistente"] = "esistente"
    listino_id: int


class UploadTargetNuovaCitta(BaseModel):
    kind: Literal["nuova_citta"] = "nuova_citta"
    citta: str = Field(min_length=1, max_length=200)
    is_default: bool = False


UploadTarget = Annotated[
    Union[UploadTargetEsistente, UploadTargetNuovaCitta],
    Field(discriminator="kind"),
]


class VoceRigaIn(BaseModel):
    """Una riga-voce proposta dal parsing Excel, con la sua collocazione
    gerarchica — sufficiente per rieseguire l'upsert in `/confirm` senza
    ri-parsare il file (round-trip stateless)."""

    categoria_code: str = Field(min_length=1, max_length=32)
    sottocategoria_codice: str | None = None
    sottocategoria_nome: str = Field(min_length=1, max_length=200)
    sottocategoria_famiglia: str = Field(min_length=1, max_length=16)
    sottocategoria_ordine: int = 0
    codice: str | None = None
    descrizione: str = Field(min_length=1, max_length=300)
    um: str = Field(min_length=1, max_length=16)
    prezzo_unitario_cliente: Decimal = Field(gt=0)
    ordine: int = 0


class DiffRowOut(BaseModel):
    riga: VoceRigaIn
    valore_precedente: Decimal | None = None


class ScartoRowOut(BaseModel):
    riga: int
    motivo: str


class DiffPreviewOut(BaseModel):
    nuove: list[DiffRowOut]
    modificate: list[DiffRowOut]
    scarti: list[ScartoRowOut]
    target_descr: str


class DiffConfirmIn(BaseModel):
    target: UploadTarget
    nuove: list[VoceRigaIn] = Field(default_factory=list)
    modificate: list[VoceRigaIn] = Field(default_factory=list)


class ImportResultOut(BaseModel):
    righe_importate: int
    listino_id: int
