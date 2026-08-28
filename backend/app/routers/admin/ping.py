"""GET /admin/ping — proof-of-concept admin-only route.

Spostato qui da Fase 2 (`routers/admin.py`) invariato, ora dentro il
package `routers/admin/` (04-02-PLAN.md Task 1). Dimostra AUTH-04
(server-side role guard, `require_admin`, T-03-03).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies.auth import require_admin

router = APIRouter()


@router.get("/ping")
def ping(user=Depends(require_admin)) -> dict[str, str]:
    return {"status": "ok"}
