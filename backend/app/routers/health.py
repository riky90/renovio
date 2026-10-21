"""Health endpoints. GET /health/db proves the Browser -> API -> DB round-trip
required by the Walking Skeleton (see SKELETON.md).

`storage` dice quale backend serve gli avatar (`"r2"` o `"db"`). Sta qui e non
in un endpoint admin perche' la domanda "quale storage e' attivo in
produzione?" e' esattamente quella a cui si e' risposto per mesi guardando le
variabili d'ambiente invece dell'app: R2 e' rimasto spento dal deploy senza
che niente lo dicesse, e l'upload rispondeva 503. Nessun segreto esce da qui —
solo il nome del ramo scelto, mai le credenziali ne' gli URL.

`migrazione` e `migrazione_head` dicono se il database di produzione e' allo
schema del codice: le migrazioni girano al boot del container e, se una fallisce,
Render lascia online la versione vecchia. `aggiornato: false` va guardato.
"""

from functools import lru_cache
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import APIRouter
from sqlalchemy import func, select, text

from app.config import settings
from app.db import SessionLocal
from app.models import Listino

router = APIRouter(prefix="/health", tags=["health"])


_ALEMBIC_DIR = Path(__file__).resolve().parents[2] / "alembic"


@lru_cache(maxsize=1)
def _migrazione_head() -> str | None:
    config = Config()
    config.set_main_option("script_location", str(_ALEMBIC_DIR))
    return ScriptDirectory.from_config(config).get_current_head()


@router.get("/db")
def health_db() -> dict:
    with SessionLocal() as session:
        listini = session.scalar(select(func.count()).select_from(Listino)) or 0
        try:
            migrazione = session.scalar(text("SELECT version_num FROM alembic_version"))
        except Exception:
            # Database creato senza alembic (test, create_all): nessuna versione.
            session.rollback()
            migrazione = None
    head = _migrazione_head()
    return {
        "status": "ok",
        "listini": listini,
        "storage": settings.storage_backend,
        "migrazione": migrazione,
        "migrazione_head": head,
        "aggiornato": migrazione == head,
    }
