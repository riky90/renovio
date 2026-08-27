"""dettaglio pro

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, Sequence[str], None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('sottocategoria',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('listino_id', sa.Integer(), nullable=False),
    sa.Column('categoria_code', sa.String(length=32), nullable=False),
    sa.Column('codice', sa.String(length=16), nullable=True),
    sa.Column('nome', sa.String(length=200), nullable=False),
    sa.Column('famiglia', sa.String(length=16), nullable=False),
    sa.Column('ordine', sa.Integer(), server_default='0', nullable=False),
    sa.ForeignKeyConstraint(['listino_id'], ['listino.id'], ),
    sa.ForeignKeyConstraint(['categoria_code'], ['categoria.code'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('voce',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('sottocategoria_id', sa.Integer(), nullable=False),
    sa.Column('codice', sa.String(length=16), nullable=True),
    sa.Column('descrizione', sa.String(length=300), nullable=False),
    sa.Column('um', sa.String(length=16), nullable=False),
    sa.Column('prezzo_unitario_cliente', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('ordine', sa.Integer(), server_default='0', nullable=False),
    sa.ForeignKeyConstraint(['sottocategoria_id'], ['sottocategoria.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('coefficiente_qta_voce',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('voce_id', sa.Integer(), nullable=False),
    sa.Column('tipo_code', sa.String(length=32), nullable=False),
    sa.Column('coefficiente_qta_per_mq', sa.Numeric(precision=8, scale=4), nullable=True),
    sa.Column('domanda_mirata_key', sa.String(length=32), nullable=True),
    sa.Column('default_conteggio', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['voce_id'], ['voce.id'], ),
    sa.ForeignKeyConstraint(['tipo_code'], ['tipo_ristrutturazione.code'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('voce_id', 'tipo_code', name='uq_coefficiente_qta_voce_tipo')
    )
    op.add_column('stima', sa.Column('risposte_pro_json', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('stima', 'risposte_pro_json')
    op.drop_table('coefficiente_qta_voce')
    op.drop_table('voce')
    op.drop_table('sottocategoria')
