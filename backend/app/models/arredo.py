"""Forfait di arredo: quanto costa arredare un ambiente a un dato livello.

L'arredo NON e' una lavorazione, e questo modulo esiste perche' quella
distinzione sia strutturale e non una convenzione che qualcuno prima o poi
dimentica. Il totale lavori resta `Sigma categorie + extra`; l'arredo viaggia
accanto (`StimaResponse.arredo`, fratello di `totale`), mai dentro.

Due scelte che vale la pena motivare.

**Perche' una tabella e non un effetto del catalogo domande.** I sette
`tipo_effetto` portano un `valore` singolo; un forfait di arredo e' un RANGE
(`eur_min`, `eur_max`), come ogni altro numero che mostriamo. Infilarlo negli
effetti vorrebbe dire due righe per ogni cella piu' un tipo di effetto che il
motore non sa comporre con gli altri.

**Perche' `opzione_id` e non una stringa `ambiente_code`.** E' la correzione
esplicita dell'errore di `voce.livello`: una colonna stringa senza FK, curata a
mano, che il sistema non puo' verificare e che infatti e' rimasta compilata su
21 voci su 191. Qui il forfait punta alla riga dell'opzione che lo genera,
quindi cancellare un ambiente porta via i suoi forfait e un ambiente che non
esiste non puo' averne.

La conseguenza piu' utile e' che `services/arredo.py` **non conosce il codice
della domanda**: cerca i forfait fra le opzioni scelte, e un'opzione che ha un
forfait contribuisce. Rinominare la domanda, spostarla di gruppo o affiancarne
una seconda non tocca una riga di codice (ENG-02).

Gli importi sono LORDI, IVA inclusa: sono prezzi al cliente. E' anche cio' che
li rende direttamente utilizzabili come base del Bonus Mobili, che si applica
alla spesa sostenuta. Nessun coefficiente impresa entra qui, come ovunque.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ForfaitArredo(Base):
    """`(opzione di ambiente, livello di finitura) -> range in euro`."""

    __tablename__ = "forfait_arredo"
    __table_args__ = (
        UniqueConstraint("opzione_id", "livello_code", name="uq_forfait_arredo_opzione_livello"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    opzione_id: Mapped[int] = mapped_column(
        ForeignKey("opzione_domanda.id", ondelete="CASCADE"), nullable=False
    )
    livello_code: Mapped[str] = mapped_column(
        ForeignKey("livello_finitura.code"), nullable=False
    )

    # Lordi, IVA inclusa. Il range non e' incertezza di calcolo: e' la
    # differenza reale fra due cucine dello stesso livello.
    eur_min: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    eur_max: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    attivo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
