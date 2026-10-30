"""tipo_ristrutturazione: range asimmetrico (ampiezza sotto separata)

`range_pct` resta l'ampiezza SOPRA il valore stimato; `range_pct_sotto` e'
l'ampiezza SOTTO. NULL vale come `range_pct` (range simmetrico), cosi' un DB
non ancora riseminato si comporta come prima. I valori (-10% / +15% per i tre
tipi, decisione di Riccardo del 2026-10-30 dopo la taratura TAR-01) li scrive
il seed a ogni avvio, come gia' `range_pct`.

Revision ID: 0031
Revises: 0030
Create Date: 2026-10-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0031'
down_revision: Union[str, Sequence[str], None] = '0030'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("tipo_ristrutturazione") as batch:
        batch.add_column(sa.Column("range_pct_sotto", sa.Numeric(4, 3), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("tipo_ristrutturazione") as batch:
        batch.drop_column("range_pct_sotto")
