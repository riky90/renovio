"""livello_finitura + voce.livello + categoria.livello_selezionabile +
stima.livelli_pro_json

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0010'
down_revision: Union[str, Sequence[str], None] = '0009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema. SOLO additivo (D-24): una `create_table` e tre colonne
    nullable-o-con-server_default su tabelle esistenti.

    Il problema che risolve: le sottocategorie `famiglia='catalogo'` (53 voci
    di gres, 14 di parquet, 10 di porte...) sono cataloghi di ALTERNATIVE, e il
    motore Pro le sommava tutte. Su una stima reale di 120 m2 il dettaglio Pro
    usciva otto volte il sintetico. Il livello di finitura e' il selettore che
    ne sceglie una per famiglia.

    NESSUN backfill di `voce.livello`: NULL e' il valore corretto e significa
    "voce comune a tutti i livelli, sempre inclusa". Finche' l'admin non cura i
    dati, il motore produce un risultato bit-identico a prima della migrazione.
    Allo stesso modo `categoria.livello_selezionabile` nasce a 0 ovunque: e' il
    seed idempotente a metterlo a 1 su B/C/D, cosi' resta modificabile da admin
    senza una nuova migrazione.
    """
    op.create_table(
        'livello_finitura',
        sa.Column('code', sa.String(length=16), nullable=False),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column('ordine', sa.Integer(), server_default='0', nullable=False),
        sa.Column('descrizione', sa.String(length=300), nullable=True),
        sa.Column('is_default', sa.Boolean(), server_default='0', nullable=False),
        sa.PrimaryKeyConstraint('code'),
    )

    op.add_column(
        'categoria',
        sa.Column('livello_selezionabile', sa.Boolean(), server_default='0', nullable=False),
    )
    op.add_column('voce', sa.Column('livello', sa.String(length=16), nullable=True))
    op.add_column('stima', sa.Column('livelli_pro_json', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('stima', 'livelli_pro_json')
    op.drop_column('voce', 'livello')
    op.drop_column('categoria', 'livello_selezionabile')
    op.drop_table('livello_finitura')
