"""bonus_fiscale + aliquota_bonus + bonus_categoria

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0011'
down_revision: Union[str, Sequence[str], None] = '0010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema. Tre `create_table` e NESSUNA colonna su tabelle
    esistenti: rischio zero su SQLite (D-24), e nessuna riga storica toccata.

    I dati (aliquote, tetti, finestre di validita', mapping categoria->bonus)
    non stanno qui: li mette il seed idempotente, cosi' restano modificabili
    dal pannello admin senza una nuova migrazione. E' la stessa disciplina dei
    prezzi di listino.
    """
    op.create_table(
        'bonus_fiscale',
        sa.Column('code', sa.String(length=32), nullable=False),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column('descrizione', sa.String(length=500), nullable=True),
        sa.Column('ordine', sa.Integer(), server_default='0', nullable=False),
        sa.Column('attivo', sa.Boolean(), server_default='1', nullable=False),
        sa.PrimaryKeyConstraint('code'),
    )

    op.create_table(
        'aliquota_bonus',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('bonus_code', sa.String(length=32), nullable=False),
        sa.Column('destinazione', sa.String(length=32), nullable=False),
        sa.Column('aliquota_pct', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('tetto_spesa_eur', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('tetto_modalita', sa.String(length=32), nullable=True),
        sa.Column('rate_annuali', sa.Integer(), server_default='10', nullable=False),
        sa.Column('valido_dal', sa.Date(), nullable=False),
        sa.Column('valido_al', sa.Date(), nullable=True),
        sa.Column('note', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['bonus_code'], ['bonus_fiscale.code']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('bonus_code', 'destinazione', 'valido_dal', name='uq_aliquota_bonus_periodo'),
    )

    op.create_table(
        'bonus_categoria',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('bonus_code', sa.String(length=32), nullable=False),
        sa.Column('categoria_code', sa.String(length=32), nullable=False),
        sa.Column('quota_ammissibile_pct', sa.Numeric(precision=5, scale=4), server_default='1', nullable=False),
        sa.ForeignKeyConstraint(['bonus_code'], ['bonus_fiscale.code']),
        sa.ForeignKeyConstraint(['categoria_code'], ['categoria.code']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('bonus_code', 'categoria_code', name='uq_bonus_categoria'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('bonus_categoria')
    op.drop_table('aliquota_bonus')
    op.drop_table('bonus_fiscale')
