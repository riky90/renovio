"""GET /api/v1/admin/ping — proof-of-concept admin-only route.

Demonstrates AUTH-04 (server-side role guard, `require_admin`, T-03-03) with
zero admin UI (that lands in Phase 4). Not meant to be a real admin
capability — just proves 200 for admin / 403 for a normal user end-to-end.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies.auth import require_admin

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/ping")
def ping(user=Depends(require_admin)) -> dict[str, str]:
    return {"status": "ok"}
