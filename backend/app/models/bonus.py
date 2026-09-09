"""Bonus fiscali: `BonusFiscale`, `AliquotaBonus`, `BonusCategoria`.

Tre tabelle e ZERO costanti fiscali nel codice Python (ENG-02, regola 3 del
CLAUDE.md). La ragione qui e' piu' forte che altrove: le aliquote dei bonus
edilizi CAMBIANO PER LEGGE a data certa — il 50%/36% del 2026 scende dal 2027 —
e il passaggio d'anno non puo' dipendere da un deploy. La validita' temporale
e' quindi modellata come colonne (`valido_dal`/`valido_al`) su piu' righe della
stessa coppia (bonus, destinazione): il servizio sceglie la riga valida alla
data di riferimento, e la riga 2027 e' gia' seminata oggi.

Materia fiscale: quello che l'app produce e' una STIMA COMMERCIALE, non
consulenza. Il disclaimer viaggia dentro la risposta (vedi
`services/bonus_service.py`), non nella UI, cosi' non e' rimovibile lato client
e finisce anche nello snapshot congelato e nel PDF.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class BonusFiscale(Base):
    """Un bonus edilizio (Ristrutturazione, Ecobonus, Mobili, Sismabonus).

    `attivo` permette di seminare un bonus SENZA esporlo: Mobili e Sismabonus
    esistono in tabella ma sono spenti, perche' richiedono un input che il form
    non raccoglie (spesa mobili dedicata, classe di rischio sismico). Seminarli
    spenti e' meglio che ometterli: il giorno che l'input esiste, si accende una
    riga invece di scrivere una migrazione.
    """

    __tablename__ = "bonus_fiscale"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    descrizione: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ordine: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    attivo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")


class AliquotaBonus(Base):
    """Aliquota, tetto e durata di un bonus, per destinazione e per periodo.

    Piu' righe per la stessa (bonus, destinazione) con finestre temporali
    diverse: e' cosi' che il calo delle aliquote diventa un DATO. Il servizio
    seleziona la riga con `valido_dal <= data <= valido_al` (o `valido_al`
    nullo, cioe' aperta).

    `tetto_modalita` documenta a cosa si riferisce il tetto ('per_unita_
    immobiliare' per il bonus ristrutturazione, 'per_intervento' per i
    massimali dell'ecobonus). In v1 il calcolo e' lo stesso — si cappa la base
    imponibile — ma il campo evita che la distinzione si perda, ed e' cio' che
    va mostrato all'utente accanto all'importo.
    """

    __tablename__ = "aliquota_bonus"
    __table_args__ = (
        UniqueConstraint(
            "bonus_code", "destinazione", "valido_dal", name="uq_aliquota_bonus_periodo"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bonus_code: Mapped[str] = mapped_column(ForeignKey("bonus_fiscale.code"), nullable=False)
    # 'prima_casa' (abitazione principale) | 'altro' (secondi immobili).
    destinazione: Mapped[str] = mapped_column(String(32), nullable=False)
    aliquota_pct: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    # NULL = nessun tetto di spesa.
    tetto_spesa_eur: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    tetto_modalita: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rate_annuali: Mapped[int] = mapped_column(nullable=False, default=10, server_default="10")
    valido_dal: Mapped[date] = mapped_column(Date, nullable=False)
    valido_al: Mapped[date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)


class BonusCategoria(Base):
    """Quale categoria di spesa alimenta quale bonus, e per quale quota.

    `quota_ammissibile_pct` esiste per il caso in cui solo una parte della
    spesa di categoria sia detraibile con quel bonus (default 1.0 = tutta).

    REGOLA ANTI-DOPPIO-CONTEGGIO: per ogni categoria, la somma delle quote sui
    bonus ATTIVI deve stare entro 1. Senza questo vincolo la stessa spesa
    verrebbe detratta due volte e il totale delle detrazioni sarebbe una
    promessa falsa. Verificata da un test e da un 409 nell'endpoint admin.
    """

    __tablename__ = "bonus_categoria"
    __table_args__ = (
        UniqueConstraint("bonus_code", "categoria_code", name="uq_bonus_categoria"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bonus_code: Mapped[str] = mapped_column(ForeignKey("bonus_fiscale.code"), nullable=False)
    categoria_code: Mapped[str] = mapped_column(ForeignKey("categoria.code"), nullable=False)
    quota_ammissibile_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("1"), server_default="1"
    )


class BonusExtra(Base):
    """Quale voce di EXTRA alimenta quale bonus, e per quale quota.

    Gemella di `BonusCategoria`, e serve per la stessa ragione per cui esiste
    quella: gli extra (CSE/CSP, pratiche amministrative) SONO spese detraibili
    — sono prestazioni tecniche connesse all'intervento — ma non sono
    categorie, quindi `bonus_categoria` non li vede. Senza questa tabella la
    detrazione esce sottostimata di tutto l'importo degli extra (~2.800 EUR su
    una stima da 85 m2), e la sottostima e' silenziosa: nessun errore, solo un
    numero piu' basso del vero.

    Tabella separata invece di una quota di default cablata sul bonus
    ristrutturazione: quale extra sia detraibile e con che bonus e' curatela
    fiscale, non una costante (regola 3 del CLAUDE.md). Un extra futuro non
    detraibile si gestisce non mappandolo, senza toccare il codice.

    Stessa REGOLA ANTI-DOPPIO-CONTEGGIO di `BonusCategoria`: per ogni extra la
    somma delle quote sui bonus ATTIVI deve stare entro 1.
    """

    __tablename__ = "bonus_extra"
    __table_args__ = (UniqueConstraint("bonus_code", "extra_code", name="uq_bonus_extra"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bonus_code: Mapped[str] = mapped_column(ForeignKey("bonus_fiscale.code"), nullable=False)
    extra_code: Mapped[str] = mapped_column(ForeignKey("extra.code"), nullable=False)
    quota_ammissibile_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("1"), server_default="1"
    )
