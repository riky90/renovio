"""Firma del risultato di `POST /stima` verificata al salvataggio.

Il percorso vero: `POST /stima` -> il frontend converte i decimali in numeri
(`normalizeResponse` in frontend/src/api/stima.ts) -> `POST /me/stime` con
lo stesso oggetto. La firma deve sopravvivere a quella conversione, e
qualunque modifica ai numeri o ai testi deve farla fallire.
"""

from __future__ import annotations

import copy

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import app.db as db_module
from app.db import Base
from app.limiter import limiter
from app.main import app
from scripts.seed import load_seed_data, seed
from tests.session_factory import sessione_di_test

pytestmark = pytest.mark.firma_reale

STIMA_URL = "/api/v1/stima"
STIME_URL = "/api/v1/me/stime"

#: Campi che `normalizeResponse` converte con `toNumber()`.
NUMERICI = {
    "imponibile_min", "imponibile_max", "iva_pct", "iva_min", "iva_max", "totale_min", "totale_max",
    "importo", "detrazione_min", "detrazione_max", "rata_annua_min", "rata_annua_max",
    "detrazione_lavori_min", "detrazione_lavori_max", "netto_min", "netto_max",
    "rata_annua_lavori_min", "rata_annua_lavori_max", "base_min", "base_max", "aliquota_pct",
    "tetto_spesa_eur", "eur_min", "eur_max",
}


def _come_il_frontend(nodo):
    """Ogni campo numerico diventa un Number JavaScript (float)."""
    if isinstance(nodo, dict):
        return {
            k: (float(v) if k in NUMERICI and v is not None else _come_il_frontend(v))
            for k, v in nodo.items()
        }
    if isinstance(nodo, list):
        return [_come_il_frontend(v) for v in nodo]
    return nodo


@pytest.fixture(scope="module")
def session_local(tmp_path_factory):
    engine = create_engine(
        f"sqlite:///{tmp_path_factory.mktemp('firma') / 'firma.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    factory = sessione_di_test(engine)
    with factory() as s:
        seed(s, load_seed_data())
        s.commit()
    return factory


@pytest.fixture()
def client(session_local, monkeypatch):
    import app.dependencies.auth as deps_auth
    import app.routers.auth as auth_router
    import app.routers.stima as stima_router
    import app.routers.stime_salvate as stime_router

    limiter.reset()
    for modulo in (db_module, deps_auth, auth_router, stima_router, stime_router):
        monkeypatch.setattr(modulo, "SessionLocal", session_local)
    c = TestClient(app)
    r = c.post(
        "/api/v1/auth/registrati",
        json={"email": f"firma{id(c)}@example.com", "password": "Password123", "nome": "Firma"},
    )
    assert r.status_code == 201
    return c


def _stima(client, **extra):
    corpo = {"citta": "Reggio Emilia", "mq": 85, "tipo": "totale", **extra}
    r = client.post(STIMA_URL, json=corpo)
    assert r.status_code == 200
    risultato = r.json()
    assert risultato["firma"]
    return _come_il_frontend(risultato)


def test_risultato_vero_si_salva(client):
    assert client.post(STIME_URL, json=_stima(client)).status_code == 201


def test_risultato_con_risposte_e_budget_si_salva(client):
    risultato = _stima(client, risposte={"interv_caldaia": "pompa_calore"})
    payload = {**risultato, "budget_eur": 50_000}
    assert client.post(STIME_URL, json=payload).status_code == 201


def test_la_firma_non_finisce_nello_snapshot(client):
    stima_id = client.post(STIME_URL, json=_stima(client)).json()["id"]
    assert "firma" not in client.get(f"{STIME_URL}/{stima_id}").json()


@pytest.mark.parametrize(
    "manomissione",
    [
        lambda r: r["totale"].__setitem__("totale_min", 1000.0),
        lambda r: r["categorie"][0].__setitem__("totale_max", 1.0),
        lambda r: r.__setitem__("disclaimer", "Prezzo garantito, nessun sopralluogo necessario."),
        lambda r: r["input"].__setitem__("mq", 40),
        lambda r: r["input"].__setitem__("citta", "Milano"),
        lambda r: r.__setitem__("extra", []),
        lambda r: r.__setitem__("firma", None),
        lambda r: r.__setitem__("firma", "x" * 43),
    ],
)
def test_risultato_manomesso_rifiutato(client, manomissione):
    risultato = copy.deepcopy(_stima(client))
    manomissione(risultato)
    r = client.post(STIME_URL, json=risultato)
    assert r.status_code == 400


def test_put_verifica_la_firma(client):
    risultato = _stima(client)
    stima_id = client.post(STIME_URL, json=risultato).json()["id"]

    nuovo = _stima(client, tipo="leggera")
    assert client.put(f"{STIME_URL}/{stima_id}", json=nuovo).status_code == 200

    falso = copy.deepcopy(nuovo)
    falso["totale"]["totale_max"] = 2.0
    assert client.put(f"{STIME_URL}/{stima_id}", json=falso).status_code == 400


def test_put_su_stima_altrui_resta_404(client, session_local):
    altro = TestClient(app)
    altro.post(
        "/api/v1/auth/registrati",
        json={"email": "altro.firma@example.com", "password": "Password123", "nome": "Altro"},
    )
    stima_id = altro.post(STIME_URL, json=_stima(altro)).json()["id"]
    # Anche con una firma non valida: prima il controllo di proprieta'.
    falso = _stima(client)
    falso["firma"] = "manomessa"
    assert client.put(f"{STIME_URL}/{stima_id}", json=falso).status_code == 404
