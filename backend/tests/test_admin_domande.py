"""E2E per /api/v1/admin/domande (0014, 08.1): CRUD del catalogo + anteprima.

Il test che vale piu' degli altri e' `TestAnteprima`: l'anteprima e' una delle
tre mitigazioni decise contro il marcire di un motore a regole (insieme chiuso
di otto effetti, anteprima, export Excel), e serve a tarare ~50 coefficienti
guardando cosa fanno invece che sperando. Se si rompe, la curatela torna a
essere a occhio.

Copre anche: 403 per non-admin su ogni route; la validazione degli effetti
tradotta in 400 leggibili invece che in un 500; il default come radio button
(impostarne uno spegne gli altri); l'assenza di qualunque campo impresa; la
disattivazione come UNICO modo di togliere una riga (D-25, D-39: nessun
`DELETE` fisico raggiungibile); la guardia di dipendenza D-28; l'opzione
implicita degli stepper (D-35); e la visibilita' condizionale D-37.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import app.db as db_module
from app.config import settings
from app.db import Base
from app.limiter import limiter
from app.main import app
from scripts.seed import load_seed_data, seed
from tests.computo_spento import catalogo_v2
from tests.session_factory import sessione_di_test

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
    testing_session_local = sessione_di_test(engine)

    with testing_session_local() as s:
        seed(s, load_seed_data())
        # Numeri del percorso EUR/m2 + effetti (catalogo v2): tests/computo_spento.py
        catalogo_v2(s)

    monkeypatch.setattr(db_module, "SessionLocal", testing_session_local)

    import app.dependencies.auth as deps_auth_module
    import app.routers.auth as auth_router_module
    import app.routers.stima as stima_router_module
    import app.routers.stime_salvate as stime_salvate_router_module

    monkeypatch.setattr(deps_auth_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(auth_router_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(stima_router_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(stime_salvate_router_module, "SessionLocal", testing_session_local)

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

    def test_disattivare_una_domanda_non_tocca_opzioni_ed_effetti(self, client):
        """Il contrario del vecchio comportamento a cascata: D-29 dice che la
        disattivazione di una domanda non tocca ne' le sue opzioni ne' i suoi
        effetti."""
        _admin(client)
        opzioni_prima = client.get(f"{URL}/opzioni", params={"domanda_code": "anno_costruzione"}).json()
        effetti_prima = client.get(f"{URL}/effetti", params={"domanda_code": "anno_costruzione"}).json()
        assert opzioni_prima and effetti_prima

        risposta = client.patch(f"{URL}/anno_costruzione", json={"attiva": False})
        assert risposta.status_code == 200
        assert risposta.json()["attiva"] is False

        opzioni_dopo = client.get(f"{URL}/opzioni", params={"domanda_code": "anno_costruzione"}).json()
        effetti_dopo = client.get(f"{URL}/effetti", params={"domanda_code": "anno_costruzione"}).json()
        assert len(opzioni_dopo) == len(opzioni_prima)
        assert len(effetti_dopo) == len(effetti_prima)


class TestNessunDeleteFisico:
    """D-25/D-39: non esiste piu' nessuna cancellazione fisica nel catalogo,
    nemmeno con un token admin."""

    @pytest.mark.parametrize("kind", ["domanda", "opzione", "effetto", "attesa"])
    def test_nessun_delete_fisico_nel_catalogo(self, client, kind):
        _admin(client)

        if kind == "domanda":
            path = f"{URL}/anno_costruzione"

            def rilegge():
                return next((d for d in client.get(URL).json() if d["code"] == "anno_costruzione"), None)

        elif kind == "opzione":
            opzione = client.get(f"{URL}/opzioni", params={"domanda_code": "anno_costruzione"}).json()[0]
            path = f"{URL}/opzioni/{opzione['id']}"

            def rilegge():
                return next((o for o in client.get(f"{URL}/opzioni").json() if o["id"] == opzione["id"]), None)

        elif kind == "effetto":
            effetto = client.get(f"{URL}/effetti", params={"domanda_code": "anno_costruzione"}).json()[0]
            path = f"{URL}/effetti/{effetto['id']}"

            def rilegge():
                return next((e for e in client.get(f"{URL}/effetti").json() if e["id"] == effetto["id"]), None)

        else:
            attesa = next(a for a in client.get(f"{URL}/attese").json() if a["attributo_code"] == "bagni")
            path = f"{URL}/attese/{attesa['id']}"

            def rilegge():
                return next((a for a in client.get(f"{URL}/attese").json() if a["id"] == attesa["id"]), None)

        risposta = client.delete(path)
        assert risposta.status_code == 405
        assert rilegge() is not None, "la riga deve restare a database dopo il DELETE rifiutato"


class TestDefaultComeRadioButton:
    def test_impostare_un_default_spegne_gli_altri(self, client):
        _admin(client)
        opzioni = client.get(f"{URL}/opzioni", params={"domanda_code": "anno_costruzione"}).json()
        non_default = next(o for o in opzioni if not o["is_default"])

        assert client.patch(f"{URL}/opzioni/{non_default['id']}", json={"is_default": True}).status_code == 200

        dopo = client.get(f"{URL}/opzioni", params={"domanda_code": "anno_costruzione"}).json()
        assert sum(1 for o in dopo if o["is_default"]) == 1
        assert next(o for o in dopo if o["is_default"])["id"] == non_default["id"]


class TestGuardiaDipendenze:
    """D-28: il toggle rifiuta di disattivare un'opzione in uso, nominando la
    dipendenza concreta."""

    def test_disattivare_lopzione_di_default_e_rifiutata(self, client):
        _admin(client)
        domanda = next(d for d in client.get(URL).json() if d["code"] == "anno_costruzione")
        opzioni = client.get(f"{URL}/opzioni", params={"domanda_code": "anno_costruzione"}).json()
        default = next(o for o in opzioni if o["is_default"])

        risposta = client.patch(f"{URL}/opzioni/{default['id']}", json={"attiva": False})

        assert risposta.status_code == 400
        assert domanda["testo"] in risposta.json()["detail"]

    def test_disattivare_lopzione_usata_da_una_derivazione_e_rifiutata(self, client):
        _admin(client)
        opzioni = client.get(f"{URL}/opzioni", params={"domanda_code": "classe_energetica_attuale"}).json()
        non_so = next(o for o in opzioni if o["code"] == "non_so")

        risposta = client.patch(f"{URL}/opzioni/{non_so['id']}", json={"attiva": False})

        assert risposta.status_code == 400
        assert "derivazione" in risposta.json()["detail"]

    def test_disattivare_lopzione_condizione_di_visibilita_e_rifiutata(self, client):
        _admin(client)
        domanda_governata = next(
            d for d in client.get(URL).json() if d["visibile_se_domanda_code"] == "muri_lavori"
        )
        opzioni = client.get(f"{URL}/opzioni", params={"domanda_code": "muri_lavori"}).json()
        si = next(o for o in opzioni if o["code"] == "si")

        risposta = client.patch(f"{URL}/opzioni/{si['id']}", json={"attiva": False})

        assert risposta.status_code == 400
        assert domanda_governata["testo"] in risposta.json()["detail"]

    def test_disattivare_unopzione_non_usata_e_permesso_e_reversibile(self, client):
        _admin(client)
        client.post(URL, json={"code": "prova_toggle", "testo": "Prova toggle", "tipo_controllo": "scelta_singola"})
        creata = client.post(
            f"{URL}/opzioni",
            json={"domanda_code": "prova_toggle", "code": "libera", "etichetta": "Libera"},
        ).json()

        spenta = client.patch(f"{URL}/opzioni/{creata['id']}", json={"attiva": False})
        assert spenta.status_code == 200
        assert spenta.json()["attiva"] is False

        riaccesa = client.patch(f"{URL}/opzioni/{creata['id']}", json={"attiva": True})
        assert riaccesa.status_code == 200
        assert riaccesa.json()["attiva"] is True

    def test_impostare_default_su_unopzione_non_attiva_e_rifiutata(self, client):
        _admin(client)
        client.post(URL, json={"code": "prova_default", "testo": "Prova default", "tipo_controllo": "scelta_singola"})
        creata = client.post(
            f"{URL}/opzioni",
            json={"domanda_code": "prova_default", "code": "spenta", "etichetta": "Spenta"},
        ).json()
        client.patch(f"{URL}/opzioni/{creata['id']}", json={"attiva": False})

        risposta = client.patch(f"{URL}/opzioni/{creata['id']}", json={"is_default": True})

        assert risposta.status_code == 400

    def test_creare_unopzione_default_e_non_attiva_via_post_e_rifiutata(self, client):
        """CR-02: `POST /opzioni` fa upsert per chiave naturale, quindi e' un
        secondo percorso di scrittura sullo stesso vincolo del PATCH — non
        solo per una riga nuova, ma anche riaprendo una riga gia' esistente."""
        _admin(client)
        client.post(URL, json={"code": "prova_post_default", "testo": "Prova", "tipo_controllo": "scelta_singola"})

        risposta = client.post(
            f"{URL}/opzioni",
            json={
                "domanda_code": "prova_post_default",
                "code": "spenta",
                "etichetta": "Spenta",
                "is_default": True,
                "attiva": False,
            },
        )

        assert risposta.status_code == 400
        assert "non puo' essere la risposta predefinita" in risposta.json()["detail"]

        opzioni = client.get(f"{URL}/opzioni", params={"domanda_code": "prova_post_default"}).json()
        assert opzioni == []

    def test_riaprire_unopzione_esistente_via_post_verso_default_non_attiva_e_rifiutata(self, client):
        _admin(client)
        client.post(URL, json={"code": "prova_post_upsert", "testo": "Prova", "tipo_controllo": "scelta_singola"})
        creata = client.post(
            f"{URL}/opzioni",
            json={"domanda_code": "prova_post_upsert", "code": "opz", "etichetta": "Opz"},
        ).json()
        assert creata["is_default"] is False

        risposta = client.post(
            f"{URL}/opzioni",
            json={
                "domanda_code": "prova_post_upsert",
                "code": "opz",
                "etichetta": "Opz",
                "is_default": True,
                "attiva": False,
            },
        )

        assert risposta.status_code == 400
        dopo = next(
            o for o in client.get(f"{URL}/opzioni", params={"domanda_code": "prova_post_upsert"}).json()
            if o["id"] == creata["id"]
        )
        assert dopo["is_default"] is False
        assert dopo["attiva"] is True


class TestOpzioneImplicitaStepper:
    """D-35: uno stepper/numero nasce con la sua opzione implicita `valore`."""

    def test_creare_uno_stepper_crea_lopzione_valore(self, client):
        _admin(client)
        risposta = client.post(
            URL, json={"code": "prova_stepper", "testo": "Quanti?", "tipo_controllo": "stepper"}
        )
        assert risposta.status_code == 201

        opzioni = client.get(f"{URL}/opzioni", params={"domanda_code": "prova_stepper"}).json()
        assert [o["code"] for o in opzioni] == ["valore"]

    def test_creare_una_scelta_singola_non_crea_nessuna_opzione(self, client):
        _admin(client)
        client.post(URL, json={"code": "prova_scelta", "testo": "Quale?", "tipo_controllo": "scelta_singola"})

        opzioni = client.get(f"{URL}/opzioni", params={"domanda_code": "prova_scelta"}).json()
        assert opzioni == []

    def test_patch_verso_numero_crea_lopzione_valore_se_manca(self, client):
        _admin(client)
        client.post(URL, json={"code": "prova_numero", "testo": "Quanti?", "tipo_controllo": "scelta_singola"})

        risposta = client.patch(f"{URL}/prova_numero", json={"tipo_controllo": "numero"})

        assert risposta.status_code == 200
        opzioni = client.get(f"{URL}/opzioni", params={"domanda_code": "prova_numero"}).json()
        assert [o["code"] for o in opzioni] == ["valore"]


class TestVisibilitaCondizionale:
    """D-37: niente codici inesistenti o spenti nella visibilita' condizionale,
    nemmeno via API."""

    def test_post_con_solo_una_meta_della_visibilita_e_400(self, client):
        _admin(client)
        risposta = client.post(
            URL,
            json={
                "code": "prova_vis1",
                "testo": "Prova",
                "tipo_controllo": "toggle",
                "visibile_se_domanda_code": "muri_lavori",
            },
        )
        assert risposta.status_code == 400

    def test_post_con_domanda_gate_inesistente_e_400(self, client):
        _admin(client)
        risposta = client.post(
            URL,
            json={
                "code": "prova_vis2",
                "testo": "Prova",
                "tipo_controllo": "toggle",
                "visibile_se_domanda_code": "non-esiste",
                "visibile_se_opzione_code": "si",
            },
        )
        assert risposta.status_code == 400

    def test_post_con_opzione_gate_non_attiva_e_400(self, client):
        _admin(client)
        client.post(URL, json={"code": "gate_dom", "testo": "Gate", "tipo_controllo": "toggle"})
        creata = client.post(
            f"{URL}/opzioni",
            json={"domanda_code": "gate_dom", "code": "spenta", "etichetta": "Spenta"},
        ).json()
        client.patch(f"{URL}/opzioni/{creata['id']}", json={"attiva": False})

        risposta = client.post(
            URL,
            json={
                "code": "prova_vis3",
                "testo": "Prova",
                "tipo_controllo": "toggle",
                "visibile_se_domanda_code": "gate_dom",
                "visibile_se_opzione_code": "spenta",
            },
        )
        assert risposta.status_code == 400

    def test_patch_con_visibilita_incoerente_e_400(self, client):
        _admin(client)
        client.post(URL, json={"code": "prova_vis4", "testo": "Prova", "tipo_controllo": "toggle"})

        risposta = client.patch(
            f"{URL}/prova_vis4",
            json={"visibile_se_domanda_code": "muri_lavori"},
        )
        assert risposta.status_code == 400


class TestStimaSalvataDopoDisattivazione:
    """Criterio 2 di ROADMAP: disattivare una domanda non cambia il totale di
    una stima gia' salvata che la citava."""

    def test_disattivare_la_domanda_non_cambia_il_totale_salvato(self, client):
        _admin(client)

        calcolata = client.post(
            "/api/v1/stima",
            json={
                "citta": "Reggio Emilia",
                "mq": 85,
                "tipo": "totale",
                "risposte": {"anno_costruzione": "pre_1980"},
            },
        )
        assert calcolata.status_code == 200
        corpo = calcolata.json()
        totale_prima = corpo["totale"]

        salvata = client.post("/api/v1/me/stime", json=corpo)
        assert salvata.status_code == 201
        stima_id = salvata.json()["id"]

        disattiva = client.patch(f"{URL}/anno_costruzione", json={"attiva": False})
        assert disattiva.status_code == 200

        rilegge = client.get(f"/api/v1/me/stime/{stima_id}")
        assert rilegge.status_code == 200
        totale_dopo = rilegge.json()["totale"]

        assert totale_dopo["totale_min"] == totale_prima["totale_min"]
        assert totale_dopo["totale_max"] == totale_prima["totale_max"]


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

    @pytest.mark.parametrize(
        "corpo",
        [
            {"tipo_effetto": "eur_mq_categoria", "target_categoria_code": "Z-INESISTENTE", "valore": "1"},
            {"tipo_effetto": "fattore_quantita", "target_sottocategoria_id": 999999, "valore": "1"},
            {"tipo_effetto": "quantita_per_unita", "target_voce_id": 999999, "valore": "1"},
        ],
    )
    def test_crea_effetto_con_bersaglio_inesistente_e_400_leggibile(self, client, corpo):
        """CR-01: un bersaglio che non corrisponde a nessuna riga (categoria,
        sottocategoria o voce) deve essere un 400 leggibile — mai una riga
        creata silenziosamente (SQLite non forza le FK) ne' un 500 grezzo
        (Postgres in produzione, IntegrityError non catturato)."""
        _admin(client)
        opzione = client.get(f"{URL}/opzioni", params={"domanda_code": "anno_costruzione"}).json()[0]
        conteggio_prima = len(client.get(f"{URL}/effetti", params={"domanda_code": "anno_costruzione"}).json())

        risposta = client.post(f"{URL}/effetti", json={"opzione_id": opzione["id"], **corpo})

        assert risposta.status_code == 400
        assert "inesistente" in risposta.json()["detail"]

        # e non e' stata creata nessuna riga incoerente (SQLite non forza le FK)
        conteggio_dopo = len(client.get(f"{URL}/effetti", params={"domanda_code": "anno_costruzione"}).json())
        assert conteggio_dopo == conteggio_prima

    def test_crea_effetto_con_categoria_vuota_e_400_leggibile(self, client):
        """Riproduce il payload che EffettiSezione.tsx poteva mandare prima
        della guardia frontend: `target_categoria_code: ""` (form aperto e
        Salva premuto subito, prima della select nativa React)."""
        _admin(client)
        opzione = client.get(f"{URL}/opzioni", params={"domanda_code": "anno_costruzione"}).json()[0]

        risposta = client.post(
            f"{URL}/effetti",
            json={
                "opzione_id": opzione["id"],
                "tipo_effetto": "moltiplicatore_categoria",
                "target_categoria_code": "",
                "valore": "1.1",
            },
        )

        assert risposta.status_code == 422

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


class TestNullEspliciteSuCampiNonNullable:
    """CR-03: un PATCH con `null` esplicito su un campo `NOT NULL` a database
    e' un 400 leggibile, mai un `IntegrityError` grezzo (500). `{"campo": None}`
    non e' lo stesso di omettere il campo — `exclude_unset=True` lascia
    passare entrambi in modo diverso, e solo il primo va rifiutato."""

    def test_patch_domanda_con_testo_nullo_e_400(self, client):
        _admin(client)
        risposta = client.patch(f"{URL}/anno_costruzione", json={"testo": None})
        assert risposta.status_code == 400
        assert "testo" in risposta.json()["detail"]

    def test_patch_domanda_con_attiva_nulla_e_400(self, client):
        _admin(client)
        risposta = client.patch(f"{URL}/anno_costruzione", json={"attiva": None})
        assert risposta.status_code == 400

    def test_patch_opzione_con_etichetta_nulla_e_400(self, client):
        _admin(client)
        opzione = client.get(f"{URL}/opzioni", params={"domanda_code": "anno_costruzione"}).json()[0]
        risposta = client.patch(f"{URL}/opzioni/{opzione['id']}", json={"etichetta": None})
        assert risposta.status_code == 400

    def test_patch_effetto_con_attivo_nullo_e_400(self, client):
        _admin(client)
        effetto = client.get(f"{URL}/effetti", params={"domanda_code": "anno_costruzione"}).json()[0]
        risposta = client.patch(f"{URL}/effetti/{effetto['id']}", json={"attivo": None})
        assert risposta.status_code == 400

    def test_patch_attesa_con_valore_atteso_nullo_e_400(self, client):
        _admin(client)
        attesa = client.get(f"{URL}/attese").json()[0]
        risposta = client.patch(f"{URL}/attese/{attesa['id']}", json={"valore_atteso": None})
        assert risposta.status_code == 400


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
        assert corpo["base_totale_min"] == "47251"
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
        """Setup riscritto dal DELETE al PATCH (D-39): la baseline "manca"
        perche' e' disattivata, non perche' e' cancellata. Il test resta verde
        solo perche' il filtro `AttesaImmobile.attiva` e' gia' cablato in
        `attese_per_mq` (Task 2) — e' la sua regressione."""
        _admin(client)
        for attesa in client.get(f"{URL}/attese").json():
            if attesa["attributo_code"] == "bagni":
                client.patch(f"{URL}/attese/{attesa['id']}", json={"attiva": False})

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
