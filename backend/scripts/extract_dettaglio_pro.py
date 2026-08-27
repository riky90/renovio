"""One-off extraction: `docs/computo-base-reggio-emilia.xlsx` -> `docs/seed-dettaglio-pro.json`.

SOLO in `backend/scripts/` (mai sotto `backend/app/`, 03-RESEARCH.md Pitfall 4):
usa `openpyxl` (dev dependency, dichiarata in `backend/pyproject.toml`), mai
importato a runtime.

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

XLSX_PATH = _BACKEND_DIR.parent / "docs" / "computo-base-reggio-emilia.xlsx"
OUT_PATH = _BACKEND_DIR.parent / "docs" / "seed-dettaglio-pro.json"

TIPI = ["leggera", "moderata", "totale"]
# Fattore di intensita' per tipo — stessa scala 0.1..1.0 di seed-coefficienti-base.json
# (moltiplicatori_tipo), riusata qui come bozza per far crescere le quantita'
# stimate con l'intensita' dell'intervento. Tarabile da admin in Fase 4.
TIPO_FACTOR = {"leggera": 0.4, "moderata": 0.7, "totale": 1.0}

# UM che indicano quantita' proporzionale ai mq dell'appartamento (D-05).
MQ_UM = {"mq"}
ML_UM = {"ml"}
# UM che indicano conteggio a pezzo (D-05 'cad').
CAD_UM = {"cad", "cad "}
# UM residue (a corpo/forfait, percentuali, unita' particolari) -> conteggio fisso.
FORFAIT_DEFAULT = 1

# Parole chiave per le domande mirate ad alto impatto (D-04).
DOMANDA_MIRATA_KEYWORDS = {
    "bagni": ["bagno", "sanitari", "doccia", "vasca", "bidet", "vaso igienico", "wc "],
    "porte": ["porta ", "porte ", "porta interna", "porta blindata", "porta in legno", "porta finestra"],
    "condizionatori": ["condizionatore", "condizionamento", "split"],
}
DOMANDA_MIRATA_DEFAULT_CONTEGGIO = {"bagni": 1, "porte": 5, "condizionatori": 1}

# Righe descrizione-guida da scartare a prescindere (note, totali, testo libero).
SKIP_PREFIXES = ("TOTALE", "Si precisa", "DESCRIZIONE")


def _detect_domanda_mirata(descrizione: str) -> str | None:
    testo = descrizione.lower()
    for key, keywords in DOMANDA_MIRATA_KEYWORDS.items():
        if any(kw in testo for kw in keywords):
            return key
    return None


def _coefficienti_per_voce(um: str, descrizione: str) -> dict:
    """Costruisce il blocco {tipo: {...}} di coefficienti bozza per una voce,
    seguendo le regole UM di D-05."""
    um_norm = (um or "").strip().lower()
    coeff: dict[str, dict] = {}

    if um_norm in MQ_UM:
        for tipo in TIPI:
            coeff[tipo] = {"coefficiente_qta_per_mq": round(0.6 * TIPO_FACTOR[tipo], 4)}
    elif um_norm in ML_UM:
        for tipo in TIPI:
            coeff[tipo] = {"coefficiente_qta_per_mq": round(0.15 * TIPO_FACTOR[tipo], 4)}
    elif um_norm in CAD_UM:
        domanda_key = _detect_domanda_mirata(descrizione)
        if domanda_key:
            for tipo in TIPI:
                coeff[tipo] = {
                    "domanda_mirata_key": domanda_key,
                    "default_conteggio": DOMANDA_MIRATA_DEFAULT_CONTEGGIO[domanda_key],
                }
        else:
            defaults = {"leggera": 0, "moderata": 1, "totale": 2}
            for tipo in TIPI:
                coeff[tipo] = {"default_conteggio": defaults[tipo]}
    else:
        # 'ac' (a corpo/forfait), '%', 'piano', 'n.air zone', 'n.bocchette', ecc.
        for tipo in TIPI:
            coeff[tipo] = {"default_conteggio": FORFAIT_DEFAULT}

    return coeff


def _is_header_row(codice, um, prezzo) -> bool:
    return um is None and prezzo is None


def _append_voce(sotto: dict, codice: str | None, descrizione: str, um: str, prezzo: float, ordine: int) -> dict:
    voce = {
        "codice": codice,
        "descrizione": descrizione[:300],
        "um": um.strip(),
        "prezzo_unitario_cliente": float(prezzo),
        "ordine": ordine,
        "coefficienti": _coefficienti_per_voce(um, descrizione),
    }
    sotto["voci"].append(voce)
    return voce


def extract_a_edile(ws) -> list[dict]:
    """Famiglia 'gerarchica': A-EDILE.

    Stato a due fasi (Pitfall osservato in questa sessione, non nel research
    originale): il blocco iniziale "Allestimento cantiere" riusa i codici
    A.1..A.8 PRIMA che compaiano le vere sottocategorie (che riusano quegli
    stessi codici per la gerarchia A.n/A.n.m). Il confine tra le due fasi e'
    la riga "TOTALE ALLESTIMENTO DI CANTIERE".
    """
    sottocategorie: list[dict] = []
    current_sotto: dict | None = None
    allestimento_sotto: dict = {
        "categoria_code": "A-EDILE",
        "codice": "A.0",
        "nome": "Allestimento di cantiere",
        "famiglia": "gerarchica",
        "ordine": 0,
        "voci": [],
    }
    in_allestimento = True
    voce_ordine = 0
    # (base_codice, base_descrizione, variant_count) della voce-con-varianti pendente
    pending: tuple[str, str] | None = None
    variant_counters: dict[str, int] = {}

    for row in ws.iter_rows(min_row=1, values_only=True):
        codice, descrizione, um, _qta, prezzo = row[1], row[2], row[3], row[4], row[5]
        if descrizione is None:
            continue
        descrizione_str = str(descrizione).strip().replace("\n", " ")

        if descrizione_str.startswith("TOTALE ALLESTIMENTO"):
            in_allestimento = False
            pending = None
            continue
        if any(descrizione_str.startswith(p) for p in SKIP_PREFIXES):
            continue

        is_header = _is_header_row(codice, um, prezzo)

        if in_allestimento:
            target = allestimento_sotto
            if codice is not None:
                codice_str = str(codice).strip()
                if is_header:
                    pending = (codice_str, descrizione_str)
                    continue
                voce_ordine += 1
                _append_voce(target, f"A.0.{len(target['voci']) + 1}", descrizione_str, str(um), prezzo, voce_ordine)
                pending = None
                continue
            # codice is None: variante lettera di una voce pendente
            if um is not None and prezzo is not None and pending is not None:
                base_codice, base_desc = pending
                variant_counters[base_codice] = variant_counters.get(base_codice, 0) + 1
                voce_ordine += 1
                variant_descr = f"{base_desc} - {descrizione_str}"
                _append_voce(
                    target,
                    f"A.0.{len(target['voci']) + 1}",
                    variant_descr,
                    str(um),
                    prezzo,
                    voce_ordine,
                )
            continue

        # Fase gerarchia vera: sottocategorie A.n + voci A.n.m (+ varianti lettera)
        if codice is not None:
            codice_str = str(codice).strip()
            n_dots = codice_str.count(".")

            if n_dots == 1:
                # Sottocategoria (es. "A.1 DEMOLIZIONI - RIMOZIONI - TRASPORTO")
                if current_sotto is not None:
                    sottocategorie.append(current_sotto)
                current_sotto = {
                    "categoria_code": "A-EDILE",
                    "codice": codice_str,
                    "nome": descrizione_str[:200],
                    "famiglia": "gerarchica",
                    "ordine": len(sottocategorie) + 1,
                    "voci": [],
                }
                pending = None
                continue

            if n_dots >= 2:
                if current_sotto is None:
                    continue
                if is_header:
                    pending = (codice_str, descrizione_str)
                    continue
                voce_ordine += 1
                _append_voce(current_sotto, codice_str, descrizione_str, str(um), prezzo, voce_ordine)
                pending = None
                continue
            # n_dots == 0 (codice sezione, es. "A") -> ignorato, solo contenitore
            continue

        # codice is None: variante lettera (a/b/c...) di una voce pendente
        if um is not None and prezzo is not None and pending is not None and current_sotto is not None:
            base_codice, base_desc = pending
            variant_counters[base_codice] = variant_counters.get(base_codice, 0) + 1
            voce_ordine += 1
            variant_descr = f"{base_desc} - {descrizione_str}"
            _append_voce(
                current_sotto,
                f"{base_codice}.{variant_counters[base_codice]}",
                variant_descr,
                str(um),
                prezzo,
                voce_ordine,
            )

    if current_sotto is not None:
        sottocategorie.append(current_sotto)

    return [allestimento_sotto] + sottocategorie


def extract_catalogo(ws, categoria_code: str) -> list[dict]:
    """Famiglia 'catalogo': B-FINITURE / C-SERRAMENTI / D-PRODOTTI."""
    sottocategorie: list[dict] = []
    current_sotto: dict | None = None
    voce_ordine = 0

    for row in ws.iter_rows(min_row=1, values_only=True):
        descrizione, um, _qta, prezzo = row[0], row[1], row[2], row[3]
        if descrizione is None:
            continue
        descrizione_str = str(descrizione).strip().replace("\n", " ")
        if any(descrizione_str.startswith(p) for p in SKIP_PREFIXES):
            continue
        if descrizione_str in ("Dati Cliente", "Nome cliente", "Indirizzo", "Telefono", "eMail", "C.F.:") or (
            "Citt" in descrizione_str and "Provincia" in descrizione_str
        ):
            continue

        if um is None and prezzo is None:
            # Riga-intestazione: apre (o rinomina, se annidata) il gruppo corrente.
            current_sotto = {
                "categoria_code": categoria_code,
                "codice": None,
                "nome": descrizione_str[:200],
                "famiglia": "catalogo",
                "ordine": len(sottocategorie) + 1,
                "voci": [],
            }
            sottocategorie.append(current_sotto)
            continue

        if current_sotto is None:
            # Voce senza intestazione precedente (non atteso, ma robusto): crea gruppo generico
            current_sotto = {
                "categoria_code": categoria_code,
                "codice": None,
                "nome": "Generale",
                "famiglia": "catalogo",
                "ordine": len(sottocategorie) + 1,
                "voci": [],
            }
            sottocategorie.append(current_sotto)

        voce_ordine += 1
        current_sotto["voci"].append(
            {
                "codice": None,
                "descrizione": descrizione_str[:300],
                "um": str(um).strip(),
                "prezzo_unitario_cliente": float(prezzo),
                "ordine": voce_ordine,
                "coefficienti": _coefficienti_per_voce(str(um), descrizione_str),
            }
        )

    return [s for s in sottocategorie if s["voci"]]


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
