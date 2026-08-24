"""Health endpoints. GET /health/db proves the Browser -> API -> DB round-trip
required by the Walking Skeleton (see SKELETON.md)."""

from fastapi import APIRouter
from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Listino

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/db")
def health_db() -> dict:
    with SessionLocal() as session:
        listini = session.scalar(select(func.count()).select_from(Listino)) or 0
    return {"status": "ok", "listini": listini}
