"""stima salvata

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-25 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('stima',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('citta', sa.String(length=200), nullable=False),
    sa.Column('mq', sa.Integer(), nullable=False),
    sa.Column('tipo', sa.String(length=32), nullable=False),
    sa.Column('totale_min', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('totale_max', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('fallback', sa.Boolean(), server_default='0', nullable=False),
    sa.Column('risultato_json', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stima_user_id'), 'stima', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_stima_user_id'), table_name='stima')
    op.drop_table('stima')
