"""E2E per /api/v1/admin/domande (0014): CRUD del catalogo + anteprima.

Il test che vale piu' degli altri e' `TestAnteprima`: l'anteprima e' una delle
tre mitigazioni decise contro il marcire di un motore a regole (insieme chiuso
di sette effetti, anteprima, export Excel), e serve a tarare ~50 coefficienti
guardando cosa fanno invece che sperando. Se si rompe, la curatela torna a
essere a occhio.

Copre anche: 403 per non-admin su ogni route; la validazione degli effetti
tradotta in 400 leggibili invece che in un 500; il default come radio button
(impostarne uno spegne gli altri); e l'assenza di qualunque campo impresa.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db as db_module
from app.config import settings
from app.db import Base
from app.limiter import limiter
from app.main import app
from scripts.seed import load_seed_data, seed

REGISTRAZIONE_URL = "/api/v1/auth/registrati"
URL = "/api/v1/admin/domande"

ADMIN_EMAIL = "admin.domande@example.com"


@pytest.fixture()
def client(monkeypatch, tmp_path):
    limiter.reset()
    monkeypatch.setattr(settings, "ADMIN_EMAIL", ADMIN_EMAIL)

    db_path = tmp_path / "test_admin_domande.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine)

    with testing_session_local() as s:
        seed(s, load_seed_data())

    monkeypatch.setattr(db_module, "SessionLocal", testing_session_local)

    import app.dependencies.auth as deps_auth_module
    import app.routers.auth as auth_router_module
    import app.routers.stima as stima_router_module

    monkeypatch.setattr(deps_auth_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(auth_router_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(stima_router_module, "SessionLocal", testing_session_local)

    return TestClient(app)


def _admin(client):
    client.post(
        REGISTRAZIONE_URL,
        json={"email": ADMIN_EMAIL, "password": "Password123", "nome": "Admin Domande"},
    )
    return client


def _utente(client):
    client.post(
        REGISTRAZIONE_URL,
        json={
            "email": "utente.domande@example.com",
            "password": "Password123",
            "nome": "Utente",
        },
    )
    return client


class TestGuard:
    @pytest.mark.parametrize(
        "metodo,path",
        [
            ("get", ""),
            ("get", "/opzioni"),
            ("get", "/effetti"),
            ("get", "/attese"),
            ("post", "/anteprima"),
        ],
    )
    def test_403_per_non_admin(self, client, metodo, path):
        _utente(client)
        risposta = getattr(client, metodo)(
            f"{URL}{path}",
            **({"json": {"citta": "Reggio Emilia", "mq": 85, "tipo": "totale"}} if metodo == "post" else {}),
        )
        assert risposta.status_code == 403

    def test_401_per_anonimo(self, client):
        assert client.get(URL).status_code == 401


class TestCrud:
    def test_lista_domande_restituisce_il_catalogo_seminato(self, client):
        _admin(client)
        risposta = client.get(URL)

        assert risposta.status_code == 200
        codici = {d["code"] for d in risposta.json()}
        assert {"anno_costruzione", "bagni", "impianti", "livello_finiture"} <= codici

    def test_crea_domanda_e_upsert_per_code(self, client):
        _admin(client)
        payload = {
            "code": "prova",
            "testo": "Domanda di prova",
            "tipo_controllo": "scelta_singola",
            "gruppo": "prova",
            "ordine": 999,
        }
        assert client.post(URL, json=payload).status_code == 201

        payload["testo"] = "Domanda di prova, rivista"
        seconda = client.post(URL, json=payload)
        assert seconda.status_code == 201
        assert seconda.json()["testo"] == "Domanda di prova, rivista"

        codici = [d["code"] for d in client.get(URL).json()]
        assert codici.count("prova") == 1

    def test_controllo_sconosciuto_e_400_non_500(self, client):
        _admin(client)
        risposta = client.post(
            URL,
            json={"code": "x", "testo": "T", "tipo_controllo": "slider_magico"},
        )
        assert risposta.status_code == 400
        assert "Controllo sconosciuto" in risposta.json()["detail"]

    def test_patch_non_tocca_i_campi_omessi(self, client):
        _admin(client)
        prima = next(d for d in client.get(URL).json() if d["code"] == "bagni")

        risposta = client.patch(f"{URL}/bagni", json={"ordine": 42})

        assert risposta.status_code == 200
        dopo = risposta.json()
        assert dopo["ordine"] == 42
        assert dopo["testo"] == prima["testo"]
        assert dopo["attributo_code"] == prima["attributo_code"]

    def test_delete_domanda_porta_via_opzioni_ed_effetti(self, client):
        _admin(client)
        opzioni_prima = client.get(f"{URL}/opzioni", params={"domanda_code": "anno_costruzione"}).json()
        effetti_prima = client.get(f"{URL}/effetti", params={"domanda_code": "anno_costruzione"}).json()
        assert opzioni_prima and effetti_prima

        assert client.delete(f"{URL}/anno_costruzione").status_code == 204

        assert client.get(f"{URL}/opzioni", params={"domanda_code": "anno_costruzione"}).json() == []
        assert client.get(f"{URL}/effetti", params={"domanda_code": "anno_costruzione"}).json() == []

    def test_delete_404_su_domanda_inesistente(self, client):
        _admin(client)
        assert client.delete(f"{URL}/non-esiste").status_code == 404


class TestDefaultComeRadioButton:
    def test_impostare_un_default_spegne_gli_altri(self, client):
        _admin(client)
        opzioni = client.get(f"{URL}/opzioni", params={"domanda_code": "anno_costruzione"}).json()
        non_default = next(o for o in opzioni if not o["is_default"])

        assert client.patch(f"{URL}/opzioni/{non_default['id']}", json={"is_default": True}).status_code == 200

        dopo = client.get(f"{URL}/opzioni", params={"domanda_code": "anno_costruzione"}).json()
        assert sum(1 for o in dopo if o["is_default"]) == 1
        assert next(o for o in dopo if o["is_default"])["id"] == non_default["id"]


class TestEffetti:
    def test_crea_effetto_valido(self, client):
        _admin(client)
        opzione = client.get(f"{URL}/opzioni", params={"domanda_code": "anno_costruzione"}).json()[0]

        risposta = client.post(
            f"{URL}/effetti",
            json={
                "opzione_id": opzione["id"],
                "tipo_effetto": "eur_mq_categoria",
                "target_categoria_code": "B-FINITURE",
                "valore": "12.5",
            },
        )

        assert risposta.status_code == 201
        assert risposta.json()["domanda_code"] == "anno_costruzione"

    @pytest.mark.parametrize(
        "corpo,atteso",
        [
            ({"tipo_effetto": "inventato", "target_categoria_code": "A-EDILE", "valore": "1"}, "sconosciuto"),
            ({"tipo_effetto": "escludi"}, "esattamente un bersaglio"),
            ({"tipo_effetto": "eur_mq_categoria", "target_categoria_code": "A-EDILE"}, "richiede un valore"),
            (
                {"tipo_effetto": "moltiplicatore_categoria", "target_categoria_code": "A-EDILE", "valore": "-2"},
                "negativo",
            ),
            (
                {"tipo_effetto": "quantita_per_unita", "target_categoria_code": "A-EDILE", "valore": "1"},
                "non puo' puntare",
            ),
        ],
    )
    def test_effetto_incoerente_e_400_leggibile(self, client, corpo, atteso):
        _admin(client)
        opzione = client.get(f"{URL}/opzioni", params={"domanda_code": "anno_costruzione"}).json()[0]

        risposta = client.post(f"{URL}/effetti", json={"opzione_id": opzione["id"], **corpo})

        assert risposta.status_code == 400
        assert atteso in risposta.json()["detail"]

    def test_patch_valore_negativo_su_moltiplicatore_rifiutato(self, client):
        _admin(client)
        effetto = next(
            e
            for e in client.get(f"{URL}/effetti", params={"domanda_code": "anno_costruzione"}).json()
            if e["tipo_effetto"] == "moltiplicatore_categoria"
        )

        risposta = client.patch(f"{URL}/effetti/{effetto['id']}", json={"valore": "-1"})

        assert risposta.status_code == 400
        # e il valore in tabella non e' cambiato
        dopo = next(
            e for e in client.get(f"{URL}/effetti").json() if e["id"] == effetto["id"]
        )
        assert dopo["valore"] == effetto["valore"]


class TestAttese:
    def test_lista_e_patch(self, client):
        _admin(client)
        attesa = next(a for a in client.get(f"{URL}/attese").json() if a["attributo_code"] == "bagni")

        risposta = client.patch(f"{URL}/attese/{attesa['id']}", json={"valore_atteso": "2"})

        assert risposta.status_code == 200
        assert risposta.json()["valore_atteso"] == "2.00"

    def test_fascia_invertita_rifiutata(self, client):
        _admin(client)
        risposta = client.post(
            f"{URL}/attese",
            json={
                "attributo_code": "prova",
                "fascia_mq_min": 200,
                "fascia_mq_max": 100,
                "valore_atteso": "1",
            },
        )
        assert risposta.status_code == 400


class TestAnteprima:
    def test_senza_risposte_il_delta_e_zero(self, client):
        """Se qui esce un delta, qualcuno ha messo effetti su un'opzione di
        default e tutte le stime stanno cambiando valore in silenzio."""
        _admin(client)
        risposta = client.post(
            f"{URL}/anteprima",
            json={"citta": "Reggio Emilia", "mq": 85, "tipo": "totale"},
        )

        assert risposta.status_code == 200
        corpo = risposta.json()
        assert corpo["base_totale_min"] == "47985"
        assert corpo["delta_min"] == "0"
        assert corpo["delta_max"] == "0"
        assert corpo["avvisi"] == []

    def test_mostra_quali_effetti_hanno_sparato_e_con_che_numeri(self, client):
        _admin(client)
        risposta = client.post(
            f"{URL}/anteprima",
            json={
                "citta": "Reggio Emilia",
                "mq": 85,
                "tipo": "totale",
                "risposte": {"bagni": 3, "anno_costruzione": "pre_1980"},
            },
        )

        assert risposta.status_code == 200
        corpo = risposta.json()
        assert corpo["delta_min"] != "0"

        bagni = [e for e in corpo["effetti"] if e["domanda_code"] == "bagni" and e["applicato"]]
        assert bagni
        # 3 risposti contro 1 atteso: lo scostamento porta i decimali
        # dell'attesa (Numeric(10,2)), quindi "2.00" e non "2".
        assert all(Decimal(e["unita"]) == Decimal("2") for e in bagni)

        anno = next(e for e in corpo["effetti"] if e["domanda_code"] == "anno_costruzione")
        assert anno["tipo_effetto"] == "moltiplicatore_categoria"
        assert anno["categoria_code"] == "A-EDILE"

        assert corpo["attese"]["bagni"] == "1.00"

    def test_riporta_il_delta_per_categoria(self, client):
        _admin(client)
        corpo = client.post(
            f"{URL}/anteprima",
            json={
                "citta": "Reggio Emilia",
                "mq": 85,
                "tipo": "totale",
                "risposte": {"non_rifare": ["serramenti"]},
            },
        ).json()

        c = next(x for x in corpo["categorie"] if x["code"] == "C-SERRAMENTI")
        assert c["totale_min"] == "0"
        assert c["delta_min"] == "-7466"

    def test_avvisa_quando_un_default_porta_effetti(self, client):
        """Si sporca deliberatamente la curatela e si verifica che l'anteprima
        lo dica, invece di lasciarlo scoprire dal conto che non torna."""
        _admin(client)
        default = next(
            o
            for o in client.get(f"{URL}/opzioni", params={"domanda_code": "anno_costruzione"}).json()
            if o["is_default"]
        )
        client.post(
            f"{URL}/effetti",
            json={
                "opzione_id": default["id"],
                "tipo_effetto": "moltiplicatore_categoria",
                "target_categoria_code": "A-EDILE",
                "valore": "1.5",
            },
        )

        corpo = client.post(
            f"{URL}/anteprima",
            json={"citta": "Reggio Emilia", "mq": 85, "tipo": "totale"},
        ).json()

        assert corpo["avvisi"]
        assert "default" in corpo["avvisi"][0]

    def test_segnala_una_baseline_mancante(self, client):
        _admin(client)
        for attesa in client.get(f"{URL}/attese").json():
            if attesa["attributo_code"] == "bagni":
                client.delete(f"{URL}/attese/{attesa['id']}")

        corpo = client.post(
            f"{URL}/anteprima",
            json={
                "citta": "Reggio Emilia",
                "mq": 85,
                "tipo": "totale",
                "risposte": {"bagni": 3},
            },
        ).json()

        assert corpo["delta_min"] == "0"
        assert any("attesa" in a.lower() for a in corpo["avvisi"])

    def test_citta_senza_listino_segnala_il_fallback(self, client):
        _admin(client)
        corpo = client.post(
            f"{URL}/anteprima",
            json={"citta": "Modena", "mq": 85, "tipo": "totale"},
        ).json()

        assert corpo["fallback"] is True


class TestAntiLeak:
    @pytest.mark.parametrize("path", ["", "/opzioni", "/effetti", "/attese"])
    def test_nessun_campo_impresa_in_lista(self, client, path):
        _admin(client)
        grezzo = client.get(f"{URL}{path}").text.lower()
        for vietata in ("coefficiente_impresa", "prezzo_impresa", "margine"):
            assert vietata not in grezzo

    def test_nessun_campo_impresa_nellanteprima(self, client):
        _admin(client)
        grezzo = client.post(
            f"{URL}/anteprima",
            json={
                "citta": "Reggio Emilia",
                "mq": 85,
                "tipo": "totale",
                "risposte": {"bagni": 3, "livello_finiture": "alto"},
            },
        ).text.lower()
        for vietata in ("coefficiente_impresa", "prezzo_impresa", "base_eur_mq"):
            assert vietata not in grezzo
