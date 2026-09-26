"""Applica al catalogo la curatela degli ASSI del file di decisioni (D-08,
09-07-PLAN.md Task 1). Il piano 09-06 aggiungera' allo STESSO script la parte
coefficienti; oggi (`--solo-assi`, l'unica modalita' di questo piano) lo
script legge `docs/taratura/09-taratura-pro-compilato.xlsx`
(`genera_excel_taratura.leggi_decisioni`) e ricostruisce da zero, per ogni
voce con un asse approvato, gli effetti Pro corrispondenti in
`backend/seed_data/seed-domande.json` + la fixture delle famiglie di
alternative (`backend/tests/fixtures/famiglie_alternative_pro.json`).

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
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Allow `python scripts/applica_taratura.py` direct execution, stesso
# bootstrap di scripts/seed.py / scripts/genera_excel_taratura.py.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import openpyxl  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.models.dettaglio_pro import Sottocategoria, Voce  # noqa: E402
from app.services.effetti import (  # noqa: E402
    OPZIONE_VALORE,
    TIPO_ESCLUDI,
    TIPO_FATTORE_QUANTITA,
    TIPO_INCLUDI,
    TIPO_QUANTITA_PER_UNITA,
)
from scripts.genera_excel_taratura import DecisioniTaratura, leggi_decisioni  # noqa: E402

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
) -> RisultatoAssi:
    """Pura (nessun accesso a DB, nessuna scrittura su disco): ricostruisce da
    zero, dalle decisioni approvate (OK/MODIFICATO; NO gia' scartato da
    `leggi_decisioni`), gli effetti Pro a bersaglio naturale sulle cinque
    domande gestite, lasciando intatto tutto il resto (Free compreso).

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
            _aggiungi(riga.asse, riga.opzione, {"tipo_effetto": TIPO_INCLUDI, "target_voce": chiave})
        elif riga.asse in ASSI_STEPPER:
            valore = float(riga.valore_per_unita) if riga.valore_per_unita is not None else 1.0
            _aggiungi(
                riga.asse,
                OPZIONE_VALORE,
                {"tipo_effetto": TIPO_QUANTITA_PER_UNITA, "valore": valore, "target_voce": chiave},
            )
        elif riga.asse == "fattore_pavimento":
            # D-02: il bagno resta sempre gres/rivestimento, ma la SUA quota di
            # posa (voce A.6.1) deve restare nel computo anche quando il resto
            # della casa scegie un altro pavimento — altrimenti l'asse
            # tipo_pavimento la escluderebbe (governata solo dall'opzione
            # "gres"). Le rendiamo bersaglio anche delle altre opzioni, con
            # fattore_quantita che ne riduce la quantita' alla sola quota bagno.
            _aggiungi(
                DOMANDA_TIPO_PAVIMENTO, riga.opzione, {"tipo_effetto": TIPO_INCLUDI, "target_voce": chiave}
            )
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
            if riga.asse == "fattore_pavimento":
                # La quota bagno NON e' un'alternativa al pavimento scelto per
                # il resto della casa (le due voci coesistono nello stesso
                # computo, D-02): famiglia distinta per non far contare
                # A.6.1 (bagno) insieme ad A.6.2/.5/.6 (resto casa) nel test
                # CFG-02 "al massimo una voce per famiglia".
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


# --- (c) main -----------------------------------------------------------------


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
        default=True,
        help="applica solo la parte assi (unica modalita' di questo piano; il 09-06 ne aggiunge altre)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="stampa il riepilogo senza scrivere seed-domande.json / la fixture",
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

    chiavi: dict[int, dict] = {}
    with SessionLocal() as session:  # sola lettura: nessun commit/add in questo script
        for voce_id in {riga.voce_id for riga in decisioni.assi}:
            chiave = risolvi_chiave_naturale(session, voce_id)
            if chiave is not None:
                chiavi[voce_id] = chiave

    seed_path = _BACKEND_DIR / "seed_data" / "seed-domande.json"
    seed_domande = json.loads(seed_path.read_text(encoding="utf-8"))

    risultato = applica_assi(decisioni, seed_domande, chiavi)

    conteggi_per_asse: dict[str, int] = {}
    for riga in decisioni.assi:
        conteggi_per_asse[riga.asse] = conteggi_per_asse.get(riga.asse, 0) + 1

    print(f"stato: {risultato.stato}")
    for asse, n in sorted(conteggi_per_asse.items()):
        print(f"  asse {asse!r}: {n} righe")
    print(f"famiglie di alternative: {len(risultato.famiglie)}")
    print(f"righe con decisione != OK: {len(risultato.modificate)}")
    for riga in risultato.modificate:
        print(f"  - {riga}")

    if args.dry_run:
        print("dry-run: nessuna scrittura.")
        return

    seed_path.write_text(
        json.dumps(risultato.seed_domande, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    fixture_path = _BACKEND_DIR / "tests" / "fixtures" / "famiglie_alternative_pro.json"
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    fixture_path.write_text(
        json.dumps(risultato.famiglie, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"scritto {seed_path}")
    print(f"scritto {fixture_path}")


if __name__ == "__main__":
    main()
