"""Health endpoints. GET /health/db proves the Browser -> API -> DB round-trip
required by the Walking Skeleton (see SKELETON.md).

`storage` dice quale backend serve gli avatar (`"r2"` o `"db"`). Sta qui e non
in un endpoint admin perche' la domanda "quale storage e' attivo in
produzione?" e' esattamente quella a cui si e' risposto per mesi guardando le
variabili d'ambiente invece dell'app: R2 e' rimasto spento dal deploy senza
che niente lo dicesse, e l'upload rispondeva 503. Nessun segreto esce da qui —
solo il nome del ramo scelto, mai le credenziali ne' gli URL.
"""

from fastapi import APIRouter
from sqlalchemy import func, select

from app.config import settings
from app.db import SessionLocal
from app.models import Listino

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/db")
def health_db() -> dict:
    with SessionLocal() as session:
        listini = session.scalar(select(func.count()).select_from(Listino)) or 0
    return {"status": "ok", "listini": listini, "storage": settings.storage_backend}
