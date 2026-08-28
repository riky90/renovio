"""Schemi admin (D-10) per Listino/ListinoCategoria/Voce: fork DELIBERATO
dell'anti-leak di `schemas/stima.py` — queste classi *AdminOut* espongono
`coefficiente_impresa`/`base_eur_mq` (il margine interno) ma sono
utilizzabili SOLO nelle route `routers/admin/listini.py`, tutte dietro
`Depends(require_admin)`. Non sono mai la stessa classe usata dagli schemi
non-admin (`schemas/stima.py`, `schemas/stima_salvata.py`,
`schemas/dettaglio_pro.py`): campi chiusi, mai un campo opzionale
condiviso (04-RESEARCH.md Pattern 1).

`VoceAdminIn` espone SOLO `prezzo_cliente`/`um`: la descrizione/il codice
NON sono editabili via CRUD, per non destabilizzare la chiave naturale
`(sottocategoria_id, codice-o-descrizione)` delle voci senza codice
(famiglie B/C/D) — un successivo upload Excel deve poter ri-matchare la
riga per chiave, non crearne una duplicata (04-RESEARCH.md Pitfall 2,
Blocker #2, Q3 RESOLVED).
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class ListinoAdminIn(BaseModel):
    nome: str = Field(min_length=1, max_length=200)
    citta_riferimento: str = Field(min_length=1, max_length=200)
    is_default: bool = False


class ListinoAdminOut(BaseModel):
    id: int
    nome: str
    citta_riferimento: str
    is_default: bool
    attivo: bool


class ListinoPatchIn(BaseModel):
    """PATCH parziale: solo i campi presenti nel payload vengono modificati
    (nessun campo obbligatorio, D-24 — non azzera nulla non inviato)."""

    nome: str | None = Field(default=None, min_length=1, max_length=200)
    is_default: bool | None = None
    attivo: bool | None = None


class ListinoCategoriaAdminOut(BaseModel):
    id: int
    listino_id: int
    categoria_code: str
    base_eur_mq: Decimal
    coefficiente_impresa: Decimal  # admin-only — MAI riusato fuori da require_admin


class ListinoCategoriaAdminIn(BaseModel):
    categoria_code: str = Field(min_length=1, max_length=32)
    base_eur_mq: Decimal = Field(gt=0)
    coefficiente_impresa: Decimal = Field(gt=0, le=1)


class ListinoCategoriaPatchIn(BaseModel):
    base_eur_mq: Decimal | None = Field(default=None, gt=0)
    coefficiente_impresa: Decimal | None = Field(default=None, gt=0, le=1)


class VoceAdminOut(BaseModel):
    id: int
    sottocategoria_id: int
    codice: str | None
    descrizione: str
    um: str
    prezzo_cliente: Decimal


class VoceAdminIn(BaseModel):
    """Nota: NESSUN campo `descrizione`/`codice` (chiave naturale stabile,
    vedi docstring di modulo)."""

    prezzo_cliente: Decimal = Field(gt=0)
    um: str = Field(min_length=1, max_length=16)
