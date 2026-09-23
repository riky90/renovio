"""SQLAlchemy 2.0 ORM entities for the Phase 1 schema. Import this module
(or its members) to ensure all models are registered on `Base.metadata`
before Alembic autogenerate or `Base.metadata.create_all` runs.

Every module under `app/models/` MUST be re-exported here. This is not a
style rule: `alembic/env.py` builds `target_metadata` from `Base.metadata`
and relies on `from app import models` alone to populate it, so a model
module that nobody imports here is a table that autogenerate believes has
been deleted — and the migration it writes starts with `drop_table`. The
regression that enforces the rule is
`tests/test_modelli_registrati.py::test_ogni_modulo_di_app_models_e_registrato_in_metadata`:
a new entity that is forgotten here fails a test instead of a migration.
"""

from app.models.arredo import ForfaitArredo
from app.models.avatar import AvatarBlob
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
from app.models.domanda import (
    AttesaImmobile,
    DerivazioneRisposta,
    Domanda,
    EffettoOpzione,
    OpzioneDomanda,
)
from app.models.export_log import ExportLog
from app.models.lead import Lead
from app.models.listino import Listino, ListinoCategoria
from app.models.stima_salvata import StimaSalvata
from app.models.subscription import Subscription
from app.models.testo import Testo
from app.models.user import PasswordResetToken, User, UserSession

__all__ = [
    "AliquotaBonus",
    "AttesaImmobile",
    "AvatarBlob",
    "BonusCategoria",
    "BonusExtra",
    "BonusFiscale",
    "Categoria",
    "CoefficienteQuantitaVoce",
    "ComuneListino",
    "DerivazioneRisposta",
    "Domanda",
    "EffettoOpzione",
    "ExportLog",
    "Extra",
    "ForfaitArredo",
    "Lead",
    "Listino",
    "ListinoCategoria",
    "LivelloFinitura",
    "Moltiplicatore",
    "OpzioneDomanda",
    "PasswordResetToken",
    "Referente",
    "Sottocategoria",
    "StimaSalvata",
    "Subscription",
    "Testo",
    "TipoRistrutturazione",
    "User",
    "UserSession",
    "Voce",
]
