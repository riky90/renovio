"""Schemi admin per Testo (D-14): campi chiusi, uso esclusivo in
`routers/admin/testi.py` dietro `Depends(require_admin)`.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TestoAdminOut(BaseModel):
    chiave: str
    valore: str
    updated_at: datetime


class TestoPatchIn(BaseModel):
    valore: str = Field(min_length=1)
