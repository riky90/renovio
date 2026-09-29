"""Helper unico che costruisce il `BonusOut` di una stima: dettaglio dei bonus,
detrazione sui lavori e costo netto a range.

Sta in un servizio e non nel router perche' lo riusano sia il Free (POST /stima)
sia il Pro. Il client non calcola nessun valore fiscale: mappa i campi del DTO.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable

from sqlalchemy.orm import Session

from app.schemas.stima import BonusDettaglioOut, BonusOut
from app.services.bonus_service import BonusResult, BonusService
from app.services.testo_service import get_testo

#: Il codice della categoria arredo. E' l'unico punto in cui il totale arredo
#: viene PRESENTATO come se fosse una categoria — per la base dei bonus. Il
#: calcolo dell'arredo, quello vero, non lo nomina mai (vedi `services/arredo.py`).
CATEGORIA_ARREDO = "E-ARREDO"


@dataclass(frozen=True)
class CategoriaPerBonus:
    """Il minimo che `BonusService.CategoriaConTotale` chiede: un codice e due
    totali lordi."""

    code: str
    totale_min: Decimal
    totale_max: Decimal


@dataclass(frozen=True)
class ExtraPerBonus:
    """Il minimo che `BonusService.ExtraConTotale` chiede: codice e totale lordo."""

    code: str
    totale: Decimal


def _eur(value: Decimal) -> Decimal:
    return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def bonus_out_per_stima(
    session: Session,
    *,
    categorie_lorde: Iterable,
    extra_lordi: Iterable,
    arredo: tuple[Decimal, Decimal] | None,
    destinazione: str,
    totale_min: Decimal,
    totale_max: Decimal,
) -> BonusOut | None:
    """`None` quando non c'e' nulla da mostrare: la sezione sparisce, mai a zero.

    Il netto e' Totale IVA inclusa - detrazione sui LAVORI, a coppie (min con
    min, max con max), mai sotto zero. La detrazione sui lavori e' il calcolo
    fatto SENZA la pseudo-categoria E-ARREDO: l'arredo sta accanto al totale
    lavori, non dentro, quindi la detrazione sull'arredo (Bonus Mobili) non
    puo' ridurne il costo. Il dettaglio per bonus resta quello completo.
    """
    categorie = list(categorie_lorde)
    extra = list(extra_lordi)
    disclaimer = get_testo(session, "disclaimer_bonus")

    basi = list(categorie)
    if arredo is not None:
        basi.append(CategoriaPerBonus(CATEGORIA_ARREDO, arredo[0], arredo[1]))

    completo = BonusService.compute(
        session, basi, destinazione=destinazione, disclaimer=disclaimer, extra=extra
    )
    if completo is None:
        return None

    if arredo is not None:
        lavori: BonusResult | None = BonusService.compute(
            session, categorie, destinazione=destinazione, disclaimer=disclaimer, extra=extra
        )
        if lavori is None:
            detr_lavori_min = detr_lavori_max = Decimal("0")
        else:
            detr_lavori_min, detr_lavori_max = lavori.detrazione_min, lavori.detrazione_max
    else:
        detr_lavori_min, detr_lavori_max = completo.detrazione_min, completo.detrazione_max

    netto_min = _eur(max(Decimal("0"), totale_min - detr_lavori_min))
    netto_max = _eur(max(Decimal("0"), totale_max - detr_lavori_max))

    return _mappa(completo, detr_lavori_min, detr_lavori_max, netto_min, netto_max)


def _mappa(
    result: BonusResult,
    detr_lavori_min: Decimal,
    detr_lavori_max: Decimal,
    netto_min: Decimal,
    netto_max: Decimal,
) -> BonusOut:
    """Mappa campo-per-campo: mai `model_validate` su una dataclass interna."""
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
        detrazione_lavori_min=detr_lavori_min,
        detrazione_lavori_max=detr_lavori_max,
        netto_min=netto_min,
        netto_max=netto_max,
    )
