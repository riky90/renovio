"""arredo: categoria.nel_totale_lavori + forfait_arredo

Revision ID: 0015
Revises: 0014
Create Date: 2026-09-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0015'
down_revision: Union[str, Sequence[str], None] = '0014'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema. SOLO additivo (D-24): una `create_table` e una colonna
    con `server_default` su una tabella esistente.

    Il problema che risolve: l'arredo non e' una lavorazione. Sommarlo al
    totale gonfierebbe il numero che l'utente confronta con altri preventivi e
    romperebbe la riconciliazione `Sigma categorie + extra = totale`. Ma tenerlo
    fuori dalla tabella `categoria` costringerebbe a un secondo meccanismo per
    le voci Pro dell'arredo. Quindi la categoria c'e', e a escluderla dal
    totale lavori e' un DATO.

    `nel_totale_lavori` nasce a 1 OVUNQUE, ed e' il valore corretto per le
    quattro categorie esistenti: senza il seed che porta `E-ARREDO` a 0, questa
    migrazione non cambia un solo euro. Stessa disciplina di
    `categoria.livello_selezionabile` (0010): il valore e' curatela, non
    schema, quindi si sposta da pannello admin senza una migrazione nuova.
    """
    op.add_column(
        'categoria',
        sa.Column('nel_totale_lavori', sa.Boolean(), server_default='1', nullable=False),
    )

    op.create_table(
        'forfait_arredo',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('opzione_id', sa.Integer(), nullable=False),
        sa.Column('livello_code', sa.String(length=16), nullable=False),
        sa.Column('eur_min', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('eur_max', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('attivo', sa.Boolean(), server_default='1', nullable=False),
        sa.ForeignKeyConstraint(['opzione_id'], ['opzione_domanda.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['livello_code'], ['livello_finitura.code']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('opzione_id', 'livello_code', name='uq_forfait_arredo_opzione_livello'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('forfait_arredo')
    op.drop_column('categoria', 'nel_totale_lavori')
