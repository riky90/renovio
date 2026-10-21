"""Scrive `frontend/src/data/guide-costi.json`: l'istantanea delle cifre delle
guide pubbliche, calcolata dal motore sul DB locale.

Il frontend prerenderizza le guide al build con questa istantanea (cosi' i
crawler e le AI leggono numeri veri senza eseguire JavaScript) e nel browser
le aggiorna da `GET /api/v1/guide/costi`. Va rilanciato quando cambiano
listino o regole del computo, prima del deploy:

    python scripts/esporta_dati_guide.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.db import SessionLocal  # noqa: E402
from app.services.guide_costi import calcola_dati_guide  # noqa: E402

DESTINAZIONE = _BACKEND_DIR.parent / "frontend" / "src" / "data" / "guide-costi.json"


def main() -> None:
    with SessionLocal() as session:
        dati = calcola_dati_guide(session)
    DESTINAZIONE.parent.mkdir(parents=True, exist_ok=True)
    DESTINAZIONE.write_text(json.dumps(dati, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Scritto {DESTINAZIONE}")


if __name__ == "__main__":
    main()
