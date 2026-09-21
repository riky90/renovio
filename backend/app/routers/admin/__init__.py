"""Aggregatore del package admin: `router` include TUTTI i subrouter admin.

`app/main.py` continua a fare `from app.routers import admin` e
`app.include_router(admin.router, prefix="/api/v1")` senza modifiche: il
nome esportato `router` resta identico a quello dello stub Fase 2
(`routers/admin.py`, ora convertito in package).

Ogni subrouter (ping/listini/coefficienti/citta/testi/referenti/lead/
upload_listino) protegge le proprie route con `Depends(require_admin)` a
livello di singola funzione — questo file NON aggiunge un guard qui, si
limita ad aggregare (04-RESEARCH.md Project Structure).

I piani 04-03/04/05/10 aggiungono route SOLO nei rispettivi subrouter,
senza mai toccare questo file (stub gia' pronti da questo piano).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.routers.admin import (
    bonus,
    citta,
    coefficienti,
    dettaglio_pro,
    domande,
    lead,
    listini,
    ping,
    referenti,
    testi,
    upload_listino,
    utenti,
)

router = APIRouter(prefix="/admin", tags=["admin"])

router.include_router(ping.router)
router.include_router(bonus.router)
router.include_router(listini.router)
router.include_router(coefficienti.router)
router.include_router(citta.router)
router.include_router(testi.router)
router.include_router(referenti.router)
router.include_router(lead.router)
router.include_router(upload_listino.router)
router.include_router(utenti.router)
router.include_router(dettaglio_pro.router)
router.include_router(domande.router)
