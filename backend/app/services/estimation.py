"""EstimationService: the Free tier calculation engine (Ibrido C, ENG-01).

Dalla Fase 11 (v3.0) l'imponibile di ogni categoria e' il COMPUTO PARAMETRICO
sommato (`services/computo.py`, MOT-01): lo stesso calcolo voce per voce che il
Pro mostra in dettaglio, quindi Free e Pro coincidono per costruzione. Il
calcolo `base_eur_mq x moltiplicatore_tipo x mq` descritto qui sotto resta
come ripiego per un listino che non ha ancora regole (MOT-03).

ALL math happens in `Decimal`; coefficients are read from the DB (never
hardcoded — ENG-02). `coefficiente_impresa` is read off `ListinoCategoria`
internally but is NEVER placed on the result objects returned here — the
anti-leak boundary (RESEARCH Pattern 1 / threat T-02-01) is enforced by only
ever hand-building `CategoriaEstimata` / `ExtraEstimato` / `StimaResult` with
an explicit, closed set of client-facing fields.

Range/reconciliation rule (binding, 01-CONTEXT.md / 01-02-PLAN.md):
  1. The range (-range_pct_sotto / +range_pct, asymmetric since TAR-01) applies
     ONLY to the 4 category subtotals (imponibile + IVA).
  2. Extras are FIXED gross values — never scaled by the range.
  3. Grand total = SUM(category ranges) + SUM(fixed extras gross).
  4. Full Decimal math; quantize (ROUND_HALF_UP) only on output fields.

Layer parametrico (`risposte`, catalogo domande)
------------------------------------------------
Le risposte del wizard non sono colonne di questo modulo: arrivano come
dizionario e vengono tradotte in tre correzioni per categoria da
`app/services/effetti.py`, che e' l'unico posto dove una risposta diventa
aritmetica. Qui si applicano soltanto, nell'ordine dichiarato in `compute()`.

`risposte=None` spegne il layer: nessuna query in piu', nessuna correzione, e
il risultato e' bit-identico a quello prodotto prima che il catalogo domande
esistesse. E' la retrocompatibilita' dell'API pubblica resa esplicita, e il
motivo per cui l'oracolo primario (85 m2 totale RE -> 47.985-70.575) non si
muove.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models.catalogo import Categoria, Extra, Moltiplicatore, TipoRistrutturazione
from app.models.listino import Listino, ListinoCategoria
from app.services.computo import computo_free, tipo_effettivo
from app.services.effetti import risolvi_effetti_free


def _eur(value: Decimal) -> Decimal:
    """Quantize to whole euro (ROUND_HALF_UP) — used only on output fields."""
    return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class CategoriaEstimata:
    code: str
    nome: str
    iva_pct: Decimal
    totale_min: Decimal
    totale_max: Decimal


@dataclass(frozen=True)
class ExtraEstimato:
    code: str
    nome: str
    importo: Decimal
    iva_pct: Decimal
    totale: Decimal  # gross, fixed (importo * (1 + iva_pct)), same at min and max


@dataclass(frozen=True)
class StimaResult:
    categorie: list[CategoriaEstimata] = field(default_factory=list)
    extra: list[ExtraEstimato] = field(default_factory=list)
    totale_min: Decimal = Decimal("0")
    totale_max: Decimal = Decimal("0")
    #: Il tipo che le risposte descrivono (vedi `effetti.tipo_effettivo`): da
    #: qui viene l'ampiezza del range, e l'etichetta mostrata all'utente.
    tipo_effettivo: str = ""


class EstimationService:
    """Server-side calculation: (listino, mq, tipo, risposte) -> StimaResult."""

    @staticmethod
    def compute(
        session: Session,
        listino: Listino,
        mq: int,
        tipo: str,
        risposte: dict[str, Any] | None = None,
    ) -> StimaResult:
        # Il tipo scelto precompila le risposte (preset); l'ampiezza del range
        # segue invece i lavori davvero indicati.
        effettivo = tipo_effettivo(session, listino, mq=mq, tipo=tipo, risposte=risposte)
        tipo_row = session.query(TipoRistrutturazione).filter_by(code=effettivo).one()
        range_pct, range_sotto = tipo_row.range_pct, tipo_row.range_sotto

        # Computo parametrico (Fase 11, MOT-01): il Free e' il computo delle
        # voci sommato per categoria. Solo un listino senza regole ricade sul
        # calcolo EUR/m2 x moltiplicatore della v1 (MOT-03). Nel computo non
        # c'e' un layer spento: senza risposte vale il preset del tipo.
        computo = computo_free(session, listino, mq=mq, tipo=tipo, risposte=risposte)
        if computo is not None and risposte is None:
            risposte = {}

        correzioni = risolvi_effetti_free(session, mq=mq, tipo=tipo, risposte=risposte).correzioni

        # SOLO le categorie che fanno parte del totale lavori. L'arredo
        # (`E-ARREDO`, `nel_totale_lavori=False`) e' una categoria a tutti gli
        # effetti — ha voci, IVA e un suo posto nel dettaglio Pro — ma non e'
        # una lavorazione, e il totale che l'utente confronta con un preventivo
        # edile non deve contenerla. Il filtro e' sul dato, non sul codice:
        # vedi `models/catalogo.py::Categoria.nel_totale_lavori`.
        categorie_rows = (
            session.query(Categoria)
            .filter(Categoria.nel_totale_lavori.is_(True))
            .order_by(Categoria.ordine)
            .all()
        )

        categorie: list[CategoriaEstimata] = []
        sum_min = Decimal("0")
        sum_max = Decimal("0")

        for cat in categorie_rows:
            if computo is not None:
                imponibile = computo.per_categoria.get(cat.code, Decimal("0"))
            else:
                lc = (
                    session.query(ListinoCategoria)
                    .filter_by(listino_id=listino.id, categoria_code=cat.code)
                    .one()
                )
                molt = (
                    session.query(Moltiplicatore)
                    .filter_by(tipo_code=tipo, categoria_code=cat.code)
                    .one()
                )
                imponibile = lc.base_eur_mq * molt.valore * Decimal(mq)

            corr = correzioni.get(cat.code)
            if corr is not None:
                # Ordine vincolante (contratto in services/effetti.py):
                # moltiplicatori PRIMA dei termini additivi, cosi' un euro/m2
                # di efficientamento non viene scalato da un moltiplicatore
                # che riguarda tutt'altro. Un moltiplicatore complessivo a 0
                # azzera la categoria e ne salta i termini additivi: e' il
                # modo in cui "questo non lo rifaccio" resta intuitivo invece
                # di lasciare in piedi una coda di correzioni.
                imponibile = imponibile * corr.moltiplicatore
                if corr.moltiplicatore != 0:
                    imponibile += (
                        corr.eur_mq * Decimal(mq) + corr.eur_fisso + corr.eur_scostamento
                    )
                if imponibile < 0:
                    imponibile = Decimal("0")

            iva = imponibile * cat.iva_pct
            categoria_totale = imponibile + iva

            cat_min = _eur(categoria_totale * (Decimal("1") - range_sotto))
            cat_max = _eur(categoria_totale * (Decimal("1") + range_pct))

            categorie.append(
                CategoriaEstimata(
                    code=cat.code,
                    nome=cat.nome,
                    iva_pct=cat.iva_pct,
                    totale_min=cat_min,
                    totale_max=cat_max,
                )
            )
            sum_min += cat_min
            sum_max += cat_max

        extra_rows = session.query(Extra).filter_by(attivo=True).order_by(Extra.code).all()
        extras: list[ExtraEstimato] = []
        extra_sum = Decimal("0")
        for ex in extra_rows:
            gross = _eur(ex.importo * (Decimal("1") + ex.iva_pct))
            extras.append(
                ExtraEstimato(code=ex.code, nome=ex.nome, importo=ex.importo, iva_pct=ex.iva_pct, totale=gross)
            )
            extra_sum += gross

        return StimaResult(
            categorie=categorie,
            extra=extras,
            totale_min=sum_min + extra_sum,
            totale_max=sum_max + extra_sum,
            tipo_effettivo=effettivo,
        )
