"""Fabbrica di sessioni per i test, con ESATTAMENTE la configurazione di
produzione (WR-04).

Le fixture costruivano la sessione con `sessionmaker(bind=engine)`, che
lascia il default `autoflush=True`; la produzione usa
`sessionmaker(autocommit=False, autoflush=False, bind=engine)`
(`app/db.py`). La differenza non e' cosmetica: decide se una query vede gli
oggetti pendenti aggiunti poco prima, cioe' proprio la semantica di
scrittura che la suite dell'import deve presidiare.

E' la divergenza che ha reso invisibile a 555 test la CR-02 dell'iterazione
2 (due righe con la stessa chiave naturale nello stesso file): lo stesso
script stampava `COMMIT OK` con la configurazione di test e sollevava
`IntegrityError` con quella di produzione.

I kwargs NON sono ricopiati a mano ma letti da `SessionLocal.kw`: se un
giorno la produzione cambiasse configurazione, i test la seguirebbero da
soli invece di divergere in silenzio una seconda volta.
"""

from __future__ import annotations

from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.db import SessionLocal as _SessionLocalProduzione


def sessione_di_test(engine: Engine) -> sessionmaker:
    """`sessionmaker` legato a `engine` con i kwargs della produzione.

    L'unico kwarg sostituito e' `bind`: i test girano su un SQLite
    temporaneo, non sul database dell'applicazione.
    """
    kwargs = {chiave: valore for chiave, valore in _SessionLocalProduzione.kw.items() if chiave != "bind"}
    return sessionmaker(bind=engine, **kwargs)
