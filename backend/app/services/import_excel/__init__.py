"""Lettori del formato piatto scritto da `export_excel/*.py` (fase 08).

Ogni re-import della Fase 08 (listino, domande, parametri, lead) legge da
qui il foglio dati e il foglio `ISTRUZIONI`, senza duplicare la logica di
riconoscimento del formato o del token di cancellazione.
"""

from __future__ import annotations
