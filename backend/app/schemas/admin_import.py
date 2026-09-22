"""Contratto generico dell'import Excel per risorsa (piano 08-06, CUR-01/CUR-02).

Round-trip stateless (Fase 4/08-03, riusato qui): `POST /{risorsa}/preview`
non scrive nulla e ritorna l'intero diff al client; `POST /{risorsa}/confirm`
si aspetta che il client re-invii lo stesso payload (righe nuove/modificate)
— nessuna cache/sessione server per il pending import. Ogni risorsa futura
(parametri qui, lead/altre nei piani successivi) usa questo stesso contratto
dichiarato una sola volta, invece di uno schema dedicato a coppia di route.

`RigaPiattaIn.id` e' sempre una stringa: la maggior parte delle risorse ha
una PK intera (serializzata come stringa), ma `Extra.code` e' una PK
testuale — un contratto a stringa evita due varianti dello stesso schema.
`campi_da_cancellare` elenca i nomi-campo che il file marcava con
`#CANCELLA#` (vedi `services/import_excel/flat.py`): quei campi NON
compaiono in `valori` (che porta solo i valori reali), cosi' un handler
non deve mai distinguere "valore None reale" da "cancellazione richiesta"
ispezionando `valori` — la distinzione e' gia' nella struttura.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.admin_upload import ScartoRowOut


class RigaPiattaIn(BaseModel):
    """Una riga proposta per l'import, gia' risolta sul foglio di
    provenienza. Sufficiente per rieseguire diff/apply in `/confirm` senza
    ri-parsare il file (round-trip stateless)."""

    foglio: str = Field(min_length=1, max_length=64)
    id: str | None = None
    valori: dict[str, Any] = Field(default_factory=dict)
    campi_da_cancellare: list[str] = Field(default_factory=list)


class DiffRigaOut(BaseModel):
    """Una riga di diff pronta per la UI: `chiave_descr` e' come la riga si
    presenta a schermo (es. `"leggera x A-EDILE"`), non un id tecnico."""

    foglio: str
    id: str | None
    chiave_descr: str
    nuova: bool
    campi_modificati: list[str] = Field(default_factory=list)
    valori_precedenti: dict[str, Any] = Field(default_factory=dict)
    valori_nuovi: dict[str, Any] = Field(default_factory=dict)
    # D-11: True se il record a database e' stato modificato DOPO il
    # timestamp di generazione del file caricato — informativo, non
    # blocca ne' /confirm ne' l'apply (vedi services/import_excel/registry.py).
    riga_modificata_dopo_export: bool = False


class DiffPiattoOut(BaseModel):
    risorsa: str
    nuove: list[DiffRigaOut] = Field(default_factory=list)
    modificate: list[DiffRigaOut] = Field(default_factory=list)
    scarti: list[ScartoRowOut] = Field(default_factory=list)
    generato_il: datetime | None = None


class ConfirmPiattoIn(BaseModel):
    risorsa: str = Field(min_length=1, max_length=32)
    nuove: list[RigaPiattaIn] = Field(default_factory=list)
    modificate: list[RigaPiattaIn] = Field(default_factory=list)
