"""Bersagli a chiave naturale nel seed del catalogo Pro (09-02 Task 1).

Copre `_risolvi_bersaglio_naturale` e `seed_domande` con dati costruiti nel
test (non il JSON reale, che arriva nel Task 2). Sessione in memoria + seed
completo come in `test_seed.py`, cosi' sottocategorie/voci del listino di
default esistono davvero quando si risolve un bersaglio naturale.
"""

import pytest
from sqlalchemy import create_engine

from app.db import Base
from app.models.domanda import Domanda, EffettoOpzione, OpzioneDomanda
from app.models.dettaglio_pro import Sottocategoria, Voce
from app.models.listino import Listino
from scripts.seed import load_seed_data, seed, seed_domande
from tests.session_factory import sessione_di_test


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)
    with testing_session_local() as s:
        seed(s, load_seed_data())
        yield s


def _domanda_con_effetto(code: str, opzione_code: str, e_data: dict) -> dict:
    return {
        "domande": [
            {
                "code": code,
                "testo": "domanda di test",
                "tipo_controllo": "scelta_singola",
                "opzioni": [
                    {
                        "code": opzione_code,
                        "etichetta": "Opzione di test",
                        "effetti": [e_data],
                    }
                ],
            }
        ]
    }


def test_target_voce_con_codice_risolve_id_reale(session):
    """target_voce con codice esplicito (A.6.2, A-EDILE) risolve alla voce vera."""
    voce_reale = (
        session.query(Voce)
        .join(Sottocategoria)
        .filter(Sottocategoria.categoria_code == "A-EDILE", Voce.codice == "A.6.2")
        .one()
    )
    data = _domanda_con_effetto(
        "test_target_voce",
        "opt1",
        {
            "tipo_effetto": "includi",
            "target_voce": {
                "categoria_code": "A-EDILE",
                "sottocategoria": "A.6",
                "voce": "A.6.2",
            },
        },
    )
    non_risolti = seed_domande(session, data)

    assert non_risolti == 0
    effetto = session.query(EffettoOpzione).join(OpzioneDomanda).filter(
        OpzioneDomanda.domanda_code == "test_target_voce"
    ).one()
    assert effetto.target_voce_id == voce_reale.id


def test_target_sottocategoria_per_nome_senza_codice(session):
    """target_sottocategoria senza codice risolve per nome esatto (B-FINITURE / PAVIMENTI PARQUET)."""
    sotto_reale = (
        session.query(Sottocategoria)
        .filter_by(categoria_code="B-FINITURE", codice=None, nome="PAVIMENTI PARQUET")
        .one()
    )
    data = _domanda_con_effetto(
        "test_target_sotto",
        "opt1",
        {
            "tipo_effetto": "includi",
            "target_sottocategoria": {
                "categoria_code": "B-FINITURE",
                "sottocategoria": "PAVIMENTI PARQUET",
            },
        },
    )
    non_risolti = seed_domande(session, data)

    assert non_risolti == 0
    effetto = session.query(EffettoOpzione).join(OpzioneDomanda).filter(
        OpzioneDomanda.domanda_code == "test_target_sotto"
    ).one()
    assert effetto.target_sottocategoria_id == sotto_reale.id


def test_voce_senza_codice_risolve_per_descrizione_esatta(session):
    """Una voce senza codice (famiglia catalogo) si risolve per descrizione esatta
    dentro la sottocategoria."""
    voce_reale = (
        session.query(Voce)
        .join(Sottocategoria)
        .filter(
            Sottocategoria.categoria_code == "B-FINITURE",
            Sottocategoria.nome == "PAVIMENTI PARQUET",
            Voce.codice.is_(None),
        )
        .first()
    )
    assert voce_reale is not None
    data = _domanda_con_effetto(
        "test_target_voce_desc",
        "opt1",
        {
            "tipo_effetto": "includi",
            "target_voce": {
                "categoria_code": "B-FINITURE",
                "sottocategoria": "PAVIMENTI PARQUET",
                "voce": voce_reale.descrizione,
            },
        },
    )
    non_risolti = seed_domande(session, data)

    assert non_risolti == 0
    effetto = session.query(EffettoOpzione).join(OpzioneDomanda).filter(
        OpzioneDomanda.domanda_code == "test_target_voce_desc"
    ).one()
    assert effetto.target_voce_id == voce_reale.id


def test_bersaglio_naturale_inesistente_viene_saltato_senza_eccezione(session):
    """Un bersaglio naturale che non esiste viene saltato in silenzio (il seed
    gira al boot) e conta come non risolto — nessuna eccezione."""
    data = _domanda_con_effetto(
        "test_target_rotto",
        "opt1",
        {
            "tipo_effetto": "includi",
            "target_voce": {
                "categoria_code": "A-EDILE",
                "sottocategoria": "A.6",
                "voce": "A.6.999-inesistente",
            },
        },
    )
    non_risolti = seed_domande(session, data)

    assert non_risolti == 1
    count = session.query(EffettoOpzione).join(OpzioneDomanda).filter(
        OpzioneDomanda.domanda_code == "test_target_rotto"
    ).count()
    assert count == 0


def test_seed_due_volte_e_idempotente_sui_bersagli_naturali(session):
    """Due esecuzioni consecutive di seed() (che chiama seed_domande sul JSON
    reale, privo di bersagli naturali oggi) producono lo stesso numero di righe
    effetto_opzione anche quando si aggiungono a mano effetti Pro a bersaglio
    naturale fra le due chiamate a seed_domande."""
    data = _domanda_con_effetto(
        "test_target_idempotente",
        "opt1",
        {
            "tipo_effetto": "includi",
            "target_voce": {
                "categoria_code": "A-EDILE",
                "sottocategoria": "A.6",
                "voce": "A.6.2",
            },
        },
    )
    seed_domande(session, data)
    count_dopo_primo = session.query(EffettoOpzione).count()

    seed_domande(session, data)
    count_dopo_secondo = session.query(EffettoOpzione).count()

    assert count_dopo_primo == count_dopo_secondo


def test_senza_listino_default_bersaglio_naturale_si_salta(session):
    """Senza listino di default, gli effetti con bersaglio naturale si saltano
    (non_risolti conta) invece di far fallire il seed."""
    session.query(Listino).filter_by(is_default=True).update({"is_default": False})
    session.flush()

    data = _domanda_con_effetto(
        "test_target_senza_listino",
        "opt1",
        {
            "tipo_effetto": "includi",
            "target_voce": {
                "categoria_code": "A-EDILE",
                "sottocategoria": "A.6",
                "voce": "A.6.2",
            },
        },
    )
    non_risolti = seed_domande(session, data)

    assert non_risolti == 1


def test_effetto_senza_bersaglio_naturale_passa_invariato(session):
    """Un effetto con target_categoria_code / target_sottocategoria_id /
    target_voce_id espliciti (come oggi, nessuna chiave target_voce/
    target_sottocategoria) non passa dalla risoluzione e si crea come sempre."""
    data = _domanda_con_effetto(
        "test_target_esplicito",
        "opt1",
        {
            "tipo_effetto": "moltiplicatore_categoria",
            "target_categoria_code": "A-EDILE",
            "valore": 1.05,
        },
    )
    non_risolti = seed_domande(session, data)

    assert non_risolti == 0
    effetto = session.query(EffettoOpzione).join(OpzioneDomanda).filter(
        OpzioneDomanda.domanda_code == "test_target_esplicito"
    ).one()
    assert effetto.target_categoria_code == "A-EDILE"
