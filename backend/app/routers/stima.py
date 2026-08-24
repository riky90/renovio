"""POST /api/v1/stima — the public estimate endpoint.

Wires `resolve_listino` + `EstimationService.compute` (both server-side,
01-02) into the anti-leak `StimaResponse` DTO. The response is built
explicitly field-by-field from `StimaResult` — never `model_validate`'d off
an ORM entity — so `coefficiente_impresa`/`base_eur_mq`/`moltiplicatore`
never reach the wire (RESEARCH Pattern 1, T-03-01).

`EstimationService.compute()` returns each category's `totale_min`/`max` as
a single already-ranged gross value (imponibile+IVA combined, then ±range
applied uniformly to both terms — see 01-02-PLAN.md). The imponibile/IVA
split published in the API contract is recovered here by dividing back out
the (fixed) `iva_pct` scalar: since both terms were scaled by the same
range factor, `imponibile = totale / (1 + iva_pct)` is an exact split, not
an approximation — see `_split_imponibile_iva`.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Request

from app.db import SessionLocal
from app.limiter import limiter
from app.schemas.stima import (
    CategoriaOut,
    ExtraOut,
    StimaInputEcho,
    StimaRequest,
    StimaResponse,
    TotaleOut,
)
from app.services.city_resolver import resolve_listino
from app.services.estimation import EstimationService

router = APIRouter(prefix="/stima", tags=["stima"])

DISCLAIMER_TEMPLATE = "Stima basata sul listino di Reggio Emilia, non ancora tarata su {citta}."


def _split_imponibile_iva(totale: Decimal, iva_pct: Decimal) -> tuple[Decimal, Decimal]:
    """Exact split of a gross (imponibile+IVA) value back into its parts.

    `totale` was produced as `imponibile * (1 + iva_pct)` scaled uniformly
    by the range factor, so `imponibile = totale / (1 + iva_pct)` recovers
    the exact pre-range-scaled ratio; `iva = totale - imponibile` guarantees
    the two always sum back to `totale` with zero rounding drift.
    """
    imponibile = (totale / (Decimal("1") + iva_pct)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    iva = totale - imponibile
    return imponibile, iva


@router.post("", response_model=StimaResponse)
@limiter.limit("20/minute")
def crea_stima(payload: StimaRequest, request: Request) -> StimaResponse:
    with SessionLocal() as session:
        listino, fallback = resolve_listino(session, payload.citta)
        result = EstimationService.compute(session, listino, mq=payload.mq, tipo=payload.tipo.value)

        categorie_out: list[CategoriaOut] = []
        for cat in result.categorie:
            imp_min, iva_min = _split_imponibile_iva(cat.totale_min, cat.iva_pct)
            imp_max, iva_max = _split_imponibile_iva(cat.totale_max, cat.iva_pct)
            categorie_out.append(
                CategoriaOut(
                    code=cat.code,
                    nome=cat.nome,
                    imponibile_min=imp_min,
                    imponibile_max=imp_max,
                    iva_pct=cat.iva_pct,
                    iva_min=iva_min,
                    iva_max=iva_max,
                    totale_min=cat.totale_min,
                    totale_max=cat.totale_max,
                )
            )

        extra_out = [
            ExtraOut(code=ex.code, nome=ex.nome, importo=ex.importo, iva_pct=ex.iva_pct)
            for ex in result.extra
        ]

        totale_imponibile_min = sum((c.imponibile_min for c in categorie_out), Decimal("0"))
        totale_imponibile_max = sum((c.imponibile_max for c in categorie_out), Decimal("0"))
        totale_iva_min = sum((c.iva_min for c in categorie_out), Decimal("0"))
        totale_iva_max = sum((c.iva_max for c in categorie_out), Decimal("0"))

        # Extra imponibile/IVA split derived from the service's own rounded
        # gross (`ex.totale`) so the sum always reconciles exactly with
        # `result.totale_min/max` (which was built from that same gross).
        extra_imponibile_sum = sum((ex.importo for ex in result.extra), Decimal("0"))
        extra_iva_sum = sum((ex.totale - ex.importo for ex in result.extra), Decimal("0"))

        totale_out = TotaleOut(
            imponibile_min=totale_imponibile_min + extra_imponibile_sum,
            imponibile_max=totale_imponibile_max + extra_imponibile_sum,
            iva_min=totale_iva_min + extra_iva_sum,
            iva_max=totale_iva_max + extra_iva_sum,
            totale_min=result.totale_min,
            totale_max=result.totale_max,
        )

        disclaimer = DISCLAIMER_TEMPLATE.format(citta=payload.citta) if fallback else None

        return StimaResponse(
            input=StimaInputEcho(citta=payload.citta, mq=payload.mq, tipo=payload.tipo),
            fallback=fallback,
            disclaimer=disclaimer,
            valuta=listino.valuta,
            categorie=categorie_out,
            extra=extra_out,
            totale=totale_out,
        )
