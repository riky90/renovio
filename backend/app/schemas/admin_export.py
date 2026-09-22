"""Schemi admin dell'audit export (D-15).

Stesso fork deliberato di `schemas/admin_domande.py`: queste classi sono
usate SOLO dalle route export/import, tutte dietro `Depends(require_admin)`
o `Depends(require_staff)`, mai le stesse degli schemi pubblici. Nessun
campo di questo modulo espone `coefficiente_impresa`: `include_margine` e'
un booleano che dice SE il file scaricato conteneva la variante marcata, non
il suo contenuto.

Definito qui una volta sola: i piani successivi della Fase 08 (import,
export parametri/domande/lead) leggono questo modulo senza modificarlo.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ExportLogOut(BaseModel):
    id: int
    user_id: int
    # Nome o email, risolto dal router — mai l'id nudo in UI.
    user_label: str
    risorsa: str
    righe: int
    include_margine: bool
    created_at: datetime
