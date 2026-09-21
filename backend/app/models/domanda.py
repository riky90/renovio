"""Catalogo di domande in database: domanda -> opzione -> effetto.

Questo modulo sostituisce tre meccanismi scollegati che facevano pezzi dello
stesso lavoro:

  - `voce.livello` (una colonna String senza FK, un asse solo, curato a mano);
  - `coefficiente_qta_voce.domanda_mirata_key` (tre chiavi hardcoded in tre
    punti che non si conoscono fra loro: il keyword matching del parser, lo
    schema Pydantic e le label React);
  - i campi del form nati come colonne dedicate di `StimaRequest`.

Tutti e tre sono casi particolari di "una risposta dell'utente cambia il
calcolo". Modellarli una volta sola in DB (ENG-02: mai costanti di business nel
codice) significa che aggiungere una domanda torna a essere un lavoro da
pannello admin invece che un deploy di backend e frontend.

Il vincolo che tiene in piedi il tutto e' che `tipo_effetto` e' un INSIEME
CHIUSO di sette valori, ognuno con una sua aritmetica nota al motore: niente
espressioni, niente formule arbitrarie in tabella. I motori a regole marciscono
quando si puo' scrivere qualunque cosa in una cella. Vedi
`app/services/effetti.py` per l'elenco e l'ordine di risoluzione.

Nessuna di queste tabelle porta il coefficiente impresa: le correzioni sono in
euro-cliente, come `listino_categoria.base_eur_mq` (regola non negoziabile #1).
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Domanda(Base):
    """Una domanda del catalogo, con il suo controllo e il suo pubblico.

    `tier_minimo` decide chi la vede: `free` e' nel wizard pubblico, `pro`
    entra solo nel configuratore dietro paywall. Non e' una colonna di comodo —
    e' la linea Free/Pro resa dato, cosi' si sposta una domanda da un tier
    all'altro senza toccare il codice.

    `attributo_code` collega la domanda alla sua baseline in `attesa_immobile`.
    Vale per gli `stepper` che si correggono sullo SCOSTAMENTO dall'atteso
    (bagni, finestre, porte...): senza una riga di attesa che copra i m2 della
    stima, la correzione non si applica affatto. E' deliberato — meglio nessuna
    correzione che una correzione su una baseline inventata — e l'anteprima
    admin lo segnala esplicitamente invece di lasciarlo sparire in silenzio.
    """

    __tablename__ = "domanda"

    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    testo: Mapped[str] = mapped_column(String(300), nullable=False)
    help: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # stepper | scelta_singola | scelta_multipla | toggle | numero
    tipo_controllo: Mapped[str] = mapped_column(String(24), nullable=False)

    gruppo: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    ordine: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")

    # free | pro
    tier_minimo: Mapped[str] = mapped_column(
        String(8), nullable=False, default="free", server_default="free"
    )

    attributo_code: Mapped[str | None] = mapped_column(String(32), nullable=True)

    obbligatoria: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )

    # Visibilita' condizionale: la domanda compare solo se un'altra domanda ha
    # una certa risposta (es. "quali impianti" solo se "rifai gli impianti"=si).
    visibile_se_domanda_code: Mapped[str | None] = mapped_column(
        ForeignKey("domanda.code", ondelete="SET NULL"), nullable=True
    )
    visibile_se_opzione_code: Mapped[str | None] = mapped_column(String(64), nullable=True)

    attiva: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )


class OpzioneDomanda(Base):
    """Una risposta possibile.

    Uno `stepper`/`numero` ha UNA SOLA opzione implicita, per convenzione con
    `code='valore'`: il numero digitato dall'utente non sceglie fra opzioni, ma
    moltiplica l'effetto agganciato a quell'unica opzione. Cosi' la FK di
    `effetto_opzione` resta singola e non nullable, invece di dover essere "o
    l'opzione o la domanda".

    `immagine_url` serve ai livelli di finitura, dove la differenza fra "medie"
    e "alte" si spiega con una foto molto meglio che con un aggettivo.
    """

    __tablename__ = "opzione_domanda"
    __table_args__ = (
        UniqueConstraint("domanda_code", "code", name="uq_opzione_domanda_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    domanda_code: Mapped[str] = mapped_column(
        ForeignKey("domanda.code", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    etichetta: Mapped[str] = mapped_column(String(200), nullable=False)
    descrizione: Mapped[str | None] = mapped_column(String(500), nullable=True)
    immagine_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    ordine: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")


class EffettoOpzione(Base):
    """Cosa fa una risposta al calcolo. Sette tipi, nessuno di piu'.

    Il target e' esattamente uno fra categoria / sottocategoria / voce, scelto
    in base al `tipo_effetto`; la validazione sta in `app/services/effetti.py`
    (errori leggibili) e non in un CHECK di tabella.

    `tipo_code` nullo significa "vale per tutti i tipi di ristrutturazione", che
    e' il caso normale: si riempie solo quando un effetto deve pesare in modo
    diverso su una ristrutturazione leggera e su una totale. Lasciarlo nullo
    tiene la curatela a ~60 numeri invece che a ~180.
    """

    __tablename__ = "effetto_opzione"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    opzione_id: Mapped[int] = mapped_column(
        ForeignKey("opzione_domanda.id", ondelete="CASCADE"), nullable=False
    )

    tipo_effetto: Mapped[str] = mapped_column(String(32), nullable=False)

    target_categoria_code: Mapped[str | None] = mapped_column(
        ForeignKey("categoria.code"), nullable=True
    )
    target_sottocategoria_id: Mapped[int | None] = mapped_column(
        ForeignKey("sottocategoria.id", ondelete="CASCADE"), nullable=True
    )
    target_voce_id: Mapped[int | None] = mapped_column(
        ForeignKey("voce.id", ondelete="CASCADE"), nullable=True
    )

    tipo_code: Mapped[str | None] = mapped_column(
        ForeignKey("tipo_ristrutturazione.code"), nullable=True
    )

    # Numeric(12,4): regge sia un fattore (1.0800) sia un importo in euro
    # (1900.0000). Nullo per gli effetti che non hanno un valore (includi /
    # escludi).
    valore: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)

    attivo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )


class AttesaImmobile(Base):
    """La baseline: quanti bagni/finestre/porte ha "normalmente" un immobile di
    tot metri quadri.

    Doppio uso deliberato, ed e' il motivo per cui e' una tabella sola:
      - il wizard ci prende i DEFAULT dei contatori, cosi' l'utente aggiusta
        invece di compilare da zero;
      - il motore ci prende la BASELINE, perche' le correzioni si applicano
        sullo scostamento e non sul valore assoluto.

    La seconda meta' e' cio' che protegge l'oracolo: un 85 m2 con i valori
    attesi ha scostamento zero su ogni attributo, quindi costa esattamente
    quanto costava prima che questo layer esistesse.

    Le fasce sono chiuse a entrambi gli estremi e non devono sovrapporsi; se si
    sovrappongono vince la prima per `fascia_mq_min`, ma e' un errore di
    curatela che l'anteprima admin mostra.
    """

    __tablename__ = "attesa_immobile"
    __table_args__ = (
        UniqueConstraint("attributo_code", "fascia_mq_min", name="uq_attesa_attributo_fascia"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    attributo_code: Mapped[str] = mapped_column(String(32), nullable=False)
    fascia_mq_min: Mapped[int] = mapped_column(nullable=False)
    fascia_mq_max: Mapped[int] = mapped_column(nullable=False)
    valore_atteso: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
