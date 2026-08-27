"""DettaglioProService: motore Pro bottom-up (PRO-01, 03-03-PLAN.md Task 1).

Indipendente dal motore di stima Free (D-01): questo modulo non importa
alcuna classe del servizio di stima Fase 1 e non riconcilia il proprio
risultato col totale della Fase 1 — sono misure diverse, e' atteso e
accettabile che i due numeri differiscano.

ALL math happens in `Decimal`; coefficienti/prezzi letti dal DB (mai
cablati nel codice, ENG-02). Nessun campo/colonna impresa esiste su `Voce`
(D-10) ne' viene mai letto o restituito da questo modulo: l'anti-leak e'
strutturale, non solo di schema-risposta (stessa disciplina di
`estimation.py` — dataclass frozen a campi chiusi).

Range per-voce (Assunzione A1, 03-RESEARCH.md Pattern 4): riuso di
`TipoRistrutturazione.range_pct` (10/15/20% per tipo, gia' a DB per il
Free) applicato a `quantita_stimata * prezzo_unitario_cliente`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.models.catalogo import Categoria, TipoRistrutturazione
from app.models.dettaglio_pro import CoefficienteQuantitaVoce, Sottocategoria, Voce
from app.models.listino import Listino


def _eur(value: Decimal) -> Decimal:
    """Quantize to whole euro (ROUND_HALF_UP) — used only on output fields."""
    return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _qta(value: Decimal) -> Decimal:
    """Quantize a stimata quantity to 0.01 (ROUND_HALF_UP)."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class VoceEstimata:
    codice: str | None
    descrizione: str
    um: str
    quantita_stimata: Decimal
    prezzo_min: Decimal
    prezzo_max: Decimal


@dataclass(frozen=True)
class SottocategoriaEstimata:
    codice: str | None
    nome: str
    famiglia: str
    voci: list[VoceEstimata] = field(default_factory=list)


@dataclass(frozen=True)
class CategoriaDettagliata:
    code: str
    nome: str
    sottocategorie: list[SottocategoriaEstimata] = field(default_factory=list)


@dataclass(frozen=True)
class DettaglioProResult:
    categorie: list[CategoriaDettagliata] = field(default_factory=list)


class DettaglioProService:
    """Server-side calculation: (listino, mq, tipo, risposte) -> DettaglioProResult."""

    @staticmethod
    def compute(
        session: Session, listino: Listino, mq: int, tipo: str, risposte: dict[str, int]
    ) -> DettaglioProResult:
        tipo_row = session.query(TipoRistrutturazione).filter_by(code=tipo).one()
        range_pct = tipo_row.range_pct

        categorie_rows = session.query(Categoria).order_by(Categoria.ordine).all()

        categorie: list[CategoriaDettagliata] = []
        for cat in categorie_rows:
            sotto_rows = (
                session.query(Sottocategoria)
                .filter_by(listino_id=listino.id, categoria_code=cat.code)
                .order_by(Sottocategoria.ordine)
                .all()
            )

            sottocategorie: list[SottocategoriaEstimata] = []
            for sotto in sotto_rows:
                voce_rows = (
                    session.query(Voce).filter_by(sottocategoria_id=sotto.id).order_by(Voce.ordine).all()
                )

                voci: list[VoceEstimata] = []
                for voce in voce_rows:
                    coeff = (
                        session.query(CoefficienteQuantitaVoce)
                        .filter_by(voce_id=voce.id, tipo_code=tipo)
                        .one_or_none()
                    )

                    quantita_stimata = DettaglioProService._quantita(coeff, mq, risposte)

                    totale_voce = quantita_stimata * voce.prezzo_unitario_cliente
                    prezzo_min = _eur(totale_voce * (Decimal("1") - range_pct))
                    prezzo_max = _eur(totale_voce * (Decimal("1") + range_pct))

                    voci.append(
                        VoceEstimata(
                            codice=voce.codice,
                            descrizione=voce.descrizione,
                            um=voce.um,
                            quantita_stimata=quantita_stimata,
                            prezzo_min=prezzo_min,
                            prezzo_max=prezzo_max,
                        )
                    )

                sottocategorie.append(
                    SottocategoriaEstimata(
                        codice=sotto.codice,
                        nome=sotto.nome,
                        famiglia=sotto.famiglia,
                        voci=voci,
                    )
                )

            categorie.append(
                CategoriaDettagliata(code=cat.code, nome=cat.nome, sottocategorie=sottocategorie)
            )

        return DettaglioProResult(categorie=categorie)

    @staticmethod
    def _quantita(
        coeff: CoefficienteQuantitaVoce | None, mq: int, risposte: dict[str, int]
    ) -> Decimal:
        """Applica le due strategie UM del blocco <behavior> del piano:
        coefficiente-per-mq (voci UM=mq/ml) vs conteggio da domanda mirata
        con default (voci a `cad`/`ac`). Se la riga coefficiente manca del
        tutto, la quantita' e' 0 (nessuna voce senza copertura nel seed)."""
        if coeff is None:
            return Decimal("0.00")
        if coeff.coefficiente_qta_per_mq is not None:
            return _qta(coeff.coefficiente_qta_per_mq * Decimal(mq))
        if coeff.domanda_mirata_key is not None:
            valore = risposte.get(coeff.domanda_mirata_key, coeff.default_conteggio)
            return _qta(Decimal(valore if valore is not None else 0))
        if coeff.default_conteggio is not None:
            return _qta(Decimal(coeff.default_conteggio))
        return Decimal("0.00")
