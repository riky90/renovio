"""avatar_blob: secondo backend di storage per gli avatar

Revision ID: 0016
Revises: 0015
Create Date: 2026-09-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0016'
down_revision: Union[str, Sequence[str], None] = '0015'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema. SOLO additivo (D-24): una `create_table`, nessuna
    colonna esistente toccata.

    Il problema che risolve: l'upload avatar risponde 503 in produzione dal
    giorno del deploy, perche' le cinque `R2_*` non sono mai state configurate
    e `settings.storage_configured` e' un `all([...])`. Aprire un bucket R2
    richiede una carta di credito anche sul piano gratuito. Questa tabella
    da' all'app un posto durevole dove mettere i byte senza dipendere da
    nessuno: il filesystem di Render e' effimero, il database no.

    Il ramo R2 resta intatto e ha la precedenza: se un giorno le cinque
    variabili ci sono, `storage_service` torna a usarlo senza migrazioni.
    """
    op.create_table(
        "avatar_blob",
        # Stesso spazio dei nomi di R2 (`avatars/{user_id}/{uuid4}.webp`), cosi'
        # `key_from_url` resta una sola funzione per entrambi i backend.
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "content_type",
            sa.String(length=64),
            nullable=False,
            server_default="image/webp",
        ),
        sa.Column("dati", sa.LargeBinary(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("key"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_avatar_blob_user_id", "avatar_blob", ["user_id"])


def downgrade() -> None:
    """Downgrade schema. Distruttivo per costruzione: i byte degli avatar
    vivono solo qui, quindi tornare indietro li perde. E' accettabile perche'
    `user.avatar_url` non e' un dato di dominio e l'utente puo' ricaricare la
    foto."""
    op.drop_index("ix_avatar_blob_user_id", table_name="avatar_blob")
    op.drop_table("avatar_blob")
