"""catalogo domande: domanda + opzione_domanda + effetto_opzione + attesa_immobile

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0014'
down_revision: Union[str, Sequence[str], None] = '0013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema. SOLO additivo (D-24): quattro `create_table`, nessuna
    colonna tolta o cambiata su tabelle esistenti.

    Nessun backfill e nessuna riga: e' il seed idempotente a popolare il
    catalogo di domande, cosi' resta curabile da admin senza una migrazione
    nuova a ogni modifica (ENG-02). Finche' le tabelle sono vuote il motore
    Free produce un risultato bit-identico a prima: `EstimationService` con
    zero effetti risolti non applica alcuna correzione, e l'oracolo primario
    (85 m2 totale RE -> 47.985-70.575) resta intatto per costruzione.
    """
    op.create_table(
        'domanda',
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('testo', sa.String(length=300), nullable=False),
        sa.Column('help', sa.String(length=500), nullable=True),
        sa.Column('tipo_controllo', sa.String(length=24), nullable=False),
        sa.Column('gruppo', sa.String(length=64), server_default='', nullable=False),
        sa.Column('ordine', sa.Integer(), server_default='0', nullable=False),
        sa.Column('tier_minimo', sa.String(length=8), server_default='free', nullable=False),
        sa.Column('attributo_code', sa.String(length=32), nullable=True),
        sa.Column('obbligatoria', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('visibile_se_domanda_code', sa.String(length=64), nullable=True),
        sa.Column('visibile_se_opzione_code', sa.String(length=64), nullable=True),
        sa.Column('attiva', sa.Boolean(), server_default='1', nullable=False),
        sa.ForeignKeyConstraint(['visibile_se_domanda_code'], ['domanda.code'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('code'),
    )

    op.create_table(
        'opzione_domanda',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('domanda_code', sa.String(length=64), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('etichetta', sa.String(length=200), nullable=False),
        sa.Column('descrizione', sa.String(length=500), nullable=True),
        sa.Column('immagine_url', sa.String(length=500), nullable=True),
        sa.Column('is_default', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('ordine', sa.Integer(), server_default='0', nullable=False),
        sa.ForeignKeyConstraint(['domanda_code'], ['domanda.code'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('domanda_code', 'code', name='uq_opzione_domanda_code'),
    )

    op.create_table(
        'effetto_opzione',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('opzione_id', sa.Integer(), nullable=False),
        sa.Column('tipo_effetto', sa.String(length=32), nullable=False),
        sa.Column('target_categoria_code', sa.String(length=32), nullable=True),
        sa.Column('target_sottocategoria_id', sa.Integer(), nullable=True),
        sa.Column('target_voce_id', sa.Integer(), nullable=True),
        sa.Column('tipo_code', sa.String(length=32), nullable=True),
        sa.Column('valore', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('attivo', sa.Boolean(), server_default='1', nullable=False),
        sa.ForeignKeyConstraint(['opzione_id'], ['opzione_domanda.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_categoria_code'], ['categoria.code']),
        sa.ForeignKeyConstraint(['target_sottocategoria_id'], ['sottocategoria.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_voce_id'], ['voce.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tipo_code'], ['tipo_ristrutturazione.code']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'attesa_immobile',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('attributo_code', sa.String(length=32), nullable=False),
        sa.Column('fascia_mq_min', sa.Integer(), nullable=False),
        sa.Column('fascia_mq_max', sa.Integer(), nullable=False),
        sa.Column('valore_atteso', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('attributo_code', 'fascia_mq_min', name='uq_attesa_attributo_fascia'),
    )


def downgrade() -> None:
    """Downgrade schema. Ordine inverso: prima le figlie, poi le madri."""
    op.drop_table('attesa_immobile')
    op.drop_table('effetto_opzione')
    op.drop_table('opzione_domanda')
    op.drop_table('domanda')
