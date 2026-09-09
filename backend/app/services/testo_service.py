"""Read-through service for the `Testo` key/value table (D-14).

`get_testo()` is the single read path used by any backend code that renders
a previously-hardcoded string (currently: the EST-06 disclaimer in
`routers/stima.py`). If the DB row is somehow missing (e.g. a test DB that
skipped the seed step), it falls back in-code to the original hardcoded
string so a missing seed never crashes the render path — the seed is still
the source of truth in normal operation (T-04-14).

Scope v1 (04-RESEARCH.md Open Question 1): backend-owned strings only.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.testo import Testo

# In-code fallback values, keyed the same as the seeded rows. Defensive only
# — the seed always creates these keys, this is a last-resort safety net if
# a row is ever missing (T-04-14).
_FALLBACK_VALORI = {
    "disclaimer_fallback_citta": (
        "Stima basata sul listino di Reggio Emilia, non ancora tarata su {citta}."
    ),
    "email_conferma_lead_subject": "Conferma richiesta contatto professionista",
    "disclaimer_bonus": (
        "Gli importi delle detrazioni sono una stima commerciale, non consulenza fiscale: verificali sempre con il tuo commercialista prima di impegnarti in una spesa. La detrazione si recupera in 10 quote annuali di pari importo e solo entro la capienza IRPEF: se l'imposta lorda dell'anno e' inferiore alla rata, la parte eccedente si perde e non e' recuperabile negli anni successivi. Per averne diritto servono il pagamento con bonifico parlante e gli adempimenti previsti (per l'ecobonus, la comunicazione ENEA entro 90 giorni dalla fine dei lavori). Gli importi qui indicati derivano da una stima pre-sopralluogo e sono espressi a range."
    ),
}


def get_testo(session: Session, chiave: str, **fmt: object) -> str:
    """Read `Testo.valore` for `chiave`, applying `.format(**fmt)` if the
    string has placeholders. Falls back to `_FALLBACK_VALORI[chiave]` if the
    row is missing (defensive; the seed always creates it)."""
    row = session.get(Testo, chiave)
    valore = row.valore if row is not None else _FALLBACK_VALORI[chiave]
    return valore.format(**fmt) if fmt else valore
