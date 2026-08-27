"""POST /api/v1/me/pro/attiva (stub) + POST /api/v1/admin/pro/attiva.

D-07: flusso "production-shaped" — l'attivazione utente e' uno stub (nessun
addebito reale) che comunque passa dall'endpoint server-side reale;
in produzione bastera' accendere il pagamento vero davanti a questa stessa
attivazione. Upsert idempotente della `Subscription` per `user_id`: una
seconda chiamata non crea una seconda riga (stesso pattern
`.filter_by(...).one_or_none()` di `scripts/seed.py`). Rate limit
10/minute su `/me/pro/attiva` (T-03-04, coerente con `/auth/login`).
L'endpoint admin e' dietro `require_admin` (T-03-03b) e attiva Pro per un
`user_id` arbitrario (attivazione manuale, D-07).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.db import SessionLocal
from app.dependencies.auth import get_current_user, require_admin
from app.limiter import limiter
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.subscription import AttivaProResponse

router = APIRouter(tags=["subscription"])


def _attiva_subscription_per_user_id(session, user_id: int) -> Subscription:
    sub = session.query(Subscription).filter_by(user_id=user_id).one_or_none()
    if sub is None:
        sub = Subscription(user_id=user_id, stato="attivo", scaduta_il=None)
        session.add(sub)
    else:
        sub.stato = "attivo"
        sub.scaduta_il = None
    session.commit()
    session.refresh(sub)
    return sub


@router.post("/me/pro/attiva", response_model=AttivaProResponse)
@limiter.limit("10/minute")
def attiva_pro(request: Request, current_user: User = Depends(get_current_user)) -> AttivaProResponse:
    with SessionLocal() as session:
        sub = _attiva_subscription_per_user_id(session, current_user.id)
        return AttivaProResponse(pro=True, stato=sub.stato)


class AdminAttivaProRequest(BaseModel):
    user_id: int


@router.post("/admin/pro/attiva", response_model=AttivaProResponse)
def admin_attiva_pro(
    payload: AdminAttivaProRequest,
    admin_user: User = Depends(require_admin),
) -> AttivaProResponse:
    with SessionLocal() as session:
        sub = _attiva_subscription_per_user_id(session, payload.user_id)
        return AttivaProResponse(pro=True, stato=sub.stato)
