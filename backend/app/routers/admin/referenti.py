"""Stub — CRUD referenti (ADM-04, D-15/D-16), riempito dal piano 04-10.

Non toccare `routers/admin/__init__.py`: questo file resta il solo punto
di estensione per le route di questa sezione (04-02-PLAN.md Task 1).
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/referenti", tags=["admin-referenti"])
