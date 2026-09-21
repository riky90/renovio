"""`AvatarBlob`: i byte dell'avatar quando lo storage esterno non c'e'.

Renovio nasce con gli avatar su object storage S3-compatibile (Cloudflare R2).
Quel percorso resta la strada maestra ed e' intatto: questa tabella e' il
**secondo backend** di `services/storage_service.py`, scelto quando le cinque
`R2_*` non sono configurate. Non e' un fallback silenzioso — la scelta e'
esplicita in `settings.storage_backend` e visibile in `/health` — ed e' la
ragione per cui l'endpoint di upload puo' smettere di rispondere 503 senza
che nessuno debba aprire un conto con carta di credito.

Perche' i byte in tabella e non su disco: il filesystem di Render e'
effimero, quindi un avatar scritto su disco sopravvive fino al primo redeploy.
Il database e' l'unico posto durevole che l'app ha gia'.

Il costo e' noto e accettato: un avatar normalizzato da `avatar_service` e'
un WEBP 512x512 q=82, cioe' ~20-30 KB, e ogni immagine viene servita dal
processo applicativo invece che da una CDN. Con `Cache-Control: immutable` e
una key che cambia a ogni upload, il browser la richiede una volta sola.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AvatarBlob(Base):
    __tablename__ = "avatar_blob"

    # La key e' la stessa di R2 (`avatars/{user_id}/{uuid4}.webp`): cosi' i due
    # backend hanno lo stesso spazio dei nomi e `key_from_url` resta una sola
    # funzione. E' anche la PK, perche' e' gia' unica per costruzione.
    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    # ON DELETE CASCADE: cancellato l'utente, i suoi byte se ne vanno con lui.
    # Non c'e' nessuna ragione per cui una foto debba sopravvivere all'account.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default="image/webp", server_default="image/webp"
    )
    dati: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
