"""`Lead`: independent immutable snapshot of a contact request (LEAD-01/02/03).

Mirrors `models/stima_salvata.py::StimaSalvata`'s freeze-at-write-time shape
(04-RESEARCH.md Pattern 2): `citta`/`mq`/`tipo`/`totale_min`/`totale_max` are
scalar columns copied by value at submit time — the record is readable and
defensible even if the user later deletes the underlying `StimaSalvata` row
(D-03). `stima_salvata_id` is an OPTIONAL nullable trace-back FK only, never
required to render the lead.

NO `coefficiente_impresa`/`base_eur_mq`/margin-shaped column exists on this
model (D-22, absolute anti-leak) — this is enforced structurally, not by a
response-schema fork alone.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Lead(Base):
    __tablename__ = "lead"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False, index=True)
    stima_salvata_id: Mapped[int | None] = mapped_column(ForeignKey("stima.id"), nullable=True)

    # Dati di contatto (D-02)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    preferenza_contatto: Mapped[str] = mapped_column(String(16), nullable=False)  # "email" | "telefono"
    fascia_oraria: Mapped[str | None] = mapped_column(String(32), nullable=True)
    messaggio: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    # Snapshot indipendente (D-03) — mai coefficiente/prezzo impresa (D-22).
    citta: Mapped[str] = mapped_column(String(200), nullable=False)
    mq: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    totale_min: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    totale_max: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    referente_id: Mapped[int | None] = mapped_column(ForeignKey("referente.id"), nullable=True)
    email_inviata: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")  # D-07
    stato: Mapped[str] = mapped_column(String(16), nullable=False, default="nuovo", server_default="nuovo")  # D-17
    nota: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
