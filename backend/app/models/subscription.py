"""`Subscription`: tessera abbonamento Pro (D-06), non un semplice flag.

Una riga per utente (1:1 applicativo, non vincolato a livello di schema per
restare compatibile con futuri rinnovi/storico): `stato` di default
"inattivo"; una riga con `stato="attivo"` e `scaduta_il` None e' considerata
sempre attiva (nessuna scadenza), mentre `scaduta_il` nel passato rende la
tessera non attiva anche se `stato="attivo"` (si veda
`subscription_is_active` in `app/dependencies/auth.py`). `piano_code` e'
un placeholder nullable (D-07, "production-shaped": in produzione bastera'
accendere il pagamento reale, lo schema e' gia' pronto per un piano/prezzo).

Questo modello NON contiene, e non deve mai contenere, colonne
prezzo/coefficiente impresa (D-10): la tessera Pro riguarda solo lo stato
dell'abbonamento, mai margini o prezzi interni.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, false, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Subscription(Base):
    __tablename__ = "subscription"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False, index=True)
    stato: Mapped[str] = mapped_column(String(16), nullable=False, default="inattivo", server_default="inattivo")
    scaduta_il: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    piano_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    # Pagamento con Stripe (migrazione 0032). Il cliente Stripe si crea al
    # primo checkout e si riusa; l'abbonamento Stripe e' quello che i webhook
    # aggiornano. `cancella_a_fine_periodo`: l'utente ha disdetto, il Pro resta
    # attivo fino a `scaduta_il` e poi non si rinnova.
    stripe_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    cancella_a_fine_periodo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
