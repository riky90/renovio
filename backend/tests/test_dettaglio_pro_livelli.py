"""Livelli di finitura nel motore Pro (migrazione 0010).

Il difetto che questa feature chiude: le sottocategorie `famiglia='catalogo'`
sono cataloghi di ALTERNATIVE (22 voci di gres, 7 di parquet, le rubinetterie)
e il motore le sommava tutte. Su una stima reale di 120 m2 il dettaglio Pro
usciva otto volte il sintetico.

Il vincolo piu' importante verificato qui NON e' il filtro: e' che introdurlo
non cambi nulla finche' i dati non sono curati (tutte le voci a
`livello=NULL`). La curatela e' dell'admin, e avviene dopo il deploy.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import app.db as db_module
from app.db import Base
from app.limiter import limiter
from app.main import app
from app.models.catalogo import Categoria, LivelloFinitura
from app.models.dettaglio_pro import Sottocategoria, Voce
from app.models.stima_salvata import StimaSalvata
from app.services.city_resolver import resolve_listino
from app.services.dettaglio_pro import DettaglioProService
from scripts.seed import load_seed_data, seed
from tests.session_factory import sessione_di_test

REGISTRAZIONE_URL = "/api/v1/auth/registrati"
STIME_URL = "/api/v1/me/stime"
ATTIVA_PRO_URL = "/api/v1/me/pro/attiva"
OPZIONI_PRO_URL = "/api/v1/me/opzioni-pro"
GRES = "PAVIMENTI E RIVESTIMENTI GRES"


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)
    with testing_session_local() as s:
        seed(s, load_seed_data())
        yield s


def _sotto_gres(session) -> Sottocategoria:
    return session.query(Sottocategoria).filter_by(categoria_code="B-FINITURE", nome=GRES).one()


def _voci_di(session, sotto: Sottocategoria) -> list[Voce]:
    return (
        session.query(Voce)
        .filter_by(sottocategoria_id=sotto.id)
        .order_by(Voce.ordine, Voce.id)
        .all()
    )


def _compute(session, **kwargs):
    listino, _ = resolve_listino(session, "Reggio Emilia")
    return DettaglioProService.compute(session, listino, mq=85, tipo="totale", risposte={}, **kwargs)


def _descrizioni_sotto(result, nome_sotto: str) -> list[str]:
    for cat in result.categorie:
        for sotto in cat.sottocategorie:
            if sotto.nome == nome_sotto:
                return [v.descrizione for v in sotto.voci]
    return []


class TestFiltroPuro:
    """`_voce_inclusa` non tocca il DB: si verifica da sola, caso per caso."""

    def test_categoria_non_selezionabile_include_tutto(self):
        assert DettaglioProService._voce_inclusa("alto", False, "base") is True

    def test_nessun_livello_risolto_include_tutto(self):
        """Tabella `livello_finitura` vuota (DB migrato ma non ri-seminato):
        si torna al comportamento precedente, non a un risultato vuoto."""
        assert DettaglioProService._voce_inclusa("alto", True, None) is True

    def test_voce_senza_livello_sempre_inclusa(self):
        assert DettaglioProService._voce_inclusa(None, True, "base") is True

    def test_voce_del_livello_scelto_inclusa(self):
        assert DettaglioProService._voce_inclusa("medio", True, "medio") is True

    def test_voce_di_altro_livello_esclusa(self):
        assert DettaglioProService._voce_inclusa("alto", True, "medio") is False


class TestRetrocompatibilita:
    def test_oracolo_per_voce_invariato(self, session):
        """L'oracolo pinnato di `test_dettaglio_pro.py` deve reggere identico:
        A.1.1.1 sta in A-EDILE, che il livello non tocca mai."""
        result = _compute(session)

        voce = next(
            v
            for cat in result.categorie
            for sotto in cat.sottocategorie
            for v in sotto.voci
            if v.codice == "A.1.1.1"
        )
        assert voce.quantita_stimata == Decimal("51.00")
        assert voce.prezzo_min == Decimal("1836")
        assert voce.prezzo_max == Decimal("2754")

    def test_con_voci_non_curate_il_livello_non_cambia_nulla(self, session):
        """Tutte le voci a NULL (stato subito dopo la migrazione): qualunque
        livello si scelga, il totale e' lo stesso. E' la garanzia che il deploy
        della 0010 non muove un euro finche' l'admin non cura i dati."""
        base = _compute(session)
        for livello in ("base", "medio", "alto"):
            scelto = _compute(session, livelli={"B-FINITURE": livello})
            assert scelto.totale_min == base.totale_min
            assert scelto.totale_max == base.totale_max


class TestSelezionePerLivello:
    @pytest.fixture()
    def gres_taggato(self, session):
        """Tre voci di gres etichettate base/medio/alto; le altre restano NULL."""
        voci = _voci_di(session, _sotto_gres(session))
        voci[0].livello = "base"
        voci[1].livello = "medio"
        voci[2].livello = "alto"
        session.flush()
        return [voci[0].descrizione, voci[1].descrizione, voci[2].descrizione]

    def test_solo_la_voce_del_livello_scelto(self, session, gres_taggato):
        base_desc, medio_desc, alto_desc = gres_taggato

        incluse = _descrizioni_sotto(_compute(session, livelli={"B-FINITURE": "medio"}), GRES)

        assert medio_desc in incluse
        assert base_desc not in incluse
        assert alto_desc not in incluse

    def test_le_voci_senza_livello_restano(self, session, gres_taggato):
        """Posa, consumo e montaggio non hanno livello: devono sopravvivere al
        filtro, altrimenti il computo perde le lavorazioni."""
        voci_null = [
            v.descrizione for v in _voci_di(session, _sotto_gres(session)) if v.livello is None
        ]
        assert voci_null, "il seed deve avere voci di gres non etichettate"

        incluse = _descrizioni_sotto(_compute(session, livelli={"B-FINITURE": "medio"}), GRES)

        for descrizione in voci_null:
            assert descrizione in incluse

    def test_livello_alto_costa_piu_del_livello_base(self, session):
        """Con voci curate, il livello muove davvero il totale — e nella
        direzione giusta. Due sole voci etichettate, una per livello: e' il
        confronto pulito, perche' tutto il resto del computo e' identico."""
        voci = _voci_di(session, _sotto_gres(session))
        voci[0].livello = "base"
        voci[0].prezzo_unitario_cliente = Decimal("20.00")
        voci[1].livello = "alto"
        voci[1].prezzo_unitario_cliente = Decimal("500.00")
        session.flush()

        totale_base = _compute(session, livelli={"B-FINITURE": "base"}).totale_max
        totale_alto = _compute(session, livelli={"B-FINITURE": "alto"}).totale_max

        assert totale_alto > totale_base

    def test_a_edile_ignora_il_livello(self, session):
        """A-EDILE non e' selezionabile: anche etichettando le sue voci, il
        totale di categoria non cambia al variare del livello."""
        sotto_edile = (
            session.query(Sottocategoria)
            .filter_by(categoria_code="A-EDILE")
            .order_by(Sottocategoria.id)
            .first()
        )
        for voce in _voci_di(session, sotto_edile):
            voce.livello = "alto"
        session.flush()

        def totale_edile(livello: str) -> Decimal:
            result = _compute(session, livelli={"B-FINITURE": livello})
            return next(c.totale_max for c in result.categorie if c.code == "A-EDILE")

        assert totale_edile("base") == totale_edile("alto")

    def test_livello_assente_applica_il_default_non_tutte_le_voci(self, session, gres_taggato):
        """Senza scelta si applica `is_default` ('medio'). Il caso sbagliato da
        escludere e' "nessuna scelta => nessun filtro", che riporterebbe il bug
        della somma dei cataloghi."""
        base_desc, medio_desc, alto_desc = gres_taggato

        incluse = _descrizioni_sotto(_compute(session), GRES)

        assert medio_desc in incluse
        assert base_desc not in incluse
        assert alto_desc not in incluse

    def test_livello_scelto_riportato_sulla_categoria(self, session):
        result = _compute(session, livelli={"B-FINITURE": "alto"})

        per_code = {c.code: c for c in result.categorie}
        assert per_code["B-FINITURE"].livello_scelto == "alto"
        assert per_code["B-FINITURE"].livello_scelto_nome == "Lusso"
        # A-EDILE non selezionabile -> nessun livello da mostrare.
        assert per_code["A-EDILE"].livello_scelto is None

    def test_sottocategoria_svuotata_dal_filtro_e_assente(self, session):
        """Niente accordion vuoti a 0 EUR: se il livello svuota una
        sottocategoria, sparisce — e ricompare col livello giusto."""
        sotto = _sotto_gres(session)
        for voce in _voci_di(session, sotto):
            voce.livello = "alto"
        session.flush()

        def nomi(livello: str) -> list[str]:
            return [
                s.nome
                for cat in _compute(session, livelli={"B-FINITURE": livello}).categorie
                for s in cat.sottocategorie
            ]

        assert GRES not in nomi("base")
        assert GRES in nomi("alto")


class TestSeedEAdmin:
    def test_seed_marca_solo_b_c_d_come_selezionabili(self, session):
        flag = {c.code: c.livello_selezionabile for c in session.query(Categoria).all()}

        assert flag["A-EDILE"] is False
        assert flag["B-FINITURE"] is True
        assert flag["C-SERRAMENTI"] is True
        assert flag["D-PRODOTTI"] is True

    def test_seed_crea_i_tre_livelli_con_un_solo_default(self, session):
        rows = session.query(LivelloFinitura).all()

        assert {r.code for r in rows} == {"base", "medio", "alto"}
        assert [r.code for r in rows if r.is_default] == ["medio"]

    def test_seed_ripetuto_non_azzera_la_curatela(self, session):
        """Il seed gira a ogni boot del container: se sovrascrivesse
        `voce.livello`, ogni deploy cancellerebbe la classificazione fatta
        dall'admin — stesso morso di `seed_testi` prima della Fase 0."""
        voce = _voci_di(session, _sotto_gres(session))[0]
        voce.livello = "alto"
        session.commit()

        seed(session, load_seed_data())
        session.expire_all()

        assert session.get(Voce, voce.id).livello == "alto"

    def test_upload_excel_non_azzera_livello(self, session):
        """`listino_upload_service._upsert_voce` sovrascrive incondizionatamente
        i campi che tocca, e il file Excel non ha una colonna livello: `livello`
        deve restare fuori dal suo giro."""
        from app.schemas.admin_upload import VoceRigaIn
        from app.services.listino_upload_service import _upsert_voce as upsert_da_excel

        sotto = _sotto_gres(session)
        voce = _voci_di(session, sotto)[0]
        voce.livello = "alto"
        session.flush()

        upsert_da_excel(
            session,
            sotto,
            VoceRigaIn(
                categoria_code=sotto.categoria_code,
                sottocategoria_codice=sotto.codice,
                sottocategoria_nome=sotto.nome,
                sottocategoria_famiglia=sotto.famiglia,
                sottocategoria_ordine=sotto.ordine,
                codice=voce.codice,
                descrizione=voce.descrizione,
                um=voce.um,
                prezzo_unitario_cliente=Decimal("99.00"),
                ordine=voce.ordine,
            ),
        )
        session.flush()

        assert voce.prezzo_unitario_cliente == Decimal("99.00")  # il prezzo si aggiorna...
        assert voce.livello == "alto"  # ...il livello no.


@pytest.fixture()
def client(monkeypatch, tmp_path):
    limiter.reset()

    db_path = tmp_path / "test_livelli.db"
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

    return TestClient(app), testing_session_local


def _stima_payload(preferenze_pro: dict | None = None) -> dict:
    payload = {
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
    if preferenze_pro is not None:
        payload["preferenze_pro"] = preferenze_pro
    return payload


def _registra_pro(c):
    c.post(
        REGISTRAZIONE_URL,
        json={"email": "livelli@example.com", "password": "Password123", "nome": "Livelli"},
    )
    c.post(ATTIVA_PRO_URL)


class TestApiLivelli:
    def test_preferenze_pro_non_finiscono_nello_snapshot(self, client):
        """Lo snapshot congelato deve conservare ESATTAMENTE la forma di
        `StimaResponse`: e' la prova di cio' che l'utente ha visto, non un
        contenitore di parametri."""
        c, session_factory = client
        _registra_pro(c)

        stima_id = c.post(
            STIME_URL,
            json=_stima_payload({"livelli": {"B-FINITURE": "alto"}, "risposte": {"bagni": 2}}),
        ).json()["id"]

        with session_factory() as session:
            row = session.get(StimaSalvata, stima_id)
            assert "preferenze_pro" not in row.risultato_json
            assert row.livelli_pro_json == {"B-FINITURE": "alto"}
            assert row.risposte_pro_json == {"bagni": 2, "porte": 0, "condizionatori": 0}

    def test_stima_senza_preferenze_resta_valida(self, client):
        c, session_factory = client
        _registra_pro(c)

        stima_id = c.post(STIME_URL, json=_stima_payload()).json()["id"]

        with session_factory() as session:
            row = session.get(StimaSalvata, stima_id)
            assert row.livelli_pro_json is None
            assert row.risposte_pro_json is None

    def test_livelli_applicati_in_eco_nel_dettaglio(self, client):
        c, _ = client
        _registra_pro(c)
        stima_id = c.post(
            STIME_URL, json=_stima_payload({"livelli": {"B-FINITURE": "alto"}})
        ).json()["id"]

        body = c.get(f"{STIME_URL}/{stima_id}/dettaglio-pro").json()

        assert body["livelli"]["B-FINITURE"] == "alto"
        # Senza scelta esplicita, l'eco riporta comunque il default applicato.
        assert body["livelli"]["C-SERRAMENTI"] == "medio"
        assert [liv["code"] for liv in body["livelli_disponibili"]] == ["base", "medio", "alto"]

    def test_post_risposte_salva_anche_i_livelli(self, client):
        c, session_factory = client
        _registra_pro(c)
        stima_id = c.post(STIME_URL, json=_stima_payload()).json()["id"]

        response = c.post(
            f"{STIME_URL}/{stima_id}/dettaglio-pro/risposte",
            json={"bagni": 1, "porte": 4, "condizionatori": 2, "livelli": {"D-PRODOTTI": "base"}},
        )

        assert response.status_code == 200
        assert response.json()["livelli"]["D-PRODOTTI"] == "base"
        with session_factory() as session:
            row = session.get(StimaSalvata, stima_id)
            # `livelli` non deve inquinare le risposte mirate.
            assert row.risposte_pro_json == {"bagni": 1, "porte": 4, "condizionatori": 2}
            assert row.livelli_pro_json == {"D-PRODOTTI": "base"}

    def test_livello_inesistente_400(self, client):
        c, _ = client
        _registra_pro(c)
        stima_id = c.post(STIME_URL, json=_stima_payload()).json()["id"]

        response = c.post(
            f"{STIME_URL}/{stima_id}/dettaglio-pro/risposte",
            json={"bagni": 0, "porte": 0, "condizionatori": 0, "livelli": {"B-FINITURE": "extra"}},
        )

        assert response.status_code == 400

    def test_livello_su_categoria_non_selezionabile_400(self, client):
        """Mandare un livello per A-EDILE e' un errore del client, non un no-op
        silenzioso: le chiavi di un dict non validato non sono fidate."""
        c, _ = client
        _registra_pro(c)
        stima_id = c.post(STIME_URL, json=_stima_payload()).json()["id"]

        response = c.post(
            f"{STIME_URL}/{stima_id}/dettaglio-pro/risposte",
            json={"bagni": 0, "porte": 0, "condizionatori": 0, "livelli": {"A-EDILE": "alto"}},
        )

        assert response.status_code == 400

    def test_livelli_invalidi_al_salvataggio_400(self, client):
        c, _ = client
        _registra_pro(c)

        response = c.post(STIME_URL, json=_stima_payload({"livelli": {"B-FINITURE": "boh"}}))

        assert response.status_code == 400


class TestOpzioniPro:
    """`GET /me/opzioni-pro` alimenta i selettori del form Pro, che esiste
    prima che una stima sia stata calcolata."""

    def test_ritorna_livelli_e_categorie_selezionabili(self, client):
        c, _session_factory = client
        _registra_pro(c)

        response = c.get(OPZIONI_PRO_URL)

        assert response.status_code == 200
        body = response.json()
        assert [liv["code"] for liv in body["livelli"]] == ["base", "medio", "alto"]
        codici_categorie = {cat["code"] for cat in body["categorie"]}
        assert "A-EDILE" not in codici_categorie
        assert codici_categorie == {"B-FINITURE", "C-SERRAMENTI", "D-PRODOTTI"}

    def test_utente_free_prende_403(self, client):
        c, _session_factory = client
        c.post(
            REGISTRAZIONE_URL,
            json={"email": "free.opzioni@example.com", "password": "Password123", "nome": "Free"},
        )

        assert c.get(OPZIONI_PRO_URL).status_code == 403

    def test_anonimo_prende_401(self, client):
        c, _session_factory = client

        assert c.get(OPZIONI_PRO_URL).status_code == 401
