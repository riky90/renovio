"""Il tipo di ristrutturazione e' un punto di partenza, non un vincolo.

Il tipo scelto precompila le risposte col suo preset; ampiezza del range ed
etichetta seguono invece i lavori davvero indicati (`effetti.tipo_effettivo`).
Chi parte da "leggera" e poi rifa' tutto deve vedere il range di una totale.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import app.db as db_module
from app.db import Base
from app.main import app
from app.services.computo import tipo_effettivo
from app.models.listino import Listino
from app.services.effetti import preset_per_tipo
from scripts.seed import load_seed_data, seed
from tests.session_factory import sessione_di_test


@pytest.fixture(scope="module")
def sessione(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db") / "test_tipo_effettivo.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)
    with testing_session_local() as s:
        seed(s, load_seed_data())
        s.commit()

    import app.routers.stima as stima_router

    originale = db_module.SessionLocal
    db_module.SessionLocal = testing_session_local
    stima_router.SessionLocal = testing_session_local
    yield testing_session_local
    db_module.SessionLocal = originale
    stima_router.SessionLocal = originale


def _te(s, tipo, risposte):
    listino = s.query(Listino).first()
    return tipo_effettivo(s, listino, mq=85, tipo=tipo, risposte=risposte)


def test_senza_risposte_resta_il_tipo_scelto(sessione):
    with sessione() as s:
        for tipo in ("leggera", "moderata", "totale"):
            assert _te(s, tipo, None) == tipo
            assert _te(s, tipo, {}) == tipo


def test_il_preset_di_un_tipo_descrive_quel_tipo(sessione):
    with sessione() as s:
        for scelto in ("leggera", "moderata", "totale"):
            for preset in ("leggera", "moderata", "totale"):
                assert _te(s, scelto, preset_per_tipo(s, preset)) == preset


def test_una_modifica_isolata_non_cambia_tipo(sessione):
    with sessione() as s:
        assert _te(s, "leggera", {"interv_cucina": "si"}) == "leggera"


def test_pesa_il_costo_non_il_numero_di_risposte(sessione):
    """Tre risposte cambiate, ma pesanti: pavimenti, tutti i bagni, elettrico."""
    with sessione() as s:
        risposte = {"interv_pavimenti": "rifai", "interv_bagni": "tutti", "interv_elettrico": "rifacimento"}
        assert _te(s, "leggera", risposte) != "leggera"


def test_le_finiture_non_spostano_il_tipo(sessione):
    """Finiture di pregio su una leggera: costa di piu', ma i lavori sono gli stessi."""
    with sessione() as s:
        assert _te(s, "leggera", {"livello_finiture": "alto"}) == "leggera"


def _stima(tipo, risposte):
    r = TestClient(app).post(
        "/api/v1/stima", json={"citta": "Reggio Emilia", "mq": 85, "tipo": tipo, "risposte": risposte}
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_range_ed_etichetta_seguono_le_risposte(sessione):
    with sessione() as s:
        lavori_totale = preset_per_tipo(s, "totale")

    da_leggera = _stima("leggera", lavori_totale)
    da_totale = _stima("totale", lavori_totale)

    assert da_leggera["input"]["tipo"] == "leggera"
    assert da_leggera["tipo_effettivo"] == "totale"
    # Stessi lavori, stesso range: il punto di partenza non conta piu'.
    assert da_leggera["totale"] == da_totale["totale"]


def test_senza_modifiche_il_tipo_effettivo_e_quello_scelto(sessione):
    assert _stima("moderata", {})["tipo_effettivo"] == "moderata"
