"""Confronto del computo parametrico con i computi reali (TAR-01, fase 11).

Per ogni fixture di `backend/tests/fixtures/casi_reali/` (scritta da
`estrai_casi_reali.py`, input del wizard dedotti a mano) esegue il motore sugli
input del caso e lo confronta col computo del tecnico:

- per categoria, sull'imponibile: il reale e' il totale del riepilogo diviso
  per l'IVA del file, con le `riclassifica` della fixture (un importo scritto
  dal tecnico in una categoria diversa da quella del listino);
- voce per voce: quantita' e importo dei due lati, e l'importo che il motore
  darebbe con i prezzi del file (cosi' uno scarto solo di prezzo non passa per
  un errore del motore);
- il totale lavori reale (IVA inclusa) contro il range mostrato all'utente.

`tests/test_casi_reali.py` usa le stesse funzioni come casi d'oro.

Run (da backend/): `.venv/bin/python scripts/confronta_casi_reali.py [OUT.md]`
scrive il report Markdown (default: stdout).
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from sqlalchemy.orm import Session  # noqa: E402

from app.models.listino import Listino  # noqa: E402
from app.services.computo import computo_free  # noqa: E402
from app.services.estimation import EstimationService  # noqa: E402

FIXTURE_DIR = _BACKEND_DIR / "tests" / "fixtures" / "casi_reali"
#: IVA con cui il file reale calcola i totali del riepilogo (etichette del
#: foglio `Analisi preliminareTOTALI`). Serve solo a tornare all'imponibile.
IVA_FILE = {
    "A-EDILE": Decimal("0.10"),
    "B-FINITURE": Decimal("0.22"),
    "C-SERRAMENTI": Decimal("0.10"),
    "D-PRODOTTI": Decimal("0.10"),
}
CATEGORIE = tuple(IVA_FILE)


def carica_casi() -> list[dict]:
    return [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(FIXTURE_DIR.glob("caso-*.json"))
    ]


@dataclass
class RigaVoce:
    codice: str
    descrizione: str
    q_reale: Decimal
    q_motore: Decimal
    imp_reale: Decimal
    imp_motore: Decimal
    #: Quantita' del motore x prezzo unitario del file (se la voce e' nel file).
    imp_motore_prezzi_file: Decimal
    traccia: str

    @property
    def scarto(self) -> Decimal:
        return self.imp_motore - self.imp_reale


@dataclass
class Confronto:
    caso: str
    reale: dict[str, Decimal]
    motore: dict[str, Decimal]
    voci: list[RigaVoce]
    totale_reale_ivato: Decimal
    range_min: Decimal
    range_max: Decimal
    tipo_effettivo: str
    nella_soglia: bool
    note: list[str] = field(default_factory=list)

    def scarto_pct(self, categoria: str) -> Decimal | None:
        reale = self.reale.get(categoria, Decimal("0"))
        if reale == 0:
            return None
        return (self.motore.get(categoria, Decimal("0")) - reale) / reale * 100

    @property
    def errore_voci_edile(self) -> Decimal:
        """Somma degli scarti assoluti voce per voce di A-EDILE, con le
        quantita' del motore ai prezzi del file: misura le quantita' e non i
        prezzi, e non lascia che un errore in eccesso ne compensi uno in
        difetto come fa il totale."""
        return sum(
            (abs(v.imp_motore_prezzi_file - v.imp_reale) for v in self.voci if v.codice.startswith("A.")),
            Decimal("0"),
        )

    @property
    def nel_range(self) -> bool:
        return self.range_min <= self.totale_reale_ivato <= self.range_max


def _d(valore) -> Decimal:
    return Decimal(str(valore or 0))


def confronta(session: Session, listino: Listino, caso: dict) -> Confronto:
    inp = caso["input"]
    computo = computo_free(
        session, listino, mq=inp["mq"], tipo=inp["tipo"], risposte=inp["risposte"]
    )
    assert computo is not None, "il listino di default ha le regole del computo"
    stima = EstimationService.compute(
        session, listino, mq=inp["mq"], tipo=inp["tipo"], risposte=inp["risposte"]
    )

    totali = caso["totali_ivati"]
    reale = {c: _d(totali.get(c)) / (1 + IVA_FILE[c]) for c in CATEGORIE}
    # Importi che il tecnico ha scritto in una categoria diversa da quella del
    # listino (porte o caldaia fornite dentro l'edile): per lo scarto per
    # categoria si confronta a parita' di perimetro. Il totale non cambia.
    for r in caso.get("riclassifica", []):
        reale[r["da"]] -= _d(r["importo"])
        reale[r["a"]] += _d(r["importo"])

    # Lato reale per codice (piu' righe con lo stesso codice si sommano).
    file_q: dict[str, Decimal] = defaultdict(Decimal)
    file_imp: dict[str, Decimal] = defaultdict(Decimal)
    file_desc: dict[str, str] = {}
    file_prezzo: dict[str, Decimal] = {}
    for v in caso["voci"]:
        codice = v["codice"] or (v.get("codici_candidati") or ["?"])[0]
        file_q[codice] += _d(v["quantita"])
        file_imp[codice] += _d(v["totale"])
        file_desc.setdefault(codice, v["descrizione"])
        if v["um"] not in ("ac", "%") and v["prezzo"]:
            file_prezzo.setdefault(codice, _d(v["prezzo"]))

    motore_voci = {v.codice: v for v in computo.voci if v.codice}
    righe: list[RigaVoce] = []
    for codice in sorted(set(file_imp) | set(motore_voci), key=_ordine_codice):
        mv = motore_voci.get(codice)
        q_m = mv.quantita if mv else Decimal("0")
        imp_m = mv.importo if mv else Decimal("0")
        prezzo_file = file_prezzo.get(codice)
        righe.append(
            RigaVoce(
                codice=codice,
                descrizione=(mv.descrizione if mv else file_desc.get(codice, ""))[:70],
                q_reale=file_q.get(codice, Decimal("0")),
                q_motore=q_m,
                imp_reale=file_imp.get(codice, Decimal("0")),
                imp_motore=imp_m,
                imp_motore_prezzi_file=q_m * prezzo_file if prezzo_file is not None else imp_m,
                traccia=mv.traccia if mv else "",
            )
        )

    return Confronto(
        caso=caso["caso"],
        reale=reale,
        # Il centro del range della stima, tolta l'IVA: e' quello che vede
        # l'utente, con le categorie che ha escluso (`non_rifare`) a zero.
        motore={
            c: next(
                ((s.totale_min + s.totale_max) / 2 / (1 + s.iva_pct) for s in stima.categorie if s.code == c),
                Decimal("0"),
            )
            for c in CATEGORIE
        },
        voci=righe,
        totale_reale_ivato=_d(totali.get("totale_lavori")),
        range_min=sum((c.totale_min for c in stima.categorie), Decimal("0")),
        range_max=sum((c.totale_max for c in stima.categorie), Decimal("0")),
        tipo_effettivo=stima.tipo_effettivo,
        nella_soglia=caso.get("soglia", {}).get("nella_soglia", True),
    )


def _ordine_codice(codice: str) -> tuple:
    parti = codice.replace("?", "0").split(".")
    return tuple((0, int(p)) if p.isdigit() else (1, p) for p in parti)


# --- report -------------------------------------------------------------------


def _eur(valore: Decimal) -> str:
    return f"{valore:,.0f}".replace(",", ".")


def _pct(valore: Decimal | None) -> str:
    return "—" if valore is None else f"{valore:+.0f}%"


def report_caso(c: Confronto, n_voci: int = 10) -> str:
    righe = [f"### {c.caso}", ""]
    righe.append("| Categoria | Reale (imponibile) | Motore | Scarto |")
    righe.append("|---|---:|---:|---:|")
    for cat in CATEGORIE:
        if c.reale[cat] == 0 and c.motore[cat] == 0:
            continue
        righe.append(
            f"| {cat} | {_eur(c.reale[cat])} | {_eur(c.motore[cat])} | {_pct(c.scarto_pct(cat))} |"
        )
    tot_r, tot_m = sum(c.reale.values()), sum(c.motore.values())
    righe.append(
        f"| **Totale lavori** | **{_eur(tot_r)}** | **{_eur(tot_m)}** | "
        f"**{_pct((tot_m - tot_r) / tot_r * 100 if tot_r else None)}** |"
    )
    righe.append("")
    esito = "dentro" if c.nel_range else "FUORI"
    righe.append(
        f"Totale reale IVA inclusa {_eur(c.totale_reale_ivato)} € — range del motore "
        f"{_eur(c.range_min)}–{_eur(c.range_max)} € (tipo effettivo `{c.tipo_effettivo}`): **{esito}**."
    )
    righe.append("")
    edile = [v for v in c.voci if v.codice.startswith("A.")]
    peggiori = sorted(edile, key=lambda v: abs(v.scarto), reverse=True)[:n_voci]
    righe.append(f"Le {n_voci} voci di A-EDILE più lontane (imponibile):")
    righe.append("")
    righe.append("| Voce | q reale | q motore | € reale | € motore | € motore a prezzi file | Traccia del motore |")
    righe.append("|---|---:|---:|---:|---:|---:|---|")
    for v in peggiori:
        righe.append(
            f"| {v.codice} {v.descrizione[:40]} | {v.q_reale:g} | {v.q_motore:.1f} | {_eur(v.imp_reale)} | "
            f"{_eur(v.imp_motore)} | {_eur(v.imp_motore_prezzi_file)} | {v.traccia[:70]} |"
        )
    righe.append("")
    return "\n".join(righe)


def report(confronti: list[Confronto]) -> str:
    righe = [
        "| Caso | Edile reale | Edile motore | Scarto edile | Errore voce per voce | "
        "Totale reale IVA | Range motore | Nel range | In soglia |"
    ]
    righe.append("|---|---:|---:|---:|---:|---:|---:|---|---|")
    for c in confronti:
        righe.append(
            f"| {c.caso} | {_eur(c.reale['A-EDILE'])} | {_eur(c.motore['A-EDILE'])} | "
            f"{_pct(c.scarto_pct('A-EDILE'))} | {_eur(c.errore_voci_edile)} | {_eur(c.totale_reale_ivato)} | "
            f"{_eur(c.range_min)}–{_eur(c.range_max)} | {'sì' if c.nel_range else 'no'} | "
            f"{'sì' if c.nella_soglia else 'frontiera'} |"
        )
    righe.append("")
    return "\n".join(righe) + "\n" + "\n".join(report_caso(c) for c in confronti)


def main() -> None:
    from sqlalchemy import create_engine

    from app.db import Base
    from app.services.city_resolver import resolve_listino
    from scripts.seed import load_seed_data, seed
    from tests.session_factory import sessione_di_test

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    with sessione_di_test(engine)() as session:
        seed(session, load_seed_data())
        listino, _ = resolve_listino(session, "Reggio Emilia")
        testo = report([confronta(session, listino, caso) for caso in carica_casi()])
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(testo, encoding="utf-8")
    else:
        print(testo)


if __name__ == "__main__":
    main()
