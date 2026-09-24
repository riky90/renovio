"""GET /api/v1/domande — il contratto che alimenta il wizard (Fase 2).

Quattro cose vanno dimostrate:

  1. I DEFAULT ARRIVANO DAI METRI QUADRI, gia' risolti. E' il motivo per cui
     l'endpoint esiste in questa forma: se il client ricalcolasse la fascia per
     conto suo, una fascia modificata dall'admin sposterebbe il motore senza
     spostare cio' che l'utente vede.
  2. NIENTE ZERO al posto di un default mancante. Zero e' una risposta
     ("nessun bagno"), non un'assenza di risposta, e sullo scostamento vale
     come una correzione al ribasso.
  3. IL TIER FILTRA CORRETTAMENTE, e `pro` include `free` invece di
     sostituirlo — altrimenti il wizard Pro avrebbe un secondo catalogo da
     tenere allineato a mano.
  4. GLI EFFETTI NON ESCONO. Il client riceve le domande, non la taratura.

Il primo test e' anche un test di coerenza col motore: confronta il default
servito con la baseline che `attese_per_mq()` usa per lo scostamento. Se i due
divergessero, un utente che non tocca lo stepper vedrebbe uno scostamento da un
valore che non ha mai scelto.
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import app.db as db_module
from app.db import Base
from app.main import app
from app.models.domanda import OpzioneDomanda
from app.services.effetti import CONTROLLI_NUMERICI, attese_per_mq
from scripts.seed import load_seed_data, seed
from tests.session_factory import sessione_di_test


@pytest.fixture(autouse=True, scope="module")
def _seeded_db(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db") / "test_domande_api.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)

    with testing_session_local() as s:
        seed(s, load_seed_data())
        s.commit()

    original_session_local = db_module.SessionLocal
    db_module.SessionLocal = testing_session_local

    import app.routers.domande as domande_router

    domande_router.SessionLocal = testing_session_local

    yield testing_session_local

    db_module.SessionLocal = original_session_local
    domande_router.SessionLocal = original_session_local


@pytest.fixture()
def client():
    return TestClient(app)


def _get(client, **params):
    response = client.get("/api/v1/domande", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_catalogo_free_non_vuoto_e_ordinato(client):
    body = _get(client, tier="free")

    assert body["tier"] == "free"
    assert body["mq"] is None
    assert len(body["domande"]) > 0
    assert all(d["tier_minimo"] == "free" for d in body["domande"])

    chiavi = [(d["gruppo"], d["ordine"], d["code"]) for d in body["domande"]]
    assert chiavi == sorted(chiavi), "l'ordine deve essere stabile e per (gruppo, ordine, code)"


def test_default_degli_stepper_vengono_dalla_fascia_di_mq(client, _seeded_db):
    """Il default servito e' la stessa baseline che il motore usa."""
    body = _get(client, tier="free", mq=85)

    with _seeded_db() as session:
        attese = attese_per_mq(session, 85)

    assert body["mq"] == 85
    assert body["attese"], "il seed deve coprire 85 m2"

    steppers = [d for d in body["domande"] if d["tipo_controllo"] in CONTROLLI_NUMERICI]
    assert steppers, "il catalogo Free ha degli stepper"

    for domanda in steppers:
        attributo = domanda["attributo_code"]
        if attributo is None or attributo not in attese:
            continue
        assert domanda["valore_default"] is not None
        atteso = attese[attributo]
        assert float(domanda["valore_default"]) == float(atteso), domanda["code"]


def test_fasce_diverse_danno_default_diversi(client):
    """Se i default non si muovessero coi m2, la tabella delle attese sarebbe
    decorativa e il wizard proporrebbe gli stessi numeri a un monolocale e a una
    villa."""
    piccolo = {d["code"]: d["valore_default"] for d in _get(client, mq=40)["domande"]}
    grande = {d["code"]: d["valore_default"] for d in _get(client, mq=200)["domande"]}

    assert piccolo != grande


def test_senza_mq_i_default_numerici_sono_null_mai_zero(client):
    """Zero e' una risposta, non un'assenza di risposta."""
    body = _get(client, tier="free")

    for domanda in body["domande"]:
        if domanda["tipo_controllo"] in CONTROLLI_NUMERICI:
            assert domanda["valore_default"] is None, domanda["code"]


def test_default_delle_scelte_e_il_codice_opzione(client):
    body = _get(client, tier="free", mq=85)

    for domanda in body["domande"]:
        opzioni = {o["code"] for o in domanda["opzioni"]}
        default_flaggati = [o["code"] for o in domanda["opzioni"] if o["is_default"]]

        if domanda["tipo_controllo"] == "scelta_multipla":
            assert domanda["valore_default"] == default_flaggati
        elif domanda["tipo_controllo"] not in CONTROLLI_NUMERICI:
            if default_flaggati:
                assert domanda["valore_default"] == default_flaggati[0]
                assert domanda["valore_default"] in opzioni
            else:
                assert domanda["valore_default"] is None


def test_tier_pro_include_le_domande_free(client):
    free = {d["code"] for d in _get(client, tier="free")["domande"]}
    pro = {d["code"] for d in _get(client, tier="pro")["domande"]}

    assert free, "il catalogo Free non deve essere vuoto"
    assert free <= pro, "un utente Pro compila anche le domande Free"


def test_tier_sconosciuto_e_422(client):
    assert client.get("/api/v1/domande", params={"tier": "enterprise"}).status_code == 422


def test_mq_fuori_range_e_422(client):
    assert client.get("/api/v1/domande", params={"mq": 0}).status_code == 422
    assert client.get("/api/v1/domande", params={"mq": 99_999}).status_code == 422


def test_opzione_disattivata_sparisce_dal_wizard_pubblico(client, _seeded_db):
    """D-27: il wizard non deve piu' elencare un'opzione spenta fra le opzioni
    della sua domanda. Il test tocca il database e lo ripristina, perche' il
    database del modulo e' condiviso con gli altri test."""
    prima = _get(client, tier="free")
    domanda_prima = next(d for d in prima["domande"] if d["code"] == "anno_costruzione")
    assert "pre_1980" in {o["code"] for o in domanda_prima["opzioni"]}, (
        "precondizione: pre_1980 deve comparire prima della disattivazione"
    )

    with _seeded_db() as session:
        opzione = (
            session.query(OpzioneDomanda)
            .filter_by(domanda_code="anno_costruzione", code="pre_1980")
            .one()
        )
        opzione.attiva = False
        session.commit()

    try:
        dopo = _get(client, tier="free")
        domanda_dopo = next(d for d in dopo["domande"] if d["code"] == "anno_costruzione")
        assert "pre_1980" not in {o["code"] for o in domanda_dopo["opzioni"]}
    finally:
        with _seeded_db() as session:
            opzione = (
                session.query(OpzioneDomanda)
                .filter_by(domanda_code="anno_costruzione", code="pre_1980")
                .one()
            )
            opzione.attiva = True
            session.commit()


def test_il_catalogo_non_pubblica_gli_effetti(client):
    """La taratura resta server-side: il client sa *cosa* chiedere, non quanto
    vale la risposta. Controllo sul JSON serializzato e non sulle chiavi del
    dizionario, cosi' un campo annidato non sfugge."""
    grezzo = json.dumps(_get(client, tier="pro", mq=85))

    for vietato in (
        "effetto",
        "effetti",
        "tipo_effetto",
        "valore_atteso",
        "moltiplicatore",
        "coefficiente_impresa",
        "base_eur_mq",
        "prezzo_impresa",
    ):
        assert vietato not in grezzo, f"{vietato!r} non deve uscire dal catalogo"
