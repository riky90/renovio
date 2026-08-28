"""CRUD testi/disclaimer (ADM-03, D-14): GET lista + PATCH aggiorna valore.

Ogni route ha `Depends(require_admin)` (T-04-11): righe mancanti -> 404
(nessun ownership check, solo il gate require_admin, stesso pattern di
`routers/admin/listini.py`). Nessuna route qui crea/modifica una chiave
Testo per il fallback referente (D-05, silenzioso — Pitfall 5, T-04-13):
lo scope resta limitato alle chiavi seedate da `scripts/seed.py`.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies.auth import get_db, require_admin
from app.models.testo import Testo
from app.schemas.admin_testi import TestoAdminOut, TestoPatchIn

router = APIRouter(prefix="/testi", tags=["admin-testi"])


def _to_out(row: Testo) -> TestoAdminOut:
    return TestoAdminOut(chiave=row.chiave, valore=row.valore, updated_at=row.updated_at)


@router.get("", response_model=list[TestoAdminOut])
def lista_testi(user=Depends(require_admin), db: Session = Depends(get_db)) -> list[TestoAdminOut]:
    rows = db.execute(select(Testo).order_by(Testo.chiave)).scalars().all()
    return [_to_out(row) for row in rows]


@router.patch("/{chiave}", response_model=TestoAdminOut)
def modifica_testo(
    chiave: str,
    payload: TestoPatchIn,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> TestoAdminOut:
    row = db.get(Testo, chiave)
    if row is None:
        raise HTTPException(404, "Testo non trovato")

    row.valore = payload.valore
    row.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(row)
    return _to_out(row)
