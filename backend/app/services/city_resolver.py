"""City -> listino resolution (D-06/D-07).

Free-text city input selects only the price list (listino), never a price
multiplier. A city without its own listino falls back to the default (RE)
listino and the caller must show the transparency disclaimer.
"""

from __future__ import annotations

from slugify import slugify
from sqlalchemy.orm import Session

from app.models.catalogo import ComuneListino
from app.models.listino import Listino


def resolve_listino(session: Session, citta: str) -> tuple[Listino, bool]:
    """Resolve a free-text città to its listino.

    Returns (listino, fallback). `fallback=True` means no dedicated listino
    was found and the default (RE) listino is being used instead — the
    caller must surface a disclaimer to the user.
    """
    slug = slugify(citta)
    row = session.query(ComuneListino).filter_by(comune_slug=slug).one_or_none()
    if row is not None:
        listino = session.get(Listino, row.listino_id)
        return listino, False

    default = session.query(Listino).filter_by(is_default=True).one()
    return default, True
