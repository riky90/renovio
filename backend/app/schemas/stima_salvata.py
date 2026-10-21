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

from pydantic import BaseModel, Field, field_validator

from app.schemas.stima import (
    ArredoOut,
    BonusOut,
    CategoriaOut,
    ConfrontoFinitureOut,
    ExtraOut,
    StimaInputEcho,
    StimaInputSalvataIn,
    TipoEnum,
    TotaleOut,
)


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
    # Scelte del configuratore Pro raccolte nel wizard (09-11, es.
    # {"tipo_pavimento": "parquet"}). Come `RisposteDomandeRequest`
    # (schemas/dettaglio_pro.py): lo schema garantisce solo la FORMA (<=20
    # chiavi, chiavi/valori <=64 caratteri, ASVS V5), il CONTENUTO (quali
    # codici sono ammessi, quali opzioni) lo valida il router contro il
    # catalogo via `valida_risposte_pro`.
    scelte: dict[str, str] | None = None

    @field_validator("scelte")
    @classmethod
    def _valida_forma_scelte(cls, v: dict[str, str] | None) -> dict[str, str] | None:
        if v is None:
            return v
        if len(v) > 20:
            raise ValueError("scelte: massimo 20 chiavi")
        for chiave, valore in v.items():
            if len(chiave) > 64 or len(valore) > 64:
                raise ValueError("scelte: chiavi e valori devono avere al massimo 64 caratteri")
        return v


class StimaSalvataCreate(BaseModel):
    """Mirrors `StimaResponse` (schemas/stima.py) — the already-computed
    payload the client received a moment earlier from `POST /api/v1/stima`.
    Frozen as-is into `risultato_json`; never re-derived server-side.

    Uniche eccezioni: `preferenze_pro` e `budget_eur`, che sono parametri e non
    risultati — vanno nelle loro colonne, mai nello snapshot."""

    # Vincoli di `StimaRequest` in ingresso (WR-06): il PUT riscrive citta/mq e
    # il dettaglio Pro ricalcola da li'. In lettura resta `StimaInputEcho`.
    input: StimaInputSalvataIn
    fallback: bool
    disclaimer: str | None = None
    valuta: str
    categorie: list[CategoriaOut]
    extra: list[ExtraOut]
    totale: TotaleOut
    bonus: BonusOut | None = None
    # Risultato del motore come `bonus`: entra nello snapshot. Prima di G9 pydantic
    # lo scartava in silenzio perche' il campo non esisteva.
    arredo: ArredoOut | None = None
    # Risultati calcolati dal motore (10-04): finiscono nello snapshot.
    confronto_finiture: ConfrontoFinitureOut | None = None
    finiture_al_minimo: bool = False
    tipo_effettivo: TipoEnum | None = None
    preferenze_pro: PreferenzeProIn | None = None
    # Come `preferenze_pro`: parametro, non risultato. Va nella colonna
    # `budget_eur`, mai nello snapshot.
    budget_eur: int | None = Field(default=None, ge=1, le=999_999_999)


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
    # Assente negli snapshot salvati prima di G9: il router lo legge con `.get()`.
    arredo: ArredoOut | None = None
    # Assenti negli snapshot salvati prima del 10-04: il router li legge con
    # `.get()`, default None/False.
    confronto_finiture: ConfrontoFinitureOut | None = None
    finiture_al_minimo: bool = False
    tipo_effettivo: TipoEnum | None = None
    # Dalla colonna `stima.budget_eur`, non dallo snapshot. None = nessun budget.
    budget_eur: int | None = None


class BudgetIn(BaseModel):
    budget_eur: int | None = Field(default=None, ge=1, le=999_999_999)


class BudgetOut(BaseModel):
    budget_eur: int | None
