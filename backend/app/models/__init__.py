"""SQLAlchemy 2.0 ORM entities for the Phase 1 schema. Import this module
(or its members) to ensure all models are registered on `Base.metadata`
before Alembic autogenerate or `Base.metadata.create_all` runs.
"""

from app.models.bonus import AliquotaBonus, BonusCategoria, BonusExtra, BonusFiscale
from app.models.catalogo import (
    Categoria,
    ComuneListino,
    Extra,
    LivelloFinitura,
    Moltiplicatore,
    Referente,
    TipoRistrutturazione,
)
from app.models.dettaglio_pro import CoefficienteQuantitaVoce, Sottocategoria, Voce
from app.models.listino import Listino, ListinoCategoria
from app.models.stima_salvata import StimaSalvata
from app.models.subscription import Subscription
from app.models.user import PasswordResetToken, User, UserSession

__all__ = [
    "AliquotaBonus",
    "BonusCategoria",
    "BonusExtra",
    "BonusFiscale",
    "Categoria",
    "CoefficienteQuantitaVoce",
    "ComuneListino",
    "Extra",
    "Listino",
    "ListinoCategoria",
    "LivelloFinitura",
    "Moltiplicatore",
    "PasswordResetToken",
    "Referente",
    "Sottocategoria",
    "StimaSalvata",
    "Subscription",
    "TipoRistrutturazione",
    "User",
    "UserSession",
    "Voce",
]
