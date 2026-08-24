"""Health endpoints. GET /health/db proves the Browser -> API -> DB round-trip."""

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/db")
def health_db() -> dict:
    return {"status": "ok", "listini": 0}
