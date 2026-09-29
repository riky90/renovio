"""Seed idempotency + completeness tests (backend/scripts/seed.py).

Uses an isolated in-memory SQLite DB per test — never touches dev.db.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.models.catalogo import Categoria, ComuneListino, Extra, Moltiplicatore, TipoRistrutturazione
from app.models.listino import Listino, ListinoCategoria
from app.models.testo import Testo as TestoRow  # alias: evita la collection di pytest
from scripts.seed import TESTI_INIZIALI, load_seed_data, seed
from tests.session_factory import sessione_di_test

EXPECTED_COUNTS = {
    "listino": 1,
    # 5 e non 4 dalla fase 07: `E-ARREDO` e' una categoria vera in tabella,
    # ma `nel_totale_lavori=False` la tiene fuori dal motore Free. Il conteggio
    # qui e' un ORACOLO di seed, quindi si aggiorna a mano quando la struttura
    # cambia davvero — mai allentandolo a `>= 4`.
    "categoria": 5,
    "tipo": 3,
    "moltiplicatore": 12,
    "extra": 2,
    "comune_listino": 2,  # RE aliases: "Reggio Emilia" + "Reggio nell'Emilia"
}


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)
    with testing_session_local() as s:
        yield s


def _counts(session: Session) -> dict[str, int]:
    return {
        "listino": session.query(Listino).count(),
        "categoria": session.query(Categoria).count(),
        "tipo": session.query(TipoRistrutturazione).count(),
        "moltiplicatore": session.query(Moltiplicatore).count(),
        "extra": session.query(Extra).count(),
        "comune_listino": session.query(ComuneListino).count(),
    }


def test_seed_loads_full_re_dataset(session):
    data = load_seed_data()
    seed(session, data)

    assert _counts(session) == EXPECTED_COUNTS

    listino = session.query(Listino).one()
    assert listino.is_default is True
    assert listino.nome == "Reggio Emilia"

    lc_count = session.query(ListinoCategoria).filter_by(listino_id=listino.id).count()
    assert lc_count == 4


def test_seed_dopo_rinomina_del_listino_re_non_ne_crea_un_secondo(session):
    """CR-01 review 09: il nome del listino si modifica dal pannello. Il seed
    lo ritrova per `citta_riferimento`, quindi una rinomina non crea al boot
    un secondo listino RE predefinito."""
    data = load_seed_data()
    seed(session, data)
    listino = session.query(Listino).one()
    listino.nome = "Reggio Emilia 2026"
    session.flush()

    seed(session, data)

    assert session.query(Listino).count() == 1
    assert session.query(Listino).filter_by(is_default=True).count() == 1


def test_seed_non_crea_un_secondo_predefinito(session):
    """Se l'admin ha scelto un altro listino come predefinito, il seed non
    rimette il flag su RE: due predefiniti bloccano seed_domande al boot."""
    data = load_seed_data()
    seed(session, data)
    re_listino = session.query(Listino).one()
    re_listino.is_default = False
    session.add(Listino(nome="Parma", citta_riferimento="Parma", is_default=True))
    session.flush()

    seed(session, data)

    predefiniti = session.query(Listino).filter_by(is_default=True).all()
    assert [p.nome for p in predefiniti] == ["Parma"]


def test_seed_is_idempotent(session):
    data = load_seed_data()
    seed(session, data)
    seed(session, data)  # re-run must not duplicate any row

    assert _counts(session) == EXPECTED_COUNTS


def test_seed_non_sovrascrive_testi_modificati(session):
    """`seed()` gira a ogni boot del container (Dockerfile CMD). Se `seed_testi`
    riscrivesse `valore`, ogni testo modificato dal pannello admin tornerebbe al
    default cablato a ogni deploy — i disclaimer sono contenuto editoriale
    dell'admin, il seed li crea ma non li possiede."""
    data = load_seed_data()
    seed(session, data)

    chiave = next(iter(TESTI_INIZIALI))
    row = session.get(TestoRow, chiave)
    assert row is not None
    row.valore = "Testo riscritto dall'admin dal pannello."
    session.flush()

    seed(session, data)  # secondo boot del container

    assert session.get(TestoRow, chiave).valore == "Testo riscritto dall'admin dal pannello."
    # e le chiavi mancanti continuano a essere create
    assert session.query(TestoRow).count() == len(TESTI_INIZIALI)
