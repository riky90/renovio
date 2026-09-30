"""Domain-guard test (EST-05 / CLAUDE.md rule 1): the impresa secret must
never appear anywhere in the serialized POST /api/v1/stima response, for any
città (RE non-fallback and a fallback città) and any tipo.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import app.db as db_module
from app.db import Base
from app.main import app
from scripts.seed import load_seed_data, seed
from tests.session_factory import sessione_di_test

FORBIDDEN_SUBSTRINGS = [
    "base_eur_mq",
    "moltiplicatore",
    "coefficiente_impresa",
    "prezzo_impresa",
]

FORBIDDEN_COEFFICIENT_VALUES = ["0.65", "0.6", "0.55", "0.5"]

FORBIDDEN_KEYS = {
    "base_eur_mq",
    "moltiplicatore",
    "coefficiente_impresa",
    "prezzo_impresa",
}


@pytest.fixture(autouse=True, scope="module")
def _seeded_db(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db") / "test_no_leak.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)

    with testing_session_local() as s:
        seed(s, load_seed_data())
        s.commit()

    original_session_local = db_module.SessionLocal
    db_module.SessionLocal = testing_session_local

    import app.routers.stima as stima_router

    stima_router.SessionLocal = testing_session_local

    yield

    db_module.SessionLocal = original_session_local
    stima_router.SessionLocal = original_session_local


@pytest.fixture()
def client():
    return TestClient(app)


def _assert_no_forbidden_keys(node) -> None:
    """Recurse the parsed JSON and assert no key matches the forbidden set
    at any depth."""
    if isinstance(node, dict):
        for key, value in node.items():
            assert key not in FORBIDDEN_KEYS, f"forbidden key '{key}' found in response"
            _assert_no_forbidden_keys(value)
    elif isinstance(node, list):
        for item in node:
            _assert_no_forbidden_keys(item)


@pytest.mark.parametrize(
    "citta,fallback_expected",
    [
        ("Reggio Emilia", False),
        ("Modena", True),
    ],
)
@pytest.mark.parametrize("tipo", ["leggera", "moderata", "totale"])
def test_response_never_leaks_impresa_secret(client, citta, fallback_expected, tipo):
    response = client.post(
        "/api/v1/stima",
        json={"citta": citta, "mq": 85, "tipo": tipo},
    )
    assert response.status_code == 200

    body = response.json()
    assert body["fallback"] is fallback_expected

    # Il blocco `bonus` (0011) viene ESCLUSO dallo scan a sottostringhe, ed e'
    # l'unica esclusione del file. Motivo: le aliquote fiscali abitano lo stesso
    # intervallo numerico dei coefficienti impresa e li COINCIDONO davvero — il
    # coefficiente di D-PRODOTTI e' 0.5 e il bonus ristrutturazione prima casa
    # e' il 50%, cioe' "0.5000". Nessuno scan testuale (ne' un confronto per
    # valore) puo' distinguere i due, quindi tenerli insieme renderebbe il test
    # rosso per una collisione di cifre invece che per una fuga.
    #
    # La garanzia non si indebolisce, si sposta: il blocco bonus e' un DTO a
    # campi chiusi (`BonusOut`/`BonusDettaglioOut` in schemas/stima.py) e qui
    # sotto se ne verifica l'elenco esatto delle chiavi. Aggiungere un campo a
    # quel DTO rompe questo test, che e' esattamente il comportamento voluto:
    # nessun campo nuovo entra nella risposta senza passare da qui.
    bonus = body.get("bonus")
    corpo_senza_bonus = {k: v for k, v in body.items() if k != "bonus"}
    raw_text = json.dumps(corpo_senza_bonus)

    for forbidden in FORBIDDEN_SUBSTRINGS:
        assert forbidden not in raw_text, f"forbidden substring '{forbidden}' leaked in response"

    for coeff_value in FORBIDDEN_COEFFICIENT_VALUES:
        assert coeff_value not in raw_text, f"forbidden coefficient value '{coeff_value}' leaked in response"

    _assert_no_forbidden_keys(body)

    if bonus is not None:
        assert set(bonus) == {
            "bonus",
            "detrazione_min",
            "detrazione_max",
            "rata_annua_min",
            "rata_annua_max",
            "disclaimer",
            "detrazione_lavori_min",
            "detrazione_lavori_max",
            "netto_min",
            "netto_max",
            "rata_annua_lavori_min",
            "rata_annua_lavori_max",
        }
        for dettaglio in bonus["bonus"]:
            assert set(dettaglio) == {
                "code",
                "nome",
                "descrizione",
                "base_min",
                "base_max",
                "aliquota_pct",
                "tetto_spesa_eur",
                "tetto_modalita",
                "tetto_raggiunto",
                "rate_annuali",
                "detrazione_min",
                "detrazione_max",
                "rata_annua_min",
                "rata_annua_max",
                "su_arredo",
            }


def test_confronto_finiture_non_leaka(client):
    """10-04: il confronto a finiture inferiori e' un DTO chiuso di 4 campi."""
    response = client.post(
        "/api/v1/stima",
        json={
            "citta": "Reggio Emilia",
            "mq": 85,
            "tipo": "totale",
            "risposte": {"livello_finiture": "alto"},
        },
    )
    assert response.status_code == 200
    body = response.json()
    conf = body["confronto_finiture"]
    assert conf is not None
    assert set(conf) == {"livello_code", "livello_nome", "totale_min", "totale_max"}
    _assert_no_forbidden_keys(body)
    raw_text = json.dumps({k: v for k, v in body.items() if k != "bonus"})
    for forbidden in FORBIDDEN_SUBSTRINGS:
        assert forbidden not in raw_text


# --- 09-05: GET/POST del dettaglio-pro (configuratore) ---------------------
#
# Il DTO generico (domande/opzioni/risposte) e' il punto piu' vicino agli
# effetti che il client vede. Il controllo e' sulle CHIAVI del JSON, non sul
# testo grezzo: le descrizioni delle voci del listino sono prosa libera e
# contengono legittimamente sottostringhe come "effettuato" — uno scan a
# sottostringa sul testo intero darebbe un falso positivo.
FORBIDDEN_KEY_SUBSTRINGS_CONFIGURATORE = [
    "effett",
    "coefficiente",
    "impresa",
    "tipo_effetto",
    "target_",
]


def _assert_no_forbidden_key_substrings(node) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            for forbidden in FORBIDDEN_KEY_SUBSTRINGS_CONFIGURATORE:
                assert forbidden not in key, f"forbidden substring '{forbidden}' found in key '{key}'"
            _assert_no_forbidden_key_substrings(value)
    elif isinstance(node, list):
        for item in node:
            _assert_no_forbidden_key_substrings(item)

REGISTRAZIONE_URL = "/api/v1/auth/registrati"
STIME_URL = "/api/v1/me/stime"
ATTIVA_PRO_URL = "/api/v1/me/pro/attiva"


def _stima_pro_payload() -> dict:
    return {
        "input": {"citta": "Reggio Emilia", "mq": 85, "tipo": "totale"},
        "fallback": False,
        "disclaimer": None,
        "valuta": "EUR",
        "categorie": [],
        "extra": [],
        "totale": {
            "imponibile_min": "10000.00",
            "imponibile_max": "15000.00",
            "iva_min": "1000.00",
            "iva_max": "1500.00",
            "totale_min": "11000.00",
            "totale_max": "16500.00",
        },
    }


@pytest.fixture()
def pro_client(monkeypatch, tmp_path):
    """Client dedicato con l'intero set di router puntato al DB di test —
    a differenza di `client()` sopra (che riusa `_seeded_db`, patchato solo su
    `stima_router`), qui serve anche auth/stime-salvate/dettaglio-pro/
    subscription, stesso pattern di `test_dettaglio_pro_paywall.py`."""
    from app.limiter import limiter

    limiter.reset()

    db_path = tmp_path / "test_no_leak_configuratore.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)

    with testing_session_local() as s:
        seed(s, load_seed_data())
        s.commit()

    monkeypatch.setattr(db_module, "SessionLocal", testing_session_local)

    import app.dependencies.auth as deps_auth_module
    import app.routers.auth as auth_router_module
    import app.routers.dettaglio_pro as dettaglio_pro_router_module
    import app.routers.stime_salvate as stime_salvate_router_module
    import app.routers.subscription as subscription_router_module

    monkeypatch.setattr(deps_auth_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(auth_router_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(dettaglio_pro_router_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(stime_salvate_router_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(subscription_router_module, "SessionLocal", testing_session_local)

    return TestClient(app)


def test_get_e_post_dettaglio_pro_non_leakano_effetti_ne_coefficienti(pro_client):
    """Estende l'anti-leak al configuratore Pro (09-05): il DTO
    `domande`/`opzioni` deve restare a campi chiusi (code/etichetta/
    descrizione/is_default/valore/valore_etichetta) — nessuna traccia degli
    effetti che hanno risolto quei valori."""
    pro_client.post(
        REGISTRAZIONE_URL,
        json={"email": "noleak.pro@example.com", "password": "Password123", "nome": "NoLeak"},
    )
    pro_client.post(ATTIVA_PRO_URL)
    stima_id = pro_client.post(STIME_URL, json=_stima_pro_payload()).json()["id"]

    get_response = pro_client.get(f"{STIME_URL}/{stima_id}/dettaglio-pro")
    assert get_response.status_code == 200

    post_response = pro_client.post(
        f"{STIME_URL}/{stima_id}/dettaglio-pro/risposte",
        json={"risposte": {"tipo_pavimento": "parquet", "bagni": 2}},
    )
    assert post_response.status_code == 200

    for response in (get_response, post_response):
        _assert_no_forbidden_keys(response.json())
        _assert_no_forbidden_key_substrings(response.json())


def test_opzioni_pro_non_leaka_effetti_ne_coefficienti(pro_client):
    """Estende l'anti-leak (09-11) a `GET /me/opzioni-pro`, che ora espone
    anche `domande` (le stesse del pannello, servite al wizard PRIMA che una
    stima esista): stesso DTO chiuso, stesso controllo."""
    pro_client.post(
        REGISTRAZIONE_URL,
        json={"email": "noleak.opzioni@example.com", "password": "Password123", "nome": "NoLeak2"},
    )
    pro_client.post(ATTIVA_PRO_URL)

    response = pro_client.get("/api/v1/me/opzioni-pro")

    assert response.status_code == 200
    _assert_no_forbidden_keys(response.json())
    _assert_no_forbidden_key_substrings(response.json())


def test_dettaglio_con_budget_e_patch_budget_non_leakano(pro_client):
    """10-05: GET dettaglio con budget/confronto e risposta PATCH budget sono
    DTO chiusi, senza chiavi ne' valori dell'area impresa."""
    pro_client.post(
        REGISTRAZIONE_URL,
        json={"email": "noleak.budget@example.com", "password": "Password123", "nome": "NoLeak3"},
    )
    payload = _stima_pro_payload()
    payload["budget_eur"] = 40000
    payload["confronto_finiture"] = {
        "livello_code": "medio",
        "livello_nome": "Medio",
        "totale_min": "9000.00",
        "totale_max": "14000.00",
    }
    stima_id = pro_client.post(STIME_URL, json=payload).json()["id"]

    get_response = pro_client.get(f"{STIME_URL}/{stima_id}")
    patch_response = pro_client.patch(f"{STIME_URL}/{stima_id}/budget", json={"budget_eur": 50000})

    assert get_response.status_code == 200
    assert patch_response.status_code == 200
    assert get_response.json()["budget_eur"] == 40000
    for response in (get_response, patch_response):
        _assert_no_forbidden_keys(response.json())
        raw_text = json.dumps(response.json())
        for forbidden in FORBIDDEN_SUBSTRINGS:
            assert forbidden not in raw_text


def test_dettaglio_pro_con_budget_e_confronto_non_leakano(pro_client):
    """10-06: riepilogo IVA, lettura categorie e confronto Pro (livelli "alto")
    sono DTO chiusi, senza chiavi ne' valori dell'area impresa."""
    pro_client.post(
        REGISTRAZIONE_URL,
        json={"email": "noleak.confrontopro@example.com", "password": "Password123", "nome": "NoLeak4"},
    )
    pro_client.post(ATTIVA_PRO_URL)
    payload = _stima_pro_payload()
    payload["budget_eur"] = 40000
    payload["preferenze_pro"] = {
        "livelli": {"B-FINITURE": "alto", "C-SERRAMENTI": "alto", "D-PRODOTTI": "alto"}
    }
    stima_id = pro_client.post(STIME_URL, json=payload).json()["id"]

    response = pro_client.get(f"{STIME_URL}/{stima_id}/dettaglio-pro")

    assert response.status_code == 200
    body = response.json()
    assert body["confronto_finiture"] is not None
    assert body["budget_eur"] == 40000
    _assert_no_forbidden_keys(body)
    _assert_no_forbidden_key_substrings(body)
    raw_text = json.dumps({k: v for k, v in body.items() if k != "bonus"})
    for forbidden in FORBIDDEN_SUBSTRINGS:
        assert forbidden not in raw_text
    # 10-14 (G6): il bonus del Pro e' escluso dallo scan testuale (le aliquote
    # collidono coi coefficienti) ma resta un DTO a chiavi chiuse.
    bonus = body["bonus"]
    assert bonus is not None
    assert set(bonus) == {
        "bonus", "detrazione_min", "detrazione_max", "rata_annua_min", "rata_annua_max",
        "disclaimer", "detrazione_lavori_min", "detrazione_lavori_max", "netto_min", "netto_max",
        "rata_annua_lavori_min", "rata_annua_lavori_max",
    }
    for dettaglio in bonus["bonus"]:
        assert set(dettaglio) == {
            "code", "nome", "descrizione", "base_min", "base_max", "aliquota_pct",
            "tetto_spesa_eur", "tetto_modalita", "tetto_raggiunto", "rate_annuali",
            "detrazione_min", "detrazione_max", "rata_annua_min", "rata_annua_max",
            "su_arredo",
        }
