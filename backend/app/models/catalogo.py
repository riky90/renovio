"""Reference/catalog entities: categoria, tipo_ristrutturazione, moltiplicatore,
extra, comune_listino, referente.

See 01-RESEARCH.md "Data Model (prescrittivo)" - implemented verbatim.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Categoria(Base):
    """Le 4 categorie fisse: A-EDILE, B-FINITURE, C-SERRAMENTI, D-PRODOTTI."""

    __tablename__ = "categoria"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    ordine: Mapped[int] = mapped_column(nullable=False)
    iva_pct: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)

    # Il livello di finitura si sceglie solo dove dipende dal GUSTO del cliente
    # (B-FINITURE / C-SERRAMENTI / D-PRODOTTI), non dove dipende dal tipo di
    # ristrutturazione (A-EDILE). E' un DATO in tabella e non un `if` sul codice
    # categoria (ENG-02): un domani una categoria nuova entra o esce dal
    # meccanismo dal pannello admin, senza deploy.
    livello_selezionabile: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )

    # Se questa categoria entra nel TOTALE LAVORI. `false` solo per l'arredo,
    # che non e' una lavorazione: viaggia accanto al totale, mai dentro, cosi'
    # la riconciliazione `Sigma categorie + extra = totale` resta vera e il
    # numero resta confrontabile con un preventivo edile.
    #
    # E' un DATO e non un `if` sul codice categoria, per la stessa ragione di
    # `livello_selezionabile`: un domani una categoria nuova entra o esce dal
    # totale dal pannello admin, senza deploy e senza migrazione (ENG-02).
    nel_totale_lavori: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )

    # D-11: data dell'ultima modifica, aggiornata da sola a ogni scrittura ORM
    # (onupdate) — dice se questa riga e' cambiata dopo che un export e' stato
    # scaricato, per la guardia di staleness dell'import.
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )


class LivelloFinitura(Base):
    """I livelli di finitura selezionabili: base / medio / alto.

    Gemello strutturale di `TipoRistrutturazione` (lookup a `code` PK, con
    `ordine` e `nome` visualizzabili). Tabella e non enum Python per due
    ragioni: serve un default lato server (`is_default`, applicato quando il
    client non manda nulla) e la regola ENG-02 vuole questi dati in DB,
    modificabili da admin.

    Il livello e' cio' che sceglie UNA voce per famiglia nei cataloghi
    `famiglia='catalogo'`: gres, parquet e porte sono ALTERNATIVE per la stessa
    stanza, non addendi. Vedi `services/dettaglio_pro.py`.
    """

    __tablename__ = "livello_finitura"

    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    ordine: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    descrizione: Mapped[str | None] = mapped_column(String(300), nullable=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )


class TipoRistrutturazione(Base):
    """I 3 tipi: leggera, moderata, totale."""

    __tablename__ = "tipo_ristrutturazione"
    #: Niente RETURNING del `server_default` di `range_pct_sotto` all'INSERT:
    #: su un DB prima della 0031 la colonna non c'e' (vedi sotto).
    __mapper_args__ = {"eager_defaults": False}

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    ordine: Mapped[int] = mapped_column(nullable=False)
    #: Ampiezza del range SOPRA il valore stimato (max = valore x (1 + range_pct)).
    range_pct: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    #: Ampiezza SOTTO (min = valore x (1 - range_pct_sotto)). NULL = simmetrico,
    #: cioe' uguale a `range_pct`. Il range e' asimmetrico dal 2026-10-30: la
    #: taratura sui computi reali (TAR-01) mostra che i lavori a corpo non
    #: chiesti spostano il reale verso l'alto, mai verso il basso.
    #: `deferred` e `server_default`: le query sul tipo non la leggono finche'
    #: non serve e un INSERT che non la imposta non la nomina, cosi' il seed gira
    #: anche su un DB fermo prima della 0031 (test delle migrazioni).
    range_pct_sotto: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 3), nullable=True, deferred=True, server_default=text("NULL")
    )

    @property
    def range_sotto(self) -> Decimal:
        return self.range_pct if self.range_pct_sotto is None else self.range_pct_sotto


class Moltiplicatore(Base):
    """Moltiplicatore per (tipo, categoria) - 12 righe in v1, globale."""

    __tablename__ = "moltiplicatore"
    __table_args__ = (UniqueConstraint("tipo_code", "categoria_code", name="uq_moltiplicatore_tipo_categoria"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tipo_code: Mapped[str] = mapped_column(ForeignKey("tipo_ristrutturazione.code"), nullable=False)
    categoria_code: Mapped[str] = mapped_column(ForeignKey("categoria.code"), nullable=False)
    valore: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)

    # D-11: vedi Categoria.updated_at.
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Extra(Base):
    """Extra fissi (CSE/CSP, pratiche amministrative), sempre inclusi nel totale."""

    __tablename__ = "extra"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    importo: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    iva_pct: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    tipo_calcolo: Mapped[str] = mapped_column(String(32), nullable=False, default="fisso", server_default="fisso")
    attivo: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="1")

    # D-11: vedi Categoria.updated_at.
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ComuneListino(Base):
    """Mappa città -> listino. Città non presente -> fallback su listino.is_default."""

    __tablename__ = "comune_listino"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    comune_nome: Mapped[str] = mapped_column(String(200), nullable=False)
    comune_slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    codice_istat: Mapped[str | None] = mapped_column(String(20), nullable=True)
    listino_id: Mapped[int] = mapped_column(ForeignKey("listino.id"), nullable=False)


class Referente(Base):
    """Multi-referente per listino/città. Schema pronto dal giorno 1; nessun
    endpoint in Fase 1 (predisposizione per Fase 4)."""

    __tablename__ = "referente"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    listino_id: Mapped[int] = mapped_column(ForeignKey("listino.id"), nullable=False)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    attivo: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="1")
    priorita: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
