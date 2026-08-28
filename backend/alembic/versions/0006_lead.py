"""lead

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0006'
down_revision: Union[str, Sequence[str], None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema. SOLO additivo: nessuna tabella/seed esistente toccata (D-24)."""
    op.create_table(
        'lead',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('stima_salvata_id', sa.Integer(), nullable=True),
        sa.Column('nome', sa.String(length=200), nullable=False),
        sa.Column('email', sa.String(length=320), nullable=False),
        sa.Column('telefono', sa.String(length=50), nullable=True),
        sa.Column('preferenza_contatto', sa.String(length=16), nullable=False),
        sa.Column('fascia_oraria', sa.String(length=32), nullable=True),
        sa.Column('messaggio', sa.String(length=2000), nullable=True),
        sa.Column('citta', sa.String(length=200), nullable=False),
        sa.Column('mq', sa.Integer(), nullable=False),
        sa.Column('tipo', sa.String(length=32), nullable=False),
        sa.Column('totale_min', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('totale_max', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('referente_id', sa.Integer(), nullable=True),
        sa.Column('email_inviata', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('stato', sa.String(length=16), server_default='nuovo', nullable=False),
        sa.Column('nota', sa.String(length=2000), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['stima_salvata_id'], ['stima.id'], ),
        sa.ForeignKeyConstraint(['referente_id'], ['referente.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_lead_user_id'), 'lead', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_lead_user_id'), table_name='lead')
    op.drop_table('lead')
