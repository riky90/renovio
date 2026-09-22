"""GET /admin/export-log (D-15, D-16, CUR-04): traccia di lettura per
tutte e quattro le risorse esportabili del pannello — listino, domande,
parametri, lead.

`Depends(require_staff)` — stesso perimetro della dashboard lead dove la
traccia si vede (D-16), e stessa scelta di trasparenza reciproca: nessun
filtro per ruolo sulle righe, il consulente vede anche i download altrui e
gli altri vedono i suoi. Ultimi 50 record ordinati per `created_at`
decrescente, nessuna paginazione (coerente col resto del pannello).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.auth import get_db, require_staff
from app.models.export_log import ExportLog
from app.models.user import User
from app.schemas.admin_export import ExportLogOut

router = APIRouter(prefix="/export-log", tags=["admin-export-log"])


@router.get("", response_model=list[ExportLogOut])
def lista_export_log(
    _staff: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> list[ExportLogOut]:
    """Join in una sola query su `User` per risolvere `user_label` (nome,
    mai l'id nudo che a schermo non dice niente) — non una query per riga."""
    rows = (
        db.query(ExportLog, User)
        .join(User, ExportLog.user_id == User.id)
        .order_by(ExportLog.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        ExportLogOut(
            id=log.id,
            user_id=log.user_id,
            user_label=user.nome or user.email,
            risorsa=log.risorsa,
            righe=log.righe,
            include_margine=log.include_margine,
            created_at=log.created_at,
        )
        for log, user in rows
    ]
