"""La sessione dei test deve essere configurata come quella di produzione
(WR-04).

La produzione usa `sessionmaker(autocommit=False, autoflush=False,
bind=engine)` (`app/db.py`); ogni fixture usava `sessionmaker(bind=engine)`,
che lascia il default `autoflush=True`. La differenza decide se una query
vede gli oggetti pendenti aggiunti poco prima — cioe' proprio la semantica
di scrittura che la suite dell'import deve presidiare. E' la divergenza che
ha reso la CR-02 dell'iterazione 2 invisibile a 555 test: lo stesso script
stampava `COMMIT OK` con la configurazione di test e sollevava
`IntegrityError` con quella di produzione.

I due test qui sotto chiudono il buco da entrambi i lati: uno verifica che
la fabbrica condivisa riproduca davvero la configurazione di produzione,
l'altro che nessun file di test se la ricostruisca per conto suo.
"""

from __future__ import annotations

import ast
from pathlib import Path

from sqlalchemy import create_engine

from app.db import SessionLocal
from tests.session_factory import sessione_di_test

CARTELLA_TEST = Path(__file__).resolve().parent
MODULO_AMMESSO = "session_factory.py"


def test_la_fabbrica_di_test_riproduce_la_configurazione_di_produzione() -> None:
    """Tutti i kwargs tranne `bind` devono coincidere con quelli di
    `app.db.SessionLocal`. Il confronto e' sull'intero dizionario, non sulle
    due chiavi note: se la produzione ne aggiungesse una terza, i test la
    seguirebbero invece di divergere di nuovo in silenzio."""
    fabbrica = sessione_di_test(create_engine("sqlite://"))

    attesi = {chiave: valore for chiave, valore in SessionLocal.kw.items() if chiave != "bind"}
    effettivi = {chiave: valore for chiave, valore in fabbrica.kw.items() if chiave != "bind"}

    assert effettivi == attesi
    # Ridondante ma esplicito: e' QUESTO il flag che nascondeva CR-02.
    assert effettivi["autoflush"] is False


def test_nessun_file_di_test_costruisce_un_sessionmaker_per_conto_suo() -> None:
    """Il modo in cui la divergenza si ripresenterebbe non e' una modifica
    a `session_factory.py` — e' un file di test nuovo che si scrive il suo
    `sessionmaker(bind=engine)`, come facevano tutti e 41 prima di WR-04.

    L'analisi e' sull'AST, non sul testo: un `sessionmaker` nominato in un
    commento o in una docstring (ce ne sono, e spiegano proprio questo
    difetto) non deve far fallire il test.
    """
    colpevoli: list[str] = []
    for percorso in sorted(CARTELLA_TEST.glob("*.py")):
        if percorso.name == MODULO_AMMESSO:
            continue
        albero = ast.parse(percorso.read_text(encoding="utf-8"), filename=str(percorso))
        for nodo in ast.walk(albero):
            if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name) and nodo.func.id == "sessionmaker":
                colpevoli.append(f"{percorso.name}:{nodo.lineno}")

    assert not colpevoli, (
        "Questi file costruiscono una sessione per conto loro invece di usare "
        "`tests.session_factory.sessione_di_test(engine)`, e rischiano di "
        "divergere dalla configurazione di produzione (autoflush!):\n  "
        + "\n  ".join(colpevoli)
    )
