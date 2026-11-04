"""user.email_verificata: la casella e' dimostrata (Google o reset password)

Serve a due difese:
  - la promozione ad admin via ADMIN_EMAIL avviene solo con l'email
    verificata, non alla prima registrazione con quell'indirizzo;
  - quando un login Google (email verificata) si aggancia a un account mai
    verificato che ha una password, quella password puo' essere di chi ha
    registrato l'account per primo: si azzera (pre-hijacking).

Gli account esistenti partono da False: il ruolo admin gia' assegnato resta.

Revision ID: 0035
Revises: 0034
Create Date: 2026-11-04 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0035'
down_revision: Union[str, Sequence[str], None] = '0034'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("email_verificata", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("user", "email_verificata")
