"""export_log: audit dei download admin (chi, cosa, quando, quante righe, margine)

Revision ID: 0018
Revises: 0017
Create Date: 2026-09-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0018'
down_revision: Union[str, Sequence[str], None] = '0017'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema. SOLO additivo: una `create_table`.

    D-15 chiede che ogni download admin lasci una traccia interrogabile: il
    log applicativo non basta perche' su Render ruota. Nessuna tabella
    esistente viene toccata, il seed resta intatto.
    """
    op.create_table(
        "export_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("risorsa", sa.String(length=32), nullable=False),
        sa.Column("righe", sa.Integer(), nullable=False),
        sa.Column("include_margine", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_export_log_user_id"), "export_log", ["user_id"], unique=False)


def downgrade() -> None:
    """Nessun dato applicativo da preservare: la tabella e' pura traccia
    tecnica, non input curato a mano."""
    op.drop_index(op.f("ix_export_log_user_id"), table_name="export_log")
    op.drop_table("export_log")
