"""Dettaglio Pro: `Sottocategoria`/`Voce`/`CoefficienteQuantitaVoce`, appese a
`Listino` (D-03, predisposte multi-citta per Fase 4).

Le due forme strutturali del computo (03-RESEARCH.md Pitfall 1) sono
rappresentate da un unico schema: `codice` e' nullable sia su `Sottocategoria`
che su `Voce` (obbligatorio solo per A-EDILE, gerarchia a codici `A.n`/
`A.n.m`), e il discriminatore `famiglia` ('gerarchica' | 'catalogo') distingue
A-EDILE dai cataloghi piatti B-FINITURE/C-SERRAMENTI/D-PRODOTTI (raggruppati
per intestazione, senza sotto-codici).

IMPORTANTE (D-10, anti-leak esteso al Pro): NESSUNA colonna relativa al
margine/prezzo riservato all'impresa esiste su `Voce`. A differenza di
`ListinoCategoria` (che tiene quel margine sull'entita' ORM e si affida solo
alla disciplina dello schema di risposta per non serializzarlo), qui la
postura e' piu' forte: quel dato a livello di singola voce non viene
proprio persistito, quindi non puo' fuoriuscire nemmeno per un futuro
disallineamento schema-risposta.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Sottocategoria(Base):
    """Macro-raggruppamento di voci: sottocategoria a codice (A.1..A.12 per
    A-EDILE, famiglia='gerarchica') oppure gruppo-intestazione senza codice
    (B/C/D, famiglia='catalogo')."""

    __tablename__ = "sottocategoria"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    listino_id: Mapped[int] = mapped_column(ForeignKey("listino.id"), nullable=False)
    categoria_code: Mapped[str] = mapped_column(ForeignKey("categoria.code"), nullable=False)
    codice: Mapped[str | None] = mapped_column(String(16), nullable=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    famiglia: Mapped[str] = mapped_column(String(16), nullable=False)  # 'gerarchica' | 'catalogo'
    ordine: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")


class Voce(Base):
    """Riga di dettaglio: descrizione + UM + prezzo unitario CLIENTE.

    Nessun dato di margine/prezzo riservato all'impresa (D-10) — vedi
    docstring di modulo.
    """

    __tablename__ = "voce"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sottocategoria_id: Mapped[int] = mapped_column(ForeignKey("sottocategoria.id"), nullable=False)
    codice: Mapped[str | None] = mapped_column(String(16), nullable=True)
    descrizione: Mapped[str] = mapped_column(String(300), nullable=False)
    um: Mapped[str] = mapped_column(String(16), nullable=False)
    prezzo_unitario_cliente: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    ordine: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")


class CoefficienteQuantitaVoce(Base):
    """Coefficiente quantita-per-m2 (o domanda mirata) per voce, per tipo di
    ristrutturazione (D-04/D-05). Valori bozza, tarabili da admin in Fase 4.
    """

    __tablename__ = "coefficiente_qta_voce"
    __table_args__ = (UniqueConstraint("voce_id", "tipo_code", name="uq_coefficiente_qta_voce_tipo"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    voce_id: Mapped[int] = mapped_column(ForeignKey("voce.id"), nullable=False)
    tipo_code: Mapped[str] = mapped_column(ForeignKey("tipo_ristrutturazione.code"), nullable=False)
    coefficiente_qta_per_mq: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    domanda_mirata_key: Mapped[str | None] = mapped_column(String(32), nullable=True)
    default_conteggio: Mapped[int | None] = mapped_column(nullable=True)
