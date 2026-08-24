"""Listino entities. `coefficiente_impresa` is the internal margin secret:
mapped on the ORM entity only, NEVER referenced by any Pydantic response
schema (see 01-RESEARCH.md Pattern 1 - response schema as anti-leak gate).
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Listino(Base):
    __tablename__ = "listino"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    citta_riferimento: Mapped[str] = mapped_column(String(200), nullable=False)
    valuta: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR", server_default="EUR")
    is_default: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="0")
    attivo: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())


class ListinoCategoria(Base):
    """€/m² base (prezzo CLIENTE) + margine impresa, per (listino, categoria)."""

    __tablename__ = "listino_categoria"
    __table_args__ = (UniqueConstraint("listino_id", "categoria_code", name="uq_listino_categoria"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    listino_id: Mapped[int] = mapped_column(ForeignKey("listino.id"), nullable=False)
    categoria_code: Mapped[str] = mapped_column(ForeignKey("categoria.code"), nullable=False)
    base_eur_mq: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    # SEGRETO: margine interno (0.65/0.6/0.55/0.5). Mai serializzato in nessuna risposta.
    coefficiente_impresa: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
