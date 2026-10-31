"""subscription: cliente e abbonamento Stripe, disdetta a fine periodo, recesso

Il Pro si paga con un abbonamento Stripe (mensile o annuale). La tessera
`subscription` resta la fonte dello stato Pro (`subscription_is_active`):
i webhook di Stripe la aggiornano. `acquistato_il` e `receduto_il` servono al
recesso di 14 giorni (art. 54-bis Codice del Consumo). Colonne nuove, tutte senza dati da
migrare: le tessere attivate a mano o con l'attivazione dimostrativa restano
come sono.

Revision ID: 0032
Revises: 0031
Create Date: 2026-10-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0032'
down_revision: Union[str, Sequence[str], None] = '0031'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("subscription") as batch:
        batch.add_column(sa.Column("stripe_customer_id", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("stripe_subscription_id", sa.String(length=64), nullable=True))
        batch.add_column(
            sa.Column("cancella_a_fine_periodo", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch.add_column(sa.Column("acquistato_il", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("receduto_il", sa.DateTime(), nullable=True))
        batch.create_index("ix_subscription_stripe_customer_id", ["stripe_customer_id"])
        batch.create_index("ix_subscription_stripe_subscription_id", ["stripe_subscription_id"])


def downgrade() -> None:
    with op.batch_alter_table("subscription") as batch:
        batch.drop_index("ix_subscription_stripe_subscription_id")
        batch.drop_index("ix_subscription_stripe_customer_id")
        batch.drop_column("receduto_il")
        batch.drop_column("acquistato_il")
        batch.drop_column("cancella_a_fine_periodo")
        batch.drop_column("stripe_subscription_id")
        batch.drop_column("stripe_customer_id")
