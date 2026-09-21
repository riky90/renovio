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
    BonusDettaglioOut,
    BonusOut,
    CategoriaOut,
    ExtraOut,
    StimaInputEcho,
    StimaRequest,
    StimaResponse,
    TotaleOut,
)
from app.services.bonus_service import BonusService
from app.services.city_resolver import resolve_listino
from app.services.estimation import EstimationService
from app.services.testo_service import get_testo

router = APIRouter(prefix="/stima", tags=["stima"])


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
        result = EstimationService.compute(
            session,
            listino,
            mq=payload.mq,
            tipo=payload.tipo.value,
            risposte=payload.risposte,
        )

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

        disclaimer = get_testo(session, "disclaimer_fallback_citta", citta=payload.citta) if fallback else None

        # I bonus si calcolano DOPO, dai totali lordi gia' pronti: cosi'
        # `EstimationService` non viene toccato e il suo oracolo di regressione
        # (85 mq totale RE -> 47.985-70.575) resta intatto per costruzione.
        #
        # Si passa `result.extra` e non `extra_out`: il primo porta `.totale`
        # (il lordo IVA inclusa gia' arrotondato dal servizio), il secondo solo
        # importo e aliquota. La detrazione si applica alla spesa sostenuta,
        # cioe' al lordo — e usare quello del servizio garantisce che la base
        # dei bonus riconcili esattamente col totale mostrato all'utente.
        bonus_result = BonusService.compute(
            session,
            categorie_out,
            destinazione=payload.destinazione.value,
            disclaimer=get_testo(session, "disclaimer_bonus"),
            extra=result.extra,
        )

        return StimaResponse(
            input=StimaInputEcho(
                citta=payload.citta,
                mq=payload.mq,
                tipo=payload.tipo,
                destinazione=payload.destinazione,
                risposte=payload.risposte,
            ),
            fallback=fallback,
            disclaimer=disclaimer,
            valuta=listino.valuta,
            categorie=categorie_out,
            extra=extra_out,
            totale=totale_out,
            bonus=_bonus_out(bonus_result),
        )


def _bonus_out(result) -> BonusOut | None:
    """Mappa campo-per-campo, come ovunque nei router: mai `model_validate` su
    una dataclass interna."""
    if result is None:
        return None
    return BonusOut(
        bonus=[
            BonusDettaglioOut(
                code=d.code,
                nome=d.nome,
                descrizione=d.descrizione,
                base_min=d.base_min,
                base_max=d.base_max,
                aliquota_pct=d.aliquota_pct,
                tetto_spesa_eur=d.tetto_spesa_eur,
                tetto_modalita=d.tetto_modalita,
                tetto_raggiunto=d.tetto_raggiunto,
                rate_annuali=d.rate_annuali,
                detrazione_min=d.detrazione_min,
                detrazione_max=d.detrazione_max,
                rata_annua_min=d.rata_annua_min,
                rata_annua_max=d.rata_annua_max,
            )
            for d in result.bonus
        ],
        detrazione_min=result.detrazione_min,
        detrazione_max=result.detrazione_max,
        rata_annua_min=result.rata_annua_min,
        rata_annua_max=result.rata_annua_max,
        disclaimer=result.disclaimer,
    )
