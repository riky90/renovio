"""Confronto a finiture inferiori in POST /stima (10-04, D-07/D-08/D-09)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import app.db as db_module
from app.db import Base
from app.main import app
from scripts.seed import load_seed_data, seed
from tests.computo_spento import catalogo_v2
from tests.session_factory import sessione_di_test


@pytest.fixture(autouse=True, scope="module")
def _seeded_db(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db") / "test_confronto.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)
    with testing_session_local() as s:
        seed(s, load_seed_data())
        # Numeri del percorso EUR/m2 + effetti (catalogo v2): tests/computo_spento.py
        catalogo_v2(s)
        s.commit()

    original = db_module.SessionLocal
    db_module.SessionLocal = testing_session_local
    import app.routers.stima as stima_router

    stima_router.SessionLocal = testing_session_local
    yield
    db_module.SessionLocal = original
    stima_router.SessionLocal = original


@pytest.fixture()
def client():
    from app.limiter import limiter

    # Il test parametrico G3 fa centinaia di POST: il rate limit non e' l'oggetto.
    abilitato = limiter.enabled
    limiter.enabled = False
    yield TestClient(app)
    limiter.enabled = abilitato


def _post(client, risposte=None):
    body = {"citta": "Reggio Emilia", "mq": 85, "tipo": "totale"}
    if risposte is not None:
        body["risposte"] = risposte
    r = client.post("/api/v1/stima", json=body)
    assert r.status_code == 200
    return r.json()


def test_alto_confronta_con_medio(client):
    body = _post(client, {"livello_finiture": "alto"})
    conf = body["confronto_finiture"]
    assert conf is not None
    assert conf["livello_code"] == "medio"
    assert conf["livello_nome"] == "Medie"
    assert float(conf["totale_max"]) < float(body["totale"]["totale_max"])
    assert float(conf["totale_min"]) < float(body["totale"]["totale_min"])
    assert body["finiture_al_minimo"] is False


def test_confronto_e_ricalcolo_vero(client):
    alto = _post(client, {"livello_finiture": "alto"})
    medio = _post(client, {"livello_finiture": "medio"})
    assert float(alto["confronto_finiture"]["totale_min"]) == float(medio["totale"]["totale_min"])
    assert float(alto["confronto_finiture"]["totale_max"]) == float(medio["totale"]["totale_max"])


def test_medio_confronta_con_base(client):
    body = _post(client, {"livello_finiture": "medio"})
    assert body["confronto_finiture"]["livello_code"] == "base"


def test_base_al_minimo(client):
    body = _post(client, {"livello_finiture": "base"})
    assert body["confronto_finiture"] is None
    assert body["finiture_al_minimo"] is True


def test_risposte_assenti_oracolo_intatto(client):
    body = _post(client)
    assert body["confronto_finiture"] is None
    assert body["finiture_al_minimo"] is False
    assert float(body["totale"]["totale_min"]) == 52807
    assert float(body["totale"]["totale_max"]) == 66696


def test_arredo_non_entra_nel_confronto(client):
    senza = _post(client, {"livello_finiture": "alto"})
    con = _post(client, {"livello_finiture": "alto", "ambienti_arredo": ["cucina"]})
    assert con["confronto_finiture"] == senza["confronto_finiture"]


def test_codice_sconosciuto_nessun_confronto(client):
    body = _post(client, {"livello_finiture": "inesistente"})
    assert body["confronto_finiture"] is None
    assert body["finiture_al_minimo"] is False


# --- G3 (10-11): il confronto deve coincidere con una stima fresca -----------


def _default_catalogo(client, mq):
    """Catalogo Free e risposte di default, come le estrae il client."""
    r = client.get(f"/api/v1/domande?tier=free&mq={mq}")
    assert r.status_code == 200
    domande = r.json()["domande"]
    base = {}
    for d in domande:
        v = d["valore_default"]
        if v is None:
            continue
        base[d["code"]] = float(v) if d["tipo_controllo"] in ("stepper", "numero") else v
    return domande, base


def _varianti(domande, base):
    """Insiemi di risposte non di default, una domanda alla volta."""
    out = [dict(base)]
    for d in domande:
        code, tipo = d["code"], d["tipo_controllo"]
        opz = [o["code"] for o in d["opzioni"]]
        if code == "livello_finiture":
            continue
        if tipo == "scelta_singola":
            for o in opz:
                out.append({**base, code: o})
        elif tipo == "scelta_multipla" and opz:
            out.append({**base, code: opz})
        elif tipo in ("stepper", "numero") and base.get(code) is not None:
            for inc in (1,):
                out.append({**base, code: base[code] + inc})
    for code in ("muri_lavori", "efficientamento"):
        out.append({**base, code: "si"})
    return out


@pytest.mark.parametrize("tipo", ["leggera", "moderata", "totale"])
@pytest.mark.parametrize("mq", [85, 140, 300])
def test_confronto_coincide_con_stima_fresca(client, tipo, mq):
    domande, base = _default_catalogo(client, mq)
    for risposte in _varianti(domande, base):
        risposte = {**risposte, "livello_finiture": "alto"}
        body = {"citta": "Reggio Emilia", "mq": mq, "tipo": tipo, "risposte": risposte}
        r = client.post("/api/v1/stima", json=body)
        assert r.status_code == 200, (risposte, r.text)
        conf = r.json()["confronto_finiture"]
        if conf is None:
            continue
        fresca = client.post(
            "/api/v1/stima",
            json={**body, "risposte": {**risposte, "livello_finiture": conf["livello_code"]}},
        ).json()["totale"]
        assert float(conf["totale_min"]) == float(fresca["totale_min"]), risposte
        assert float(conf["totale_max"]) == float(fresca["totale_max"]), risposte
