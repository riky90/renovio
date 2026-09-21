"""Schemi pubblici del catalogo domande (Fase 2).

Fork deliberato da `schemas/admin_domande.py`, per la stessa ragione per cui
`schemas/stima.py` non riusa `admin_listino.py`: le classi admin portano campi
che il pubblico non deve vedere, e riusarle significherebbe che aggiungere un
campo per l'admin lo pubblica per sbaglio.

**Qui non compaiono gli effetti.** Il client riceve la domanda, le opzioni e il
valore di default; *cosa* fa una risposta al prezzo resta server-side. Non e'
un segreto come il coefficiente impresa — sono euro-cliente — ma e' la taratura
del prodotto, e un client che non la conosce non puo' ricalcolare la stima per
conto suo ne' andare fuori sincrono quando l'admin la cambia.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class OpzioneOut(BaseModel):
    """Una risposta possibile. Nessun `id`: il client lavora per `code`."""

    code: str
    etichetta: str
    descrizione: str | None
    immagine_url: str | None
    is_default: bool
    ordine: int


class DomandaOut(BaseModel):
    code: str
    testo: str
    help: str | None
    tipo_controllo: str
    gruppo: str
    ordine: int
    tier_minimo: str

    #: Attributo di `attesa_immobile` su cui si misura lo scostamento. Presente
    #: sugli stepper; `None` sulle domande a scelta.
    attributo_code: str | None
    obbligatoria: bool

    #: Visibilita' condizionale, risolta dal client mentre l'utente compila.
    #: Le stesse due colonne le rilegge il motore quando ricalcola, quindi una
    #: domanda nascosta non puo' contribuire al prezzo nemmeno se il client
    #: mandasse comunque la sua risposta.
    visibile_se_domanda_code: str | None
    visibile_se_opzione_code: str | None

    #: Il default gia' risolto per questi metri quadri: il numero atteso per uno
    #: stepper, il codice dell'opzione `is_default` per una scelta, la lista dei
    #: codici di default per una scelta multipla. `None` quando non c'e' un
    #: default sensato — e in quel caso il wizard non deve inventarne uno.
    valore_default: Decimal | str | list[str] | None

    opzioni: list[OpzioneOut]


class CatalogoDomandeOut(BaseModel):
    """Il catalogo servito al wizard.

    `mq` e `attese` viaggiano insieme alle domande, e non dietro una seconda
    chiamata, perche' i default dipendono dai metri quadri: separarli renderebbe
    possibile mostrare uno stepper con il default di un'altra superficie.
    """

    tier: str
    mq: int | None
    attese: dict[str, Decimal]
    domande: list[DomandaOut]
