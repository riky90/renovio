"""Gestione utenti/ruoli lato admin. Solo `require_admin`: assegnare ruoli
e' un potere riservato all'admin (non ai consulenti).

Guardrail anti-lockout:
- un admin non puo' cambiare il PROPRIO ruolo (evita di auto-declassarsi e
  perdere l'accesso mentre lavora);
- non si puo' rimuovere l'ULTIMO admin del sistema (evita di lasciare
  l'istanza senza nessun amministratore).

Non toccare `routers/admin/__init__.py` per la logica: questo file resta il
solo punto di estensione delle route di questa sezione.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from app.db import SessionLocal
from app.dependencies.auth import ROLE_ADMIN, require_admin
from app.models.user import User
from app.schemas.admin_utenti import RoleUpdate, UserAdminOut

router = APIRouter(prefix="/utenti", tags=["admin-utenti"])


@router.get("", response_model=list[UserAdminOut])
def lista_utenti(_admin: User = Depends(require_admin)) -> list[UserAdminOut]:
    with SessionLocal() as session:
        rows = session.execute(select(User).order_by(User.id)).scalars().all()
        return [UserAdminOut.model_validate(row, from_attributes=True) for row in rows]


@router.patch("/{user_id}", response_model=UserAdminOut)
def aggiorna_ruolo(
    user_id: int,
    payload: RoleUpdate,
    admin: User = Depends(require_admin),
) -> UserAdminOut:
    if user_id == admin.id:
        raise HTTPException(403, "Non puoi cambiare il tuo stesso ruolo")

    with SessionLocal() as session:
        row = session.get(User, user_id)
        if row is None:
            raise HTTPException(404, "Utente non trovato")

        # Anti-lockout: non degradare l'ultimo admin rimasto.
        if row.role == ROLE_ADMIN and payload.role != ROLE_ADMIN:
            admin_count = session.execute(
                select(func.count()).select_from(User).where(User.role == ROLE_ADMIN)
            ).scalar_one()
            if admin_count <= 1:
                raise HTTPException(409, "Deve restare almeno un amministratore")

        row.role = payload.role
        session.commit()
        session.refresh(row)

        return UserAdminOut.model_validate(row, from_attributes=True)
