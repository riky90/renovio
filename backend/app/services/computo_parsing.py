"""Classificazione riga del computo Excel (A-EDILE gerarchico + cataloghi
piatti B/C/D), condivisa tra `backend/scripts/extract_dettaglio_pro.py`
(estrazione one-off per il seed, Fase 3) e
`app/services/listino_upload_service.py` (upload runtime admin, Fase 4,
ADM-01/D-18).

State of the Art (04-RESEARCH.md): la regola Fase 3 "openpyxl mai importato
sotto app/" e' deliberatamente superata da questo modulo — qui vive SOLO
classificazione pura (nessuna chiamata openpyxl diretta, riceve un
worksheet gia' aperto dal chiamante), non il caricamento del workbook.

Le funzioni qui sono PURE per costruzione, ma accettano un parametro
opzionale `scarti` (04-RESEARCH.md Pitfall 1): quando fornito, ogni riga
malformata (prezzo non numerico/non positivo, UM mancante) produce una
voce nella lista `scarti` invece di sollevare un'eccezione, cosi' un
singolo errore di riga non blocca l'intero import (D-19). Quando `scarti`
e' `None` (uso da `extract_dettaglio_pro.py`, input fidato/dev-controlled),
il comportamento resta INVARIATO rispetto a Fase 3: le eccezioni si
propagano normalmente — nessuna regressione sullo script esistente.
"""

from __future__ import annotations

TIPI = ["leggera", "moderata", "totale"]
# Fattore di intensita' per tipo — stessa scala 0.1..1.0 di seed-coefficienti-base.json
# (moltiplicatori_tipo), riusata qui come bozza per far crescere le quantita'
# stimate con l'intensita' dell'intervento. Tarabile da admin in Fase 4.
TIPO_FACTOR = {"leggera": 0.4, "moderata": 0.7, "totale": 1.0}

# UM che indicano quantita' proporzionale ai mq dell'appartamento (D-05 Fase 3).
MQ_UM = {"mq"}
ML_UM = {"ml"}
# UM che indicano conteggio a pezzo (D-05 Fase 3 'cad').
CAD_UM = {"cad", "cad "}
# UM residue (a corpo/forfait, percentuali, unita' particolari) -> conteggio fisso.
FORFAIT_DEFAULT = 1

# Parole chiave per le domande mirate ad alto impatto (D-04 Fase 3).
DOMANDA_MIRATA_KEYWORDS = {
    "bagni": ["bagno", "sanitari", "doccia", "vasca", "bidet", "vaso igienico", "wc "],
    "porte": ["porta ", "porte ", "porta interna", "porta blindata", "porta in legno", "porta finestra"],
    "condizionatori": ["condizionatore", "condizionamento", "split"],
}
DOMANDA_MIRATA_DEFAULT_CONTEGGIO = {"bagni": 1, "porte": 5, "condizionatori": 1}

# Righe descrizione-guida da scartare a prescindere (note, totali, testo libero).
SKIP_PREFIXES = ("TOTALE", "Si precisa", "DESCRIZIONE")

# UM ammesse: le stesse riconosciute da coefficienti_per_voce, piu' le
# forfait/percentuale residue del file reale (04-RESEARCH.md Task 2 azione
# 3(b) "UM in set ammesso"). Validazione permissiva-per-costruzione: solo
# UM vuota e' rifiutata (04-RESEARCH.md Pitfall 1 riguarda soprattutto il
# prezzo, non un elenco chiuso di UM che finirebbe per scartare varianti
# lecite del file reale non ancora osservate).


def detect_domanda_mirata(descrizione: str) -> str | None:
    testo = descrizione.lower()
    for key, keywords in DOMANDA_MIRATA_KEYWORDS.items():
        if any(kw in testo for kw in keywords):
            return key
    return None


def coefficienti_per_voce(um: str, descrizione: str) -> dict:
    """Costruisce il blocco {tipo: {...}} di coefficienti bozza per una voce,
    seguendo le regole UM di D-05 (Fase 3)."""
    um_norm = (um or "").strip().lower()
    coeff: dict[str, dict] = {}

    if um_norm in MQ_UM:
        for tipo in TIPI:
            coeff[tipo] = {"coefficiente_qta_per_mq": round(0.6 * TIPO_FACTOR[tipo], 4)}
    elif um_norm in ML_UM:
        for tipo in TIPI:
            coeff[tipo] = {"coefficiente_qta_per_mq": round(0.15 * TIPO_FACTOR[tipo], 4)}
    elif um_norm in CAD_UM:
        domanda_key = detect_domanda_mirata(descrizione)
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


def is_header_row(codice, um, prezzo) -> bool:
    return um is None and prezzo is None


def _validate_voce_input(um, prezzo) -> tuple[str, float]:
    """Valida UM/prezzo di una riga-voce grezza a livello di CLASSIFICAZIONE
    (non di business rule): UM presente, prezzo convertibile a float. Il
    file reale contiene voci con prezzo 0.0 (es. voci non ancora quotate) —
    NON rifiutate qui per non regredire `extract_dettaglio_pro.py` (Fase 3).
    La regola di business "prezzo>0" per l'upload runtime (D-19/D-20) vive
    in `listino_upload_service.py`, un livello sopra, come scarto separato
    dalla classificazione pura."""
    um_str = str(um).strip() if um is not None else ""
    if not um_str:
        raise ValueError("UM mancante")
    try:
        prezzo_f = float(prezzo)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"prezzo non numerico: {prezzo!r}") from exc
    return um_str, prezzo_f


def append_voce(
    sotto: dict,
    codice: str | None,
    descrizione: str,
    um,
    prezzo,
    ordine: int,
    scarti: list[dict] | None = None,
    riga_excel: int | None = None,
) -> dict | None:
    """Valida e appende una voce a `sotto['voci']`. Se `scarti` e' fornito e
    la riga e' malformata, la scarta (appende il motivo a `scarti`) invece
    di sollevare — nessun errore isolato blocca l'intero import (D-19,
    04-RESEARCH.md Pitfall 1). Se `scarti` e' None (script dev, Fase 3),
    il comportamento resta quello originale: solleva ValueError."""
    if scarti is not None:
        try:
            um_str, prezzo_f = _validate_voce_input(um, prezzo)
        except ValueError as exc:
            scarti.append({"riga": riga_excel or 0, "motivo": f"{descrizione[:120]}: {exc}"})
            return None
    else:
        um_str, prezzo_f = _validate_voce_input(um, prezzo)

    voce = {
        "codice": codice,
        "descrizione": descrizione[:300],
        "um": um_str,
        "prezzo_unitario_cliente": prezzo_f,
        "ordine": ordine,
        "coefficienti": coefficienti_per_voce(um_str, descrizione),
    }
    sotto["voci"].append(voce)
    return voce


def extract_a_edile(ws, scarti: list[dict] | None = None) -> list[dict]:
    """Famiglia 'gerarchica': A-EDILE.

    Stato a due fasi: il blocco iniziale "Allestimento cantiere" riusa i
    codici A.1..A.8 PRIMA che compaiano le vere sottocategorie (che riusano
    quegli stessi codici per la gerarchia A.n/A.n.m). Il confine tra le due
    fasi e' la riga "TOTALE ALLESTIMENTO DI CANTIERE".
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
    # (base_codice, base_descrizione) della voce-con-varianti pendente
    pending: tuple[str, str] | None = None
    variant_counters: dict[str, int] = {}

    for riga_idx, row in enumerate(ws.iter_rows(min_row=1, values_only=True), start=1):
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

        is_header = is_header_row(codice, um, prezzo)

        if in_allestimento:
            target = allestimento_sotto
            if codice is not None:
                codice_str = str(codice).strip()
                if is_header:
                    pending = (codice_str, descrizione_str)
                    continue
                voce_ordine += 1
                append_voce(
                    target,
                    f"A.0.{len(target['voci']) + 1}",
                    descrizione_str,
                    um,
                    prezzo,
                    voce_ordine,
                    scarti,
                    riga_idx,
                )
                pending = None
                continue
            # codice is None: variante lettera di una voce pendente
            if um is not None and prezzo is not None and pending is not None:
                base_codice, base_desc = pending
                variant_counters[base_codice] = variant_counters.get(base_codice, 0) + 1
                voce_ordine += 1
                variant_descr = f"{base_desc} - {descrizione_str}"
                append_voce(
                    target,
                    f"A.0.{len(target['voci']) + 1}",
                    variant_descr,
                    um,
                    prezzo,
                    voce_ordine,
                    scarti,
                    riga_idx,
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
                append_voce(current_sotto, codice_str, descrizione_str, um, prezzo, voce_ordine, scarti, riga_idx)
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
            append_voce(
                current_sotto,
                f"{base_codice}.{variant_counters[base_codice]}",
                variant_descr,
                um,
                prezzo,
                voce_ordine,
                scarti,
                riga_idx,
            )

    if current_sotto is not None:
        sottocategorie.append(current_sotto)

    return [allestimento_sotto] + sottocategorie


def extract_catalogo(ws, categoria_code: str, scarti: list[dict] | None = None) -> list[dict]:
    """Famiglia 'catalogo': B-FINITURE / C-SERRAMENTI / D-PRODOTTI."""
    sottocategorie: list[dict] = []
    current_sotto: dict | None = None
    voce_ordine = 0

    for riga_idx, row in enumerate(ws.iter_rows(min_row=1, values_only=True), start=1):
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
        append_voce(current_sotto, None, descrizione_str, um, prezzo, voce_ordine, scarti, riga_idx)

    return [s for s in sottocategorie if s["voci"]]
