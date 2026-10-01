"""E2E tests (RED, TDD) for the saved-estimate slice: POST/GET /me/stime,
GET /me/stime/{id}, over real cookie-jar HTTP calls (`TestClient`).

Covers AUTH-03 (02-07-PLAN.md <must_haves>): snapshot save (never
recomputed, D-09/Pitfall 5), per-user history list, immutable detail,
anti-IDOR (404 not 403, T-07-01), anti-leak of the impresa secret in the
saved snapshot (T-07-02), and 401 without a session (T-07-04).

Until `app/routers/stime_salvate.py` exists, `app.main` fails to include it
and these requests 404 on `/api/v1/me/stime` -> RED as expected.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import app.db as db_module
from app.db import Base
from app.limiter import limiter
from app.main import app
from tests.session_factory import sessione_di_test

REGISTRAZIONE_URL = "/api/v1/auth/registrati"
LOGOUT_URL = "/api/v1/auth/logout"
STIME_URL = "/api/v1/me/stime"

FORBIDDEN_SUBSTRINGS = [
    "base_eur_mq",
    "moltiplicatore",
    "coefficiente_impresa",
    "prezzo_impresa",
]

FORBIDDEN_KEYS = {
    "base_eur_mq",
    "moltiplicatore",
    "coefficiente_impresa",
    "prezzo_impresa",
}


def _stima_payload() -> dict:
    """A StimaResponse-shaped payload, as returned by POST /api/v1/stima."""
    return {
        "input": {"citta": "Reggio Emilia", "mq": 85, "tipo": "totale"},
        "fallback": False,
        "disclaimer": None,
        "valuta": "EUR",
        "categorie": [
            {
                "code": "edile",
                "nome": "Edile",
                "imponibile_min": "10000.00",
                "imponibile_max": "15000.00",
                "iva_pct": "0.10",
                "iva_min": "1000.00",
                "iva_max": "1500.00",
                "totale_min": "11000.00",
                "totale_max": "16500.00",
            },
            {
                "code": "finiture",
                "nome": "Finiture",
                "imponibile_min": "8000.00",
                "imponibile_max": "12000.00",
                "iva_pct": "0.22",
                "iva_min": "1760.00",
                "iva_max": "2640.00",
                "totale_min": "9760.00",
                "totale_max": "14640.00",
            },
            {
                "code": "serramenti",
                "nome": "Serramenti",
                "imponibile_min": "5000.00",
                "imponibile_max": "7000.00",
                "iva_pct": "0.10",
                "iva_min": "500.00",
                "iva_max": "700.00",
                "totale_min": "5500.00",
                "totale_max": "7700.00",
            },
            {
                "code": "prodotti",
                "nome": "Prodotti",
                "imponibile_min": "3000.00",
                "imponibile_max": "4500.00",
                "iva_pct": "0.10",
                "iva_min": "300.00",
                "iva_max": "450.00",
                "totale_min": "3300.00",
                "totale_max": "4950.00",
            },
        ],
        "extra": [
            {"code": "cse", "nome": "CSE/CSP", "importo": "1500.00", "iva_pct": "0.22"},
            {"code": "pratiche", "nome": "Pratiche", "importo": "800.00", "iva_pct": "0.22"},
        ],
        "totale": {
            "imponibile_min": "26000.00",
            "imponibile_max": "38500.00",
            "iva_min": "4120.00",
            "iva_max": "5850.00",
            "totale_min": "30120.00",
            "totale_max": "44350.00",
        },
    }


def _assert_no_forbidden_keys(node) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            assert key not in FORBIDDEN_KEYS, f"forbidden key '{key}' found in response"
            _assert_no_forbidden_keys(value)
    elif isinstance(node, list):
        for item in node:
            _assert_no_forbidden_keys(item)


@pytest.fixture()
def client(monkeypatch, tmp_path):
    # slowapi Limiter is a process-wide singleton (see 02-03-SUMMARY.md) —
    # reset it so /registrati's 5/minute cap doesn't leak between tests.
    limiter.reset()

    db_path = tmp_path / "test_stime_salvate.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)

    monkeypatch.setattr(db_module, "SessionLocal", testing_session_local)

    import app.dependencies.auth as deps_auth_module
    import app.routers.auth as auth_router_module

    monkeypatch.setattr(deps_auth_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(auth_router_module, "SessionLocal", testing_session_local)

    try:
        import app.routers.stime_salvate as stime_salvate_router_module

        if hasattr(stime_salvate_router_module, "SessionLocal"):
            monkeypatch.setattr(stime_salvate_router_module, "SessionLocal", testing_session_local)
    except ModuleNotFoundError:
        pass

    return TestClient(app)


def _registra(client, email="utente.a@example.com", password="Password123", nome="Utente A"):
    return client.post(REGISTRAZIONE_URL, json={"email": email, "password": password, "nome": nome})


class TestSalvaListaDettaglio:
    def test_post_stime_salva_e_ritorna_201_con_id(self, client):
        _registra(client)

        response = client.post(STIME_URL, json=_stima_payload())

        assert response.status_code == 201
        body = response.json()
        assert "id" in body

    def test_get_stime_lista_le_stime_utente(self, client):
        _registra(client)
        client.post(STIME_URL, json=_stima_payload())

        response = client.get(STIME_URL)

        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)
        assert len(body) == 1
        row = body[0]
        assert row["citta"] == "Reggio Emilia"
        assert row["mq"] == 85
        assert row["tipo"] == "totale"
        assert "created_at" in row
        assert row["totale_min"] is not None
        assert row["totale_max"] is not None

    def test_get_stima_dettaglio_ritorna_snapshot_completo(self, client):
        _registra(client)
        created = client.post(STIME_URL, json=_stima_payload())
        stima_id = created.json()["id"]

        response = client.get(f"{STIME_URL}/{stima_id}")

        assert response.status_code == 200
        body = response.json()
        assert body["input"]["citta"] == "Reggio Emilia"
        assert len(body["categorie"]) == 4
        assert body["totale"]["totale_min"] is not None
        assert body["totale"]["totale_max"] is not None

    def test_dettaglio_salvato_non_contiene_dati_impresa(self, client):
        _registra(client)
        created = client.post(STIME_URL, json=_stima_payload())
        stima_id = created.json()["id"]

        response = client.get(f"{STIME_URL}/{stima_id}")
        raw_text = response.text

        for forbidden in FORBIDDEN_SUBSTRINGS:
            assert forbidden not in raw_text, f"forbidden substring '{forbidden}' leaked in saved snapshot"

        _assert_no_forbidden_keys(response.json())


class TestAntiIdorEAntiSpoofing:
    def test_utente_b_non_puo_leggere_stima_di_utente_a(self, client):
        _registra(client, email="utente.a2@example.com")
        created = client.post(STIME_URL, json=_stima_payload())
        stima_id = created.json()["id"]
        client.post(LOGOUT_URL)

        _registra(client, email="utente.b@example.com")
        response = client.get(f"{STIME_URL}/{stima_id}")

        assert response.status_code == 404

    def test_post_stime_senza_sessione_ritorna_401(self, client):
        response = client.post(STIME_URL, json=_stima_payload())

        assert response.status_code == 401


def _arredo_payload() -> dict:
    return {
        "livello_code": "medio",
        "livello_nome": "Medio",
        "ambienti": [
            {"code": "cucina", "nome": "Cucina", "eur_min": "3000.00", "eur_max": "4500.00"},
            {"code": "bagno", "nome": "Bagno", "eur_min": "1500.00", "eur_max": "2200.00"},
        ],
        "totale_min": "4500.00",
        "totale_max": "6700.00",
        "disclaimer": "Stima indicativa dell'arredo, esclusa dal totale dei lavori.",
    }


class TestArredoNelloSnapshot:
    def test_post_con_arredo_lo_salva_nello_snapshot(self, client):
        from decimal import Decimal

        import app.db as db_module
        from app.models.stima_salvata import StimaSalvata

        _registra(client)
        payload = _stima_payload()
        payload["arredo"] = _arredo_payload()
        r = client.post(STIME_URL, json=payload)
        assert r.status_code == 201
        with db_module.SessionLocal() as s:
            riga = s.get(StimaSalvata, r.json()["id"])
            arredo = riga.risultato_json.get("arredo")
        assert arredo is not None
        assert Decimal(str(arredo["totale_min"])) == Decimal("4500.00")
        assert Decimal(str(arredo["totale_max"])) == Decimal("6700.00")

    def test_get_restituisce_l_arredo(self, client):
        from decimal import Decimal

        _registra(client)
        payload = _stima_payload()
        payload["arredo"] = _arredo_payload()
        sid = client.post(STIME_URL, json=payload).json()["id"]
        r = client.get(f"{STIME_URL}/{sid}")
        assert r.status_code == 200
        body = r.json()
        assert body["arredo"] is not None
        assert body["arredo"]["livello_nome"] == "Medio"
        assert [a["code"] for a in body["arredo"]["ambienti"]] == ["cucina", "bagno"]
        assert Decimal(body["arredo"]["totale_min"]) == Decimal("4500.00")
        assert Decimal(body["arredo"]["totale_max"]) == Decimal("6700.00")
        for vietata in FORBIDDEN_SUBSTRINGS:
            assert vietata not in r.text
        _assert_no_forbidden_keys(body)

    def test_bonus_con_su_arredo_e_rata_lavori_round_trip(self, client):
        _registra(client)
        voce = {
            "code": "MOBILI",
            "nome": "Bonus Mobili",
            "descrizione": None,
            "base_min": "4500.00",
            "base_max": "6700.00",
            "aliquota_pct": "0.50",
            "tetto_spesa_eur": None,
            "tetto_modalita": None,
            "tetto_raggiunto": False,
            "rate_annuali": 10,
            "detrazione_min": "2250.00",
            "detrazione_max": "3350.00",
            "rata_annua_min": "225.00",
            "rata_annua_max": "335.00",
            "su_arredo": True,
        }
        payload = _stima_payload()
        payload["arredo"] = _arredo_payload()
        payload["bonus"] = {
            "bonus": [voce],
            "detrazione_min": "2250.00",
            "detrazione_max": "3350.00",
            "rata_annua_min": "225.00",
            "rata_annua_max": "335.00",
            "disclaimer": "d",
            "detrazione_lavori_min": "0",
            "detrazione_lavori_max": "0",
            "netto_min": "100.00",
            "netto_max": "200.00",
            "rata_annua_lavori_min": "0",
            "rata_annua_lavori_max": "0",
        }
        r = client.post(STIME_URL, json=payload)
        assert r.status_code == 201
        body = client.get(f"{STIME_URL}/{r.json()['id']}").json()
        assert body["bonus"]["bonus"][0]["su_arredo"] is True
        assert body["bonus"]["rata_annua_lavori_min"] is not None
        assert body["bonus"]["rata_annua_lavori_max"] is not None

    def test_post_senza_arredo_da_arredo_null(self, client):
        _registra(client)
        sid = client.post(STIME_URL, json=_stima_payload()).json()["id"]
        body = client.get(f"{STIME_URL}/{sid}").json()
        assert "arredo" in body and body["arredo"] is None

    def test_snapshot_vecchio_senza_chiave_arredo_si_apre(self, client):
        import app.db as db_module
        from app.models.stima_salvata import StimaSalvata

        _registra(client)
        sid = client.post(STIME_URL, json=_stima_payload()).json()["id"]
        with db_module.SessionLocal() as s:
            riga = s.get(StimaSalvata, sid)
            snap = dict(riga.risultato_json)
            snap.pop("arredo", None)
            snap["schema_version"] = 2
            riga.risultato_json = snap
            s.commit()
        r = client.get(f"{STIME_URL}/{sid}")
        assert r.status_code == 200
        assert r.json()["arredo"] is None


def _stima_modificata() -> dict:
    """Come `_stima_payload()` ma con mq e totale diversi (esito di una Modifica)."""
    p = _stima_payload()
    p["input"]["mq"] = 120
    p["totale"]["totale_min"] = "41000.00"
    p["totale"]["totale_max"] = "59000.00"
    return p


class TestAggiornaStima:
    """G14: PUT /me/stime/{id} sostituisce lo snapshot della propria stima."""

    def _crea(self, client, payload=None) -> int:
        _registra(client)
        return client.post(STIME_URL, json=payload or _stima_payload()).json()["id"]

    def test_put_stessa_id_nuovo_snapshot(self, client):
        sid = self._crea(client)
        created_at = client.get(f"{STIME_URL}/{sid}").json()["created_at"]

        r = client.put(f"{STIME_URL}/{sid}", json=_stima_modificata())

        assert r.status_code == 200
        assert r.json()["id"] == sid
        body = client.get(f"{STIME_URL}/{sid}").json()
        assert body["created_at"] == created_at
        assert body["input"]["mq"] == 120
        assert body["totale"]["totale_max"] == "59000.00"

    def test_lista_ha_una_sola_stima_con_valori_nuovi(self, client):
        sid = self._crea(client)
        client.put(f"{STIME_URL}/{sid}", json=_stima_modificata())

        lista = client.get(STIME_URL).json()

        assert len(lista) == 1
        assert lista[0]["id"] == sid
        assert lista[0]["mq"] == 120
        assert float(lista[0]["totale_max"]) == 59000.0

    def test_snapshot_senza_preferenze_ne_budget_e_con_schema_version(self, client):
        from app.models.stima_salvata import StimaSalvata
        from app.routers.stime_salvate import SCHEMA_VERSION

        sid = self._crea(client)
        payload = _stima_modificata()
        payload["budget_eur"] = 50000
        payload["preferenze_pro"] = {"livelli": None}
        client.put(f"{STIME_URL}/{sid}", json=payload)

        with db_module.SessionLocal() as s:
            snap = s.get(StimaSalvata, sid).risultato_json
        assert "preferenze_pro" not in snap
        assert "budget_eur" not in snap
        assert snap["schema_version"] == SCHEMA_VERSION

    def test_budget_aggiornato_e_azzerato(self, client):
        sid = self._crea(client)
        p = _stima_modificata()
        p["budget_eur"] = 70000
        client.put(f"{STIME_URL}/{sid}", json=p)
        assert client.get(f"{STIME_URL}/{sid}").json()["budget_eur"] == 70000

        client.put(f"{STIME_URL}/{sid}", json=_stima_modificata())
        assert client.get(f"{STIME_URL}/{sid}").json()["budget_eur"] is None

    def test_senza_preferenze_pro_le_colonne_restano(self, client):
        from app.models.stima_salvata import StimaSalvata

        sid = self._crea(client)
        with db_module.SessionLocal() as s:
            riga = s.get(StimaSalvata, sid)
            riga.livelli_pro_json = {"finiture": "alto"}
            riga.risposte_pro_json = {"bagni": 2}
            s.commit()

        r = client.put(f"{STIME_URL}/{sid}", json=_stima_modificata())

        assert r.status_code == 200
        with db_module.SessionLocal() as s:
            riga = s.get(StimaSalvata, sid)
            assert riga.livelli_pro_json == {"finiture": "alto"}
            assert riga.risposte_pro_json == {"bagni": 2}

    def test_livelli_non_validi_400_e_riga_invariata(self, client):
        sid = self._crea(client)
        p = _stima_modificata()
        p["preferenze_pro"] = {"livelli": {"categoria-inesistente": "x"}}

        r = client.put(f"{STIME_URL}/{sid}", json=p)

        assert r.status_code == 400
        assert client.get(f"{STIME_URL}/{sid}").json()["input"]["mq"] == 85

    def test_arredo_aggiunto_e_tolto(self, client):
        sid = self._crea(client)
        p = _stima_modificata()
        p["arredo"] = _arredo_payload()
        client.put(f"{STIME_URL}/{sid}", json=p)
        assert client.get(f"{STIME_URL}/{sid}").json()["arredo"]["livello_code"] == "medio"

        client.put(f"{STIME_URL}/{sid}", json=_stima_modificata())
        assert client.get(f"{STIME_URL}/{sid}").json()["arredo"] is None

    def test_snapshot_vecchio_viene_riscritto_nella_forma_nuova(self, client):
        from app.models.stima_salvata import StimaSalvata

        sid = self._crea(client)
        with db_module.SessionLocal() as s:
            riga = s.get(StimaSalvata, sid)
            snap = dict(riga.risultato_json)
            snap.pop("arredo", None)
            snap.pop("bonus", None)
            riga.risultato_json = snap
            s.commit()

        r = client.put(f"{STIME_URL}/{sid}", json=_stima_modificata())

        assert r.status_code == 200
        body = client.get(f"{STIME_URL}/{sid}").json()
        assert body["input"]["mq"] == 120
        assert "arredo" in body and "bonus" in body

    def test_utente_b_riceve_404_e_la_stima_di_a_non_cambia(self, client):
        sid = self._crea(client)
        client.post(LOGOUT_URL)
        _registra(client, email="utente.b@example.com", nome="B")

        r = client.put(f"{STIME_URL}/{sid}", json=_stima_modificata())

        assert r.status_code == 404
        client.post(LOGOUT_URL)
        client.post("/api/v1/auth/login", json={"email": "utente.a@example.com", "password": "Password123"})
        assert client.get(f"{STIME_URL}/{sid}").json()["input"]["mq"] == 85

    def test_id_inesistente_404(self, client):
        _registra(client)
        assert client.put(f"{STIME_URL}/99999", json=_stima_modificata()).status_code == 404

    def test_senza_sessione_401(self, client):
        sid = self._crea(client)
        client.post(LOGOUT_URL)
        assert client.put(f"{STIME_URL}/{sid}", json=_stima_modificata()).status_code == 401

    def test_payload_non_valido_422_e_riga_invariata(self, client):
        sid = self._crea(client)
        p = _stima_modificata()
        del p["totale"]

        assert client.put(f"{STIME_URL}/{sid}", json=p).status_code == 422
        assert client.get(f"{STIME_URL}/{sid}").json()["input"]["mq"] == 85

    @pytest.mark.parametrize(
        ("campo", "valore"),
        [("mq", 0), ("mq", -10), ("mq", 2001), ("mq", 2**31), ("citta", ""), ("citta", "x" * 101)],
    )
    def test_input_fuori_dai_vincoli_di_stima_request_422(self, client, campo, valore):
        """WR-06: citta/mq pilotano il ricalcolo Pro, quindi in ingresso valgono
        gli stessi vincoli di POST /stima. La riga resta invariata."""
        sid = self._crea(client)
        p = _stima_modificata()
        p["input"][campo] = valore

        assert client.put(f"{STIME_URL}/{sid}", json=p).status_code == 422
        assert client.get(f"{STIME_URL}/{sid}").json()["input"]["mq"] == 85

    def test_post_con_mq_fuori_dai_vincoli_422(self, client):
        _registra(client)
        p = _stima_payload()
        p["input"]["mq"] = 0
        assert client.post(STIME_URL, json=p).status_code == 422

    def test_nessun_dato_impresa_nelle_risposte(self, client):
        sid = self._crea(client)
        put = client.put(f"{STIME_URL}/{sid}", json=_stima_modificata())
        get = client.get(f"{STIME_URL}/{sid}")
        for r in (put, get):
            for forbidden in FORBIDDEN_SUBSTRINGS:
                assert forbidden not in r.text
        _assert_no_forbidden_keys(get.json())
