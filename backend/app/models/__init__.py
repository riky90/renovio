"""SQLAlchemy 2.0 ORM entities for the Phase 1 schema. Import this module
(or its members) to ensure all models are registered on `Base.metadata`
before Alembic autogenerate or `Base.metadata.create_all` runs.
"""

from app.models.catalogo import (
    Categoria,
    ComuneListino,
    Extra,
    Moltiplicatore,
    Referente,
    TipoRistrutturazione,
)
from app.models.listino import Listino, ListinoCategoria
from app.models.user import PasswordResetToken, User, UserSession

__all__ = [
    "Categoria",
    "ComuneListino",
    "Extra",
    "Listino",
    "ListinoCategoria",
    "Moltiplicatore",
    "PasswordResetToken",
    "Referente",
    "TipoRistrutturazione",
    "User",
    "UserSession",
]
