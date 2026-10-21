"""`StimaSalvata`: hybrid immutable snapshot of a Free estimate.

Scalar columns (`citta`/`mq`/`tipo`/`totale_min`/`totale_max`/`fallback`)
make the per-user history list a cheap query with no JSON parsing per row
(02-RESEARCH.md Pattern 3). `risultato_json` (generic `sqlalchemy.JSON`, NOT
`JSONB` — portable to SQLite dev, 02-RESEARCH.md Environment Availability)
holds the full frozen payload — identical in shape to `StimaResponse`
(schemas/stima.py) plus `schema_version` — used verbatim by the detail
endpoint and, later, the PDF (Plan 08). This row is written ONCE at save
time and NEVER recomputed (D-09, Pitfall 5) — no `EstimationService` call
anywhere near this model.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class StimaSalvata(Base):
    __tablename__ = "stima"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False, index=True)

    # Colonne scalari congelate — storico economico, no JSON parsing per riga.
    citta: Mapped[str] = mapped_column(String(200), nullable=False)
    mq: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    totale_min: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    totale_max: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    fallback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")

    # Snapshot completo congelato — stessa forma di StimaResponse + schema_version.
    # JSON generico (non JSONB): portabile SQLite dev / Postgres prod.
    risultato_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    @property
    def tipo_mostrato(self) -> str:
        """Il tipo da mostrare: quello che le risposte descrivono, se lo
        snapshot lo porta, altrimenti quello scelto. `tipo` resta il tipo
        scelto perche' il dettaglio Pro ricalcola da li' (preset)."""
        return (self.risultato_json or {}).get("tipo_effettivo") or self.tipo

    # Risposte alle domande mirate del dettaglio Pro (bagni/porte/condizionatori,
    # max 3 interi) — nullable, colonna JSON generica per portabilita (03-RESEARCH.md
    # Pitfall 3 / Open Question 2): persistita cosi' il dettaglio Pro e il PDF Pro
    # non divergono se l'utente risponde una volta e poi rivede lo stesso risultato.
    risposte_pro_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Livelli di finitura scelti per categoria ({"B-FINITURE": "medio", ...}) —
    # gemello di `risposte_pro_json`: stessa colonna JSON generica, stessa
    # ragione (schermata e PDF Pro leggono da qui, quindi non possono
    # divergere). Nullable: NULL significa "l'utente non ha scelto", e il
    # motore applica il livello `is_default`.
    livelli_pro_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Tier con cui la stima e' stata creata ('free' | 'pro'). Valorizzato UNA
    # VOLTA al salvataggio dal piano allora attivo e MAI piu' toccato: se
    # l'utente passa a Pro, le sue stime Free storiche restano Free. Nullable a
    # schema per la regola additiva su SQLite (D-24) — il codice legge sempre
    # `row.tier or "free"`.
    tier: Mapped[str | None] = mapped_column(String(16), nullable=True)

    # Budget dichiarato dall'utente (EUR, IVA inclusa). E' un parametro, non un
    # risultato: sta FUORI da `risultato_json` (che e' scritto una volta) cosi'
    # si puo' cambiare con un PATCH senza toccare lo snapshot. Mai letto dal
    # motore di stima. NULL = nessun budget.
    budget_eur: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
