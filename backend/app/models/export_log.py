"""ExportLog: audit dei download admin (D-15).

Il log applicativo (stdout/stderr) non basta: su Render ruota e non e'
interrogabile, e "chi ha scaricato cosa e quando" e' esattamente il tipo di
domanda a cui un log di processo non sa rispondere in modo affidabile a
distanza di settimane. Questa tabella registra i cinque fatti minimi che
D-15 chiede — chi (`user_id`), cosa (`risorsa`), quando (`created_at`),
quante righe (`righe`), se il file includeva il margine (`include_margine`)
— ed e' scritta nella stessa richiesta che genera il download, mai in un
passo differibile: un download non tracciato e' un download che non deve
avvenire (CUR-04).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ExportLog(Base):
    __tablename__ = "export_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False, index=True)
    # Valori ammessi a livello applicativo: "listino" | "domande" | "parametri" | "lead".
    risorsa: Mapped[str] = mapped_column(String(32), nullable=False)
    righe: Mapped[int] = mapped_column(nullable=False)
    include_margine: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
