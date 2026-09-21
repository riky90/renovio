"""Reference/catalog entities: categoria, tipo_ristrutturazione, moltiplicatore,
extra, comune_listino, referente.

See 01-RESEARCH.md "Data Model (prescrittivo)" - implemented verbatim.
"""

from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String, UniqueConstraint
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

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    ordine: Mapped[int] = mapped_column(nullable=False)
    range_pct: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)


class Moltiplicatore(Base):
    """Moltiplicatore per (tipo, categoria) - 12 righe in v1, globale."""

    __tablename__ = "moltiplicatore"
    __table_args__ = (UniqueConstraint("tipo_code", "categoria_code", name="uq_moltiplicatore_tipo_categoria"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tipo_code: Mapped[str] = mapped_column(ForeignKey("tipo_ristrutturazione.code"), nullable=False)
    categoria_code: Mapped[str] = mapped_column(ForeignKey("categoria.code"), nullable=False)
    valore: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)


class Extra(Base):
    """Extra fissi (CSE/CSP, pratiche amministrative), sempre inclusi nel totale."""

    __tablename__ = "extra"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    importo: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    iva_pct: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    tipo_calcolo: Mapped[str] = mapped_column(String(32), nullable=False, default="fisso", server_default="fisso")
    attivo: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="1")


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
