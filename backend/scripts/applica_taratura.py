"""Applica al catalogo la curatela del file di decisioni: gli ASSI (D-08,
09-07-PLAN.md Task 1) e i COEFFICIENTI quantita'-per-mq (D-03, 09-06-PLAN.md
Task 1). Lo script legge `docs/taratura/09-taratura-pro-compilato.xlsx`
(`genera_excel_taratura.leggi_decisioni`) e ricostruisce da zero:
- gli effetti Pro a bersaglio naturale in `backend/seed_data/seed-domande.json`
  + la fixture delle famiglie di alternative
  (`backend/tests/fixtures/famiglie_alternative_pro.json`) — vedi `applica_assi`;
- i coefficienti quantita'-per-mq in `backend/seed_data/seed-dettaglio-pro.json`
  (e la copia `docs/seed-dettaglio-pro.json`) + i valori per classe in
  `backend/seed_data/taratura-classi.json` — vedi `applica_coefficienti` e
  `calcola_classi`.

Senza `--solo-assi` (default da questo piano) applica ENTRAMBE le parti in
un'unica esecuzione.

REGOLA DI PROPRIETA' (vedi `<action>` del piano): gli effetti con
`target_voce`/`target_sottocategoria` sotto le domande `finitura`,
`tipo_pavimento` e sotto l'opzione "valore" di `bagni`/`porte`/
`condizionatori` sono GENERATI da questo script: vengono ricostruiti da zero
a ogni chiamata dalle decisioni del file. Ogni altro effetto (gli effetti
Free esistenti, es. `eur_per_scostamento` sulla stessa opzione "valore")
resta com'e', stesso ordine.

Vincolo di Riccardo del 2026-09-26 (fasi 09-10 di fila, senza fermarsi): lo
stato "bozza-accettata" e' ammesso e stampato con un avviso esplicito; solo
"da-compilare" viene rifiutato, perche' significa che nessuna decisione e'
mai stata presa.

Nessun coefficiente impresa in questo script (regola di dominio #1,
CLAUDE.md): tutto cio' che legge/scrive e' euro-cliente o puro dato di
assegnazione (asse/opzione/quantita').
"""

from __future__ import annotations

import argparse
import copy
import json
import statistics
import sys
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

# Allow `python scripts/applica_taratura.py` direct execution, stesso
# bootstrap di scripts/seed.py / scripts/genera_excel_taratura.py.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import openpyxl  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.models.dettaglio_pro import Sottocategoria, Voce  # noqa: E402
from app.services.computo_parsing import (  # noqa: E402
    PROPOSTA_PER_CLASSE,
    TIPI,
    TIPO_FACTOR,
    proponi_coefficiente,
)
from app.services.effetti import (  # noqa: E402
    OPZIONE_VALORE,
    TIPO_ESCLUDI,
    TIPO_FATTORE_QUANTITA,
    TIPO_INCLUDI,
    TIPO_QUANTITA_PER_UNITA,
)
from scripts.genera_excel_taratura import AsseDeciso, DecisioniTaratura, leggi_decisioni  # noqa: E402

#: Le cinque domande su cui questo script ha proprieta' esclusiva degli
#: effetti a bersaglio naturale (vedi docstring di modulo).
DOMANDA_FINITURA = "finitura"
DOMANDA_TIPO_PAVIMENTO = "tipo_pavimento"
ASSI_STEPPER = ("bagni", "porte", "condizionatori")
DOMANDE_GESTITE = (DOMANDA_FINITURA, DOMANDA_TIPO_PAVIMENTO, *ASSI_STEPPER)

STATO_DA_COMPILARE = "da-compilare"
STATO_BOZZA_ACCETTATA = "bozza-accettata"


# --- (a) risolvi_chiave_naturale ---------------------------------------------


def risolvi_chiave_naturale(session: Session, voce_id: int) -> dict | None:
    """Da un `voce_id` di `dev.db` (letto in sola lettura, mai scritto) ricava
    {categoria_code, sottocategoria, voce} — le stesse regole di chiave
    naturale del seed/09-02 (codice se esiste, altrimenti nome/descrizione
    esatta). `None` se la voce non esiste (piu' non fa nulla: la riga viene
    saltata dal chiamante, mai un'eccezione)."""
    voce = session.get(Voce, voce_id)
    if voce is None:
        return None
    sotto = session.get(Sottocategoria, voce.sottocategoria_id)
    if sotto is None:
        return None
    return {
        "categoria_code": sotto.categoria_code,
        "sottocategoria": sotto.codice if sotto.codice is not None else sotto.nome,
        "voce": voce.codice if voce.codice is not None else voce.descrizione,
    }


#: Le sei famiglie di alternative per fascia di prezzo (D-08, genera_excel_
#: taratura._FAMIGLIE_ALTERNATIVE_KEYWORDS): pensate per le sottocategorie
#: 'catalogo' (RUBINETTERIE, PORTE, PRODOTTI). Il match e' per PAROLA-CHIAVE
#: sulla descrizione, senza distinguere sottocategoria: prende anche righe
#: 'gerarchica' di A-EDILE (rimozioni/montaggi) che menzionano "bidet"/
#: "doccia"/"condizionatore" nel testo ma sono operazioni, non prodotti
#: alternativi — falso positivo della bozza 09-01. `applica_assi` (sotto) li
#: ignora quando la sottocategoria bersaglio e' 'gerarchica'.
FAMIGLIE_ALTERNATIVE_PER_FASCIA_PREZZO = frozenset(
    {
        "sanitari_vaso",
        "sanitari_bidet",
        "sanitari_cassetta",
        "sanitari_doccia_vasca",
        "porte_apertura",
        "condizionatori_marca",
    }
)


def sottocategoria_famiglia_di(session: Session, voce_id: int) -> str | None:
    """`sottocategoria.famiglia` ('gerarchica' o 'catalogo') della voce, o
    `None` se non risolvibile."""
    voce = session.get(Voce, voce_id)
    if voce is None:
        return None
    sotto = session.get(Sottocategoria, voce.sottocategoria_id)
    return sotto.famiglia if sotto is not None else None


# --- (b) applica_assi ---------------------------------------------------------


@dataclass(frozen=True)
class RisultatoAssi:
    seed_domande: dict
    famiglie: list[dict] = field(default_factory=list)
    stato: str = ""
    modificate: list[str] = field(default_factory=list)


def _chiave_ordinamento(effetto: dict) -> tuple[str, str, str, str]:
    """(categoria, sottocategoria, voce, tipo_effetto) per un ordine
    deterministico degli effetti generati per opzione."""
    target = effetto.get("target_voce") or effetto.get("target_sottocategoria") or {}
    return (
        str(target.get("categoria_code", "")),
        str(target.get("sottocategoria", "")),
        str(target.get("voce", "")),
        str(effetto.get("tipo_effetto", "")),
    )


def _pulisci_effetti_a_bersaglio_naturale(seed_domande: dict) -> dict[str, dict]:
    """Svuota, per le domande gestite, gli effetti con `target_voce`/
    `target_sottocategoria` (quelli che questo script possiede); per
    bagni/porte/condizionatori solo sull'opzione "valore". Ritorna la mappa
    domanda_code -> dict domanda per il resto della funzione."""
    domande_per_code = {d["code"]: d for d in seed_domande.get("domande", [])}
    for code in DOMANDE_GESTITE:
        domanda = domande_per_code.get(code)
        if domanda is None:
            continue
        for opzione in domanda.get("opzioni", []):
            if code in ASSI_STEPPER and opzione.get("code") != OPZIONE_VALORE:
                continue
            opzione["effetti"] = [
                e
                for e in opzione.get("effetti", [])
                if "target_voce" not in e and "target_sottocategoria" not in e
            ]
    return domande_per_code


def applica_assi(
    decisioni: DecisioniTaratura,
    seed_domande: dict,
    chiavi: dict[int, dict],
    *,
    sottocategorie_gerarchiche: frozenset[int] = frozenset(),
) -> RisultatoAssi:
    """Pura (nessun accesso a DB, nessuna scrittura su disco): ricostruisce da
    zero, dalle decisioni approvate (OK/MODIFICATO; NO gia' scartato da
    `leggi_decisioni`), gli effetti Pro a bersaglio naturale sulle cinque
    domande gestite, lasciando intatto tutto il resto (Free compreso).

    `sottocategorie_gerarchiche`: i `voce_id` la cui sottocategoria e'
    `famiglia='gerarchica'` (A-EDILE gerarchica). Le sei famiglie di
    alternative per fascia di prezzo (`FAMIGLIE_ALTERNATIVE_PER_FASCIA_
    PREZZO`) sono pensate per le sottocategorie 'catalogo' (RUBINETTERIE,
    PORTE, PRODOTTI): una riga con quella famiglia su una voce gerarchica e'
    un falso positivo del match per parola-chiave della bozza 09-01 (Rule 1
    — es. una rimozione A.0 che menziona "bidet" nel testo non e' un
    sanitario alternativo), ignorata qui senza creare alcun effetto — la
    voce resta sempre inclusa, come prima di questa fase.

    Solleva `ValueError` se `decisioni.stato == "da-compilare"`: nessuna
    decisione e' mai stata presa, non si applica per sbaglio."""
    if decisioni.stato == STATO_DA_COMPILARE:
        raise ValueError(
            "Il file di taratura e' ancora 'da-compilare': nessuna decisione "
            "presa, applica_assi non procede."
        )

    seed_domande = copy.deepcopy(seed_domande)
    domande_per_code = _pulisci_effetti_a_bersaglio_naturale(seed_domande)

    nuovi: dict[tuple[str, str], list[dict]] = {}

    def _aggiungi(domanda_code: str, opzione_code: str | None, effetto: dict) -> None:
        if opzione_code is None:
            return
        nuovi.setdefault((domanda_code, opzione_code), []).append(effetto)

    modificate: list[str] = []
    famiglie: list[dict] = []

    assi_validi: list[AsseDeciso] = []
    for riga in decisioni.assi:
        if (
            riga.famiglia_alternativa in FAMIGLIE_ALTERNATIVE_PER_FASCIA_PREZZO
            and riga.voce_id in sottocategorie_gerarchiche
        ):
            modificate.append(
                f"voce_id={riga.voce_id} famiglia={riga.famiglia_alternativa!r} "
                f"asse={riga.asse!r} IGNORATA: falso positivo del match per "
                "parola-chiave su una voce gerarchica (rimozione/montaggio), "
                "non un prodotto alternativo — resta sempre inclusa (Rule 1)"
            )
            continue
        assi_validi.append(riga)
    decisioni = DecisioniTaratura(
        stato=decisioni.stato, coefficienti=decisioni.coefficienti, assi=assi_validi, dati=decisioni.dati
    )

    # D-02: il bagno resta sempre gres/rivestimento, ma la SUA quota di posa
    # (voce A.6.1) deve restare nel computo anche quando il resto della casa
    # scegie un altro pavimento. Una voce con almeno una riga fattore_pavimento
    # NON diventa bersaglio di alcun `includi` (nemmeno sulla sua opzione
    # "gres" della riga tipo_pavimento gemella): resta NON governata dall'asse
    # tipo_pavimento, quindi SEMPRE inclusa (regola 4 di effetti.py) — la
    # fattore_quantita (sotto) si applica comunque, perche' effetti.py la
    # risolve per l'opzione scelta indipendentemente dalla governance
    # dell'asse. Se le dessimo un `includi` sulle altre opzioni per "salvarla"
    # dall'esclusione, tornerebbe bersaglio di PIU' di un'opzione (gres +
    # parquet/maxi_lastra/mosaico) e romperebbe il conteggio per-asse di
    # CFG-02 (09-03), che assume bersagli disgiunti fra opzioni.
    voci_con_quota_bagno: set[int] = {
        riga.voce_id for riga in decisioni.assi if riga.asse == "fattore_pavimento"
    }

    # Deduplica le famiglie di alternative che la bozza di 09-01 ha assegnato
    # TUTTE alla stessa opzione (es. 6 forniture 'PAVIMENTI PARQUET' o 4
    # zoccolini in legno, tutte -> tipo_pavimento=parquet): senza questo passo
    # tornerebbero a sommarsi fra loro, lo stesso bug che la fase chiude.
    # Eccezione esplicita: la famiglia 'finitura:<sottocategoria>' (varieta' di
    # SKU migrata da voce.livello, 09-02/09-03/09-04) mette DELIBERATAMENTE piu'
    # voci sulla stessa opzione — non e' un difetto di curatela, e' il
    # comportamento gia' verificato da test_dettaglio_pro_alternative.py
    # (test_gres_default_include_bersagli_di_medio_piu_le_non_governate).
    gruppi_asse_opzione: dict[tuple[str, str, str], list[AsseDeciso]] = {}
    for riga in decisioni.assi:
        if (
            riga.asse in (DOMANDA_FINITURA, DOMANDA_TIPO_PAVIMENTO)
            and riga.opzione
            and riga.voce_id not in voci_con_quota_bagno
        ):
            gruppi_asse_opzione.setdefault(
                (riga.asse, riga.opzione, riga.famiglia_alternativa), []
            ).append(riga)

    voce_id_da_deduplicare: set[int] = set()
    for (asse, opzione, famiglia), righe_gruppo in gruppi_asse_opzione.items():
        if famiglia.startswith("finitura:") or len(righe_gruppo) <= 1:
            continue
        ordinate = sorted(righe_gruppo, key=lambda r: r.voce_id)
        for extra in ordinate[1:]:
            voce_id_da_deduplicare.add(extra.voce_id)
            modificate.append(
                f"voce_id={extra.voce_id} asse={asse!r} opzione={opzione!r} DEDUPLICATA: "
                f"famiglia {famiglia!r} aveva {len(righe_gruppo)} voci sulla stessa opzione, "
                f"tenuta solo voce_id={ordinate[0].voce_id} (Rule 1, evita di sommare le "
                "alternative)"
            )

    for riga in decisioni.assi:
        if riga.decisione == "MODIFICATO":
            modificate.append(
                f"voce_id={riga.voce_id} asse={riga.asse!r} opzione={riga.opzione!r} "
                f"decisione=MODIFICATO nota={riga.note!r}"
            )

        chiave = chiavi.get(riga.voce_id)
        if chiave is None:
            # Bersaglio non risolto (voce sparita da dev.db dopo la generazione
            # del file): saltata in silenzio, coerente con la disciplina del
            # seed (mai un'eccezione per un dato di curatela rotto).
            continue

        if riga.asse in (DOMANDA_FINITURA, DOMANDA_TIPO_PAVIMENTO):
            if riga.voce_id in voci_con_quota_bagno:
                # Vedi commento sopra: nessun `includi` per la quota bagno,
                # resta sempre inclusa e la sua quantita' la regola solo la
                # riga fattore_pavimento (gestita dal ramo successivo).
                pass
            else:
                _aggiungi(riga.asse, riga.opzione, {"tipo_effetto": TIPO_INCLUDI, "target_voce": chiave})
                if riga.voce_id in voce_id_da_deduplicare:
                    # Governata (includi) ma sempre esclusa: sparisce anche
                    # quando e' proprio questa opzione a essere scelta, senza
                    # smettere di essere "governata" quando NON lo e' (regola
                    # 4 di effetti.py la includerebbe sempre, altrimenti).
                    _aggiungi(riga.asse, riga.opzione, {"tipo_effetto": TIPO_ESCLUDI, "target_voce": chiave})
        elif riga.asse in ASSI_STEPPER:
            valore = float(riga.valore_per_unita) if riga.valore_per_unita is not None else 1.0
            _aggiungi(
                riga.asse,
                OPZIONE_VALORE,
                {"tipo_effetto": TIPO_QUANTITA_PER_UNITA, "valore": valore, "target_voce": chiave},
            )
        elif riga.asse == "fattore_pavimento":
            if riga.fattore_quantita is not None:
                _aggiungi(
                    DOMANDA_TIPO_PAVIMENTO,
                    riga.opzione,
                    {
                        "tipo_effetto": TIPO_FATTORE_QUANTITA,
                        "valore": float(riga.fattore_quantita),
                        "target_voce": chiave,
                    },
                )
        elif riga.asse == "escludi_sempre":
            domanda_finitura = domande_per_code.get(DOMANDA_FINITURA)
            if domanda_finitura is not None:
                for opzione in domanda_finitura.get("opzioni", []):
                    _aggiungi(
                        DOMANDA_FINITURA,
                        opzione.get("code"),
                        {"tipo_effetto": TIPO_ESCLUDI, "target_voce": chiave},
                    )
        # "sempre_inclusa" e assi non riconosciuti: nessun effetto da creare.

        if riga.famiglia_alternativa:
            famiglia = riga.famiglia_alternativa
            if riga.voce_id in voci_con_quota_bagno:
                # La quota bagno NON e' un'alternativa al pavimento scelto per
                # il resto della casa (le due voci coesistono nello stesso
                # computo, D-02): famiglia distinta per non far contare
                # A.6.1 (bagno, sia dalla sua riga tipo_pavimento->gres sia
                # dalle righe fattore_pavimento) insieme ad A.6.2/.5/.6 (resto
                # casa) nel test CFG-02 "al massimo una voce per famiglia".
                famiglia = f"{famiglia}:bagno"
            famiglie.append(
                {
                    "categoria_code": chiave["categoria_code"],
                    "sottocategoria": chiave["sottocategoria"],
                    "voce": chiave["voce"],
                    "famiglia": famiglia,
                }
            )

    for (domanda_code, opzione_code), effetti in nuovi.items():
        domanda = domande_per_code.get(domanda_code)
        if domanda is None:
            continue
        opzione = next((o for o in domanda.get("opzioni", []) if o.get("code") == opzione_code), None)
        if opzione is None:
            continue
        opzione.setdefault("effetti", [])
        opzione["effetti"].extend(sorted(effetti, key=_chiave_ordinamento))

    famiglie.sort(key=lambda f: (f["categoria_code"], f["sottocategoria"], f["voce"], f["famiglia"]))

    return RisultatoAssi(
        seed_domande=seed_domande,
        famiglie=famiglie,
        stato=decisioni.stato,
        modificate=modificate,
    )


# --- (c) applica_coefficienti + calcola_classi -------------------------------
#
# Parte "coefficienti" del piano 09-06 (D-03): scrive nel seed-dettaglio-pro.json
# il valore finale (OK=proposto/ATTUALE=attuale/MODIFICATO=scritto a mano) per
# ogni (voce, tipo) del foglio coefficienti_pro, e ricava i valori per CLASSE
# (`taratura-classi.json`) che alimentano `computo_parsing.coefficienti_per_voce()`
# per i computi futuri (Pitfall 4 09-RESEARCH.md). Nessun coefficiente impresa.


def _indice_seed_dettaglio(seed_dettaglio: dict) -> dict[tuple[str, str, str], dict]:
    """Chiave naturale (categoria_code, sottocategoria, voce) -> dict voce
    (riferimento mutabile dentro `seed_dettaglio`, mai una copia)."""
    indice: dict[tuple[str, str, str], dict] = {}
    for sotto in seed_dettaglio.get("sottocategorie", []):
        chiave_sotto = sotto.get("codice") if sotto.get("codice") is not None else sotto["nome"]
        for voce in sotto.get("voci", []):
            chiave_voce = voce.get("codice") if voce.get("codice") is not None else voce["descrizione"]
            indice[(sotto["categoria_code"], chiave_sotto, chiave_voce)] = voce
    return indice


def applica_coefficienti(
    decisioni: DecisioniTaratura,
    seed_dettaglio: dict,
    chiavi: dict[int, dict],
) -> tuple[dict, list[str]]:
    """Pura salvo la copia profonda di `seed_dettaglio` (nessun accesso a DB,
    nessuna scrittura su disco): per ogni `CoeffDeciso` scrive nel dict di
    seed il valore finale di quel (voce, tipo) — OK/MODIFICATO = il proposto/
    scritto a mano (colonna `coefficiente_qta_per_mq`/`default_conteggio` del
    foglio), ATTUALE = il valore attuale letto a DB (stesse colonne "_attuale",
    gia' risolte da `genera_excel_taratura.leggi_decisioni`). Le voci non
    presenti nel seed (bersaglio non risolto o sparito) sono segnalate nella
    lista di ritorno e saltate, mai un'eccezione (stessa disciplina del seed:
    un dato di curatela rotto non deve bloccare l'applicazione).

    Solleva `ValueError` su un coefficiente o un default_conteggio negativo
    (stessa regola >= 0 del resto del motore Pro)."""
    seed_dettaglio = copy.deepcopy(seed_dettaglio)
    indice = _indice_seed_dettaglio(seed_dettaglio)
    saltate: list[str] = []

    for riga in decisioni.coefficienti:
        if riga.coefficiente_qta_per_mq is not None and riga.coefficiente_qta_per_mq < 0:
            raise ValueError(
                f"voce_id={riga.voce_id} tipo={riga.tipo_code!r}: "
                f"coefficiente_qta_per_mq negativo ({riga.coefficiente_qta_per_mq})"
            )
        if riga.default_conteggio is not None and riga.default_conteggio < 0:
            raise ValueError(
                f"voce_id={riga.voce_id} tipo={riga.tipo_code!r}: "
                f"default_conteggio negativo ({riga.default_conteggio})"
            )

        chiave_dict = chiavi.get(riga.voce_id)
        if chiave_dict is None:
            saltate.append(f"voce_id={riga.voce_id} tipo={riga.tipo_code!r}: non risolta a DB, saltata")
            continue
        chiave = (chiave_dict["categoria_code"], chiave_dict["sottocategoria"], chiave_dict["voce"])
        voce_entry = indice.get(chiave)
        if voce_entry is None:
            saltate.append(
                f"voce_id={riga.voce_id} chiave={chiave} tipo={riga.tipo_code!r}: "
                "non presente nel seed-dettaglio-pro.json, saltata"
            )
            continue

        blocco = voce_entry.setdefault("coefficienti", {}).setdefault(riga.tipo_code, {})
        if riga.coefficiente_qta_per_mq is not None:
            blocco["coefficiente_qta_per_mq"] = round(float(riga.coefficiente_qta_per_mq), 4)
            blocco.pop("default_conteggio", None)
        elif riga.default_conteggio is not None:
            blocco["default_conteggio"] = riga.default_conteggio
            blocco.pop("coefficiente_qta_per_mq", None)

    return seed_dettaglio, saltate


#: codice_dato del foglio `dati_richiesti` (genera_excel_taratura.
#: DATI_RICHIESTI_PROPOSTI, 09-01) -> classe di `proponi_coefficiente`.
#: Solo i dati che corrispondono a UNA classe: gli altri (rivestimento_cucina,
#: mq_controsoffitto, ml_cassonetti_per_mq, radiatori_per_locale,
#: punti_impianto_per_mq, scala_tipo_factor, famiglie_alternative_livelli)
#: non hanno una classe dedicata in `PROPOSTA_PER_CLASSE` e restano fuori.
DATO_PER_CLASSE: dict[str, str] = {
    "quota_calpestabile": "pavimento",
    "mq_rivestimento_bagno": "rivestimento",
    "ml_battiscopa_per_mq": "battiscopa",
    "quota_massetto": "massetto",
    "mq_pareti_soffitti_per_mq": "pareti_soffitti",
    "quota_demolizioni": "demolizione",
    "superficie_finestrata": "serramento_mq",
}


def _valore_numerico(valore) -> Decimal | None:
    """Converte in Decimal un valore del foglio dati_richiesti, tollerando
    testo libero non numerico (es. "circa 20 m2 per bagno...", D-03): ritorna
    None quando non e' interpretabile come numero, mai un'eccezione — un dato
    discorsivo non deve bloccare il calcolo delle classi."""
    if valore in (None, ""):
        return None
    testo = str(valore).strip()
    try:
        return Decimal(testo)
    except (ValueError, ArithmeticError):
        primo_token = testo.split()[0] if testo.split() else ""
        try:
            return Decimal(primo_token)
        except (ValueError, ArithmeticError):
            return None


def calcola_classi(
    decisioni: DecisioniTaratura,
    chiavi_classe: dict[int, str],
) -> dict[str, dict[str, str]]:
    """Per ogni classe di `proponi_coefficiente` e ogni tipo, il valore
    mediano dei coefficienti FINALI (post-decisione) delle voci di quella
    classe fra `decisioni.coefficienti`; se `decisioni.dati` ha un valore per
    un `codice_dato` mappato a una classe (`DATO_PER_CLASSE`), il valore di
    quella classe per il tipo `totale` e' quello (leggera/moderata =
    totale x TIPO_FACTOR) — sovrascrive la mediana. Classi senza alcuna voce
    decisa e senza un dato_richiesto usano `PROPOSTA_PER_CLASSE x TIPO_FACTOR`
    (stesso fallback di `coefficienti_per_voce`, mai un buco). Valori
    serializzati come stringa (JSON-safe, precisione Decimal preservata)."""
    valori_per_classe_tipo: dict[str, dict[str, list[Decimal]]] = {}
    for riga in decisioni.coefficienti:
        if riga.coefficiente_qta_per_mq is None:
            continue
        classe = chiavi_classe.get(riga.voce_id)
        if classe is None or classe not in PROPOSTA_PER_CLASSE:
            continue
        valori_per_classe_tipo.setdefault(classe, {}).setdefault(riga.tipo_code, []).append(
            riga.coefficiente_qta_per_mq
        )

    classi: dict[str, dict[str, str]] = {}
    for classe in PROPOSTA_PER_CLASSE:
        classi[classe] = {}
        for tipo in TIPI:
            valori = valori_per_classe_tipo.get(classe, {}).get(tipo)
            if valori:
                valore = Decimal(str(statistics.median(valori)))
            else:
                valore = Decimal(str(round(float(PROPOSTA_PER_CLASSE[classe]) * TIPO_FACTOR[tipo], 4)))
            classi[classe][tipo] = str(valore)

    for codice_dato, classe in DATO_PER_CLASSE.items():
        if classe not in PROPOSTA_PER_CLASSE:
            continue
        valore_totale = _valore_numerico(decisioni.dati.get(codice_dato))
        if valore_totale is None:
            continue
        for tipo in TIPI:
            valore = valore_totale if tipo == "totale" else valore_totale * Decimal(str(TIPO_FACTOR[tipo]))
            classi[classe][tipo] = str(round(valore, 4))

    return classi


# --- (d) emetti_migrazione ----------------------------------------------------
#
# Parte "migrazione" del piano 09-06 (Task 3): calcola il diff in chiavi
# naturali fra i JSON di seed BASE (cio' che i DB esistenti hanno dopo
# l'ultima migrazione) e i JSON NUOVI (prodotti da applica_coefficienti/
# applica_assi su questo lancio), e rende un modulo Alembic autosufficiente
# — una migrazione e' uno snapshot: nessuna lettura di file esterni a
# runtime. Gli effetti NUOVI (assenti dalla base) non entrano nel diff: li
# crea il seed create-if-missing al boot (D-41).

import re as _re  # noqa: E402


def _chiave_target_voce(effetto: dict) -> tuple[str, str, str] | None:
    """(categoria_code, sottocategoria, voce) da un effetto con `target_voce`,
    o `None` se l'effetto non ha un bersaglio a voce (es. `target_sottocategoria`,
    non prodotto da `applica_assi`/`applica_coefficienti`, fuori scope qui)."""
    tv = effetto.get("target_voce")
    if tv is None:
        return None
    return (tv["categoria_code"], tv["sottocategoria"], tv["voce"])


def _record_effetti(seed_domande: dict) -> dict[str, dict]:
    """Indici per il diff degli effetti a bersaglio voce:
    - `includi`: (domanda_code, chiave_voce) -> opzione_code
    - `quantita`: (domanda_code, opzione_code, tipo_effetto, chiave_voce, tipo_code) -> valore
      (tipo_effetto in quantita_per_unita/fattore_quantita)
    - `escludi`: (domanda_code, opzione_code, chiave_voce, tipo_code) -> True
    """
    includi: dict[tuple[str, tuple], str] = {}
    quantita: dict[tuple, object] = {}
    escludi: dict[tuple, bool] = {}
    for domanda in seed_domande.get("domande", []):
        d_code = domanda["code"]
        for opzione in domanda.get("opzioni", []):
            o_code = opzione.get("code")
            for effetto in opzione.get("effetti", []):
                chiave_voce = _chiave_target_voce(effetto)
                if chiave_voce is None:
                    continue
                tipo_eff = effetto.get("tipo_effetto")
                tipo_code = effetto.get("tipo_code")
                if tipo_eff == TIPO_INCLUDI:
                    includi[(d_code, chiave_voce)] = o_code
                elif tipo_eff in (TIPO_QUANTITA_PER_UNITA, TIPO_FATTORE_QUANTITA):
                    quantita[(d_code, o_code, tipo_eff, chiave_voce, tipo_code)] = effetto.get("valore")
                elif tipo_eff == TIPO_ESCLUDI:
                    escludi[(d_code, o_code, chiave_voce, tipo_code)] = True
    return {"includi": includi, "quantita": quantita, "escludi": escludi}


def _diff_coefficienti(base_dettaglio: dict, nuovo_dettaglio: dict) -> list[tuple]:
    """[(categoria_code, sottocategoria, voce, tipo_code, campo, vecchio, nuovo)]
    per ogni (voce, tipo, campo) che differisce fra base e nuovo. `campo` in
    {coefficiente_qta_per_mq, default_conteggio}. Voci assenti da uno dei due
    lati sono saltate (bersaglio non risolto, mai un'eccezione)."""
    base_idx = _indice_seed_dettaglio(base_dettaglio)
    nuovo_idx = _indice_seed_dettaglio(nuovo_dettaglio)
    diff: list[tuple] = []
    for chiave, voce_base in base_idx.items():
        voce_nuovo = nuovo_idx.get(chiave)
        if voce_nuovo is None:
            continue
        categoria_code, sottocategoria, voce_nome = chiave
        for tipo_code in TIPI:
            blocco_base = voce_base.get("coefficienti", {}).get(tipo_code, {})
            blocco_nuovo = voce_nuovo.get("coefficienti", {}).get(tipo_code, {})
            for campo in ("coefficiente_qta_per_mq", "default_conteggio"):
                vecchio = blocco_base.get(campo)
                nuovo_valore = blocco_nuovo.get(campo)
                if vecchio != nuovo_valore and (vecchio is not None or nuovo_valore is not None):
                    diff.append((categoria_code, sottocategoria, voce_nome, tipo_code, campo, vecchio, nuovo_valore))
    return diff


def _prossima_revisione(versions_dir: Path) -> tuple[str, str | None]:
    """(prossima_revision, down_revision): il numero a 4 cifre libero e la
    testa attuale (il numero piu' alto trovato nei nomi file di
    `versions_dir`, catena lineare — stesso schema di 0001..0021)."""
    numeri = sorted(
        int(m.group(1)) for f in versions_dir.glob("*.py") if (m := _re.match(r"^(\d{4})_", f.name))
    )
    if not numeri:
        return "0001", None
    testa = numeri[-1]
    return f"{testa + 1:04d}", f"{testa:04d}"


_TEMPLATE_MIGRAZIONE = '''"""Migrazione generata da scripts/applica_taratura.py:emetti_migrazione() dal
diff fra i JSON di seed versionati e il file di decisioni (D-03/D-08). Una
migrazione e' uno snapshot immutabile: nessuna lettura di file esterni a
runtime, i valori sono costanti incorporate qui sotto. Aggiorna SOLO le
righe ancora al valore BASE (WHERE campo = vecchio): una taratura fatta a
mano dal pannello dopo questa migrazione non viene mai sovrascritta. Gli
effetti NUOVI (assenti dalla base) non sono qui: li crea il seed
create-if-missing al boot (D-41). Nessun coefficiente impresa.

Revision ID: {revision}
Revises: {down_revision}
Create Date: {create_date}
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = {revision!r}
down_revision: Union[str, Sequence[str], None] = {down_revision!r}
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_COEFFICIENTI: tuple[tuple, ...] = {coefficienti!r}
_VALORI_EFFETTO: tuple[tuple, ...] = {valori_effetto!r}
_INCLUDI_SPOSTATI: tuple[tuple, ...] = {includi_spostati!r}
_EFFETTI_RIMOSSI: tuple[tuple, ...] = {effetti_rimossi!r}

_TOLLERANZA = 1e-6


def _tabelle():
    """Definizioni locali delle tabelle toccate (mai i modelli ORM: una
    migrazione dati non deve dipendere da come saranno i modelli in futuro,
    stesso principio della 0021)."""
    sottocategoria = sa.table(
        "sottocategoria",
        sa.column("id"),
        sa.column("categoria_code"),
        sa.column("codice"),
        sa.column("nome"),
    )
    voce = sa.table(
        "voce",
        sa.column("id"),
        sa.column("sottocategoria_id"),
        sa.column("codice"),
        sa.column("descrizione"),
    )
    coefficiente = sa.table(
        "coefficiente_qta_voce",
        sa.column("id"),
        sa.column("voce_id"),
        sa.column("tipo_code"),
        sa.column("coefficiente_qta_per_mq"),
        sa.column("default_conteggio"),
        sa.column("updated_at"),
    )
    opzione = sa.table(
        "opzione_domanda",
        sa.column("id"),
        sa.column("domanda_code"),
        sa.column("code"),
    )
    effetto = sa.table(
        "effetto_opzione",
        sa.column("id"),
        sa.column("opzione_id"),
        sa.column("tipo_effetto"),
        sa.column("target_voce_id"),
        sa.column("tipo_code"),
        sa.column("valore"),
        sa.column("attivo"),
        sa.column("updated_at"),
    )
    return sottocategoria, voce, coefficiente, opzione, effetto


def _risolvi_voce_id(bind, sottocategoria, voce, categoria_code, sottocategoria_key, voce_key):
    """Chiave naturale -> voce.id (codice se esiste, altrimenti nome/descrizione
    esatta — stessa regola del seed/09-02). `None` se non risolta: la riga
    del diff viene saltata, mai un'eccezione (dato di curatela rotto non deve
    bloccare il boot)."""
    riga_sotto = bind.execute(
        sa.select(sottocategoria.c.id).where(
            sottocategoria.c.categoria_code == categoria_code,
            sottocategoria.c.codice == sottocategoria_key,
        )
    ).first()
    if riga_sotto is None:
        riga_sotto = bind.execute(
            sa.select(sottocategoria.c.id).where(
                sottocategoria.c.categoria_code == categoria_code,
                sottocategoria.c.codice.is_(None),
                sottocategoria.c.nome == sottocategoria_key,
            )
        ).first()
    if riga_sotto is None:
        return None
    sotto_id = riga_sotto[0]
    riga_voce = bind.execute(
        sa.select(voce.c.id).where(voce.c.sottocategoria_id == sotto_id, voce.c.codice == voce_key)
    ).first()
    if riga_voce is None:
        riga_voce = bind.execute(
            sa.select(voce.c.id).where(
                voce.c.sottocategoria_id == sotto_id,
                voce.c.codice.is_(None),
                voce.c.descrizione == voce_key,
            )
        ).first()
    return riga_voce[0] if riga_voce is not None else None


def _opzione_id(bind, opzione, domanda_code, opzione_code):
    riga = bind.execute(
        sa.select(opzione.c.id).where(opzione.c.domanda_code == domanda_code, opzione.c.code == opzione_code)
    ).first()
    return riga[0] if riga is not None else None


def _vicino(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return abs(float(a) - float(b)) <= _TOLLERANZA


def upgrade() -> None:
    bind = op.get_bind()
    adesso = datetime.now(timezone.utc).replace(tzinfo=None)
    sottocategoria, voce, coefficiente, opzione, effetto = _tabelle()

    for categoria_code, sottocategoria_key, voce_key, tipo_code, campo, vecchio, nuovo in _COEFFICIENTI:
        voce_id = _risolvi_voce_id(bind, sottocategoria, voce, categoria_code, sottocategoria_key, voce_key)
        if voce_id is None:
            continue
        riga = bind.execute(
            sa.select(coefficiente.c.id, coefficiente.c[campo]).where(
                coefficiente.c.voce_id == voce_id, coefficiente.c.tipo_code == tipo_code
            )
        ).first()
        if riga is None or not _vicino(riga[1], vecchio):
            continue
        bind.execute(
            sa.update(coefficiente).where(coefficiente.c.id == riga[0]).values(**{{campo: nuovo, "updated_at": adesso}})
        )

    for domanda_code, opzione_code, tipo_effetto, chiave_voce, tipo_code, vecchio, nuovo in _VALORI_EFFETTO:
        categoria_code, sottocategoria_key, voce_key = chiave_voce
        opzione_id = _opzione_id(bind, opzione, domanda_code, opzione_code)
        voce_id = _risolvi_voce_id(bind, sottocategoria, voce, categoria_code, sottocategoria_key, voce_key)
        if opzione_id is None or voce_id is None:
            continue
        cond_tipo_code = (
            effetto.c.tipo_code == tipo_code if tipo_code is not None else effetto.c.tipo_code.is_(None)
        )
        riga = bind.execute(
            sa.select(effetto.c.id, effetto.c.valore).where(
                effetto.c.opzione_id == opzione_id,
                effetto.c.tipo_effetto == tipo_effetto,
                effetto.c.target_voce_id == voce_id,
                cond_tipo_code,
            )
        ).first()
        if riga is None or not _vicino(riga[1], vecchio):
            continue
        bind.execute(sa.update(effetto).where(effetto.c.id == riga[0]).values(valore=nuovo, updated_at=adesso))

    for domanda_code, chiave_voce, opzione_vecchia, opzione_nuova in _INCLUDI_SPOSTATI:
        categoria_code, sottocategoria_key, voce_key = chiave_voce
        voce_id = _risolvi_voce_id(bind, sottocategoria, voce, categoria_code, sottocategoria_key, voce_key)
        opzione_nuova_id = _opzione_id(bind, opzione, domanda_code, opzione_nuova)
        opzione_vecchia_id = _opzione_id(bind, opzione, domanda_code, opzione_vecchia)
        if voce_id is None or opzione_nuova_id is None or opzione_vecchia_id is None:
            continue
        gia_su_nuova = bind.execute(
            sa.select(effetto.c.id).where(
                effetto.c.opzione_id == opzione_nuova_id,
                effetto.c.tipo_effetto == "includi",
                effetto.c.target_voce_id == voce_id,
            )
        ).first()
        riga_vecchia = bind.execute(
            sa.select(effetto.c.id).where(
                effetto.c.opzione_id == opzione_vecchia_id,
                effetto.c.tipo_effetto == "includi",
                effetto.c.target_voce_id == voce_id,
            )
        ).first()
        if gia_su_nuova is not None:
            if riga_vecchia is not None:
                bind.execute(sa.delete(effetto).where(effetto.c.id == riga_vecchia[0]))
            continue
        if riga_vecchia is None:
            continue
        bind.execute(
            sa.update(effetto).where(effetto.c.id == riga_vecchia[0]).values(opzione_id=opzione_nuova_id, updated_at=adesso)
        )

    for domanda_code, opzione_code, tipo_effetto, chiave_voce, tipo_code, valore in _EFFETTI_RIMOSSI:
        categoria_code, sottocategoria_key, voce_key = chiave_voce
        opzione_id = _opzione_id(bind, opzione, domanda_code, opzione_code)
        voce_id = _risolvi_voce_id(bind, sottocategoria, voce, categoria_code, sottocategoria_key, voce_key)
        if opzione_id is None or voce_id is None:
            continue
        cond_tipo_code = (
            effetto.c.tipo_code == tipo_code if tipo_code is not None else effetto.c.tipo_code.is_(None)
        )
        riga = bind.execute(
            sa.select(effetto.c.id, effetto.c.valore).where(
                effetto.c.opzione_id == opzione_id,
                effetto.c.tipo_effetto == tipo_effetto,
                effetto.c.target_voce_id == voce_id,
                cond_tipo_code,
            )
        ).first()
        if riga is None:
            continue
        if valore is not None and not _vicino(riga[1], valore):
            continue
        bind.execute(sa.delete(effetto).where(effetto.c.id == riga[0]))


def downgrade() -> None:
    bind = op.get_bind()
    adesso = datetime.now(timezone.utc).replace(tzinfo=None)
    sottocategoria, voce, coefficiente, opzione, effetto = _tabelle()

    for categoria_code, sottocategoria_key, voce_key, tipo_code, campo, vecchio, nuovo in _COEFFICIENTI:
        voce_id = _risolvi_voce_id(bind, sottocategoria, voce, categoria_code, sottocategoria_key, voce_key)
        if voce_id is None:
            continue
        riga = bind.execute(
            sa.select(coefficiente.c.id, coefficiente.c[campo]).where(
                coefficiente.c.voce_id == voce_id, coefficiente.c.tipo_code == tipo_code
            )
        ).first()
        if riga is None or not _vicino(riga[1], nuovo):
            continue
        bind.execute(
            sa.update(coefficiente).where(coefficiente.c.id == riga[0]).values(**{{campo: vecchio, "updated_at": adesso}})
        )

    for domanda_code, opzione_code, tipo_effetto, chiave_voce, tipo_code, vecchio, nuovo in _VALORI_EFFETTO:
        categoria_code, sottocategoria_key, voce_key = chiave_voce
        opzione_id = _opzione_id(bind, opzione, domanda_code, opzione_code)
        voce_id = _risolvi_voce_id(bind, sottocategoria, voce, categoria_code, sottocategoria_key, voce_key)
        if opzione_id is None or voce_id is None:
            continue
        cond_tipo_code = (
            effetto.c.tipo_code == tipo_code if tipo_code is not None else effetto.c.tipo_code.is_(None)
        )
        riga = bind.execute(
            sa.select(effetto.c.id, effetto.c.valore).where(
                effetto.c.opzione_id == opzione_id,
                effetto.c.tipo_effetto == tipo_effetto,
                effetto.c.target_voce_id == voce_id,
                cond_tipo_code,
            )
        ).first()
        if riga is None or not _vicino(riga[1], nuovo):
            continue
        bind.execute(sa.update(effetto).where(effetto.c.id == riga[0]).values(valore=vecchio, updated_at=adesso))

    for domanda_code, chiave_voce, opzione_vecchia, opzione_nuova in _INCLUDI_SPOSTATI:
        categoria_code, sottocategoria_key, voce_key = chiave_voce
        voce_id = _risolvi_voce_id(bind, sottocategoria, voce, categoria_code, sottocategoria_key, voce_key)
        opzione_nuova_id = _opzione_id(bind, opzione, domanda_code, opzione_nuova)
        opzione_vecchia_id = _opzione_id(bind, opzione, domanda_code, opzione_vecchia)
        if voce_id is None or opzione_nuova_id is None or opzione_vecchia_id is None:
            continue
        gia_su_vecchia = bind.execute(
            sa.select(effetto.c.id).where(
                effetto.c.opzione_id == opzione_vecchia_id,
                effetto.c.tipo_effetto == "includi",
                effetto.c.target_voce_id == voce_id,
            )
        ).first()
        riga_nuova = bind.execute(
            sa.select(effetto.c.id).where(
                effetto.c.opzione_id == opzione_nuova_id,
                effetto.c.tipo_effetto == "includi",
                effetto.c.target_voce_id == voce_id,
            )
        ).first()
        if gia_su_vecchia is not None:
            if riga_nuova is not None:
                bind.execute(sa.delete(effetto).where(effetto.c.id == riga_nuova[0]))
            continue
        if riga_nuova is None:
            continue
        bind.execute(
            sa.update(effetto).where(effetto.c.id == riga_nuova[0]).values(opzione_id=opzione_vecchia_id, updated_at=adesso)
        )

    for domanda_code, opzione_code, tipo_effetto, chiave_voce, tipo_code, valore in _EFFETTI_RIMOSSI:
        categoria_code, sottocategoria_key, voce_key = chiave_voce
        opzione_id = _opzione_id(bind, opzione, domanda_code, opzione_code)
        voce_id = _risolvi_voce_id(bind, sottocategoria, voce, categoria_code, sottocategoria_key, voce_key)
        if opzione_id is None or voce_id is None:
            continue
        gia_presente = bind.execute(
            sa.select(effetto.c.id).where(
                effetto.c.opzione_id == opzione_id,
                effetto.c.tipo_effetto == tipo_effetto,
                effetto.c.target_voce_id == voce_id,
            )
        ).first()
        if gia_presente is not None:
            continue
        bind.execute(
            sa.insert(effetto).values(
                opzione_id=opzione_id,
                tipo_effetto=tipo_effetto,
                target_voce_id=voce_id,
                tipo_code=tipo_code,
                valore=valore,
                attivo=True,
                updated_at=adesso,
            )
        )
'''


def emetti_migrazione(
    base_dettaglio: dict,
    nuovo_dettaglio: dict,
    base_domande: dict,
    nuovo_domande: dict,
    versions_dir: Path,
    slug: str,
) -> Path | None:
    """Calcola il diff (chiavi naturali) fra i JSON base e nuovi e rende un
    modulo Alembic autosufficiente in `versions_dir`. Ritorna `None` (nessun
    file emesso) se non c'e' alcuna differenza."""
    coefficienti_diff = _diff_coefficienti(base_dettaglio, nuovo_dettaglio)

    base_idx = _record_effetti(base_domande)
    nuovo_idx = _record_effetti(nuovo_domande)

    includi_spostati: list[tuple] = []
    effetti_rimossi: list[tuple] = []
    for chiave, opz_base in base_idx["includi"].items():
        d_code, chiave_voce = chiave
        opz_nuovo = nuovo_idx["includi"].get(chiave)
        if opz_nuovo is None:
            effetti_rimossi.append((d_code, opz_base, TIPO_INCLUDI, chiave_voce, None, None))
        elif opz_nuovo != opz_base:
            includi_spostati.append((d_code, chiave_voce, opz_base, opz_nuovo))

    valori_effetto: list[tuple] = []
    for chiave, valore_base in base_idx["quantita"].items():
        d_code, o_code, tipo_eff, chiave_voce, tipo_code = chiave
        valore_nuovo = nuovo_idx["quantita"].get(chiave)
        if valore_nuovo is None:
            effetti_rimossi.append((d_code, o_code, tipo_eff, chiave_voce, tipo_code, valore_base))
        elif valore_nuovo != valore_base:
            valori_effetto.append((d_code, o_code, tipo_eff, chiave_voce, tipo_code, valore_base, valore_nuovo))

    for chiave in base_idx["escludi"]:
        if chiave not in nuovo_idx["escludi"]:
            d_code, o_code, chiave_voce, tipo_code = chiave
            effetti_rimossi.append((d_code, o_code, TIPO_ESCLUDI, chiave_voce, tipo_code, None))

    if not (coefficienti_diff or valori_effetto or includi_spostati or effetti_rimossi):
        print("emetti_migrazione: nessuna differenza, nessun file emesso.")
        return None

    revisione, down_revision = _prossima_revisione(versions_dir)
    contenuto = _TEMPLATE_MIGRAZIONE.format(
        revision=revisione,
        down_revision=down_revision,
        create_date=__import__("datetime").datetime.now().isoformat(),
        coefficienti=tuple(coefficienti_diff),
        valori_effetto=tuple(valori_effetto),
        includi_spostati=tuple(includi_spostati),
        effetti_rimossi=tuple(effetti_rimossi),
    )
    versions_dir.mkdir(parents=True, exist_ok=True)
    percorso = versions_dir / f"{revisione}_{slug}.py"
    percorso.write_text(contenuto, encoding="utf-8")
    return percorso


# --- (e) main -----------------------------------------------------------------


def _percorso_sqlite_da_database_url(url: str) -> str:
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        raise ValueError(f"applica_taratura richiede un DATABASE_URL sqlite, non {url!r}")
    return url[len(prefix) :]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--file",
        default=str(_BACKEND_DIR.parent / "docs" / "taratura" / "09-taratura-pro-compilato.xlsx"),
        help="file di taratura da applicare (default: la bozza accettata del 09-01)",
    )
    parser.add_argument(
        "--solo-assi",
        action="store_true",
        help="applica solo la parte assi (comportamento del 09-07); senza questo flag "
        "(default dal piano 09-06) applica ANCHE i coefficienti quantita'-per-mq",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="stampa il riepilogo senza scrivere alcun file",
    )
    parser.add_argument(
        "--migrazione",
        action="store_true",
        help="emette anche la migrazione Alembic dal diff fra i JSON a --base-rev e quelli "
        "prodotti da questo lancio (Task 3, 09-06-PLAN.md); senza questo flag nessun file "
        "in alembic/versions viene creato",
    )
    parser.add_argument(
        "--slug",
        default="taratura_pro",
        help="suffisso del nome file della migrazione emessa (default: taratura_pro)",
    )
    parser.add_argument(
        "--base-rev",
        default="HEAD",
        help="revisione git da cui leggere i JSON di seed BASE per il diff (default: HEAD, "
        "cioe' cio' che i DB esistenti hanno dopo l'ultima migrazione)",
    )
    args = parser.parse_args()

    wb = openpyxl.load_workbook(args.file, data_only=True)
    decisioni = leggi_decisioni(wb)

    if decisioni.stato == STATO_DA_COMPILARE:
        print(
            "ERRORE: il file e' ancora 'da-compilare' — nessuna decisione presa. "
            "Non applicato.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    if decisioni.stato == STATO_BOZZA_ACCETTATA:
        print("ATTENZIONE: applicata la bozza accettata, non rivista da Riccardo.")

    from app.db import SessionLocal  # import tardivo: serve solo qui, mai nei test unitari puri

    voce_ids_assi = {riga.voce_id for riga in decisioni.assi}
    voce_ids_coeff = {riga.voce_id for riga in decisioni.coefficienti}

    chiavi: dict[int, dict] = {}
    sottocategorie_gerarchiche: set[int] = set()
    chiavi_classe: dict[int, str] = {}
    with SessionLocal() as session:  # sola lettura: nessun commit/add in questo script
        for voce_id in voce_ids_assi | voce_ids_coeff:
            chiave = risolvi_chiave_naturale(session, voce_id)
            if chiave is not None:
                chiavi[voce_id] = chiave
            if voce_id in voce_ids_assi and sottocategoria_famiglia_di(session, voce_id) == "gerarchica":
                sottocategorie_gerarchiche.add(voce_id)

        if not args.solo_assi:
            for voce_id in voce_ids_coeff:
                voce = session.get(Voce, voce_id)
                if voce is None:
                    continue
                sotto = session.get(Sottocategoria, voce.sottocategoria_id)
                if sotto is None:
                    continue
                proposta = proponi_coefficiente(voce.um, voce.descrizione, sotto.nome, sotto.categoria_code)
                chiavi_classe[voce_id] = proposta.classe

    seed_path = _BACKEND_DIR / "seed_data" / "seed-domande.json"
    seed_domande = json.loads(seed_path.read_text(encoding="utf-8"))

    risultato_assi = applica_assi(
        decisioni,
        seed_domande,
        chiavi,
        sottocategorie_gerarchiche=frozenset(sottocategorie_gerarchiche),
    )

    conteggi_per_asse: dict[str, int] = {}
    for riga in decisioni.assi:
        conteggi_per_asse[riga.asse] = conteggi_per_asse.get(riga.asse, 0) + 1

    print(f"stato: {risultato_assi.stato}")
    for asse, n in sorted(conteggi_per_asse.items()):
        print(f"  asse {asse!r}: {n} righe")
    print(f"famiglie di alternative: {len(risultato_assi.famiglie)}")
    print(f"righe assi con decisione != OK: {len(risultato_assi.modificate)}")
    for riga in risultato_assi.modificate:
        print(f"  - {riga}")

    dettaglio_path = _BACKEND_DIR / "seed_data" / "seed-dettaglio-pro.json"
    risultato_coeff_seed: dict | None = None
    saltate_coeff: list[str] = []
    classi: dict[str, dict[str, str]] | None = None
    if not args.solo_assi:
        seed_dettaglio = json.loads(dettaglio_path.read_text(encoding="utf-8"))
        risultato_coeff_seed, saltate_coeff = applica_coefficienti(decisioni, seed_dettaglio, chiavi)
        classi = calcola_classi(decisioni, chiavi_classe)
        print(f"coefficienti: {len(decisioni.coefficienti)} righe decise, {len(saltate_coeff)} saltate")
        for riga in saltate_coeff:
            print(f"  - {riga}")
        print(f"classi calcolate: {len(classi)}")

    if args.dry_run:
        print("dry-run: nessuna scrittura.")
        return

    seed_path.write_text(
        json.dumps(risultato_assi.seed_domande, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    fixture_path = _BACKEND_DIR / "tests" / "fixtures" / "famiglie_alternative_pro.json"
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    fixture_path.write_text(
        json.dumps(risultato_assi.famiglie, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"scritto {seed_path}")
    print(f"scritto {fixture_path}")

    if not args.solo_assi:
        contenuto_dettaglio = json.dumps(risultato_coeff_seed, indent=2, ensure_ascii=False) + "\n"
        dettaglio_path.write_text(contenuto_dettaglio, encoding="utf-8")
        docs_dettaglio_path = _BACKEND_DIR.parent / "docs" / "seed-dettaglio-pro.json"
        docs_dettaglio_path.write_text(contenuto_dettaglio, encoding="utf-8")
        classi_path = _BACKEND_DIR / "seed_data" / "taratura-classi.json"
        classi_path.write_text(
            json.dumps(
                {"stato": decisioni.stato, "fonte": Path(args.file).name, "classi": classi},
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"scritto {dettaglio_path}")
        print(f"scritto {docs_dettaglio_path}")
        print(f"scritto {classi_path}")

    if args.migrazione:
        import subprocess

        repo_root = _BACKEND_DIR.parent

        def _git_show_json(rev: str, path_relativo: str) -> dict:
            risultato = subprocess.run(
                ["git", "show", f"{rev}:{path_relativo}"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                encoding="utf-8",  # su Windows il default e' cp1252: le descrizioni uscirebbero in mojibake
                check=True,
            )
            return json.loads(risultato.stdout)

        base_domande = _git_show_json(args.base_rev, "backend/seed_data/seed-domande.json")
        base_dettaglio = _git_show_json(args.base_rev, "backend/seed_data/seed-dettaglio-pro.json")
        nuovo_domande = risultato_assi.seed_domande
        nuovo_dettaglio = risultato_coeff_seed if risultato_coeff_seed is not None else base_dettaglio

        versions_dir = _BACKEND_DIR / "alembic" / "versions"
        percorso_migrazione = emetti_migrazione(
            base_dettaglio, nuovo_dettaglio, base_domande, nuovo_domande, versions_dir, args.slug
        )
        if percorso_migrazione is not None:
            print(f"emessa migrazione: {percorso_migrazione}")
        else:
            print("nessuna migrazione emessa: nessuna differenza rispetto alla base.")


if __name__ == "__main__":
    main()
