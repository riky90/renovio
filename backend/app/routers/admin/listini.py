"""CRUD listini/prezzi (ADM-01, D-09/D-10/D-13): creazione Listino per
citta nuova + mappatura ComuneListino, CRUD categoria (base_eur_mq/
coefficiente_impresa) e CRUD voce (prezzo/UM, chiave naturale stabile).

Task 1 di questo piano crea solo lo scheletro del router (`router` vuoto,
incluso da `routers/admin/__init__.py`); le route sono implementate nei
Task 2 (Listino+categoria) e 3 (voce) dello stesso piano.

Ogni route DEVE avere `Depends(require_admin)` (T-04-07/D-10/D-22): questa
e' l'unica sede in cui `coefficiente_impresa`/`base_eur_mq` sono esposti.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/listini", tags=["admin-listini"])
