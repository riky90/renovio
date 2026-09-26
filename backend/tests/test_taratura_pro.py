"""Taratura Pro (09-01-PLAN.md, D-03/D-04/D-08): la bozza ragionata di
coefficienti (`proponi_coefficiente`), il generatore del file Excel di
taratura + il lettore delle decisioni compilate (`genera_excel_taratura.py`).

Nessun coefficiente impresa in nessuno dei due moduli (regola di dominio #1,
CLAUDE.md) — verificato qui anche con un test anti-leak dedicato.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine

from app.db import Base
from app.models.dettaglio_pro import CoefficienteQuantitaVoce
from app.services import computo_parsing
from app.services.computo_parsing import (
    PROPOSTA_PER_CLASSE,
    PropostaCoefficiente,
    TIPI,
    TIPO_FACTOR,
    coefficienti_per_voce,
    proponi_coefficiente,
)
import app.services.import_excel.parametri  # noqa: F401 - registra l'handler "parametri"
from app.services.import_excel.registry import risolvi_handler
from scripts.genera_excel_taratura import (
    accetta_bozza,
    costruisci_workbook_taratura,
    leggi_decisioni,
)
from scripts.seed import load_seed_data, seed
from tests.session_factory import sessione_di_test


class TestProponiCoefficiente:
    def test_pavimento_diverso_da_pareti_soffitti_per_tipo_totale(self):
        pavimento = proponi_coefficiente(
            "mq",
            "Posa in opera della pavimentazione con disegno a correre",
            "A.6 PAVIMENTI E RIVESTIMENTI",
            "A-EDILE",
        )
        pittura = proponi_coefficiente(
            "mq",
            "Tinteggiatura di pareti con pittura lavabile",
            "A.11 OPERE DA PITTORE",
            "A-EDILE",
        )
        assert pavimento.classe == "pavimento"
        assert pittura.classe == "pareti_soffitti"
        coeff_pav_totale, _ = pavimento.per_tipo["totale"]
        coeff_pit_totale, _ = pittura.per_tipo["totale"]
        assert coeff_pav_totale != coeff_pit_totale

    def test_rivestimento_cita_i_bagni_in_motivazione(self):
        proposta = proponi_coefficiente(
            "mq",
            "Posa in opera dei rivestimenti e stuccatura finale",
            "A.6 PAVIMENTI E RIVESTIMENTI",
            "A-EDILE",
        )
        assert proposta.classe == "rivestimento"
        assert "bagn" in proposta.motivazione.lower()

    def test_battiscopa_ml_coefficiente_in_ml_per_mq(self):
        proposta = proponi_coefficiente(
            "ml",
            "Posa in opera di battiscopa in legno mediante l'ausilio di chiodini",
            "BATTISCOPA",
            "B-FINITURE",
        )
        assert proposta.classe == "battiscopa"
        coeff, conteggio = proposta.per_tipo["totale"]
        assert coeff is not None
        assert conteggio is None

    def test_voce_cad_senza_coefficiente_per_mq_e_default_conteggio_proposto(self):
        proposta = proponi_coefficiente(
            "cad",
            "Fornitura e posa di piatto doccia",
            "RUBINETTERIE",
            "B-FINITURE",
        )
        for tipo in TIPI:
            coeff, conteggio = proposta.per_tipo[tipo]
            assert coeff is None
            assert conteggio is not None
        assert proposta.motivazione != ""

    def test_voce_cad_radiatore_usa_default_conteggio_2_con_motivazione_esplicita(self):
        proposta = proponi_coefficiente(
            "cad",
            "Fornitura e posa di radiatore in alluminio",
            "IMPIANTI",
            "A-EDILE",
        )
        _, conteggio = proposta.per_tipo["totale"]
        assert conteggio == 2
        assert "15" in proposta.motivazione

    def test_coefficiente_cresce_con_il_tipo(self):
        proposta = proponi_coefficiente(
            "mq",
            "Posa in opera della pavimentazione con disegno a correre",
            "A.6 PAVIMENTI E RIVESTIMENTI",
            "A-EDILE",
        )
        leggera, _ = proposta.per_tipo["leggera"]
        moderata, _ = proposta.per_tipo["moderata"]
        totale, _ = proposta.per_tipo["totale"]
        assert leggera <= moderata <= totale

    def test_voce_percentuale_nessuna_proposta(self):
        proposta = proponi_coefficiente("%", "Spese generali", "A.9 ASSISTENZA MURARIA", "A-EDILE")
        assert proposta.classe == "percentuale"
        for tipo in TIPI:
            coeff, conteggio = proposta.per_tipo[tipo]
            assert coeff is None
            assert conteggio is None
        assert "Riccardo" in proposta.motivazione

    def test_almeno_nove_classi_distinte_su_voci_reali_del_computo(self):
        casi = [
            ("mq", "Posa in opera della pavimentazione con disegno a correre", "A.6 PAVIMENTI E RIVESTIMENTI"),
            ("mq", "Posa in opera dei rivestimenti e stuccatura finale", "A.6 PAVIMENTI E RIVESTIMENTI"),
            ("ml", "Posa in opera di battiscopa in legno", "BATTISCOPA"),
            ("mq", "Realizzazione Massetto premiscelato pronto all'impiego", "A.2 MASSETTI"),
            ("mq", "Tinteggiatura di pareti con pittura lavabile", "A.11 OPERE DA PITTORE"),
            ("mq", "Demolizione di muratura di tamponamento", "A.1 DEMOLIZIONI - RIMOZIONI - TRASPORTO"),
            ("mq", "Fornitura e posa di finestra in PVC", "C-SERRAMENTI"),
            ("ml", "Fornitura di profilo di raccordo", "A.9 ASSISTENZA MURARIA"),
            ("mq", "Fornitura di tappeto isolante generico", "D-PRODOTTI"),
            ("cad", "Fornitura e posa di piatto doccia", "RUBINETTERIE"),
        ]
        classi = {proponi_coefficiente(um, descr, sotto, "A-EDILE").classe for um, descr, sotto in casi}
        assert len(classi) >= 9

    def test_ogni_motivazione_non_vuota(self):
        casi = [
            ("mq", "Posa in opera della pavimentazione", "A.6"),
            ("ml", "Posa in opera di battiscopa in legno", "BATTISCOPA"),
            ("cad", "Fornitura sanitario", "RUBINETTERIE"),
            ("%", "Spese generali", "A.9"),
        ]
        for um, descr, sotto in casi:
            proposta = proponi_coefficiente(um, descr, sotto, "A-EDILE")
            assert proposta.motivazione.strip() != ""

    def test_no_leak_coefficiente_impresa(self):
        import inspect

        from app.services import computo_parsing

        source = inspect.getsource(computo_parsing)
        assert "coefficiente_impresa" not in source

    def test_proposta_per_classe_ha_valori_per_tutte_le_classi_m2(self):
        for classe in ("pavimento", "rivestimento", "battiscopa", "massetto",
                        "pareti_soffitti", "demolizione", "serramento_mq",
                        "lineare", "altro_mq"):
            assert classe in PROPOSTA_PER_CLASSE
            assert isinstance(PROPOSTA_PER_CLASSE[classe], Decimal)


class TestCoefficientiPerVoce:
    """coefficienti_per_voce() (piano 09-06, D-03): deriva da
    proponi_coefficiente() con i valori per classe di taratura-classi.json,
    non piu' 0.6/0.15 x TIPO_FACTOR uniforme."""

    @pytest.fixture(autouse=True)
    def _reset_cache(self, monkeypatch):
        # ogni test imposta esplicitamente la cache (mai il file reale su disco)
        monkeypatch.setattr(computo_parsing, "_taratura_classi_cache", None)
        yield
        monkeypatch.setattr(computo_parsing, "_taratura_classi_cache", None)

    def test_senza_json_usa_il_fallback_proposta_per_classe(self, monkeypatch):
        monkeypatch.setattr(computo_parsing, "_taratura_classi_cache", {})
        coeff = coefficienti_per_voce(
            "mq", "Posa in opera della pavimentazione con disegno a correre", "A.6", "A-EDILE"
        )
        atteso = round(float(PROPOSTA_PER_CLASSE["pavimento"]) * TIPO_FACTOR["totale"], 4)
        assert coeff["totale"]["coefficiente_qta_per_mq"] == atteso

    def test_classi_diverse_danno_coefficienti_diversi_per_tipo_totale(self, monkeypatch):
        monkeypatch.setattr(
            computo_parsing,
            "_taratura_classi_cache",
            {
                "pavimento": {"leggera": "0.34", "moderata": "0.6", "totale": "0.9"},
                "pareti_soffitti": {"leggera": "1.2", "moderata": "1.8", "totale": "2.5"},
            },
        )
        pavimento = coefficienti_per_voce(
            "mq", "Posa in opera della pavimentazione con disegno a correre", "A.6", "A-EDILE"
        )
        pittura = coefficienti_per_voce(
            "mq", "Tinteggiatura di pareti con pittura lavabile", "A.11", "A-EDILE"
        )
        assert pavimento["totale"]["coefficiente_qta_per_mq"] != pittura["totale"]["coefficiente_qta_per_mq"]
        assert pavimento["totale"]["coefficiente_qta_per_mq"] == 0.9
        assert pittura["totale"]["coefficiente_qta_per_mq"] == 2.5

    def test_classe_mancante_nel_json_usa_il_fallback(self, monkeypatch):
        monkeypatch.setattr(computo_parsing, "_taratura_classi_cache", {"pavimento": {"totale": "0.9"}})
        coeff = coefficienti_per_voce(
            "mq", "Tinteggiatura di pareti con pittura lavabile", "A.11", "A-EDILE"
        )
        atteso = round(float(PROPOSTA_PER_CLASSE["pareti_soffitti"]) * TIPO_FACTOR["totale"], 4)
        assert coeff["totale"]["coefficiente_qta_per_mq"] == atteso

    def test_cad_con_parola_chiave_resta_su_domanda_mirata(self, monkeypatch):
        monkeypatch.setattr(computo_parsing, "_taratura_classi_cache", {})
        coeff = coefficienti_per_voce("cad", "Fornitura e posa di piatto doccia", "RUBINETTERIE", "B-FINITURE")
        for tipo in TIPI:
            assert coeff[tipo]["domanda_mirata_key"] == "bagni"
            assert coeff[tipo]["default_conteggio"] == 1

    def test_default_e_retrocompatibile_senza_sottocategoria_e_categoria(self, monkeypatch):
        monkeypatch.setattr(computo_parsing, "_taratura_classi_cache", {})
        coeff = coefficienti_per_voce("mq", "Demolizione di muratura di tamponamento")
        assert "coefficiente_qta_per_mq" in coeff["totale"]


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)
    with testing_session_local() as s:
        seed(s, load_seed_data())
        yield s


def _tutte_le_celle(wb):
    for nome_foglio in wb.sheetnames:
        ws = wb[nome_foglio]
        for row in ws.iter_rows():
            for cella in row:
                yield cella.value


class TestWorkbookTaratura:
    def test_fogli_presenti(self, session):
        wb = costruisci_workbook_taratura(session)
        for nome in (
            "ISTRUZIONI",
            "moltiplicatori",
            "listino_categoria",
            "extra",
            "coefficienti_pro",
            "forfait_arredo",
            "assi_proposti",
            "dati_richiesti",
            "LEGGIMI_TARATURA",
        ):
            assert nome in wb.sheetnames

        assert "AVVISO" not in wb.sheetnames

    def test_coefficienti_pro_righe_coerenti_con_db(self, session):
        wb = costruisci_workbook_taratura(session)
        n_db = session.query(CoefficienteQuantitaVoce).count()
        ws = wb["coefficienti_pro"]
        assert ws.max_row - 1 == n_db

    def test_round_trip_senza_scarti(self, session):
        wb = costruisci_workbook_taratura(session)
        righe, scarti_parse = risolvi_handler("parametri").parse(wb)
        assert scarti_parse == []
        nuove, modificate, scarti_diff = risolvi_handler("parametri").diff(session, righe)
        assert scarti_diff == []
        assert nuove == []
        # Le uniche modifiche ammesse sono sul foglio coefficienti_pro, sui
        # campi coefficiente_qta_per_mq / default_conteggio (D-04).
        for m in modificate:
            assert m.foglio == "coefficienti_pro"
            assert set(m.campi_modificati) <= {"coefficiente_qta_per_mq", "default_conteggio"}

    def test_nessuna_cella_contiene_coefficiente_impresa_o_avviso(self, session):
        wb = costruisci_workbook_taratura(session)
        assert "AVVISO" not in wb.sheetnames
        for valore in _tutte_le_celle(wb):
            if isinstance(valore, str):
                assert "coefficiente_impresa" not in valore

    def test_stato_iniziale_da_compilare(self, session):
        wb = costruisci_workbook_taratura(session)
        decisioni = leggi_decisioni(wb)
        assert decisioni.stato == "da-compilare"

    def test_leggi_decisioni_ok_atteso_valore_proposto(self, session):
        wb = costruisci_workbook_taratura(session)
        decisioni = leggi_decisioni(wb)
        assert len(decisioni.coefficienti) == session.query(CoefficienteQuantitaVoce).count()

    def test_leggi_decisioni_attuale_legge_colonne_attuali(self, session):
        wb = costruisci_workbook_taratura(session)
        ws = wb["coefficienti_pro"]
        header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
        idx = {n: i for i, n in enumerate(header)}
        prima_riga = next(ws.iter_rows(min_row=2, max_row=2))
        prima_riga[idx["decisione"]].value = "ATTUALE"
        attuale = prima_riga[idx["coefficiente_attuale"]].value

        decisioni = leggi_decisioni(wb)
        voce_id = prima_riga[idx["voce_id"]].value
        tipo_code = prima_riga[idx["tipo_code"]].value
        trovato = next(c for c in decisioni.coefficienti if c.voce_id == voce_id and c.tipo_code == tipo_code)
        if attuale is None:
            assert trovato.coefficiente_qta_per_mq is None
        else:
            assert float(trovato.coefficiente_qta_per_mq) == pytest.approx(attuale)

    def test_leggi_decisioni_valore_non_riconosciuto_solleva(self, session):
        wb = costruisci_workbook_taratura(session)
        ws = wb["coefficienti_pro"]
        header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
        idx = {n: i for i, n in enumerate(header)}
        prima_riga = next(ws.iter_rows(min_row=2, max_row=2))
        prima_riga[idx["decisione"]].value = "BOH"

        with pytest.raises(ValueError):
            leggi_decisioni(wb)

    def test_riga_assi_con_decisione_no_esclusa(self, session):
        wb = costruisci_workbook_taratura(session)
        ws = wb["assi_proposti"]
        header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
        idx = {n: i for i, n in enumerate(header)}
        prima_riga = next(ws.iter_rows(min_row=2, max_row=2))
        voce_id = prima_riga[idx["voce_id"]].value
        asse = prima_riga[idx["asse_proposto"]].value
        prima_riga[idx["decisione"]].value = "NO"

        decisioni = leggi_decisioni(wb)
        assert not any(a.voce_id == voce_id and a.asse == asse for a in decisioni.assi)

    def test_stato_fuori_insieme_ammesso_solleva(self, session):
        wb = costruisci_workbook_taratura(session)
        ws = wb["LEGGIMI_TARATURA"]
        header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
        idx_sezione = header.index("sezione")
        idx_testo = header.index("testo")
        for riga in ws.iter_rows(min_row=2):
            if riga[idx_sezione].value == "stato":
                riga[idx_testo].value = "qualcosa-a-caso"
                break

        with pytest.raises(ValueError):
            leggi_decisioni(wb)

    def test_accetta_bozza_stato_e_decisioni(self, session):
        wb = costruisci_workbook_taratura(session)
        bozza = accetta_bozza(wb)

        decisioni = leggi_decisioni(bozza)
        assert decisioni.stato == "bozza-accettata"
        assert len(decisioni.coefficienti) == session.query(CoefficienteQuantitaVoce).count()

        ws_coeff = bozza["coefficienti_pro"]
        header = [c.value for c in next(ws_coeff.iter_rows(min_row=1, max_row=1))]
        idx = {n: i for i, n in enumerate(header)}
        for riga in ws_coeff.iter_rows(min_row=2):
            assert riga[idx["decisione"]].value == "OK"

        ws_assi = bozza["assi_proposti"]
        header_assi = [c.value for c in next(ws_assi.iter_rows(min_row=1, max_row=1))]
        idx_assi = {n: i for i, n in enumerate(header_assi)}
        for riga in ws_assi.iter_rows(min_row=2):
            assert riga[idx_assi["decisione"]].value == "OK"

        ws_dati = bozza["dati_richiesti"]
        header_dati = [c.value for c in next(ws_dati.iter_rows(min_row=1, max_row=1))]
        idx_dati = {n: i for i, n in enumerate(header_dati)}
        for riga in ws_dati.iter_rows(min_row=2):
            assert riga[idx_dati["valore_riccardo"]].value == riga[idx_dati["valore_proposto_claude"]].value

        assert "AVVISO" not in bozza.sheetnames
        for valore in _tutte_le_celle(bozza):
            if isinstance(valore, str):
                assert "coefficiente_impresa" not in valore

    def test_workbook_originale_non_modificato_da_accetta_bozza(self, session):
        wb = costruisci_workbook_taratura(session)
        decisioni_prima = leggi_decisioni(wb)
        accetta_bozza(wb)
        decisioni_dopo = leggi_decisioni(wb)
        assert decisioni_prima.stato == decisioni_dopo.stato == "da-compilare"

    def test_assi_proposti_riflette_le_voci_con_livello_curato(self, session):
        """La curatela di `voce.livello` vive solo su dev.db, non sul seed
        di questa fixture in-memory (STATE.md/09-CONTEXT.md): si simula qui
        curando 3 voci, per verificare che `proponi_assegnazione` propone
        l'asse finitura esattamente su quelle e non su altre."""
        from app.models.dettaglio_pro import Voce

        candidate = session.query(Voce).limit(3).all()
        for v, livello in zip(candidate, ("base", "medio", "alto")):
            v.livello = livello
        session.flush()

        wb = costruisci_workbook_taratura(session)
        ws = wb["assi_proposti"]
        header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
        idx = {n: i for i, n in enumerate(header)}
        righe_finitura = {
            r[idx["voce_id"]]
            for r in ws.iter_rows(min_row=2, values_only=True)
            if r[idx["asse_proposto"]] == "finitura" and r[idx["livello_attuale"]] is not None
        }
        assert righe_finitura == {v.id for v in candidate}
        session.rollback()

    def test_assi_proposti_contiene_le_pose_a6(self, session):
        wb = costruisci_workbook_taratura(session)
        ws = wb["assi_proposti"]
        header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
        idx = {n: i for i, n in enumerate(header)}
        codici_pavimento = {
            r[idx["codice_voce"]]
            for r in ws.iter_rows(min_row=2, values_only=True)
            if r[idx["asse_proposto"]] == "tipo_pavimento" and r[idx["codice_voce"]] is not None
        }
        assert {"A.6.1", "A.6.2", "A.6.5", "A.6.6"} <= codici_pavimento

    def test_dati_richiesti_ha_almeno_14_righe(self, session):
        wb = costruisci_workbook_taratura(session)
        ws = wb["dati_richiesti"]
        assert ws.max_row - 1 >= 14
