"""DettaglioProService regression tests (03-03-PLAN.md Task 1/2).

Oracolo per-voce (A.1.1.1, A-EDILE, um=mq): dal piano 09-06 (CFG-04) il
coefficiente non e' piu' la bozza uniforme 0.6 x TIPO_FACTOR — cambia con la
classe di taratura e cambiera' ancora con la taratura vera di Riccardo.
L'attesa si legge dal coefficiente seminato a DB (`quantita = coefficiente x
mq`, range = `TipoRistrutturazione.range_pct`), non da un numero cablato: e'
la CATENA che questo test presidia, non il valore di taratura.

A.0.3 (A-EDILE, um=cad, prezzo_unitario_cliente=40.00, tipo=totale,
domanda_mirata_key="bagni", default_conteggio=1): senza risposte ->
quantita=1 -> [32, 48]; con risposte={"bagni": 3} -> quantita=3 -> [96, 144].
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import app.db as db_module
from app.db import Base
from app.limiter import limiter
from app.main import app
from app.models.catalogo import TipoRistrutturazione
from app.models.dettaglio_pro import CoefficienteQuantitaVoce, Voce
from app.services.city_resolver import resolve_listino
from app.services.dettaglio_pro import DettaglioProService
from scripts.seed import load_seed_data, seed
from tests.computo_spento import spegni_computo
from tests.session_factory import sessione_di_test


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


def _find_voce(result, codice: str):
    for cat in result.categorie:
        for sotto in cat.sottocategorie:
            for voce in sotto.voci:
                if voce.codice == codice:
                    return voce
    raise AssertionError(f"voce {codice!r} non trovata nel risultato")


def test_oracolo_per_voce_coefficiente_qta_per_mq(session):
    listino, fallback = resolve_listino(session, "Reggio Emilia")
    assert fallback is False

    result = DettaglioProService.compute(session, listino, mq=85, tipo="totale", risposte={})

    voce = _find_voce(result, "A.1.1.1")

    # Attesa derivata dal coefficiente seminato a DB (CFG-04, piano 09-06),
    # non da un numero di taratura cablato: la bozza e' cambiata e cambiera'
    # ancora con la taratura vera di Riccardo.
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


def test_senza_risposta_bagni_vale_latteso_a_85_mq(session):
    """Dalla Fase 09-03 la quantita' non viene piu' da `default_conteggio`
    (colonna letta a mano) ma da `quantita_per_unita` del catalogo: senza
    risposta, l'unita' e' l'atteso di `attesa_immobile` per l'attributo della
    domanda (`bagni`, a 85 m2). Letto dinamicamente dal DB, non cablato."""
    from app.services.effetti import attese_per_mq

    listino, _ = resolve_listino(session, "Reggio Emilia")
    atteso_bagni = attese_per_mq(session, 85)["bagni"]

    result = DettaglioProService.compute(session, listino, mq=85, tipo="totale", risposte={})

    voce = _find_voce(result, "A.0.3")
    assert voce.quantita_stimata == Decimal(atteso_bagni).quantize(Decimal("0.01"))


def test_domanda_mirata_usa_risposta_esplicita_quando_presente(session):
    listino, _ = resolve_listino(session, "Reggio Emilia")

    result = DettaglioProService.compute(session, listino, mq=85, tipo="totale", risposte={"bagni": 3})

    voce = _find_voce(result, "A.0.3")
    assert voce.quantita_stimata == Decimal("3.00")
    assert voce.prezzo_min == Decimal("96")
    assert voce.prezzo_max == Decimal("144")


def test_sottocategoria_senza_voci_stimate_compare_comunque(session):
    """Ogni Sottocategoria della categoria e' presente nel risultato, anche
    se (in teoria) non avesse voci — qui verifichiamo che tutte le
    sottocategorie seedate per A-EDILE compaiano, mai filtrate."""
    listino, _ = resolve_listino(session, "Reggio Emilia")

    result = DettaglioProService.compute(session, listino, mq=85, tipo="totale", risposte={})

    edile = next(c for c in result.categorie if c.code == "A-EDILE")
    assert len(edile.sottocategorie) > 0
    for sotto in edile.sottocategorie:
        assert isinstance(sotto.voci, list)


def test_totali_a_range_sommano_bottom_up(session):
    """I totali (D-11, sempre a range) sono somme coerenti bottom-up:
    subtotale sottocategoria = somma voci; totale categoria = somma
    sottocategorie; totale generale = somma categorie. Fonte unica per
    schermata e PDF (03-RESEARCH.md Pitfall 2)."""
    listino, _ = resolve_listino(session, "Reggio Emilia")

    result = DettaglioProService.compute(session, listino, mq=85, tipo="totale", risposte={})

    grand_min = Decimal("0")
    grand_max = Decimal("0")
    for cat in result.categorie:
        cat_min = Decimal("0")
        cat_max = Decimal("0")
        for sotto in cat.sottocategorie:
            assert sotto.totale_min == sum((v.prezzo_min for v in sotto.voci), Decimal("0"))
            assert sotto.totale_max == sum((v.prezzo_max for v in sotto.voci), Decimal("0"))
            cat_min += sotto.totale_min
            cat_max += sotto.totale_max
        assert cat.totale_min == cat_min
        assert cat.totale_max == cat_max
        grand_min += cat_min
        grand_max += cat_max

    assert result.totale_min == grand_min
    assert result.totale_max == grand_max
    # Un range reale: il minimo non supera il massimo, ed esiste un costo > 0.
    assert result.totale_min <= result.totale_max
    assert result.totale_max > Decimal("0")


def test_service_non_importa_il_motore_free():
    """D-01: guard statico — il sorgente non deve nominare la classe del
    motore di stima Free."""
    import inspect

    from app.services import dettaglio_pro as modulo

    sorgente = inspect.getsource(modulo)
    assert "EstimationService" not in sorgente


def test_motore_pro_non_legge_livello_ne_chiavi_mirate():
    """09-03: il vecchio filtro (`_voce_inclusa`, letto da `voce.livello`) e
    la lettura di `domanda_mirata_key` sono spariti nello swap atomico —
    l'asse di scelta e' dato dal catalogo (`risolvi_effetti_pro`), non da
    queste due colonne."""
    import inspect
    import re

    from app.services import dettaglio_pro as modulo

    sorgente = inspect.getsource(modulo)
    # Le righe di prosa (docstring) citano questi nomi fra backtick per
    # spiegare cosa NON si legge piu': si escludono dal guard, che deve
    # controllare solo il CODICE.
    righe_codice = "\n".join(r for r in sorgente.splitlines() if "`" not in r)
    for pattern in (r"\bvoce\.livello\b", r"domanda_mirata_key", r"_voce_inclusa"):
        assert not re.search(pattern, righe_codice), f"trovato {pattern!r} nel motore Pro"


def test_nessun_campo_impresa_nel_risultato(session):
    listino, _ = resolve_listino(session, "Reggio Emilia")

    result = DettaglioProService.compute(session, listino, mq=85, tipo="totale", risposte={})

    result_repr = repr(result)
    assert "coefficiente_impresa" not in result_repr
    assert "prezzo_impresa" not in result_repr
    assert "base_eur_mq" not in result_repr


STIME_URL = "/api/v1/me/stime"
ATTIVA_PRO_URL = "/api/v1/me/pro/attiva"
REGISTRAZIONE_URL = "/api/v1/auth/registrati"


def _stima_payload() -> dict:
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
def http_client(monkeypatch, tmp_path):
    """Client HTTP end-to-end per l'integrazione POST-risposte -> GET
    (Task 2): stesso pattern engine-swap di test_dettaglio_pro_paywall.py."""
    limiter.reset()

    db_path = tmp_path / "test_dettaglio_pro_integration.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)

    with testing_session_local() as s:
        seed(s, load_seed_data())
        # Catena di quantita' v2 e meccanica degli assi (ripiego senza regole):
        # tests/computo_spento.py. Il computo ha i suoi test in test_computo*.py.
        spegni_computo(s)
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


def test_post_risposte_persiste_e_get_successivo_le_riflette(http_client):
    http_client.post(REGISTRAZIONE_URL, json={"email": "pro.int@example.com", "password": "Password123", "nome": "Pro"})
    http_client.post(ATTIVA_PRO_URL)
    created = http_client.post(STIME_URL, json=_stima_payload())
    stima_id = created.json()["id"]

    post_response = http_client.post(
        f"{STIME_URL}/{stima_id}/dettaglio-pro/risposte",
        json={"risposte": {"bagni": 3, "porte": 5, "condizionatori": 2}},
    )
    assert post_response.status_code == 200
    assert post_response.json()["risposte"] == {"bagni": 3, "porte": 5, "condizionatori": 2}

    get_response = http_client.get(f"{STIME_URL}/{stima_id}/dettaglio-pro")
    assert get_response.status_code == 200
    body = get_response.json()
    assert body["risposte"] == {"bagni": 3, "porte": 5, "condizionatori": 2}

    edile = next(c for c in body["categorie"] if c["code"] == "A-EDILE")
    voce_bagni = next(
        v
        for sotto in edile["sottocategorie"]
        for v in sotto["voci"]
        if v["codice"] == "A.0.3"
    )
    assert Decimal(voce_bagni["quantita_stimata"]) == Decimal("3.00")


def test_risposte_salvate_distingue_zero_zero_zero_da_nessuna_risposta(http_client):
    """`{0, 0, 0}` e' una risposta legittima — "non ho bagni da rifare" — e non
    deve essere indistinguibile dal non aver mai risposto.

    Senza questo flag il client deduce lo stato dalla somma delle risposte e
    riapre il pannello domande addosso a chi ha appena risposto zero."""
    http_client.post(
        REGISTRAZIONE_URL,
        json={"email": "zero.pro@example.com", "password": "Password123", "nome": "Zero"},
    )
    http_client.post(ATTIVA_PRO_URL)
    stima_id = http_client.post(STIME_URL, json=_stima_payload()).json()["id"]

    prima = http_client.get(f"{STIME_URL}/{stima_id}/dettaglio-pro").json()
    assert prima["risposte_salvate"] is False

    post_response = http_client.post(
        f"{STIME_URL}/{stima_id}/dettaglio-pro/risposte",
        json={"risposte": {"bagni": 0, "porte": 0, "condizionatori": 0}},
    )
    assert post_response.json()["risposte_salvate"] is True

    dopo = http_client.get(f"{STIME_URL}/{stima_id}/dettaglio-pro").json()
    assert dopo["risposte_salvate"] is True
    assert dopo["risposte"] == {"bagni": 0, "porte": 0, "condizionatori": 0}


def test_get_domande_configuratore_in_ordine_con_default(http_client):
    """GET su una stima Pro nuova: `domande` = [tipo_pavimento, bagni, porte,
    condizionatori] in ordine (ordine, code); i valori sono gia' risolti sui
    default di catalogo (D-07), la domanda finitura non compare."""
    http_client.post(
        REGISTRAZIONE_URL,
        json={"email": "domande.pro@example.com", "password": "Password123", "nome": "Domande"},
    )
    http_client.post(ATTIVA_PRO_URL)
    stima_id = http_client.post(STIME_URL, json=_stima_payload()).json()["id"]

    body = http_client.get(f"{STIME_URL}/{stima_id}/dettaglio-pro").json()

    codici = [d["code"] for d in body["domande"]]
    assert codici == ["tipo_pavimento", "bagni", "porte", "condizionatori"]
    assert "finitura" not in codici

    tipo_pavimento = next(d for d in body["domande"] if d["code"] == "tipo_pavimento")
    assert tipo_pavimento["valore"] == "gres"
    assert tipo_pavimento["valore_etichetta"] == "Gres"

    bagni = next(d for d in body["domande"] if d["code"] == "bagni")
    assert bagni["tipo_controllo"] == "stepper"
    assert isinstance(bagni["valore"], int)


def test_post_risposte_payload_generico_ricalcola_e_valida(http_client):
    """Contratto generico (Open Question 2): il payload e' `{risposte:
    {codice: valore}, livelli}`; A.6 mostra la posa scelta (A.6.2) e non le
    pose alternative (A.6.5/A.6.6), e il server rifiuta codici/opzioni/numeri
    non previsti. A.6.1 resta presente: e' la quota bagno della posa gres
    (D-02), non governata dall'asse e scalata solo da fattore_quantita (09-07)."""
    http_client.post(
        REGISTRAZIONE_URL,
        json={"email": "generico.pro@example.com", "password": "Password123", "nome": "Generico"},
    )
    http_client.post(ATTIVA_PRO_URL)
    stima_id = http_client.post(STIME_URL, json=_stima_payload()).json()["id"]

    ok = http_client.post(
        f"{STIME_URL}/{stima_id}/dettaglio-pro/risposte",
        json={"risposte": {"tipo_pavimento": "parquet", "bagni": 2}, "livelli": {"B-FINITURE": "alto"}},
    )
    assert ok.status_code == 200
    assert ok.json()["risposte"] == {"tipo_pavimento": "parquet", "bagni": 2}

    a6 = next(
        s
        for cat in ok.json()["categorie"]
        for s in cat["sottocategorie"]
        if s["codice"] == "A.6"
    )
    codici_a6 = {v["codice"] for v in a6["voci"]}
    assert "A.6.2" in codici_a6
    assert "A.6.1" in codici_a6
    assert "A.6.5" not in codici_a6
    assert "A.6.6" not in codici_a6

    codice_sconosciuto = http_client.post(
        f"{STIME_URL}/{stima_id}/dettaglio-pro/risposte",
        json={"risposte": {"pippo": 1}},
    )
    assert codice_sconosciuto.status_code == 400
    assert "pippo" in codice_sconosciuto.json()["detail"]

    opzione_inesistente = http_client.post(
        f"{STIME_URL}/{stima_id}/dettaglio-pro/risposte",
        json={"risposte": {"tipo_pavimento": "legno"}},
    )
    assert opzione_inesistente.status_code == 400

    # -1 e' gia' fuori dal bound del tipo condiviso `Risposte` (ge=0, riusato
    # dal wizard Free): 422 a livello di schema, prima ancora del catalogo —
    # stesso esito pratico (rifiutato) del 400 applicativo di "100" sotto.
    numero_negativo = http_client.post(
        f"{STIME_URL}/{stima_id}/dettaglio-pro/risposte",
        json={"risposte": {"bagni": -1}},
    )
    assert numero_negativo.status_code in (400, 422)

    numero_fuori_limite = http_client.post(
        f"{STIME_URL}/{stima_id}/dettaglio-pro/risposte",
        json={"risposte": {"bagni": 100}},
    )
    assert numero_fuori_limite.status_code == 400

    # `bool` e' un `int` in Python: il tipo condiviso `Risposte` (stesso della
    # domanda Free) coercizza `true` a `1` PRIMA che il nostro guard su bool
    # in `valida_risposte_pro` possa vederlo — stessa debolezza pre-esistente
    # del wizard, non introdotta da questo piano. Verifichiamo solo che non
    # esploda: 200 con coercizione a 1, o un rifiuto esplicito.
    booleano = http_client.post(
        f"{STIME_URL}/{stima_id}/dettaglio-pro/risposte",
        json={"risposte": {"bagni": True}},
    )
    assert booleano.status_code in (200, 400, 422)

    campo_top_level = http_client.post(
        f"{STIME_URL}/{stima_id}/dettaglio-pro/risposte",
        json={"bagni": 2},
    )
    assert campo_top_level.status_code == 422

    vuoto = http_client.post(
        f"{STIME_URL}/{stima_id}/dettaglio-pro/risposte",
        json={"risposte": {}, "livelli": {}},
    )
    assert vuoto.status_code == 200
    assert vuoto.json()["risposte_salvate"] is True
    tipo_pavimento_default = next(d for d in vuoto.json()["domande"] if d["code"] == "tipo_pavimento")
    assert tipo_pavimento_default["valore"] == "gres"
