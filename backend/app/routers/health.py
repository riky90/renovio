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

Chi vede cosa: `status` e `aggiornato` sono pubblici (un booleano non dice
nulla a un attaccante e basta a controllare un deploy). Numero di listini,
storage e revisioni delle migrazioni li vede solo un admin loggato: sono
dettagli sull'infrastruttura che a un estraneo servono solo per mirare.
Aprire l'URL dell'API nel browser con la sessione admin attiva basta.
"""

from functools import lru_cache
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import APIRouter, Cookie
from sqlalchemy import func, select, text

from app.config import settings
from app.db import SessionLocal
from app.models import Listino
from app.services.auth_service import SESSION_COOKIE_NAME

router = APIRouter(prefix="/health", tags=["health"])


_ALEMBIC_DIR = Path(__file__).resolve().parents[2] / "alembic"


@lru_cache(maxsize=1)
def _migrazione_head() -> str | None:
    config = Config()
    config.set_main_option("script_location", str(_ALEMBIC_DIR))
    return ScriptDirectory.from_config(config).get_current_head()


def _e_admin(session, session_id: str | None) -> bool:
    """Admin loggato? Mai un 401 qui: senza sessione valida si rispondono solo
    i campi pubblici."""
    if not session_id:
        return False
    from datetime import datetime, timezone

    from app.models.user import UserSession

    riga = session.query(UserSession).filter_by(id=session_id).one_or_none()
    if riga is None:
        return False
    scadenza = riga.expires_at
    if scadenza.tzinfo is None:
        scadenza = scadenza.replace(tzinfo=timezone.utc)
    return scadenza > datetime.now(timezone.utc) and riga.user.role == "admin"


@router.get("/db")
def health_db(session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME)) -> dict:
    with SessionLocal() as session:
        admin = _e_admin(session, session_id)
        listini = session.scalar(select(func.count()).select_from(Listino)) or 0
        try:
            migrazione = session.scalar(text("SELECT version_num FROM alembic_version"))
        except Exception:
            # Database creato senza alembic (test, create_all): nessuna versione.
            session.rollback()
            migrazione = None
    head = _migrazione_head()
    pubblico = {"status": "ok", "aggiornato": migrazione == head}
    if not admin:
        return pubblico
    return {
        **pubblico,
        "listini": listini,
        "storage": settings.storage_backend,
        "migrazione": migrazione,
        "migrazione_head": head,
    }
