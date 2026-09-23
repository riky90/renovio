"""Bonus fiscali (migrazione 0011).

Due cose sono piu' importanti dei numeri:

1. **Gli snapshot v1 devono continuare a funzionare.** Nessuna riga `stima`
   salvata prima di questa feature ha la chiave `bonus` ne'
   `input.destinazione`. Un `snapshot["bonus"]` diretto romperebbe tutto lo
   storico di tutti gli utenti.
2. **Le aliquote sono un dato, non codice.** Il calo del 2027 deve avvenire
   cambiando la data di riferimento, senza toccare una riga di Python.

Oracolo: 85 mq totale a Reggio Emilia, prima casa, 2026 — lo stesso caso su cui
e' pinnato `test_estimation.py` (47.985-70.575), che deve restare intatto.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import app.db as db_module
from app.db import Base
from app.limiter import limiter
from app.main import app
from app.models.bonus import AliquotaBonus, BonusCategoria, BonusExtra, BonusFiscale
from app.models.stima_salvata import StimaSalvata
from app.services.bonus_service import BonusService
from app.services.city_resolver import resolve_listino
from app.services.estimation import EstimationService
from scripts.seed import load_seed_data, seed
from tests.session_factory import sessione_di_test

STIMA_URL = "/api/v1/stima"
STIME_URL = "/api/v1/me/stime"
REGISTRAZIONE_URL = "/api/v1/auth/registrati"
ADMIN_BONUS_URL = "/api/v1/admin/bonus"

DAL_2026 = date(2026, 6, 1)
DAL_2027 = date(2027, 6, 1)


@dataclass
class CategoriaFinta:
    """Il servizio accetta qualunque oggetto con code/totale_min/totale_max
    (Protocol): questi test lo sfruttano per pinnare basi esatte senza passare
    dal motore."""

    code: str
    totale_min: Decimal
    totale_max: Decimal


@dataclass
class ExtraFinto:
    """Un extra ha un solo lordo, non un range (importo fisso IVA inclusa)."""

    code: str
    totale: Decimal


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)
    with testing_session_local() as s:
        seed(s, load_seed_data())
        yield s


def _categorie_reali(session) -> list[CategoriaFinta]:
    listino, _ = resolve_listino(session, "Reggio Emilia")
    result = EstimationService.compute(session, listino, mq=85, tipo="totale")
    return [CategoriaFinta(c.code, c.totale_min, c.totale_max) for c in result.categorie]


def _extra_reali(session) -> list[ExtraFinto]:
    listino, _ = resolve_listino(session, "Reggio Emilia")
    result = EstimationService.compute(session, listino, mq=85, tipo="totale")
    return [ExtraFinto(e.code, e.totale) for e in result.extra]


class TestOracolo:
    def test_prima_casa_2026(self, session):
        """85 mq totale RE, abitazione principale, 2026: il 50% della spesa
        mappata, in 10 rate."""
        result = BonusService.compute(session, _categorie_reali(session), "prima_casa", "d", DAL_2026)

        assert result is not None
        per_code = {b.code: b for b in result.bonus}
        assert set(per_code) == {"RISTRUTTURAZIONE", "ECOBONUS"}
        assert per_code["RISTRUTTURAZIONE"].aliquota_pct == Decimal("0.5000")
        assert result.detrazione_min == Decimal("22590")
        assert result.detrazione_max == Decimal("33885")
        # La rata annua e' la detrazione su 10 anni, per bonus.
        assert result.rata_annua_min == Decimal("2259")
        assert result.rata_annua_max == Decimal("3389")

    def test_seconda_casa_scende_al_36(self, session):
        prima = BonusService.compute(session, _categorie_reali(session), "prima_casa", "d", DAL_2026)
        altro = BonusService.compute(session, _categorie_reali(session), "altro", "d", DAL_2026)

        assert altro.detrazione_max < prima.detrazione_max
        aliquote = {b.code: b.aliquota_pct for b in altro.bonus}
        assert aliquote["RISTRUTTURAZIONE"] == Decimal("0.3600")

    def test_serramenti_vanno_su_ecobonus(self, session):
        """C-SERRAMENTI non deve finire nel bonus ristrutturazione: e' il
        mapping che evita il doppio conteggio e rispetta la normativa."""
        categorie = _categorie_reali(session)
        serramenti = next(c for c in categorie if c.code == "C-SERRAMENTI")

        result = BonusService.compute(session, categorie, "prima_casa", "d", DAL_2026)

        eco = next(b for b in result.bonus if b.code == "ECOBONUS")
        assert eco.base_max == serramenti.totale_max


class TestAliquoteComeDato:
    def test_2027_applica_le_aliquote_ridotte_senza_toccare_il_codice(self, session):
        """Il cuore del design: cambia solo la data di riferimento."""
        nel_2026 = BonusService.compute(session, _categorie_reali(session), "prima_casa", "d", DAL_2026)
        nel_2027 = BonusService.compute(session, _categorie_reali(session), "prima_casa", "d", DAL_2027)

        assert nel_2026.detrazione_max > nel_2027.detrazione_max
        assert {b.aliquota_pct for b in nel_2027.bonus} == {Decimal("0.3600")}

    def test_nessuna_aliquota_valida_esclude_il_bonus_senza_eccezione(self, session):
        """Una data fuori da ogni finestra non e' un errore: la sezione bonus
        sparisce. Dire "recuperi 0 EUR" sarebbe peggio che non dire nulla."""
        result = BonusService.compute(
            session, _categorie_reali(session), "prima_casa", "d", date(2020, 1, 1)
        )

        assert result is None

    def test_bonus_spenti_non_compaiono(self, session):
        """MOBILI e SISMABONUS sono seminati ma `attivo=False`: esistono in
        tabella e non nella risposta."""
        result = BonusService.compute(session, _categorie_reali(session), "prima_casa", "d", DAL_2026)

        assert {b.code for b in result.bonus} == {"RISTRUTTURAZIONE", "ECOBONUS"}
        assert session.get(BonusFiscale, "MOBILI") is not None


class TestTetto:
    def test_tetto_applicato_prima_dell_aliquota(self, session):
        """Base 200.000 su un tetto di 96.000 -> detrazione 48.000, non
        100.000."""
        categorie = [CategoriaFinta("A-EDILE", Decimal("200000"), Decimal("200000"))]

        result = BonusService.compute(session, categorie, "prima_casa", "d", DAL_2026)

        ristrutturazione = next(b for b in result.bonus if b.code == "RISTRUTTURAZIONE")
        assert ristrutturazione.base_max == Decimal("96000")
        assert ristrutturazione.detrazione_max == Decimal("48000")
        assert ristrutturazione.tetto_raggiunto is True

    def test_il_range_si_comprime_quando_solo_il_max_sfora(self, session):
        """Sotto il tetto il minimo, sopra il massimo: il range della
        detrazione si stringe. Non e' un artefatto — oltre il tetto la spesa in
        piu' non produce detrazione."""
        categorie = [CategoriaFinta("A-EDILE", Decimal("80000"), Decimal("150000"))]

        result = BonusService.compute(session, categorie, "prima_casa", "d", DAL_2026)

        b = next(x for x in result.bonus if x.code == "RISTRUTTURAZIONE")
        assert b.base_min == Decimal("80000")
        assert b.base_max == Decimal("96000")
        assert b.detrazione_min == Decimal("40000")
        assert b.detrazione_max == Decimal("48000")

    def test_base_a_zero_esclude_il_bonus(self, session):
        categorie = [CategoriaFinta("A-EDILE", Decimal("0"), Decimal("0"))]

        result = BonusService.compute(session, categorie, "prima_casa", "d", DAL_2026)

        assert result is None or all(b.code != "RISTRUTTURAZIONE" for b in result.bonus)


class TestExtraNellaBase:
    """CSE/CSP e pratiche amministrative SONO spesa detraibile.

    Prima della tabella `bonus_extra` la base sommava solo le categorie e la
    detrazione usciva sottostimata di ~1.400 EUR su una stima da 85 m2 — in
    silenzio, senza errori, solo un numero piu' basso del vero. Questi test
    esistono perche' quella sottostima non possa tornare inosservata.
    """

    def test_gli_extra_alzano_la_base_del_bonus_ristrutturazione(self, session):
        categorie = _categorie_reali(session)
        extra = _extra_reali(session)
        lordo_extra = sum((e.totale for e in extra), Decimal("0"))

        senza = BonusService.compute(session, categorie, "prima_casa", "d", DAL_2026)
        con = BonusService.compute(
            session, categorie, "prima_casa", "d", DAL_2026, extra=extra
        )

        b_senza = next(b for b in senza.bonus if b.code == "RISTRUTTURAZIONE")
        b_con = next(b for b in con.bonus if b.code == "RISTRUTTURAZIONE")
        assert lordo_extra > 0
        assert b_con.base_min - b_senza.base_min == lordo_extra
        assert b_con.base_max - b_senza.base_max == lordo_extra

    def test_extra_omessi_lasciano_il_calcolo_invariato(self, session):
        """`extra=None` vuol dire "nessun extra", non "usa un default": il
        comportamento dei chiamanti che non li passano non cambia."""
        categorie = _categorie_reali(session)

        assert BonusService.compute(
            session, categorie, "prima_casa", "d", DAL_2026
        ) == BonusService.compute(session, categorie, "prima_casa", "d", DAL_2026, extra=[])

    def test_extra_non_mappato_resta_fuori(self, session):
        """La detraibilita' di un extra e' curatela, non una regola cablata: un
        codice che non sta in `bonus_extra` non alza la base."""
        categorie = _categorie_reali(session)
        atteso = BonusService.compute(session, categorie, "prima_casa", "d", DAL_2026)

        con_ignoto = BonusService.compute(
            session,
            categorie,
            "prima_casa",
            "d",
            DAL_2026,
            extra=[ExtraFinto("smaltimento_extra", Decimal("5000"))],
        )

        assert con_ignoto == atteso

    def test_nessuna_spesa_detraibile_resta_fuori(self, session):
        """L'invariante che conta: con il seed attuale ogni categoria e ogni
        extra e' mappato a quota 1, quindi la somma delle basi deve coprire
        l'INTERO totale della stima. Se un domani una categoria o un extra
        nuovo restasse non mappato, questo test cade."""
        listino, _ = resolve_listino(session, "Reggio Emilia")
        stima = EstimationService.compute(session, listino, mq=85, tipo="totale")

        result = BonusService.compute(
            session,
            [CategoriaFinta(c.code, c.totale_min, c.totale_max) for c in stima.categorie],
            "prima_casa",
            "d",
            DAL_2026,
            extra=[ExtraFinto(e.code, e.totale) for e in stima.extra],
        )

        assert sum((b.base_max for b in result.bonus), Decimal("0")) == stima.totale_max

    def test_quote_extra_seminate_non_superano_il_100_per_cento(self, session):
        quote = BonusService.quote_per_extra(session)

        assert quote, "il seed deve mappare almeno un extra"
        for extra_code, totale in quote.items():
            assert totale <= Decimal("1"), f"{extra_code} supera il 100%"

    def test_ogni_extra_del_listino_e_mappato(self, session):
        """Un extra seminato ma non mappato e' una sottostima silenziosa: e'
        esattamente il bug che questa tabella chiude."""
        from app.models.catalogo import Extra

        attivi = {b.code for b in session.query(BonusFiscale).filter_by(attivo=True).all()}
        mappati = {
            m.extra_code for m in session.query(BonusExtra).all() if m.bonus_code in attivi
        }
        seminati = {e.code for e in session.query(Extra).filter_by(attivo=True).all()}

        assert seminati <= mappati


class TestAntiDoppioConteggio:
    def test_le_quote_seminate_non_superano_il_100_per_cento(self, session):
        """Invariante di dominio: la stessa spesa non puo' essere detratta due
        volte."""
        quote = BonusService.quote_per_categoria(session)

        assert quote, "il seed deve mappare almeno una categoria"
        for categoria, totale in quote.items():
            assert totale <= Decimal("1"), f"{categoria} supera il 100%"

    def test_ogni_categoria_e_mappata_su_un_solo_bonus_attivo(self, session):
        attivi = {b.code for b in session.query(BonusFiscale).filter_by(attivo=True).all()}
        conteggio: dict[str, int] = {}
        for mappa in session.query(BonusCategoria).all():
            if mappa.bonus_code in attivi:
                conteggio[mappa.categoria_code] = conteggio.get(mappa.categoria_code, 0) + 1

        assert all(n == 1 for n in conteggio.values())


class TestMassimaliEcobonus:
    """Guardia sul massimale per_intervento dell'ECOBONUS.

    Il tetto seminato, 60.000 euro, e' il massimale di *serramenti e
    schermature*. I massimali dell'ecobonus non sono uno solo — cappotto
    60.000, climatizzazione 30.000, riqualificazione globale 100.000 — ma
    `aliquota_bonus` ne tiene uno per (bonus, destinazione, periodo).

    Finche' l'unica categoria che alimenta l'ECOBONUS e' `C-SERRAMENTI` il
    valore e' semplicemente giusto, e differenziare i massimali sarebbe
    astrazione per un caso che non esiste. Il giorno che una seconda categoria
    ci si attacca, pero', quel 60.000 diventa una detrazione sbagliata
    calcolata in silenzio su una spesa che ha un altro tetto.

    Questo test e' il punto in cui quel giorno fa rumore invece di passare
    inosservato: un TODO non ferma nessuno, un test rosso si'.
    """

    def test_ecobonus_e_alimentato_da_una_sola_categoria(self, session):
        categorie = {
            m.categoria_code
            for m in session.query(BonusCategoria).filter_by(bonus_code="ECOBONUS").all()
        }

        assert categorie == {"C-SERRAMENTI"}, (
            "Una seconda categoria alimenta l'ECOBONUS. Il tetto per_intervento e' "
            "unico per (bonus, destinazione, periodo) e vale 60.000, cioe' il "
            "massimale dei soli serramenti: prima di aggiungere questa categoria "
            "il massimale va differenziato per tipo di intervento, altrimenti la "
            "detrazione esce sbagliata senza che nulla lo segnali. "
            f"Categorie trovate: {sorted(categorie)}"
        )

    def test_il_tetto_seminato_e_quello_dei_serramenti(self, session):
        """Se qualcuno cambia il numero, deve farlo sapendo a quale intervento
        si riferisce."""
        tetti = {
            a.tetto_spesa_eur
            for a in session.query(AliquotaBonus).filter_by(bonus_code="ECOBONUS").all()
        }

        assert tetti == {Decimal("60000.00")}


class TestSeedIdempotente:
    def test_seed_ripetuto_non_duplica_aliquote(self, session):
        prima = session.query(AliquotaBonus).count()

        seed(session, load_seed_data())

        assert session.query(AliquotaBonus).count() == prima

    def test_riga_2027_gia_presente(self, session):
        """Il calo di aliquota deve essere gia' a DB oggi, non un promemoria."""
        righe_2027 = (
            session.query(AliquotaBonus).filter(AliquotaBonus.valido_dal >= date(2027, 1, 1)).all()
        )

        assert righe_2027
        assert all(r.aliquota_pct < Decimal("0.5") for r in righe_2027)


# --- API -------------------------------------------------------------------


@pytest.fixture()
def client(monkeypatch, tmp_path):
    limiter.reset()

    db_path = tmp_path / "test_bonus.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)

    with testing_session_local() as s:
        seed(s, load_seed_data())
        s.commit()

    monkeypatch.setattr(db_module, "SessionLocal", testing_session_local)

    import app.dependencies.auth as deps_auth_module
    import app.routers.auth as auth_router_module
    import app.routers.stima as stima_router_module
    import app.routers.stime_salvate as stime_salvate_router_module

    monkeypatch.setattr(deps_auth_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(auth_router_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(stima_router_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(stime_salvate_router_module, "SessionLocal", testing_session_local)

    # Il router admin ha una sua `SessionLocal`: senza questa riga le rotte
    # admin parlerebbero col database reale e il 403 sarebbe un falso negativo.
    import app.routers.admin.bonus as admin_bonus_router_module

    monkeypatch.setattr(admin_bonus_router_module, "SessionLocal", testing_session_local)

    return TestClient(app), testing_session_local


class TestApiStima:
    def test_richiesta_senza_destinazione_resta_valida(self, client):
        """Contratto pubblico: {citta, mq, tipo} deve continuare a funzionare,
        con prima_casa come default."""
        c, _ = client

        r = c.post(STIMA_URL, json={"citta": "Reggio Emilia", "mq": 85, "tipo": "totale"})

        assert r.status_code == 200
        assert r.json()["input"]["destinazione"] == "prima_casa"
        assert r.json()["bonus"] is not None

    def test_seconda_casa_detrae_meno(self, client):
        c, _ = client
        base = {"citta": "Reggio Emilia", "mq": 85, "tipo": "totale"}

        prima = c.post(STIMA_URL, json={**base, "destinazione": "prima_casa"}).json()
        altro = c.post(STIMA_URL, json={**base, "destinazione": "altro"}).json()

        assert Decimal(altro["bonus"]["detrazione_max"]) < Decimal(prima["bonus"]["detrazione_max"])

    def test_disclaimer_dentro_la_risposta(self, client):
        """Non e' un testo della UI: viaggia nel payload, quindi finisce anche
        nello snapshot e nel PDF e il client non puo' toglierlo."""
        c, _ = client

        bonus = c.post(STIMA_URL, json={"citta": "Reggio Emilia", "mq": 85, "tipo": "totale"}).json()[
            "bonus"
        ]

        assert "capienza" in bonus["disclaimer"].lower()
        assert "consulenza fiscale" in bonus["disclaimer"].lower()

    def test_la_risposta_include_gli_extra_nella_base(self, client):
        """End-to-end: il router deve passare gli extra al servizio. Senza la
        riga `extra=result.extra` la somma delle basi resta sotto il totale e
        l'utente vede una detrazione piu' bassa del vero."""
        c, _ = client

        stima = c.post(STIMA_URL, json={"citta": "Reggio Emilia", "mq": 85, "tipo": "totale"}).json()

        basi = sum((Decimal(b["base_max"]) for b in stima["bonus"]["bonus"]), Decimal("0"))
        assert basi == Decimal(stima["totale"]["totale_max"])

    def test_destinazione_invalida_422(self, client):
        c, _ = client

        r = c.post(
            STIMA_URL,
            json={"citta": "Reggio Emilia", "mq": 85, "tipo": "totale", "destinazione": "boh"},
        )

        assert r.status_code == 422


class TestSnapshot:
    def _registra(self, c):
        c.post(
            REGISTRAZIONE_URL,
            json={"email": "bonus@example.com", "password": "Password123", "nome": "Bonus"},
        )

    def test_bonus_congelato_nello_snapshot(self, client):
        c, _ = client
        self._registra(c)
        stima = c.post(STIMA_URL, json={"citta": "Reggio Emilia", "mq": 85, "tipo": "totale"}).json()

        stima_id = c.post(STIME_URL, json=stima).json()["id"]
        letta = c.get(f"{STIME_URL}/{stima_id}").json()

        assert letta["bonus"]["detrazione_max"] == stima["bonus"]["detrazione_max"]
        assert letta["input"]["destinazione"] == "prima_casa"

    def test_snapshot_v1_senza_bonus_resta_leggibile(self, client):
        """LA regressione da non introdurre: le stime salvate PRIMA di questa
        feature non hanno la chiave `bonus` ne' `input.destinazione`."""
        c, session_factory = client
        self._registra(c)
        stima = c.post(STIMA_URL, json={"citta": "Reggio Emilia", "mq": 85, "tipo": "totale"}).json()
        stima_id = c.post(STIME_URL, json=stima).json()["id"]

        # Si degrada la riga a uno snapshot v1 autentico.
        with session_factory() as session:
            row = session.get(StimaSalvata, stima_id)
            snapshot = dict(row.risultato_json)
            snapshot.pop("bonus", None)
            snapshot["input"] = {
                k: v for k, v in snapshot["input"].items() if k != "destinazione"
            }
            snapshot["schema_version"] = 1
            row.risultato_json = snapshot
            session.commit()

        letta = c.get(f"{STIME_URL}/{stima_id}")

        assert letta.status_code == 200
        assert letta.json()["bonus"] is None
        assert letta.json()["input"]["destinazione"] == "prima_casa"

    def test_schema_version_2(self, client):
        c, session_factory = client
        self._registra(c)
        stima = c.post(STIMA_URL, json={"citta": "Reggio Emilia", "mq": 85, "tipo": "totale"}).json()
        stima_id = c.post(STIME_URL, json=stima).json()["id"]

        with session_factory() as session:
            assert session.get(StimaSalvata, stima_id).risultato_json["schema_version"] == 2


class TestAdminBonus:
    """Il 409 anti-doppio-conteggio va verificato sull'endpoint, non solo in
    teoria: e' l'unico punto in cui un errore di curatela puo' entrare."""

    def _admin(self, c, session_factory):
        from app.models.user import User

        c.post(
            REGISTRAZIONE_URL,
            json={"email": "admin.bonus@example.com", "password": "Password123", "nome": "Admin"},
        )
        with session_factory() as session:
            user = session.query(User).filter_by(email="admin.bonus@example.com").one()
            # La colonna e' `role`, non `ruolo`: scrivere il nome sbagliato non
            # solleva niente su un modello SQLAlchemy, resta un attributo
            # Python inerte e il test passa dalla porta di servizio del 403.
            user.role = "admin"
            session.commit()

    def test_utente_normale_403(self, client):
        c, _ = client
        c.post(
            REGISTRAZIONE_URL,
            json={"email": "tizio@example.com", "password": "Password123", "nome": "Tizio"},
        )

        assert c.get(ADMIN_BONUS_URL).status_code == 403

    def test_anonimo_401(self, client):
        c, _ = client
        assert c.get(ADMIN_BONUS_URL).status_code == 401

    def test_mappare_lo_stesso_extra_due_volte_e_409(self, client):
        """Il vincolo anti-doppio-conteggio vale sugli extra come sulle
        categorie: CSE/CSP e' gia' al 100% sul bonus ristrutturazione."""
        c, session_factory = client
        self._admin(c, session_factory)

        r = c.post(
            f"{ADMIN_BONUS_URL}/extra",
            json={
                "bonus_code": "ECOBONUS",
                "extra_code": "CSE_CSP",
                "quota_ammissibile_pct": "1",
            },
        )

        assert r.status_code == 409
        assert "due volte" in r.json()["detail"]

    def test_extra_inesistente_404(self, client):
        c, session_factory = client
        self._admin(c, session_factory)

        r = c.post(
            f"{ADMIN_BONUS_URL}/extra",
            json={"bonus_code": "ECOBONUS", "extra_code": "inesistente"},
        )

        assert r.status_code == 404

    def test_lista_extra_mostra_la_curatela_seminata(self, client):
        c, session_factory = client
        self._admin(c, session_factory)

        righe = c.get(f"{ADMIN_BONUS_URL}/extra").json()

        assert {r["extra_code"] for r in righe} == {"CSE_CSP", "pratiche"}
        assert all(r["bonus_code"] == "RISTRUTTURAZIONE" for r in righe)
