"""subscription.user_id unico: una tessera per utente

Il modello diceva "una riga per utente" ma lo schema non lo imponeva. Un
webhook Stripe e la conferma del checkout che arrivano insieme su un utente
senza tessera potevano crearne due; da li' ogni `one_or_none()` alzava
`MultipleResultsFound` e i pagamenti di quell'utente andavano in 500.

Prima del vincolo si UNISCONO gli eventuali doppioni, senza perdere nulla di
cio' che conta:
  - si tiene la riga piu' informativa: con abbonamento Stripe, poi attiva,
    poi con la scadenza piu' lontana (NULL = senza scadenza), poi la piu'
    recente;
  - i campi vuoti della riga tenuta si riempiono dalle altre (id cliente e
    abbonamento Stripe, data di acquisto);
  - `receduto_il` si tiene se una qualunque riga lo ha (la piu' vecchia): il
    recesso vale una volta per account e non deve "rinascere" da un doppione;
  - le altre righe si cancellano.

Poi l'indice su user_id diventa UNIQUE. Il downgrade lo riporta non unico
(le righe unite non si separano piu').

Revision ID: 0036
Revises: 0035
Create Date: 2026-11-04 15:00:00.000000

"""
from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0036'
down_revision: Union[str, Sequence[str], None] = '0035'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLONNE = (
    "id", "user_id", "stato", "scaduta_il", "stripe_customer_id", "stripe_subscription_id",
    "acquistato_il", "receduto_il",
)
_RIEMPIBILI = ("stripe_customer_id", "stripe_subscription_id", "acquistato_il")


def _priorita(riga: dict) -> tuple:
    scadenza = riga["scaduta_il"]
    if isinstance(scadenza, str):
        scadenza = datetime.fromisoformat(scadenza)
    return (
        riga["stripe_subscription_id"] is not None,
        riga["stato"] == "attivo",
        scadenza is None,
        scadenza or datetime.min,
        riga["id"],
    )


def _unisci_doppioni(bind) -> None:
    doppi = bind.execute(
        sa.text("SELECT user_id FROM subscription GROUP BY user_id HAVING COUNT(*) > 1")
    ).scalars().all()
    for user_id in doppi:
        righe = [
            dict(r._mapping)
            for r in bind.execute(
                sa.text(f"SELECT {', '.join(_COLONNE)} FROM subscription WHERE user_id = :u"),
                {"u": user_id},
            )
        ]
        righe.sort(key=_priorita, reverse=True)
        tenuta, altre = righe[0], righe[1:]

        aggiornamenti = {}
        for campo in _RIEMPIBILI:
            if tenuta[campo] is None:
                valore = next((r[campo] for r in altre if r[campo] is not None), None)
                if valore is not None:
                    aggiornamenti[campo] = valore
        recessi = [r["receduto_il"] for r in righe if r["receduto_il"] is not None]
        if recessi:
            aggiornamenti["receduto_il"] = min(recessi)

        if aggiornamenti:
            assegnazioni = ", ".join(f"{k} = :{k}" for k in aggiornamenti)
            bind.execute(
                sa.text(f"UPDATE subscription SET {assegnazioni} WHERE id = :id"),
                {**aggiornamenti, "id": tenuta["id"]},
            )
        for riga in altre:
            bind.execute(sa.text("DELETE FROM subscription WHERE id = :id"), {"id": riga["id"]})


def upgrade() -> None:
    _unisci_doppioni(op.get_bind())
    op.drop_index("ix_subscription_user_id", table_name="subscription")
    op.create_index("ix_subscription_user_id", "subscription", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_subscription_user_id", table_name="subscription")
    op.create_index("ix_subscription_user_id", "subscription", ["user_id"], unique=False)
