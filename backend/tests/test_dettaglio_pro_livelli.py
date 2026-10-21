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
from tests.computo_spento import spegni_computo
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
        # Catena di quantita' v2 e meccanica degli assi (ripiego senza regole):
        # tests/computo_spento.py. Il computo ha i suoi test in test_computo*.py.
        spegni_computo(s)
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
    kwargs.setdefault("risposte", {})
    return DettaglioProService.compute(session, listino, mq=85, tipo="totale", **kwargs)


def _descrizioni_sotto(result, nome_sotto: str) -> list[str]:
    for cat in result.categorie:
        for sotto in cat.sottocategorie:
            if sotto.nome == nome_sotto:
                return [v.descrizione for v in sotto.voci]
    return []


class TestRetrocompatibilita:
    def test_oracolo_per_voce_invariato(self, session):
        """L'oracolo di `test_dettaglio_pro.py` deve reggere identico: A.1.1.1
        sta in A-EDILE, che il livello non tocca mai. Dal piano 09-06 (CFG-04)
        l'attesa si legge dal coefficiente seminato a DB, non da un numero di
        taratura cablato (la bozza cambiera' ancora con la taratura di
        Riccardo)."""
        from decimal import ROUND_HALF_UP

        from app.models.catalogo import TipoRistrutturazione
        from app.models.dettaglio_pro import CoefficienteQuantitaVoce, Voce

        result = _compute(session)

        voce = next(
            v
            for cat in result.categorie
            for sotto in cat.sottocategorie
            for v in sotto.voci
            if v.codice == "A.1.1.1"
        )

        voce_db = session.query(Voce).filter_by(codice="A.1.1.1").one()
        coeff = (
            session.query(CoefficienteQuantitaVoce)
            .filter_by(voce_id=voce_db.id, tipo_code="totale")
            .one()
        )
        range_pct = session.query(TipoRistrutturazione).filter_by(code="totale").one().range_pct

        quantita_attesa = (coeff.coefficiente_qta_per_mq * Decimal(85)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        totale_voce = quantita_attesa * voce_db.prezzo_unitario_cliente
        prezzo_min_atteso = (totale_voce * (Decimal("1") - range_pct)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        prezzo_max_atteso = (totale_voce * (Decimal("1") + range_pct)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )

        assert voce.quantita_stimata == quantita_attesa
        assert voce.prezzo_min == prezzo_min_atteso
        assert voce.prezzo_max == prezzo_max_atteso

def _bersagli_esclusivi(bersagli: dict[str, list[Voce]]) -> tuple[str, str, str]:
    """Una voce per livello incluso SOLO da quel livello: dalla v3 il
    rivestimento economico (B.1.6) e' incluso sia da base sia da medio."""
    def esclusiva(livello: str) -> str:
        altri = {v.id for code, voci in bersagli.items() if code != livello for v in voci}
        return next(v for v in bersagli[livello] if v.id not in altri).descrizione

    return esclusiva("medio"), esclusiva("base"), esclusiva("alto")


class TestSelezionePerLivello:
    """Dalla Fase 09-03 il filtro per livello non e' piu' `voce.livello`
    (colonna letta a mano) ma l'asse `finitura` del catalogo domande, gia'
    curato dal seed (09-02) sulle stesse 21 voci di gres. Queste fixture
    leggono i bersagli REALI dal catalogo (`EffettoOpzione` con
    `tipo_effetto='includi'` sulla domanda `finitura`) invece di taggare
    `voce.livello` a mano — il motore non legge piu' quella colonna."""

    @pytest.fixture()
    def bersagli_finitura(self, session) -> dict[str, list[Voce]]:
        """Solo i bersagli DENTRO GRES: dal 09-10 (G2) l'asse `finitura`
        governa anche A.6.3/A.6.4 (posa rivestimenti), fuori sottocategoria —
        questa fixture serve i test che confrontano prezzi/presenza dentro
        GRES, quindi resta scoped li'."""
        from app.models.domanda import EffettoOpzione, OpzioneDomanda
        from app.services.effetti import TIPO_INCLUDI

        sotto_gres_id = _sotto_gres(session).id
        righe = (
            session.query(OpzioneDomanda, EffettoOpzione)
            .join(EffettoOpzione, EffettoOpzione.opzione_id == OpzioneDomanda.id)
            .join(Voce, Voce.id == EffettoOpzione.target_voce_id)
            .filter(
                OpzioneDomanda.domanda_code == "finitura",
                EffettoOpzione.tipo_effetto == TIPO_INCLUDI,
                Voce.sottocategoria_id == sotto_gres_id,
            )
            .all()
        )
        per_opzione: dict[str, list[Voce]] = {}
        for opzione, effetto in righe:
            voce = session.get(Voce, effetto.target_voce_id)
            per_opzione.setdefault(opzione.code, []).append(voce)
        return per_opzione

    def test_solo_la_voce_del_livello_scelto(self, session, bersagli_finitura):
        medio_desc, base_desc, alto_desc = _bersagli_esclusivi(bersagli_finitura)

        incluse = _descrizioni_sotto(_compute(session, livelli={"B-FINITURE": "medio"}), GRES)

        assert medio_desc in incluse
        assert base_desc not in incluse
        assert alto_desc not in incluse

    def test_le_voci_non_governate_da_tipo_pavimento_restano(self, session):
        """Dal 09-10 (G1/G2) quasi tutta A.6 e' governata da un asse (A.6.1/
        .2/.5/.6/.7/.8/.10 da `tipo_pavimento`, A.6.3/.4 da `finitura`, A.6.9
        esclusa su tutte le finiture): A.6.11 (taglio porta blindata) resta
        l'unica voce non governata da alcun asse, e deve sopravvivere al
        filtro qualunque pavimento si scelga (con la finitura di default)."""
        sotto_a6 = (
            session.query(Sottocategoria).filter_by(categoria_code="A-EDILE", codice="A.6").one()
        )
        governate = {
            "A.6.1", "A.6.2", "A.6.3", "A.6.4", "A.6.5",
            "A.6.6", "A.6.7", "A.6.8", "A.6.9", "A.6.10",
        }
        codici_non_governati = [
            v.codice for v in _voci_di(session, sotto_a6) if v.codice not in governate
        ]
        assert codici_non_governati, "il seed deve avere pose A.6 non governate da alcun asse"

        for pavimento in ("gres", "parquet", "maxi_lastra", "mosaico"):
            result = _compute(session, risposte={"tipo_pavimento": pavimento})
            codici_presenti = {
                v.codice
                for cat in result.categorie
                for s in cat.sottocategorie
                if s.nome == sotto_a6.nome
                for v in s.voci
            }
            for codice in codici_non_governati:
                assert codice in codici_presenti

    def test_livello_alto_costa_piu_del_livello_base(self, session, bersagli_finitura):
        """Con le voci reali del catalogo, il livello muove davvero il totale
        — e nella direzione giusta. Si alza il prezzo di una voce bersaglio
        di 'alto' e si abbassa quella di 'base': il resto del computo resta
        identico, quindi il confronto e' pulito."""
        voce_base = bersagli_finitura["base"][0]
        voce_base.prezzo_unitario_cliente = Decimal("20.00")
        voce_alto = bersagli_finitura["alto"][0]
        voce_alto.prezzo_unitario_cliente = Decimal("500.00")
        session.flush()

        totale_base = _compute(session, livelli={"B-FINITURE": "base"}).totale_max
        totale_alto = _compute(session, livelli={"B-FINITURE": "alto"}).totale_max

        assert totale_alto > totale_base

    def test_a_edile_ignora_il_livello(self, session):
        """A-EDILE non e' selezionabile: il totale di categoria non cambia al
        variare del livello di finitura (l'asse non la governa in alcun
        modo — nessuna voce di A-EDILE e' bersaglio di `finitura`)."""

        def totale_edile(livello: str) -> Decimal:
            result = _compute(session, livelli={"B-FINITURE": livello})
            return next(c.totale_max for c in result.categorie if c.code == "A-EDILE")

        assert totale_edile("base") == totale_edile("alto")

    def test_livello_assente_applica_il_default_non_tutte_le_voci(self, session, bersagli_finitura):
        """Senza scelta si applica `is_default` ('medio'). Il caso sbagliato da
        escludere e' "nessuna scelta => nessun filtro", che riporterebbe il bug
        della somma dei cataloghi."""
        medio_desc, base_desc, alto_desc = _bersagli_esclusivi(bersagli_finitura)

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

    def test_livello_finiture_del_wizard_guida_la_finitura_pro(self, session):
        """M2 dell'audit v2.0: la domanda del wizard `livello_finiture`
        (step 3, tier free) e l'asse Pro `finitura` sono due domande con gli
        stessi codici d'opzione. Senza ponte, chi sceglie "Alte" nel wizard
        vede il totale a finiture alte e il dettaglio Pro al default."""
        result = _compute(session, risposte={"livello_finiture": "alto"})

        per_code = {c.code: c for c in result.categorie}
        assert per_code["B-FINITURE"].livello_scelto == "alto"

    def test_finitura_esplicita_vince_sul_livello_del_wizard(self, session):
        result = _compute(session, risposte={"livello_finiture": "alto", "finitura": "base"})

        per_code = {c.code: c for c in result.categorie}
        assert per_code["B-FINITURE"].livello_scelto == "base"

    def test_livello_per_categoria_vince_sul_livello_del_wizard(self, session):
        result = _compute(
            session, risposte={"livello_finiture": "alto"}, livelli={"B-FINITURE": "base"}
        )

        per_code = {c.code: c for c in result.categorie}
        assert per_code["B-FINITURE"].livello_scelto == "base"

    def test_livello_finiture_sconosciuto_all_asse_ricade_sul_default(self, session):
        """Il ponte vale solo per i codici che esistono anche sull'asse
        `finitura`: un'opzione aggiunta dal pannello alla sola domanda del
        wizard non deve arrivare al motore Pro come risposta invalida."""
        result = _compute(session, risposte={"livello_finiture": "inesistente"})

        per_code = {c.code: c for c in result.categorie}
        assert per_code["B-FINITURE"].livello_scelto == "medio"

    def test_sottocategoria_svuotata_dal_filtro_e_assente(self, session):
        """Niente accordion vuoti a 0 EUR: se il livello svuota una
        sottocategoria, sparisce — e ricompare col livello giusto. Una
        sottocategoria di TEST, interamente governata dall'asse `finitura`
        (nessuna voce non governata), cosi' che uno dei due livelli la
        svuoti per intero — a differenza del GRES reale, che ha sempre le
        voci di posa non governate a tenerla non vuota."""
        from app.models.domanda import EffettoOpzione, OpzioneDomanda
        from app.services.effetti import TIPO_INCLUDI

        gres = _sotto_gres(session)
        sotto_test = Sottocategoria(
            listino_id=gres.listino_id,
            categoria_code="B-FINITURE",
            codice=None,
            nome="TEST SVUOTA",
            famiglia="catalogo",
            ordine=999,
        )
        session.add(sotto_test)
        session.flush()
        voce_base = Voce(
            sottocategoria_id=sotto_test.id,
            codice=None,
            descrizione="voce di test governata da base",
            um="cad",
            prezzo_unitario_cliente=Decimal("10.00"),
            ordine=1,
        )
        voce_alto = Voce(
            sottocategoria_id=sotto_test.id,
            codice=None,
            descrizione="voce di test governata da alto",
            um="cad",
            prezzo_unitario_cliente=Decimal("10.00"),
            ordine=2,
        )
        session.add_all([voce_base, voce_alto])
        session.flush()

        opz_base = session.query(OpzioneDomanda).filter_by(domanda_code="finitura", code="base").one()
        opz_alto = session.query(OpzioneDomanda).filter_by(domanda_code="finitura", code="alto").one()
        session.add(EffettoOpzione(opzione_id=opz_base.id, tipo_effetto=TIPO_INCLUDI, target_voce_id=voce_base.id))
        session.add(EffettoOpzione(opzione_id=opz_alto.id, tipo_effetto=TIPO_INCLUDI, target_voce_id=voce_alto.id))
        session.commit()

        def nomi(livello: str) -> list[str]:
            return [
                s.nome
                for cat in _compute(session, livelli={"B-FINITURE": livello}).categorie
                for s in cat.sottocategorie
            ]

        # medio: nessuna delle due voci di test e' bersaglio -> sottocategoria vuota, scartata.
        assert "TEST SVUOTA" not in nomi("medio")
        assert "TEST SVUOTA" in nomi("base")
        assert "TEST SVUOTA" in nomi("alto")


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

        # Catena di quantita' v2 e meccanica degli assi (ripiego senza regole):

        # tests/computo_spento.py. Il computo ha i suoi test in test_computo*.py.

        spegni_computo(session)
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
            json={
                "risposte": {"bagni": 1, "porte": 4, "condizionatori": 2},
                "livelli": {"D-PRODOTTI": "base"},
            },
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
            json={
                "risposte": {"bagni": 0, "porte": 0, "condizionatori": 0},
                "livelli": {"B-FINITURE": "extra"},
            },
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
            json={
                "risposte": {"bagni": 0, "porte": 0, "condizionatori": 0},
                "livelli": {"A-EDILE": "alto"},
            },
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
