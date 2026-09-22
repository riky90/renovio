"""updated_at sulle nove tabelle curate: guardia di staleness per il re-import (D-11)

Revision ID: 0019
Revises: 0018
Create Date: 2026-09-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0019'
down_revision: Union[str, Sequence[str], None] = '0018'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema. SOLO additivo: nove `add_column`, nessun `alter` di
    colonna esistente.

    D-11 chiede di poter dire, riga per riga, se un record e' cambiato nel
    database dopo che un file di export e' stato generato — senza questa
    colonna la domanda non ha risposta. `server_default=sa.func.now()`
    popola le righe esistenti all'istante della migrazione: quell'istante e'
    anteriore a qualunque export generato dopo, quindi il primo re-import non
    marchera' tutto come superato.
    """
    op.add_column("sottocategoria", sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False))
    op.add_column("voce", sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False))
    op.add_column("coefficiente_qta_voce", sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False))
    op.add_column("moltiplicatore", sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False))
    op.add_column("extra", sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False))
    op.add_column("categoria", sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False))
    op.add_column("listino_categoria", sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False))
    op.add_column("forfait_arredo", sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False))
    op.add_column("lead", sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False))


def downgrade() -> None:
    """Downgrade schema. Nove `drop_column` speculari."""
    op.drop_column("sottocategoria", "updated_at")
    op.drop_column("voce", "updated_at")
    op.drop_column("coefficiente_qta_voce", "updated_at")
    op.drop_column("moltiplicatore", "updated_at")
    op.drop_column("extra", "updated_at")
    op.drop_column("categoria", "updated_at")
    op.drop_column("listino_categoria", "updated_at")
    op.drop_column("forfait_arredo", "updated_at")
    op.drop_column("lead", "updated_at")
