"""Request/response schemas for the Subscription/paywall endpoints.

Same closed-fields anti-leak convention as `schemas/stima.py`/`schemas/auth.py`
— never `model_validate` a raw `Subscription` ORM entity. Nessun dato
interno di margine/prezzo (D-10): la tessera Pro espone solo
stato/scadenza/piano.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SubscriptionOut(BaseModel):
    stato: str
    scaduta_il: datetime | None
    piano_code: str | None


class AttivaProResponse(BaseModel):
    pro: bool
    stato: str
