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

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

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


# --- Valori per classe della taratura corrente (D-03, piano 09-06) ---------
#
# `taratura-classi.json` (generato da `scripts/applica_taratura.py` dal file
# di decisioni) e' la fonte PRIMARIA dei coefficienti per classe per i
# computi futuri caricati da admin; `PROPOSTA_PER_CLASSE x TIPO_FACTOR`
# (definita piu' sotto) resta SOLO il fallback di bootstrap per voci/classi
# senza un valore curato a DB o nel JSON — mai la fonte primaria. Caricamento
# pigro e in cache: il file cambia solo quando qualcuno rilancia lo script di
# taratura, non a ogni richiesta.
_BACKEND_DIR_TARATURA = Path(__file__).resolve().parent.parent.parent
_TARATURA_CLASSI_PATH = _BACKEND_DIR_TARATURA / "seed_data" / "taratura-classi.json"
_taratura_classi_cache: dict | None = None


def _carica_taratura_classi() -> dict:
    """{classe: {tipo: valore}} da `taratura-classi.json`, o `{}` se il file
    manca o e' illeggibile (upload mai bloccato dalla taratura: fallback a
    PROPOSTA_PER_CLASSE x TIPO_FACTOR in `coefficienti_per_voce`)."""
    global _taratura_classi_cache
    if _taratura_classi_cache is None:
        try:
            contenuto = json.loads(_TARATURA_CLASSI_PATH.read_text(encoding="utf-8"))
            _taratura_classi_cache = contenuto.get("classi", {})
        except (OSError, ValueError):
            _taratura_classi_cache = {}
    return _taratura_classi_cache


def coefficienti_per_voce(
    um: str,
    descrizione: str,
    sottocategoria_nome: str = "",
    categoria_code: str = "",
) -> dict:
    """Costruisce il blocco {tipo: {...}} di coefficienti bozza per una voce
    NUOVA caricata da admin (upload/parser, D-19), derivandolo da
    `proponi_coefficiente()` (D-03) con i valori per classe di
    `taratura-classi.json` — non piu' `0.6/0.15 x TIPO_FACTOR` uniforme per
    ogni voce a mq/ml (Pitfall 4 09-RESEARCH.md, chiuso dal piano 09-06).

    Le voci `cad` con una parola chiave di domanda mirata (bagni/porte/
    condizionatori) restano governate dallo stepper omonimo, invariato
    rispetto a prima: la quantita' vera arriva dalla risposta dell'utente,
    non da un coefficiente per m2."""
    um_norm = (um or "").strip().lower()

    if um_norm in CAD_UM:
        domanda_key = detect_domanda_mirata(descrizione)
        if domanda_key:
            coeff: dict[str, dict] = {}
            for tipo in TIPI:
                coeff[tipo] = {
                    "domanda_mirata_key": domanda_key,
                    "default_conteggio": DOMANDA_MIRATA_DEFAULT_CONTEGGIO[domanda_key],
                }
            return coeff

    proposta = proponi_coefficiente(um, descrizione, sottocategoria_nome, categoria_code)
    classi_taratura = _carica_taratura_classi()
    valori_classe = classi_taratura.get(proposta.classe)

    coeff = {}
    for tipo in TIPI:
        coeff_val, conteggio_val = proposta.per_tipo[tipo]
        if coeff_val is not None:
            if valori_classe and tipo in valori_classe:
                try:
                    coeff_val = Decimal(str(valori_classe[tipo]))
                except (ValueError, TypeError):
                    pass
            coeff[tipo] = {"coefficiente_qta_per_mq": round(float(coeff_val), 4)}
        else:
            coeff[tipo] = {"default_conteggio": conteggio_val}
    return coeff


# --- Proposta di taratura (D-03, Fase 09/09-01, chiusa dal piano 09-06) ---
#
# Dal piano 09-06 `coefficienti_per_voce()' sopra NON e' piu' la bozza
# uniforme 0.6/0.15 x TIPO_FACTOR (Pitfall 4 del RESEARCH 09, superato): usa
# la classificazione di `proponi_coefficiente()` con i valori per classe di
# `taratura-classi.json` (generato dal file di decisioni via
# `scripts/applica_taratura.py`). Le funzioni sotto restano il canale che
# produce quella proposta motivata per voce, usato anche dal generatore del
# file di taratura (09-01 Task 2) per riempire le colonne *_proposto —
# `PROPOSTA_PER_CLASSE` in particolare resta la bozza di Claude, letta come
# fallback di bootstrap da `coefficienti_per_voce()` quando il JSON manca o
# non ha quella classe, mai riscritta a mano con i numeri di Riccardo (i
# numeri decisi vivono nel JSON generato).

# Bozza di Claude per il tipo "totale" (valore per m2 o per ml/m2), motivata
# per classe di voce. NON e' una taratura: e' la proposta che Riccardo valida
# con la checklist (09-TARATURA-TODO.md). Tarabile da admin via il file di
# D-04/pannello, mai cablata come sorgente unica di verita' (regola 3
# CLAUDE.md: il valore vero vive in coefficiente_qta_voce, questo dict e'
# solo il punto di partenza scritto a DB una tantum).
PROPOSTA_PER_CLASSE: dict[str, Decimal] = {
    "pavimento": Decimal("0.85"),
    "rivestimento": Decimal("0.25"),
    "battiscopa": Decimal("0.9"),
    "massetto": Decimal("0.85"),
    "pareti_soffitti": Decimal("2.7"),
    "demolizione": Decimal("0.5"),
    "serramento_mq": Decimal("0.12"),
    "lineare": Decimal("0.3"),
    "altro_mq": Decimal("0.4"),
}

_MOTIVAZIONE_PER_CLASSE: dict[str, str] = {
    "pavimento": (
        "Coefficiente proposto come quota dei m2 commerciali effettivamente "
        "calpestabili (al netto di murature e vani), scalato per intensita' "
        "di intervento."
    ),
    "rivestimento": (
        "Coefficiente di fallback quando manca il numero di bagni della "
        "stima: circa 20 m2 di parete rivestita per bagno su un appartamento "
        "di riferimento di 85 m2 (D-03). Andrebbe sostituito da una domanda "
        "mirata sul numero di bagni, come le voci gia' a domanda_mirata_key."
    ),
    "battiscopa": (
        "Metri lineari di battiscopa per m2 di pavimento, stimati dal "
        "perimetro medio di una stanza di un appartamento di riferimento."
    ),
    "massetto": (
        "Quota dei m2 dell'appartamento su cui si rifa' il massetto, "
        "scalata per intensita' di intervento."
    ),
    "pareti_soffitti": (
        "Superficie di pareti e soffitto per m2 di pavimento (altezza media "
        "locale x perimetro, piu' il soffitto), coefficiente maggiore di 1 "
        "per costruzione."
    ),
    "demolizione": (
        "Quota dei m2 dell'appartamento soggetta a demolizione/rimozione, "
        "scalata per intensita' di intervento."
    ),
    "serramento_mq": (
        "Superficie finestrata stimata come frazione dei m2 dell'appartamento."
    ),
    "lineare": (
        "Coefficiente lineare bozza per voci a metro lineare non altrimenti "
        "classificate, in assenza di un dato piu' specifico."
    ),
    "altro_mq": (
        "Coefficiente a m2 bozza per voci non altrimenti classificate, in "
        "assenza di un dato piu' specifico."
    ),
}

_KEYWORDS_RIVESTIMENTO = ("rivestiment",)
_KEYWORDS_PAVIMENTO = (
    "pavimentazione", "pavimento", "parquet", "gres", "laminato", "vinilico",
    "moquette", "tesserine", "lastra",
)
_KEYWORDS_BATTISCOPA = ("battiscopa", "zoccolino")
_KEYWORDS_MASSETTO = ("massetto", "sottofondo", "impermeabilizz")
_KEYWORDS_PARETI_SOFFITTI = ("pittura", "tinteggiatura", "intonaco", "rasatura", "controsoffitt")
_KEYWORDS_DEMOLIZIONE = ("demolizione", "rimozione", "trasporto")
_KEYWORDS_SERRAMENTO_MQ = ("finestra", "porta finestra", "tapparell", "zanzarier")
_KEYWORDS_RADIATORE = ("radiator", "termosifon")


def _classe_voce(um_norm: str, testo: str) -> str:
    """Classificazione pura per UM + parole chiave, nell'ordine dell'azione
    del Task 1 (09-01-PLAN.md): rivestimento -> pavimento -> battiscopa (ml)
    -> massetto -> pareti_soffitti -> demolizione -> serramento_mq (mq) ->
    lineare (altro ml) -> altro_mq (altro mq) -> conteggio (cad/ac/n.*/piano)
    -> percentuale (%)."""
    if any(kw in testo for kw in _KEYWORDS_RIVESTIMENTO):
        return "rivestimento"
    if any(kw in testo for kw in _KEYWORDS_PAVIMENTO):
        return "pavimento"
    if um_norm in ML_UM and any(kw in testo for kw in _KEYWORDS_BATTISCOPA):
        return "battiscopa"
    if any(kw in testo for kw in _KEYWORDS_MASSETTO):
        return "massetto"
    if any(kw in testo for kw in _KEYWORDS_PARETI_SOFFITTI):
        return "pareti_soffitti"
    if any(kw in testo for kw in _KEYWORDS_DEMOLIZIONE):
        return "demolizione"
    if um_norm in MQ_UM and any(kw in testo for kw in _KEYWORDS_SERRAMENTO_MQ):
        return "serramento_mq"
    if um_norm in ML_UM:
        return "lineare"
    if um_norm in MQ_UM:
        return "altro_mq"
    if um_norm == "%":
        return "percentuale"
    return "conteggio"


@dataclass(frozen=True)
class PropostaCoefficiente:
    """Proposta di taratura per UNA voce (D-03): `classe` e' l'etichetta di
    classificazione (per diagnosi/report, non persistita), `per_tipo` mappa
    ogni tipo di ristrutturazione a `(coefficiente_qta_per_mq, default_conteggio)`
    — sempre uno dei due `None`, mai entrambi popolati — e `motivazione` e'
    il testo in italiano che finisce nella colonna omonima del file di
    taratura."""

    classe: str
    per_tipo: dict[str, tuple[Decimal | None, int | None]]
    motivazione: str


def proponi_coefficiente(
    um: str, descrizione: str, sottocategoria_nome: str, categoria_code: str
) -> PropostaCoefficiente:
    """Bozza ragionata per UM e descrizione (D-03), al posto del
    `0.6 x TIPO_FACTOR` uniforme di `coefficienti_per_voce()` (che resta
    invariata, Pitfall 4 09-RESEARCH.md). Pura: nessun accesso a database,
    nessun coefficiente impresa."""
    um_norm = (um or "").strip().lower()
    # Deviazione (Rule 1): la classificazione usa SOLO la descrizione, non
    # "descrizione + nome sottocategoria" come da testo letterale
    # dell'azione del piano. Il nome della sottocategoria A.6 e' "PAVIMENTI
    # E RIVESTIMENTI" e contiene la keyword "rivestiment" — includerlo nel
    # testo classificherebbe come "rivestimento" anche A.6.1 (posa della
    # PAVIMENTAZIONE), il caso letteralmente citato nel <behavior> del piano
    # come dover restare "pavimento". Il parametro resta nella firma per
    # compatibilita' con l'azione del piano e per un uso futuro di
    # disambiguazione, ma non alimenta il testo classificato.
    _ = sottocategoria_nome
    testo = (descrizione or "").lower()
    classe = _classe_voce(um_norm, testo)

    if classe == "percentuale":
        per_tipo = {tipo: (None, None) for tipo in TIPI}
        motivazione = "voce a percentuale: resta com'e', da decidere con Riccardo"
        return PropostaCoefficiente(classe=classe, per_tipo=per_tipo, motivazione=motivazione)

    if classe == "conteggio":
        is_radiatore = any(kw in testo for kw in _KEYWORDS_RADIATORE)
        conteggio = 2 if is_radiatore else 1
        per_tipo = {tipo: (None, conteggio) for tipo in TIPI}
        if is_radiatore:
            motivazione = (
                "Voce a conteggio (radiatori/termosifoni): la regola vera "
                "sarebbe circa 1 ogni 15 m2 arrotondato in su, fuori portata "
                "di una funzione pura senza i m2 della stima. Bozza "
                "default_conteggio=2, da confermare con Riccardo."
            )
        else:
            motivazione = (
                "Voce a conteggio (UM cad/ac/n.*): nessun coefficiente per "
                "m2 possibile, proposto un default_conteggio di partenza "
                "da confermare con Riccardo."
            )
        return PropostaCoefficiente(classe=classe, per_tipo=per_tipo, motivazione=motivazione)

    valore_totale = PROPOSTA_PER_CLASSE[classe]
    per_tipo = {
        tipo: (
            Decimal(str(round(float(valore_totale) * TIPO_FACTOR[tipo], 4))),
            None,
        )
        for tipo in TIPI
    }
    motivazione = _MOTIVAZIONE_PER_CLASSE[classe]
    if classe == "rivestimento":
        # Ridondante per costruzione (la motivazione cita i bagni sopra), ma
        # esplicito qui perche' e' proprio cio' che il Task 1 chiede di
        # verificare col test (D-03: rivestimenti per numero di bagni).
        assert "bagn" in motivazione.lower()
    return PropostaCoefficiente(classe=classe, per_tipo=per_tipo, motivazione=motivazione)


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
        "coefficienti": coefficienti_per_voce(
            um_str, descrizione, sotto.get("nome", ""), sotto.get("categoria_code", "")
        ),
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
