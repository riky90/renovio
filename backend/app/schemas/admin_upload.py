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

Formato piatto (08-03, CUR-01/CUR-02): `VoceRigaIn.id` e' la colonna
tecnica del re-import (D-03). `VoceRigaIn.campi_presenti` e' la convenzione
scelta per distinguere "campo assente dal file" (non toccare, D-09) da
"campo presente con valore nullo" (cancella, solo se la colonna a
database e' nullable): `None` significa "tutti i campi sono presenti" —
il comportamento legacy di `parse_computo`, che non ha questo concetto e
sovrascrive sempre incondizionatamente — mentre un `set[str]` esplicito
elenca SOLO i nomi-campo che la riga porta con se'; un nome assente da
questo insieme non deve mai essere scritto a database, qualunque valore
il campo omonimo abbia sull'istanza (che a quel punto e' un placeholder
mai letto, non un dato reale). Popolato da
`listino_upload_service.parse_flat_listino`, consumato da `compute_diff`
e dagli applicatori id-based di `apply_diff_idempotent`.
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

    id: int | None = None
    categoria_code: str = Field(min_length=1, max_length=32)
    sottocategoria_codice: str | None = None
    sottocategoria_nome: str = Field(min_length=1, max_length=200)
    sottocategoria_famiglia: str = Field(min_length=1, max_length=16)
    sottocategoria_ordine: int = 0
    codice: str | None = None
    descrizione: str = Field(min_length=1, max_length=300)
    um: str = Field(min_length=1, max_length=16)
    # ge=0, non gt=0: il DB contiene legittimamente voci a prezzo 0 ("non
    # ancora quotate", vedi listino_upload_service._sotto_dict_to_righe) e
    # il round-trip export->import (D-12) deve poterle rileggere senza
    # scartarle. La regola di business "un prezzo caricato da file deve
    # essere > 0" resta applicata dove il file e' input umano non ancora
    # convalidato: in parse_computo (_sotto_dict_to_righe) per OGNI riga, e
    # in parse_flat_listino per le sole righe NUOVE (senza id) — una riga
    # esistente re-importata a 0 e' semplicemente il suo stato reale.
    prezzo_unitario_cliente: Decimal = Field(ge=0)
    ordine: int = 0
    livello: str | None = None
    campi_presenti: set[str] | None = None


class DiffRowOut(BaseModel):
    riga: VoceRigaIn
    valore_precedente: Decimal | None = None
    campi_modificati: list[str] = Field(default_factory=list)


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
    # Comuni aggiuntivi da mappare (in un solo passaggio) sullo stesso listino
    # di destinazione — oltre alla città principale del ramo `nuova_citta`.
    # Idempotente: rimappare un comune esistente ne aggiorna solo il listino.
    comuni_extra: list[str] = Field(default_factory=list)


class ImportResultOut(BaseModel):
    righe_importate: int
    listino_id: int
