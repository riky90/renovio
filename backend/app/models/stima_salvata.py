"""`StimaSalvata`: hybrid immutable snapshot of a Free estimate.

Scalar columns (`citta`/`mq`/`tipo`/`totale_min`/`totale_max`/`fallback`)
make the per-user history list a cheap query with no JSON parsing per row
(02-RESEARCH.md Pattern 3). `risultato_json` (generic `sqlalchemy.JSON`, NOT
`JSONB` — portable to SQLite dev, 02-RESEARCH.md Environment Availability)
holds the full frozen payload — identical in shape to `StimaResponse`
(schemas/stima.py) plus `schema_version` — used verbatim by the detail
endpoint and, later, the PDF (Plan 08). This row is written ONCE at save
time and NEVER recomputed (D-09, Pitfall 5) — no `EstimationService` call
anywhere near this model.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class StimaSalvata(Base):
    __tablename__ = "stima"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False, index=True)

    # Colonne scalari congelate — storico economico, no JSON parsing per riga.
    citta: Mapped[str] = mapped_column(String(200), nullable=False)
    mq: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    totale_min: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    totale_max: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    fallback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")

    # Snapshot completo congelato — stessa forma di StimaResponse + schema_version.
    # JSON generico (non JSONB): portabile SQLite dev / Postgres prod.
    risultato_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
