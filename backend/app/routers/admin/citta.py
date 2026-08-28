"""Stub — CRUD citta/mappature/tipi (ADM-03), riempito dal piano 04-05.

Non toccare `routers/admin/__init__.py`: questo file resta il solo punto
di estensione per le route di questa sezione (04-02-PLAN.md Task 1).
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/citta", tags=["admin-citta"])
