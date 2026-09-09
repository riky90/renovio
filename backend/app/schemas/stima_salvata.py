"""Request/response schemas for /api/v1/me/stime.

Same closed-fields anti-leak pattern as `schemas/stima.py` (T-07-02, D-13):
`StimaSalvataCreate` mirrors `StimaResponse` exactly (it IS the payload the
client already received from `POST /api/v1/stima`, to be frozen as-is —
D-09/Pitfall 5, never recomputed here). `StimaSalvataListItem` exposes only
the scalar history columns. `StimaSalvataOut` rebuilds the full snapshot
shape (`id`/`created_at` + the frozen `StimaResponse` fields) from
`risultato_json`. None of the internal margin/cost fields (the impresa
secret family — see `models/listino.py` docstring) appear anywhere in this
module.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.stima import BonusOut, CategoriaOut, ExtraOut, StimaInputEcho, TotaleOut


class RisposteProIn(BaseModel):
    """Risposte alle domande mirate raccolte gia' nel form Pro. Stessi limiti
    di `RisposteDomandeRequest` (schemas/dettaglio_pro.py), ma con default a 0:
    qui sono opzionali, li' sono il corpo della richiesta."""

    bagni: int = Field(default=0, ge=0, le=20)
    porte: int = Field(default=0, ge=0, le=100)
    condizionatori: int = Field(default=0, ge=0, le=50)


class PreferenzeProIn(BaseModel):
    """Preferenze Pro raccolte nel form al momento della stima.

    NON fa parte dello snapshot: `risultato_json` deve conservare esattamente
    la forma di `StimaResponse`, cioe' cio' che l'utente ha VISTO. Queste
    preferenze sono invece parametri di ricalcolo, e vivono in colonne loro
    (`livelli_pro_json` / `risposte_pro_json`) da cui il dettaglio Pro le
    rilegge. Vedi l'`exclude` in `routers/stime_salvate.py::salva_stima`."""

    livelli: dict[str, str] | None = None
    risposte: RisposteProIn | None = None


class StimaSalvataCreate(BaseModel):
    """Mirrors `StimaResponse` (schemas/stima.py) — the already-computed
    payload the client received a moment earlier from `POST /api/v1/stima`.
    Frozen as-is into `risultato_json`; never re-derived server-side.

    Unica eccezione: `preferenze_pro`, che e' un parametro e non un risultato —
    va nelle sue colonne, mai nello snapshot."""

    input: StimaInputEcho
    fallback: bool
    disclaimer: str | None = None
    valuta: str
    categorie: list[CategoriaOut]
    extra: list[ExtraOut]
    totale: TotaleOut
    bonus: BonusOut | None = None
    preferenze_pro: PreferenzeProIn | None = None


class StimaSalvataListItem(BaseModel):
    id: int
    citta: str
    mq: int
    tipo: str
    totale_min: Decimal
    totale_max: Decimal
    # Piano con cui la stima e' stata creata, congelato al salvataggio. E' il
    # client a usarlo per scegliere la vista: mai `user.pro`, che cambia nel
    # tempo e trasformerebbe le stime Free storiche in Pro.
    tier: str = "free"
    created_at: datetime


class StimaSalvataOut(BaseModel):
    id: int
    created_at: datetime
    tier: str = "free"
    input: StimaInputEcho
    fallback: bool
    disclaimer: str | None
    valuta: str
    categorie: list[CategoriaOut]
    extra: list[ExtraOut]
    totale: TotaleOut
    # Assente negli snapshot v1 (salvati prima dei bonus): il router lo legge
    # con `.get()`, mai con `[]`.
    bonus: BonusOut | None = None
