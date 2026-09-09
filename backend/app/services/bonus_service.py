"""BonusService: da una stima Free a quanto se ne recupera in detrazione.

E' il dato che trasforma un totale in una decisione — "costa 50.000" e "costa
50.000, ne recuperi 25.000 in dieci anni" sono due conversazioni diverse.

SI CALCOLA SUI TOTALI LORDI DEL MOTORE FREE, non su quelli Pro. La detrazione
si applica alla spesa effettivamente sostenuta, cioe' IVA inclusa; il motore
Pro non modella l'IVA (nessun `iva_pct` in `services/dettaglio_pro.py`), quindi
usare i suoi numeri sottostimerebbe la detrazione del 10-22%. Ogni riga `stima`
ha sempre uno snapshot Free in `risultato_json`: anche la vista Pro legge i
bonus da li'. Aggiungere l'IVA al motore Pro e' una modifica invasiva,
deliberatamente rinviata.

ZERO COSTANTI FISCALI IN QUESTO FILE. Aliquote, tetti, durate e finestre di
validita' vivono in `models/bonus.py` e sono modificabili da admin: e' cio' che
permette al calo di aliquota del 2027 di avvenire senza un deploy.

Disciplina numerica identica a `estimation.py`: tutto in `Decimal`, `_eur()`
con ROUND_HALF_UP solo sui campi di output, dataclass frozen a campi chiusi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable, Protocol

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.bonus import AliquotaBonus, BonusCategoria, BonusExtra, BonusFiscale

DESTINAZIONI = ("prima_casa", "altro")


def _eur(value: Decimal) -> Decimal:
    """Quantize to whole euro (ROUND_HALF_UP) — used only on output fields."""
    return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


class CategoriaConTotale(Protocol):
    """Cio' che al servizio serve davvero di una categoria: il codice e i due
    totali LORDI. Un Protocol e non un import concreto, cosi' il servizio
    accetta sia le dataclass del motore sia i DTO del router senza legarsi a
    nessuno dei due."""

    code: str
    totale_min: Decimal
    totale_max: Decimal


class ExtraConTotale(Protocol):
    """Un extra ha un solo totale lordo, non un range: e' un importo fisso
    (`ExtraEstimato.totale` = importo * (1 + iva_pct)), quindi entra identico
    nella base minima e in quella massima. Non e' una semplificazione: e'
    esattamente cio' che il motore Free calcola."""

    code: str
    totale: Decimal


@dataclass(frozen=True)
class BonusDettaglio:
    code: str
    nome: str
    descrizione: str | None
    # Spesa ammissibile, gia' cappata al tetto se previsto.
    base_min: Decimal
    base_max: Decimal
    aliquota_pct: Decimal
    tetto_spesa_eur: Decimal | None
    tetto_modalita: str | None
    tetto_raggiunto: bool
    rate_annuali: int
    detrazione_min: Decimal
    detrazione_max: Decimal
    rata_annua_min: Decimal
    rata_annua_max: Decimal


@dataclass(frozen=True)
class BonusResult:
    bonus: list[BonusDettaglio] = field(default_factory=list)
    detrazione_min: Decimal = Decimal("0")
    detrazione_max: Decimal = Decimal("0")
    rata_annua_min: Decimal = Decimal("0")
    rata_annua_max: Decimal = Decimal("0")
    disclaimer: str = ""


class BonusService:
    """Server-side: (categorie della stima Free, destinazione, data) -> BonusResult."""

    @staticmethod
    def compute(
        session: Session,
        categorie: Iterable[CategoriaConTotale],
        destinazione: str,
        disclaimer: str = "",
        data_riferimento: date | None = None,
        extra: Iterable[ExtraConTotale] | None = None,
    ) -> BonusResult | None:
        """Ritorna `None` quando non c'e' nulla da mostrare (nessun bonus
        attivo, nessuna aliquota valida, base a zero): la sezione bonus sparisce
        dalla risposta invece di comparire a zero, e nessun caso limite diventa
        un errore. Un bonus senza aliquota valida alla data viene ESCLUSO, non
        calcolato a 0 — dire "recuperi 0 EUR" e' peggio che non dire nulla.

        GLI EXTRA FANNO PARTE DELLA BASE. CSE/CSP e pratiche amministrative
        sono prestazioni tecniche connesse all'intervento, quindi detraibili:
        ometterli sottostima la detrazione di ~2.800 EUR su una stima da 85 m2,
        e in silenzio. Quali extra entrino e con quale bonus lo dice la tabella
        `bonus_extra`, mai una regola cablata qui. `extra=None` resta valido e
        vuol dire "nessun extra da considerare", non "usa un default".
        """
        oggi = data_riferimento or date.today()
        if destinazione not in DESTINAZIONI:
            destinazione = "prima_casa"

        totali_per_categoria = {
            cat.code: (cat.totale_min, cat.totale_max) for cat in categorie
        }
        totali_per_extra = {ex.code: ex.totale for ex in (extra or ())}

        bonus_rows = (
            session.execute(
                select(BonusFiscale)
                .where(BonusFiscale.attivo.is_(True))
                .order_by(BonusFiscale.ordine, BonusFiscale.code)
            )
            .scalars()
            .all()
        )

        dettagli: list[BonusDettaglio] = []
        for bonus in bonus_rows:
            aliquota = BonusService._aliquota_valida(session, bonus.code, destinazione, oggi)
            if aliquota is None:
                continue

            base_min, base_max = BonusService._base_imponibile(
                session, bonus.code, totali_per_categoria, totali_per_extra
            )
            if base_max <= 0:
                continue

            # Il tetto si applica PRIMA dell'aliquota, separatamente a min e max:
            # se il massimo sfora e il minimo no, il range della detrazione si
            # comprime. Non e' un artefatto, e' la realta' — oltre il tetto la
            # spesa in piu' non produce detrazione.
            tetto = aliquota.tetto_spesa_eur
            tetto_raggiunto = tetto is not None and base_max > tetto
            if tetto is not None:
                base_min = min(base_min, tetto)
                base_max = min(base_max, tetto)

            detrazione_min = _eur(base_min * aliquota.aliquota_pct)
            detrazione_max = _eur(base_max * aliquota.aliquota_pct)
            rate = aliquota.rate_annuali or 1

            dettagli.append(
                BonusDettaglio(
                    code=bonus.code,
                    nome=bonus.nome,
                    descrizione=bonus.descrizione,
                    base_min=_eur(base_min),
                    base_max=_eur(base_max),
                    aliquota_pct=aliquota.aliquota_pct,
                    tetto_spesa_eur=tetto,
                    tetto_modalita=aliquota.tetto_modalita,
                    tetto_raggiunto=tetto_raggiunto,
                    rate_annuali=rate,
                    detrazione_min=detrazione_min,
                    detrazione_max=detrazione_max,
                    rata_annua_min=_eur(detrazione_min / rate),
                    rata_annua_max=_eur(detrazione_max / rate),
                )
            )

        if not dettagli:
            return None

        return BonusResult(
            bonus=dettagli,
            detrazione_min=sum((d.detrazione_min for d in dettagli), Decimal("0")),
            detrazione_max=sum((d.detrazione_max for d in dettagli), Decimal("0")),
            rata_annua_min=sum((d.rata_annua_min for d in dettagli), Decimal("0")),
            rata_annua_max=sum((d.rata_annua_max for d in dettagli), Decimal("0")),
            disclaimer=disclaimer,
        )

    @staticmethod
    def _aliquota_valida(
        session: Session, bonus_code: str, destinazione: str, oggi: date
    ) -> AliquotaBonus | None:
        """La riga valida ALLA DATA. Se ce ne fossero due sovrapposte per errore
        di curatela, vince la piu' recente per `valido_dal`: e' la scelta meno
        sorprendente, e la sovrapposizione resta un problema di dati da
        correggere, non un'eccezione a runtime."""
        stmt = (
            select(AliquotaBonus)
            .where(
                AliquotaBonus.bonus_code == bonus_code,
                AliquotaBonus.destinazione == destinazione,
                AliquotaBonus.valido_dal <= oggi,
                or_(AliquotaBonus.valido_al.is_(None), AliquotaBonus.valido_al >= oggi),
            )
            .order_by(AliquotaBonus.valido_dal.desc())
        )
        return session.execute(stmt).scalars().first()

    @staticmethod
    def _base_imponibile(
        session: Session,
        bonus_code: str,
        totali_per_categoria: dict[str, tuple[Decimal, Decimal]],
        totali_per_extra: dict[str, Decimal],
    ) -> tuple[Decimal, Decimal]:
        """Somma dei totali LORDI mappati su questo bonus — categorie ed extra,
        ciascuno per la sua quota ammissibile.

        Un extra assente dai totali passati viene saltato come una categoria
        assente: la mappatura puo' riferirsi a un extra disattivato, e cio' non
        deve produrre ne' un errore ne' una base gonfiata."""
        mappature = (
            session.execute(select(BonusCategoria).where(BonusCategoria.bonus_code == bonus_code))
            .scalars()
            .all()
        )
        base_min = Decimal("0")
        base_max = Decimal("0")
        for mappa in mappature:
            totali = totali_per_categoria.get(mappa.categoria_code)
            if totali is None:
                continue
            quota = mappa.quota_ammissibile_pct
            base_min += totali[0] * quota
            base_max += totali[1] * quota

        mappature_extra = (
            session.execute(select(BonusExtra).where(BonusExtra.bonus_code == bonus_code))
            .scalars()
            .all()
        )
        for mappa in mappature_extra:
            totale = totali_per_extra.get(mappa.extra_code)
            if totale is None:
                continue
            # Importo fisso: stessa quota su entrambi gli estremi del range.
            contributo = totale * mappa.quota_ammissibile_pct
            base_min += contributo
            base_max += contributo
        return base_min, base_max

    @staticmethod
    def quote_per_categoria(session: Session, escludi_id: int | None = None) -> dict[str, Decimal]:
        """Somma delle quote ammissibili per categoria, sui soli bonus ATTIVI.

        Serve al vincolo anti-doppio-conteggio: se una categoria supera 1, la
        stessa spesa verrebbe detratta due volte e il totale delle detrazioni
        sarebbe una promessa falsa. `escludi_id` permette di valutare l'effetto
        di una modifica prima di applicarla (l'admin sta riscrivendo QUELLA
        riga, quindi la vecchia non va contata)."""
        stmt = (
            select(BonusCategoria, BonusFiscale)
            .join(BonusFiscale, BonusFiscale.code == BonusCategoria.bonus_code)
            .where(BonusFiscale.attivo.is_(True))
        )
        totali: dict[str, Decimal] = {}
        for mappa, _bonus in session.execute(stmt).all():
            if escludi_id is not None and mappa.id == escludi_id:
                continue
            totali[mappa.categoria_code] = (
                totali.get(mappa.categoria_code, Decimal("0")) + mappa.quota_ammissibile_pct
            )
        return totali


    @staticmethod
    def quote_per_extra(session: Session, escludi_id: int | None = None) -> dict[str, Decimal]:
        """Somma delle quote ammissibili per extra, sui soli bonus ATTIVI.

        Gemella di `quote_per_categoria` e serve lo stesso vincolo: un extra
        mappato su due bonus per un totale oltre 1 verrebbe detratto due volte.
        Due funzioni invece di una parametrica perche' le due tabelle non
        condividono la colonna su cui si raggruppa, e fonderle costerebbe piu'
        indirezione di quanta ne risparmi."""
        stmt = (
            select(BonusExtra, BonusFiscale)
            .join(BonusFiscale, BonusFiscale.code == BonusExtra.bonus_code)
            .where(BonusFiscale.attivo.is_(True))
        )
        totali: dict[str, Decimal] = {}
        for mappa, _bonus in session.execute(stmt).all():
            if escludi_id is not None and mappa.id == escludi_id:
                continue
            totali[mappa.extra_code] = (
                totali.get(mappa.extra_code, Decimal("0")) + mappa.quota_ammissibile_pct
            )
        return totali
