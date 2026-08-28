"""Referente resolution for the lead-notification flow (D-04/D-05).

`resolve_referente` extends `city_resolver.resolve_listino`'s exact
two-branch shape (04-RESEARCH.md Pattern 3): resolve the città to its
listino, then look up the active `Referente` on that listino ordered by
`priorita`; if none is active there, fall back to the default listino's
active referente (the global catch-all). Returns `None` only when truly no
active referente exists anywhere — the `Lead` row is still saved regardless
(D-07), the dashboard is the safety net.

Called ONLY after the `Lead` row has already been persisted (D-07 ordering)
— never before.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.catalogo import Referente
from app.models.listino import Listino
from app.services.city_resolver import resolve_listino


def resolve_referente(session: Session, citta: str) -> Referente | None:
    listino, _fallback = resolve_listino(session, citta)

    referente = (
        session.query(Referente)
        .filter_by(listino_id=listino.id, attivo=True)
        .order_by(Referente.priorita)
        .first()
    )
    if referente is not None:
        return referente

    default_listino = session.query(Listino).filter_by(is_default=True).one()
    if default_listino.id == listino.id:
        return None  # nessun referente attivo da nessuna parte — il lead resta salvato (D-07)

    return (
        session.query(Referente)
        .filter_by(listino_id=default_listino.id, attivo=True)
        .order_by(Referente.priorita)
        .first()
    )
