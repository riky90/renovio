"""Arredo (migrazione 0015, fase 07).

Tre cose contano piu' dei numeri.

1. **L'arredo sta FUORI dal totale lavori.** `E-ARREDO` e' una categoria vera
   in tabella, ma `nel_totale_lavori=False` la tiene fuori dal motore Free.
   L'oracolo primario (85 mq totale RE -> 47.251-69.473) e la riconciliazione
   `Sigma categorie + extra = totale` devono restare intatti CON la categoria
   seminata: e' la prova che l'esclusione e' un dato che funziona, non una
   coincidenza.
2. **Mai una sezione a zero.** Nessun ambiente scelto, nessun forfait curato,
   layer spento: `arredo is None`. Stessa regola del `BonusService`.
3. **Il servizio non conosce il codice della domanda.** Rinominare
   `ambienti_arredo` non deve rompere niente: quello che conta e' che
   un'opzione abbia una riga di `forfait_arredo`.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import app.db as db_module
from app.db import Base
from app.limiter import limiter
from app.main import app
from app.models.arredo import ForfaitArredo
from app.models.bonus import BonusFiscale
from app.models.catalogo import Categoria
from app.models.domanda import Domanda, OpzioneDomanda
from app.services.arredo import ArredoService
from app.services.bonus_service import BonusService
from app.services.city_resolver import resolve_listino
from app.services.estimation import EstimationService
from scripts.seed import load_seed_data, seed
from tests.computo_spento import catalogo_v2
from tests.session_factory import sessione_di_test

STIMA_URL = "/api/v1/stima"
DAL_2026 = date(2026, 6, 1)


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)
    with testing_session_local() as s:
        seed(s, load_seed_data())
        # Numeri del percorso EUR/m2 + effetti (catalogo v2): tests/computo_spento.py
        catalogo_v2(s)
        yield s


def _stima(session, mq: int = 85, tipo: str = "totale", risposte=None):
    listino, _ = resolve_listino(session, "Reggio Emilia")
    return EstimationService.compute(session, listino, mq=mq, tipo=tipo, risposte=risposte)


class TestCategoriaFuoriDalTotale:
    def test_e_arredo_esiste_ed_e_esclusa_dal_totale(self, session):
        cat = session.get(Categoria, "E-ARREDO")
        assert cat is not None
        assert cat.nel_totale_lavori is False
        # Le altre quattro restano dentro: la colonna nasce a `true` e solo
        # l'arredo viene abbassato dal seed.
        dentro = {
            c.code for c in session.query(Categoria).filter(Categoria.nel_totale_lavori.is_(True))
        }
        assert dentro == {"A-EDILE", "B-FINITURE", "C-SERRAMENTI", "D-PRODOTTI"}

    def test_oracolo_primario_invariato(self, session):
        """85 mq totale RE con `E-ARREDO` in tabella: il numero non si muove."""
        result = _stima(session)
        assert result.totale_min == Decimal("47251")
        assert result.totale_max == Decimal("69473")

    def test_arredo_non_compare_fra_le_categorie(self, session):
        result = _stima(session)
        assert [c.code for c in result.categorie] == [
            "A-EDILE",
            "B-FINITURE",
            "C-SERRAMENTI",
            "D-PRODOTTI",
        ]

    def test_riconciliazione_esatta(self, session):
        result = _stima(session)
        somma_cat_min = sum((c.totale_min for c in result.categorie), Decimal("0"))
        somma_cat_max = sum((c.totale_max for c in result.categorie), Decimal("0"))
        extra = sum((e.totale for e in result.extra), Decimal("0"))
        assert somma_cat_min + extra == result.totale_min
        assert somma_cat_max + extra == result.totale_max

    def test_riportare_arredo_nel_totale_lo_cambia(self, session):
        """La controprova che il filtro e' vivo: rimettendo `E-ARREDO` dentro,
        il motore la cerca davvero — e fallisce, perche' non ha riga di
        listino. E' il modo piu' onesto di dimostrare che la categoria non
        viene semplicemente ignorata a valle."""
        session.get(Categoria, "E-ARREDO").nel_totale_lavori = True
        session.flush()
        with pytest.raises(Exception):
            _stima(session)


class TestForfait:
    def test_layer_spento_nessun_arredo(self, session):
        assert ArredoService.compute(session, None) is None

    def test_nessun_ambiente_scelto_nessun_arredo(self, session):
        """Mai una sezione a zero: `{}` accende il layer ma non sceglie
        ambienti, e la multiselect non ha default."""
        assert ArredoService.compute(session, {}) is None

    def test_somma_esatta_dei_forfait(self, session):
        risposte = {"ambienti_arredo": ["cucina", "bagno"], "livello_finiture": "medio"}
        result = ArredoService.compute(session, risposte)

        assert result is not None
        assert result.livello_code == "medio"
        assert [a.code for a in result.ambienti] == ["cucina", "bagno"]
        attesi = _forfait(session, ["cucina", "bagno"], "medio")
        assert result.totale_min == sum(r[0] for r in attesi)
        assert result.totale_max == sum(r[1] for r in attesi)

    def test_ordine_del_catalogo_non_del_db(self, session):
        """Gli ambienti tornano nell'ordine in cui l'utente li ha visti, non in
        quello in cui il DB restituisce i forfait."""
        result = ArredoService.compute(
            session, {"ambienti_arredo": ["bagno", "cucina", "camera"]}
        )
        assert [a.code for a in result.ambienti] == ["cucina", "camera", "bagno"]

    def test_livello_non_risposto_cade_sul_default(self, session):
        senza = ArredoService.compute(session, {"ambienti_arredo": ["cucina"]})
        medio = ArredoService.compute(
            session, {"ambienti_arredo": ["cucina"], "livello_finiture": "medio"}
        )
        assert senza.livello_code == "medio"
        assert (senza.totale_min, senza.totale_max) == (medio.totale_min, medio.totale_max)

    def test_livello_alto_costa_piu_del_base(self, session):
        base = ArredoService.compute(
            session, {"ambienti_arredo": ["cucina"], "livello_finiture": "base"}
        )
        alto = ArredoService.compute(
            session, {"ambienti_arredo": ["cucina"], "livello_finiture": "alto"}
        )
        assert alto.totale_min > base.totale_min
        assert alto.totale_max > base.totale_max

    def test_forfait_mancante_per_quel_livello_nessun_arredo(self, session):
        """Un ambiente senza forfait curato per il livello scelto non
        contribuisce, e se non resta nessun ambiente la sezione sparisce
        invece di comparire a zero."""
        session.query(ForfaitArredo).filter(ForfaitArredo.livello_code == "alto").delete()
        session.flush()
        assert (
            ArredoService.compute(
                session, {"ambienti_arredo": ["cucina"], "livello_finiture": "alto"}
            )
            is None
        )

    def test_forfait_disattivato_non_conta(self, session):
        for riga in session.query(ForfaitArredo).all():
            riga.attivo = False
        session.flush()
        assert ArredoService.compute(session, {"ambienti_arredo": ["cucina"]}) is None

    def test_il_servizio_non_conosce_il_codice_della_domanda(self, session):
        """Il legame e' la FK `forfait_arredo.opzione_id`, non una stringa.
        Rinominare la domanda non deve cambiare un euro."""
        prima = ArredoService.compute(session, {"ambienti_arredo": ["cucina"]})

        domanda = session.get(Domanda, "ambienti_arredo")
        for opzione in session.query(OpzioneDomanda).filter_by(domanda_code=domanda.code):
            opzione.domanda_code = "arredamento"
        nuova = Domanda(
            code="arredamento",
            testo=domanda.testo,
            tipo_controllo=domanda.tipo_controllo,
            gruppo=domanda.gruppo,
            ordine=domanda.ordine,
            tier_minimo=domanda.tier_minimo,
        )
        session.add(nuova)
        session.delete(domanda)
        session.flush()

        dopo = ArredoService.compute(session, {"arredamento": ["cucina"]})
        assert dopo is not None
        assert (dopo.totale_min, dopo.totale_max) == (prima.totale_min, prima.totale_max)


class TestBonusMobili:
    """ARR-04: accendere il Bonus Mobili deve essere un FLAG, non un deploy."""

    def test_seminato_ma_spento(self, session):
        mobili = session.get(BonusFiscale, "MOBILI")
        assert mobili is not None
        assert mobili.attivo is False

    def test_acceso_calcola_sulla_base_arredo(self, session):
        session.get(BonusFiscale, "MOBILI").attivo = True
        session.flush()

        arredo = ArredoService.compute(session, {"ambienti_arredo": ["bagno"]})
        categorie = [_CatFinta("E-ARREDO", arredo.totale_min, arredo.totale_max)]
        result = BonusService.compute(session, categorie, "prima_casa", "d", DAL_2026)

        assert result is not None
        mobili = next(b for b in result.bonus if b.code == "MOBILI")
        assert mobili.base_min == arredo.totale_min
        assert mobili.detrazione_max == (arredo.totale_max * mobili.aliquota_pct).quantize(
            Decimal("1")
        )

    def test_acceso_ma_senza_arredo_non_compare(self, session):
        """Base a zero -> il bonus e' ESCLUSO, non calcolato a 0."""
        session.get(BonusFiscale, "MOBILI").attivo = True
        session.flush()

        result = BonusService.compute(
            session, _categorie_lavori(session), "prima_casa", "d", DAL_2026
        )
        assert "MOBILI" not in {b.code for b in result.bonus}

    def test_tetto_di_spesa_cappa_la_base(self, session):
        """Una cucina di alto livello supera i 5.000 EUR di tetto: la
        detrazione si ferma li'."""
        session.get(BonusFiscale, "MOBILI").attivo = True
        session.flush()

        arredo = ArredoService.compute(
            session, {"ambienti_arredo": ["cucina"], "livello_finiture": "alto"}
        )
        categorie = [_CatFinta("E-ARREDO", arredo.totale_min, arredo.totale_max)]
        result = BonusService.compute(session, categorie, "prima_casa", "d", DAL_2026)

        mobili = next(b for b in result.bonus if b.code == "MOBILI")
        assert mobili.tetto_raggiunto is True
        assert mobili.base_max == mobili.tetto_spesa_eur

    def test_arredo_non_finisce_nel_bonus_ristrutturazione(self, session):
        """Nessuna doppia detrazione: `E-ARREDO` alimenta solo MOBILI."""
        from app.models.bonus import BonusCategoria

        righe = session.query(BonusCategoria).filter_by(categoria_code="E-ARREDO").all()
        assert {r.bonus_code for r in righe} == {"MOBILI"}


class _CatFinta:
    """Il `BonusService` accetta qualunque oggetto con code/totale_min/max
    (Protocol), che e' esattamente come il router gli passa l'arredo."""

    def __init__(self, code: str, totale_min: Decimal, totale_max: Decimal):
        self.code = code
        self.totale_min = totale_min
        self.totale_max = totale_max


def _categorie_lavori(session):
    return [
        _CatFinta(c.code, c.totale_min, c.totale_max) for c in _stima(session).categorie
    ]


def _forfait(session, ambienti: list[str], livello: str) -> list[tuple[Decimal, Decimal]]:
    righe = (
        session.query(ForfaitArredo)
        .join(OpzioneDomanda, ForfaitArredo.opzione_id == OpzioneDomanda.id)
        .filter(OpzioneDomanda.code.in_(ambienti), ForfaitArredo.livello_code == livello)
        .all()
    )
    return [(r.eur_min, r.eur_max) for r in righe]


@pytest.fixture()
def client(monkeypatch, tmp_path):
    limiter.reset()

    db_path = tmp_path / "test_arredo.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)
    with testing_session_local() as s:
        seed(s, load_seed_data())
        # Numeri del percorso EUR/m2 + effetti (catalogo v2): tests/computo_spento.py
        catalogo_v2(s)
        s.commit()

    monkeypatch.setattr(db_module, "SessionLocal", testing_session_local)
    import app.routers.stima as stima_router_module

    monkeypatch.setattr(stima_router_module, "SessionLocal", testing_session_local)
    with TestClient(app) as c:
        yield c


class TestApi:
    """`arredo` e' FRATELLO di `totale` nel payload, con il disclaimer dentro."""

    def test_senza_ambienti_la_chiave_e_none(self, client):
        r = client.post(STIMA_URL, json={"citta": "Reggio Emilia", "mq": 85, "tipo": "totale"})
        assert r.status_code == 200
        body = r.json()
        assert body["arredo"] is None
        assert [c["code"] for c in body["categorie"]] == [
            "A-EDILE",
            "B-FINITURE",
            "C-SERRAMENTI",
            "D-PRODOTTI",
        ]

    def test_con_ambienti_compare_accanto_al_totale(self, client):
        payload = {
            "citta": "Reggio Emilia",
            "mq": 85,
            "tipo": "totale",
            "risposte": {"ambienti_arredo": ["cucina", "bagno"], "livello_finiture": "medio"},
        }
        r = client.post(STIMA_URL, json=payload)
        assert r.status_code == 200
        body = r.json()

        arredo = body["arredo"]
        assert arredo is not None
        assert arredo["livello_code"] == "medio"
        assert [a["code"] for a in arredo["ambienti"]] == ["cucina", "bagno"]
        assert arredo["disclaimer"]

        # Il totale resta il TOTALE LAVORI: l'arredo non ci entra.
        assert Decimal(body["totale"]["totale_min"]) == Decimal("47251")
        assert Decimal(body["totale"]["totale_max"]) == Decimal("69473")
        assert Decimal(arredo["totale_min"]) > 0

    def test_nessuna_chiave_di_margine_nel_payload_arredo(self, client):
        """Stesso presidio anti-leak di `test_no_leak`, applicato allo schema
        nuovo: nel JSON serializzato non deve comparire nulla di impresa."""
        payload = {
            "citta": "Reggio Emilia",
            "mq": 85,
            "tipo": "totale",
            "risposte": {"ambienti_arredo": ["cucina"]},
        }
        raw = client.post(STIMA_URL, json=payload).text.lower()
        for vietata in ("impresa", "coefficiente_impresa", "prezzo_impresa", "margine"):
            assert vietata not in raw
