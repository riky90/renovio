"""Request/response schemas for the Subscription/paywall endpoints.

Same closed-fields anti-leak convention as `schemas/stima.py`/`schemas/auth.py`
— never `model_validate` a raw `Subscription` ORM entity. Nessun dato
interno di margine/prezzo (D-10): la tessera Pro espone solo
stato/scadenza/piano.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class SubscriptionOut(BaseModel):
    stato: str
    scaduta_il: datetime | None
    piano_code: str | None


class AttivaProResponse(BaseModel):
    pro: bool
    stato: str


class PianoOut(BaseModel):
    code: str  # "mensile" | "annuale"
    nome: str
    importo: Decimal  # IVA inclusa
    valuta: str
    intervallo: str  # "month" | "year"


class PianiOut(BaseModel):
    #: False finche' Stripe non e' configurato: il frontend mostra
    #: l'attivazione dimostrativa.
    pagamenti_attivi: bool
    piani: list[PianoOut]


class CheckoutIn(BaseModel):
    piano: str
    #: Consenso all'esecuzione immediata del servizio digitale, con perdita del
    #: diritto di recesso (Codice del Consumo, art. 59, lett. o). Obbligatorio.
    accetta_esecuzione_immediata: bool


class ConfermaCheckoutIn(BaseModel):
    session_id: str


class UrlOut(BaseModel):
    url: str


class AbbonamentoOut(BaseModel):
    pro: bool
    stato: str
    piano_code: str | None
    #: Fine del periodo pagato (data del rinnovo, o della fine se disdetto).
    scade_il: datetime | None
    #: True se l'abbonamento si rinnova da solo; False se e' stato disdetto
    #: (resta Pro fino a `scade_il`) o se non c'e' un abbonamento Stripe.
    rinnovo_automatico: bool
    #: True se l'utente puo' aprire il portale clienti Stripe.
    gestibile: bool
