"""EstimationService: the Free tier calculation engine (Ibrido C, ENG-01).

ALL math happens in `Decimal`; coefficients are read from the DB (never
hardcoded — ENG-02). `coefficiente_impresa` is read off `ListinoCategoria`
internally but is NEVER placed on the result objects returned here — the
anti-leak boundary (RESEARCH Pattern 1 / threat T-02-01) is enforced by only
ever hand-building `CategoriaEstimata` / `ExtraEstimato` / `StimaResult` with
an explicit, closed set of client-facing fields.

Range/reconciliation rule (binding, 01-CONTEXT.md / 01-02-PLAN.md):
  1. ±range_pct applies ONLY to the 4 category subtotals (imponibile + IVA).
  2. Extras are FIXED gross values — never scaled by the range.
  3. Grand total = SUM(category ranges) + SUM(fixed extras gross).
  4. Full Decimal math; quantize (ROUND_HALF_UP) only on output fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.models.catalogo import Categoria, Extra, Moltiplicatore, TipoRistrutturazione
from app.models.listino import Listino, ListinoCategoria


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


class EstimationService:
    """Server-side calculation: (listino, mq, tipo) -> StimaResult."""

    @staticmethod
    def compute(session: Session, listino: Listino, mq: int, tipo: str) -> StimaResult:
        tipo_row = session.query(TipoRistrutturazione).filter_by(code=tipo).one()
        range_pct = tipo_row.range_pct

        categorie_rows = session.query(Categoria).order_by(Categoria.ordine).all()

        categorie: list[CategoriaEstimata] = []
        sum_min = Decimal("0")
        sum_max = Decimal("0")

        for cat in categorie_rows:
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
            iva = imponibile * cat.iva_pct
            categoria_totale = imponibile + iva

            cat_min = _eur(categoria_totale * (Decimal("1") - range_pct))
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
        )
