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
    ArredoAmbienteOut,
    ArredoOut,
    CategoriaOut,
    ConfrontoFinitureOut,
    ExtraOut,
    StimaInputEcho,
    StimaRequest,
    StimaResponse,
    TotaleOut,
)
from app.services.arredo import ArredoService
from app.services.bonus_stima import bonus_out_per_stima
from app.services.city_resolver import resolve_listino
from app.models.domanda import Domanda, OpzioneDomanda
from app.services.effetti import DOMANDA_LIVELLO_FINITURE
from app.services.estimation import EstimationService
from app.services.risultato import livello_corrente, livello_inferiore
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
        # L'arredo si calcola anch'esso DOPO e per conto suo: non passa dal
        # motore Free, che e' il totale LAVORI. `None` quando non c'e' nulla
        # da mostrare — mai una sezione a zero.
        arredo_result = ArredoService.compute(session, payload.risposte)

        # Il calcolo dei bonus (con l'arredo come pseudo-categoria E-ARREDO per
        # il Bonus Mobili, la detrazione sui lavori e il netto) sta tutto in
        # `bonus_out_per_stima`: il router non contiene logica fiscale.
        bonus_out = bonus_out_per_stima(
            session,
            categorie_lorde=categorie_out,
            extra_lordi=result.extra,
            arredo=(arredo_result.totale_min, arredo_result.totale_max) if arredo_result else None,
            destinazione=payload.destinazione.value,
            totale_min=result.totale_min,
            totale_max=result.totale_max,
        )

        confronto, finiture_al_minimo = _confronto_finiture(session, listino, payload, result)

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
            bonus=bonus_out,
            arredo=_arredo_out(session, arredo_result),
            confronto_finiture=confronto,
            finiture_al_minimo=finiture_al_minimo,
            tipo_effettivo=result.tipo_effettivo or payload.tipo,
        )


def _confronto_finiture(
    session, listino, payload: StimaRequest, result
) -> tuple[ConfrontoFinitureOut | None, bool]:
    """Ricalcolo vero del motore Free con il livello finiture un gradino sotto.

    Guarda solo il totale lavori (l'arredo non entra, D-08). Ritorna
    (confronto, finiture_al_minimo). None quando il layer parametrico e' spento,
    non c'e' un livello inferiore o il ricalcolo non abbassa il massimo.
    """
    if payload.risposte is None:
        return None, False
    attiva = (
        session.query(Domanda.code)
        .filter(Domanda.code == DOMANDA_LIVELLO_FINITURE, Domanda.attiva.is_(True))
        .first()
    )
    if attiva is None:
        return None, False
    righe = (
        session.query(OpzioneDomanda)
        .filter(
            OpzioneDomanda.domanda_code == DOMANDA_LIVELLO_FINITURE,
            OpzioneDomanda.attiva.is_(True),
        )
        .all()
    )
    if not righe:
        return None, False
    opzioni = [(o.code, o.ordine, o.is_default) for o in righe]
    scelto = payload.risposte.get(DOMANDA_LIVELLO_FINITURE)
    if not isinstance(scelto, str):
        scelto = None
    corrente = livello_corrente(opzioni, scelto)
    inferiore = livello_inferiore(opzioni, scelto)
    if inferiore is None:
        return None, corrente is not None and (scelto is None or scelto == corrente)

    conf = EstimationService.compute(
        session,
        listino,
        mq=payload.mq,
        tipo=payload.tipo.value,
        risposte={**payload.risposte, DOMANDA_LIVELLO_FINITURE: inferiore},
    )
    if conf.totale_max >= result.totale_max:
        return None, False
    nome = next(o.etichetta for o in righe if o.code == inferiore)
    return (
        ConfrontoFinitureOut(
            livello_code=inferiore,
            livello_nome=nome,
            totale_min=conf.totale_min,
            totale_max=conf.totale_max,
        ),
        False,
    )


def _arredo_out(session, result) -> ArredoOut | None:
    """Mappa campo-per-campo, come `bonus_out_per_stima`. Il disclaimer si legge QUI e
    finisce dentro il payload, cosi' viaggia nello snapshot e nel PDF."""
    if result is None:
        return None
    return ArredoOut(
        livello_code=result.livello_code,
        livello_nome=result.livello_nome,
        ambienti=[
            ArredoAmbienteOut(
                code=a.code, nome=a.nome, eur_min=a.eur_min, eur_max=a.eur_max
            )
            for a in result.ambienti
        ],
        totale_min=result.totale_min,
        totale_max=result.totale_max,
        disclaimer=get_testo(session, "disclaimer_arredo"),
    )
