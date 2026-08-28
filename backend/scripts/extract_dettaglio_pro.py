"""One-off extraction: `docs/computo-base-reggio-emilia.xlsx` -> `docs/seed-dettaglio-pro.json`.

La classificazione riga (header vs voce, state machine A-EDILE, cataloghi
B/C/D) vive in `app/services/computo_parsing.py` (condivisa con l'upload
runtime della Fase 4, ADM-01) — questo script ne resta il solo chiamante
dev-side, invariato nel comportamento (04-RESEARCH.md Pitfall 1: qui
`scarti=None`, le eccezioni si propagano come prima).

`openpyxl` e' ora una dipendenza RUNTIME (`backend/pyproject.toml`
`[project].dependencies`, promossa in Fase 4 per l'upload admin — la
regola Fase 3 "mai sotto app/, mai a runtime" e' deliberatamente superata,
04-RESEARCH.md State of the Art), ma questo script resta comunque confinato
a `backend/scripts/`: mai importato da `app/`.

Layout sorgente (03-RESEARCH.md, `docs/computo-struttura-dettaglio.md`):
- `A-EDILE`: gerarchia a codici. Colonna B=codice, C=descrizione, D=UM,
  F=prezzo unitario cliente. Righe-intestazione (sezione/sottocategoria/
  totale) hanno UM/prezzo vuoti; righe-voce hanno UM+prezzo popolati
  (segnale usato per distinguere intestazione da voce, Pitfall 1). Alcune
  voci hanno varianti lettera (a/b/c...) su righe successive senza codice
  proprio: diventano Voce indipendenti sotto la stessa Sottocategoria.
  Le prime righe (codici A.1..A.8 sotto la sezione "A" prima della vera
  sottocategoria "A.1 DEMOLIZIONI...") sono un blocco "Allestimento cantiere"
  con codici che POI vengono riusati come sottocategorie vere (Pitfall
  osservato in questa sessione, non documentato prima): per evitare
  collisioni di codice, questo blocco viene raccolto sotto una sottocategoria
  sintetica "A.0" con codici voce sintetici "A.0.n".
- `B-FINITURE` / `C- SERRAMENTI PORTE  ` / `D- PRODOTTI`: cataloghi piatti.
  Colonna A=descrizione, B=UM, D=prezzo unitario. Righe-intestazione hanno
  SOLO la colonna A popolata (nessun UM/prezzo); righe-voce hanno UM+prezzo.
  Ogni riga-intestazione apre un nuovo gruppo (Sottocategoria famiglia=
  'catalogo'); righe-intestazione consecutive tengono solo l'ultima come
  nome del gruppo (sotto-intestazioni annidate, es. B-FINITURE).

Run: `uv run python scripts/extract_dettaglio_pro.py` (da backend/).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import openpyxl  # noqa: E402

from app.services.computo_parsing import extract_a_edile, extract_catalogo  # noqa: E402

XLSX_PATH = _BACKEND_DIR.parent / "docs" / "computo-base-reggio-emilia.xlsx"
OUT_PATH = _BACKEND_DIR.parent / "docs" / "seed-dettaglio-pro.json"


def main() -> None:
    wb = openpyxl.load_workbook(XLSX_PATH, data_only=True)

    sottocategorie: list[dict] = []
    sottocategorie += extract_a_edile(wb["A-EDILE"])
    sottocategorie += extract_catalogo(wb["B-FINITURE"], "B-FINITURE")
    sottocategorie += extract_catalogo(wb["C- SERRAMENTI PORTE  "], "C-SERRAMENTI")
    sottocategorie += extract_catalogo(wb["D- PRODOTTI"], "D-PRODOTTI")

    data = {"listino": "reggio-emilia", "sottocategorie": sottocategorie}

    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    n_voci = sum(len(s["voci"]) for s in sottocategorie)
    print(f"Estratte {len(sottocategorie)} sottocategorie, {n_voci} voci -> {OUT_PATH}")


if __name__ == "__main__":
    main()
