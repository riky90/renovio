"""Schemas per la gestione utenti/ruoli lato admin (ADM: assegnazione ruolo).

`UserAdminOut` e' volutamente CHIUSO a campi: mai `password_hash` (SEGRETO,
models/user.py) ne' altri dati sensibili — espone solo cio' che serve alla
tabella admin. `RoleUpdate.role` e' vincolato ai soli ruoli validi via
`Literal`, cosi' un valore fuori dominio e' 422 a livello di schema.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class UserAdminOut(BaseModel):
    id: int
    email: str
    nome: str
    role: str
    created_at: datetime


class RoleUpdate(BaseModel):
    role: Literal["user", "consulente", "admin"]
