"""Testo entity: key/value table for backend-owned editable strings (D-14).

Migrates the previously hardcoded `DISCLAIMER_TEMPLATE` (EST-06, "città
senza listino proprio") off Python source into a DB row the admin can edit
via `/admin/testi`. Scope v1 (04-RESEARCH.md Open Question 1): ONLY
backend-owned strings rendered server-side (disclaimer, email subjects) —
NOT frontend copy, NOT full HTML email bodies.

Deliberately unrelated to the referente fallback (D-05, silent — Pitfall
5): there is no `Testo` row for "nessun referente disponibile", and there
must never be one.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Testo(Base):
    """Flat key/value table. `chiave` is the natural primary key (stable,
    upsert-friendly — same pattern as `Extra`/`ComuneListino`)."""

    __tablename__ = "testo"

    chiave: Mapped[str] = mapped_column(String(100), primary_key=True)
    valore: Mapped[str] = mapped_column(Text, nullable=False)
    # No `onupdate=func.now()` (not portable SQLite/Postgres, plan note): the
    # application layer (admin PATCH) sets `updated_at` explicitly on write.
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
