"""Computo parametrico (Fase 11): grandezze della casa, regole di quantita'
per voce, preset per tipo di ristrutturazione.

Traduce in dati il ragionamento che nel computo Excel vive nelle colonne T/U
("collegamento") e nelle note H: la quantita' di una voce dipende da un dato
della casa (n. bagni, m2 di pareti), da una scelta d'intervento (cucina si'/no,
canalizzato) o da altre voci (l'intonaco dalle nuove murature, lo smaltimento
dalle demolizioni). Vedi `docs/proposta-computo-parametrico.md`.

Stesso principio di `tipo_effetto` (v2.0): i TIPI di regola e la forma di una
grandezza sono un vocabolario CHIUSO noto al motore (`services/computo.py`),
mai espressioni libere in tabella. In tabella stanno solo i numeri e i
collegamenti.

Tutto e' legato al CODICE della voce, non al suo id: le regole valgono per ogni
listino che usa quei codici, e un secondo listino porta solo prezzi.

Nessuna di queste tabelle porta il coefficiente impresa (regola non
negoziabile #1): sono quantita', fattori e flag.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Grandezza(Base):
    """Una misura della casa o un flag d'intervento (m2 di pareti, bagni
    rifatti, cucina si'/no).

    Il valore si risolve in quest'ordine (contratto in `services/computo.py`):
      1. la risposta numerica della domanda con `attributo_code` = `code`;
      2. se una domanda VISIBILE assegna questa grandezza con le sue opzioni
         (`ValoreGrandezzaOpzione`), la somma dei valori delle opzioni scelte
         (0 se nessuna scelta la assegna);
      3. il default: `costante` + somma dei `TermineGrandezza`, oppure, se
         `da_attesa` e c'e' una riga di `attesa_immobile` per i m2, quel valore.
    Poi si applicano `arrotondamento` e i limiti `minimo`/`massimo`.
    """

    __tablename__ = "grandezza"

    code: Mapped[str] = mapped_column(String(48), primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    um: Mapped[str] = mapped_column(String(16), nullable=False, default="", server_default="")
    descrizione: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ordine: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")

    costante: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, default=Decimal("0"), server_default="0"
    )
    # Il default viene dalla fascia di `attesa_immobile` con lo stesso codice
    # (bagni, porte, finestre...): una sola fonte per default del wizard,
    # baseline e computo.
    da_attesa: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    # nessuno | su | giu | vicino
    arrotondamento: Mapped[str] = mapped_column(
        String(8), nullable=False, default="nessuno", server_default="nessuno"
    )
    minimo: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    massimo: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)

    attiva: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )


class TermineGrandezza(Base):
    """Un addendo del default di una grandezza:
    `fattore x valore(sorgente) [x valore(per_grandezza)]`.

    `sorgente_code` e' `mq`, `tipo_<code>` (1 se la ristrutturazione e' di quel
    tipo, altrimenti 0) o il codice di un'altra grandezza. Il prodotto opzionale
    con `per_grandezza_code` e' cio' che permette "bagni rifatti = bagni x
    tipo_totale" senza formule libere.
    """

    __tablename__ = "termine_grandezza"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    grandezza_code: Mapped[str] = mapped_column(
        ForeignKey("grandezza.code", ondelete="CASCADE"), nullable=False
    )
    sorgente_code: Mapped[str] = mapped_column(String(48), nullable=False)
    fattore: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    per_grandezza_code: Mapped[str | None] = mapped_column(String(48), nullable=True)
    ordine: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")

    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ValoreGrandezzaOpzione(Base):
    """Un'opzione di una domanda a scelta assegna un valore a una grandezza
    ("cucina: si'" -> cucina = 1; "clima: canalizzato" -> clima_canalizzato = 1).

    E' il ponte fra interventi e quantita': le condizioni delle regole sono
    grandezze > 0, quindi una scelta accende o spegne voci senza un tipo di
    effetto in piu'.
    """

    __tablename__ = "valore_grandezza_opzione"
    __table_args__ = (
        UniqueConstraint("opzione_id", "grandezza_code", name="uq_valore_grandezza_opzione"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    opzione_id: Mapped[int] = mapped_column(
        ForeignKey("opzione_domanda.id", ondelete="CASCADE"), nullable=False
    )
    grandezza_code: Mapped[str] = mapped_column(
        ForeignKey("grandezza.code", ondelete="CASCADE"), nullable=False
    )
    valore: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )


class RegolaVoce(Base):
    """La regola di quantita' di una voce, per codice.

    `tipo_regola` (vocabolario chiuso, vedi `services/computo.py`):
      fisso                      q = fattore
      grandezza                  q = fattore x grandezza
      da_voci                    q = fattore x somma delle quantita' delle sorgenti
      percentuale                importo = fattore x somma degli importi delle sorgenti
      percentuale_per_grandezza  importo = fattore x somma importi x grandezza
      scaglioni                  q = valore del primo scaglione con grandezza <= fino_a

    `condizione_grandezza_code`: la voce entra solo se quella grandezza e' > 0.
    `importo_minimo`: "a corpo" — se l'importo e' positivo ma sotto la soglia,
    vale la soglia (es. impermeabilizzazione "a corpo 200 euro se pochi metri").
    """

    __tablename__ = "regola_voce"

    voce_codice: Mapped[str] = mapped_column(String(32), primary_key=True)
    tipo_regola: Mapped[str] = mapped_column(String(32), nullable=False)
    grandezza_code: Mapped[str | None] = mapped_column(String(48), nullable=True)
    fattore: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, default=Decimal("1"), server_default="1"
    )
    condizione_grandezza_code: Mapped[str | None] = mapped_column(String(48), nullable=True)
    importo_minimo: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    nota: Mapped[str | None] = mapped_column(String(500), nullable=True)

    attiva: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )


class SorgenteRegola(Base):
    """Le voci da cui dipende una regola `da_voci` / `percentuale*`.

    `sorgente_codice` e' il codice di una voce oppure di una sottocategoria
    (es. `A.1`: tutte le voci delle demolizioni).
    """

    __tablename__ = "sorgente_regola"
    __table_args__ = (
        UniqueConstraint("voce_codice", "sorgente_codice", name="uq_sorgente_regola"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    voce_codice: Mapped[str] = mapped_column(
        ForeignKey("regola_voce.voce_codice", ondelete="CASCADE"), nullable=False
    )
    sorgente_codice: Mapped[str] = mapped_column(String(32), nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ScaglioneRegola(Base):
    """Uno scaglione di una regola `scaglioni`: se la grandezza e' <= `fino_a`
    la quantita' e' `valore`. `fino_a` nullo = "oltre" (ultimo scaglione).

    La quantita' moltiplica il prezzo di listino: lo scaglione resta valido per
    ogni citta' (es. quadro elettrico: 0,83 / 1,2 / 1,33 / 1,36 del prezzo base).
    """

    __tablename__ = "scaglione_regola"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    voce_codice: Mapped[str] = mapped_column(
        ForeignKey("regola_voce.voce_codice", ondelete="CASCADE"), nullable=False
    )
    fino_a: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    valore: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )


class PresetRisposta(Base):
    """Il tipo di ristrutturazione come PRESET: la risposta di default di una
    domanda per quel tipo. Sostituisce `opzione.is_default` quando c'e'.

    Per le domande a scelta si indica `opzione_code` (piu' righe per una scelta
    multipla); per le numeriche `valore`.
    """

    __tablename__ = "preset_risposta"
    __table_args__ = (
        UniqueConstraint(
            "tipo_code", "domanda_code", "opzione_code", name="uq_preset_risposta"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tipo_code: Mapped[str] = mapped_column(
        ForeignKey("tipo_ristrutturazione.code"), nullable=False
    )
    domanda_code: Mapped[str] = mapped_column(
        ForeignKey("domanda.code", ondelete="CASCADE"), nullable=False
    )
    opzione_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    valore: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )
