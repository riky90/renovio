"""Stub — upload Excel a due passi (ADM-01, D-18/D-19/D-20), riempito dal
piano 04-08.

Non toccare `routers/admin/__init__.py`: questo file resta il solo punto
di estensione per le route di questa sezione (04-02-PLAN.md Task 1).
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/upload-listino", tags=["admin-upload-listino"])
