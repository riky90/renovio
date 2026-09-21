"""ArredoService: dagli ambienti scelti a un forfait di arredo, a range.

E' il gemello minore di `estimation.py` e ne condivide tre discipline:
`Decimal` ovunque, `_eur()` con ROUND_HALF_UP solo sull'output, dataclass
frozen a campi chiusi. Non ne condivide il posto nel totale: l'arredo esce da
qui e viaggia in `StimaResponse.arredo`, FRATELLO di `totale`, mai dentro.

Il servizio non sa come si chiama la domanda degli ambienti
--------------------------------------------------------
E non deve saperlo. Chiede a `effetti.risolvi_scelte()` quali opzioni sono
state scelte (con i default gia' applicati e la visibilita' gia' risolta),
poi cerca fra quelle le righe di `forfait_arredo`. Un'opzione che ha un
forfait contribuisce; una che non ce l'ha no.

Ne segue che rinominare la domanda, spostarla di gruppo o affiancarne una
seconda ("ambienti da arredare" + "elettrodomestici") non tocca una riga di
questo file. E' la stessa ragione per cui i sette tipi di effetto vivono in
tabella e non in un `if`: ENG-02 vale anche qui.

Il livello di finitura
----------------------
Per convenzione di curatela, **un'opzione il cui `code` coincide con un
`livello_finitura.code` e' la scelta del livello**. E' della stessa natura di
`OPZIONE_VALORE = "valore"` in `effetti.py`: una convenzione documentata e
verificata da un test, non un `if` sul codice di una domanda. Senza risposta si
cade su `LivelloFinitura.is_default`, come fa il motore Pro.

Perche' puo' tornare `None`
---------------------------
Nessun ambiente scelto, nessun forfait curato per quel livello, o layer
parametrico spento: in tutti e tre i casi la sezione arredo **sparisce** dalla
risposta invece di comparire a zero. Stessa regola del `BonusService`: dire
"l'arredo costa 0" e' peggio che non dire nulla.

Nessun coefficiente impresa entra qui: i forfait sono importi al cliente,
lordi, come `listino_categoria.base_eur_mq` e' un euro al cliente.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models.arredo import ForfaitArredo
from app.models.catalogo import LivelloFinitura
from app.services.effetti import risolvi_scelte


def _eur(value: Decimal) -> Decimal:
    """Quantize to whole euro (ROUND_HALF_UP) — used only on output fields."""
    return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class AmbienteArredato:
    code: str
    nome: str
    eur_min: Decimal
    eur_max: Decimal


@dataclass(frozen=True)
class ArredoResult:
    livello_code: str
    livello_nome: str
    ambienti: list[AmbienteArredato] = field(default_factory=list)
    totale_min: Decimal = Decimal("0")
    totale_max: Decimal = Decimal("0")


class ArredoService:
    """Server-side: `(risposte) -> ArredoResult | None`."""

    @staticmethod
    def compute(
        session: Session,
        risposte: dict[str, Any] | None,
    ) -> ArredoResult | None:
        scelte = risolvi_scelte(session, risposte=risposte)
        if not scelte.opzioni:
            return None

        livelli = {l.code: l for l in session.query(LivelloFinitura).all()}
        if not livelli:
            return None

        livello = ArredoService._livello_scelto(scelte.opzioni, livelli)
        if livello is None:
            return None

        per_opzione = {o.id: o for o in scelte.opzioni}
        righe = (
            session.query(ForfaitArredo)
            .filter(
                ForfaitArredo.opzione_id.in_(list(per_opzione)),
                ForfaitArredo.livello_code == livello.code,
                ForfaitArredo.attivo.is_(True),
            )
            .all()
        )
        if not righe:
            return None

        # L'ordine e' quello del catalogo (`risolvi_scelte` ordina per
        # `ordine, code`), non quello in cui il DB restituisce i forfait:
        # l'utente ha visto gli ambienti in un ordine e li ritrova uguale.
        per_opzione_forfait = {r.opzione_id: r for r in righe}
        ambienti: list[AmbienteArredato] = []
        totale_min = Decimal("0")
        totale_max = Decimal("0")
        for opzione in scelte.opzioni:
            riga = per_opzione_forfait.get(opzione.id)
            if riga is None:
                continue
            eur_min = _eur(riga.eur_min)
            eur_max = _eur(riga.eur_max)
            ambienti.append(
                AmbienteArredato(
                    code=opzione.code,
                    nome=opzione.etichetta,
                    eur_min=eur_min,
                    eur_max=eur_max,
                )
            )
            totale_min += eur_min
            totale_max += eur_max

        if not ambienti:
            return None

        return ArredoResult(
            livello_code=livello.code,
            livello_nome=livello.nome,
            ambienti=ambienti,
            totale_min=totale_min,
            totale_max=totale_max,
        )

    @staticmethod
    def _livello_scelto(
        opzioni, livelli: dict[str, LivelloFinitura]
    ) -> LivelloFinitura | None:
        """La prima opzione scelta il cui `code` e' un livello di finitura.

        Le opzioni arrivano gia' in ordine di catalogo, quindi "la prima" e'
        deterministica anche nel caso — di curatela sbagliata — in cui due
        domande diverse offrano gli stessi codici.
        """
        for opzione in opzioni:
            livello = livelli.get(opzione.code)
            if livello is not None:
                return livello
        for livello in livelli.values():
            if livello.is_default:
                return livello
        return None
