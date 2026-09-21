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

LIVELLI DI FINITURA — le sottocategorie `famiglia='catalogo'` sono cataloghi
di ALTERNATIVE, non addendi. `PAVIMENTI E RIVESTIMENTI GRES`, `PAVIMENTI` e
`PAVIMENTI PARQUET` sono tre pavimentazioni per la STESSA stanza: sommarle
tutte gonfia il totale per costruzione (misurato: otto volte il sintetico su
una stima reale di 120 m2). Il livello di finitura e' il selettore che ne
sceglie una — vedi `_voce_inclusa()`, che e' un filtro A MONTE del calcolo:
`_quantita()` non sa nulla dei livelli e non deve saperne.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.models.catalogo import Categoria, LivelloFinitura, TipoRistrutturazione
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
    # Livello di finitura della voce; None = comune a tutti i livelli.
    livello: str | None = None


@dataclass(frozen=True)
class SottocategoriaEstimata:
    codice: str | None
    nome: str
    famiglia: str
    voci: list[VoceEstimata] = field(default_factory=list)
    # Subtotale a range = somma dei prezzi min/max delle voci (D-11: sempre a
    # range, mai un punto). Calcolato dal servizio, unica fonte per schermata
    # e PDF (03-RESEARCH.md Pitfall 2).
    totale_min: Decimal = Decimal("0")
    totale_max: Decimal = Decimal("0")


@dataclass(frozen=True)
class CategoriaDettagliata:
    code: str
    nome: str
    sottocategorie: list[SottocategoriaEstimata] = field(default_factory=list)
    totale_min: Decimal = Decimal("0")
    totale_max: Decimal = Decimal("0")
    # Livello EFFETTIVAMENTE applicato a questa categoria (None dove il livello
    # non e' selezionabile, es. A-EDILE). E' il valore risolto — la scelta
    # dell'utente oppure il default di tabella — non quello grezzo in input:
    # e' cio' che schermata e PDF devono mostrare.
    livello_scelto: str | None = None
    livello_scelto_nome: str | None = None


@dataclass(frozen=True)
class DettaglioProResult:
    categorie: list[CategoriaDettagliata] = field(default_factory=list)
    # Totale generale a range = somma dei totali di categoria.
    totale_min: Decimal = Decimal("0")
    totale_max: Decimal = Decimal("0")


class LivelliNonValidi(ValueError):
    """Input `livelli` non ammesso. Il router la traduce in 400."""


def validate_livelli(session: Session, livelli: dict[str, str] | None) -> None:
    """Valida le CHIAVI oltre ai valori: `livelli` arriva dal client, e un dict
    non validato e' un dict di cui non si sa nulla. Le chiavi devono essere
    categorie con `livello_selezionabile=True` (mandare un livello per A-EDILE
    e' un errore, non un no-op silenzioso) e i valori codici esistenti in
    `livello_finitura`. Entrambi i vincoli sono letti dal DB, mai da una
    costante nel codice."""
    if not livelli:
        return
    codici_categoria = {
        row.code
        for row in session.query(Categoria).filter_by(livello_selezionabile=True).all()
    }
    codici_livello = {row.code for row in session.query(LivelloFinitura).all()}
    for categoria_code, livello_code in livelli.items():
        if categoria_code not in codici_categoria:
            raise LivelliNonValidi(
                f"La categoria '{categoria_code}' non prevede un livello di finitura"
            )
        if livello_code not in codici_livello:
            raise LivelliNonValidi(f"Livello di finitura '{livello_code}' non valido")


class DettaglioProService:
    """Server-side calculation: (listino, mq, tipo, risposte) -> DettaglioProResult."""

    @staticmethod
    def compute(
        session: Session,
        listino: Listino,
        mq: int,
        tipo: str,
        risposte: dict[str, int],
        livelli: dict[str, str] | None = None,
    ) -> DettaglioProResult:
        """`livelli` ha un default proprio perche' tutte le chiamate esistenti
        (test compresi) restano valide senza modifiche: assente significa
        "applica il livello di default di tabella", non "prendi tutte le
        voci"."""
        tipo_row = session.query(TipoRistrutturazione).filter_by(code=tipo).one()
        range_pct = tipo_row.range_pct

        livelli_scelti = livelli or {}
        livelli_rows = session.query(LivelloFinitura).order_by(LivelloFinitura.ordine).all()
        livelli_nomi = {row.code: row.nome for row in livelli_rows}
        livello_default = next((row.code for row in livelli_rows if row.is_default), None)

        categorie_rows = session.query(Categoria).order_by(Categoria.ordine).all()

        categorie: list[CategoriaDettagliata] = []
        for cat in categorie_rows:
            # Livello RISOLTO per la categoria: la scelta dell'utente, altrimenti
            # il default di tabella. None dove la categoria non e' selezionabile
            # (A-EDILE) — e None anche se la tabella dei livelli e' vuota, caso
            # in cui `_voce_inclusa` lascia passare tutto (retrocompatibilita'
            # su un DB migrato ma non ri-seminato).
            livello_scelto = (
                (livelli_scelti.get(cat.code) or livello_default)
                if cat.livello_selezionabile
                else None
            )

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
                voce_rows_incluse = [
                    v
                    for v in voce_rows
                    if DettaglioProService._voce_inclusa(
                        v.livello, cat.livello_selezionabile, livello_scelto
                    )
                ]

                voci: list[VoceEstimata] = []
                for voce in voce_rows_incluse:
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
                            livello=voce.livello,
                        )
                    )

                # Sottocategoria svuotata DAL FILTRO -> scartata: un accordion
                # vuoto a 0 EUR e' rumore. Una sottocategoria gia' priva di voci
                # in partenza resta invece visibile com'era prima dei livelli.
                if voce_rows and not voci:
                    continue

                sotto_min = sum((v.prezzo_min for v in voci), Decimal("0"))
                sotto_max = sum((v.prezzo_max for v in voci), Decimal("0"))
                sottocategorie.append(
                    SottocategoriaEstimata(
                        codice=sotto.codice,
                        nome=sotto.nome,
                        famiglia=sotto.famiglia,
                        voci=voci,
                        totale_min=sotto_min,
                        totale_max=sotto_max,
                    )
                )

            # Categoria senza NESSUNA sottocategoria nel listino -> scartata,
            # per la stessa ragione della sottocategoria svuotata poco sopra:
            # una card a 0 EUR e' rumore. Il caso vivo e' `E-ARREDO`, che
            # esiste in tabella per il Free (forfait) e per le voci Pro che
            # arriveranno con l'import Excel: finche' quelle voci non ci sono,
            # la categoria non ha niente da mostrare nel dettaglio.
            if not sotto_rows:
                continue

            cat_min = sum((s.totale_min for s in sottocategorie), Decimal("0"))
            cat_max = sum((s.totale_max for s in sottocategorie), Decimal("0"))
            categorie.append(
                CategoriaDettagliata(
                    code=cat.code,
                    nome=cat.nome,
                    sottocategorie=sottocategorie,
                    totale_min=cat_min,
                    totale_max=cat_max,
                    livello_scelto=livello_scelto,
                    livello_scelto_nome=livelli_nomi.get(livello_scelto) if livello_scelto else None,
                )
            )

        totale_min = sum((c.totale_min for c in categorie), Decimal("0"))
        totale_max = sum((c.totale_max for c in categorie), Decimal("0"))
        return DettaglioProResult(
            categorie=categorie, totale_min=totale_min, totale_max=totale_max
        )

    @staticmethod
    def _voce_inclusa(
        voce_livello: str | None, livello_selezionabile: bool, livello_scelto: str | None
    ) -> bool:
        """Filtro di inclusione per livello di finitura. Puro: nessun accesso al
        DB, testabile isolatamente.

        Tre casi, in quest'ordine:
          1. categoria non selezionabile (A-EDILE) -> tutto incluso, il livello
             non la riguarda;
          2. nessun livello risolto (tabella `livello_finitura` vuota) -> tutto
             incluso, cioe' il comportamento precedente ai livelli;
          3. voce senza livello -> inclusa sempre (posa, materiali di consumo,
             montaggio: comuni a tutti i livelli);
          4. altrimenti la voce entra solo se e' del livello scelto.
        """
        if not livello_selezionabile:
            return True
        if livello_scelto is None:
            return True
        if voce_livello is None:
            return True
        return voce_livello == livello_scelto

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
