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
    OPZIONI_CON_QUOTA_BAGNO_A6_1,
    OPZIONI_TIPO_PAVIMENTO,
    VoceTaraturaInfo,
    _FATTORE_BAGNO_PROPOSTO,
    accetta_bozza,
    aggiorna_foglio_assi,
    costruisci_workbook_taratura,
    leggi_decisioni,
    proponi_assegnazione,
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


# --- 09-09-PLAN.md Task 1: G1/G2 (09-HUMAN-UAT.md) ---------------------------
# Regole di proposta per i nuovi pavimenti (laminato/vinilico_lvt/moquette),
# A.6 intera, gres a pavimento; aggiornamento del foglio assi_proposti di un
# workbook esistente.


def _voce(
    voce_id: int,
    *,
    categoria_code: str = "A-EDILE",
    sottocategoria_codice: str | None = "A.6",
    sottocategoria_nome: str = "A.6 PAVIMENTI E RIVESTIMENTI",
    famiglia: str = "gerarchica",
    codice_voce: str | None = None,
    descrizione: str = "",
    um: str = "mq",
    prezzo: Decimal = Decimal("10"),
    livello: str | None = None,
    domanda_mirata_key: str | None = None,
) -> VoceTaraturaInfo:
    return VoceTaraturaInfo(
        voce_id=voce_id,
        categoria_code=categoria_code,
        sottocategoria_codice=sottocategoria_codice,
        sottocategoria_nome=sottocategoria_nome,
        famiglia=famiglia,
        codice_voce=codice_voce,
        descrizione=descrizione,
        um=um,
        prezzo_unitario_cliente=prezzo,
        livello_attuale=livello,
        domanda_mirata_key=domanda_mirata_key,
    )


def _voci_a6() -> list[VoceTaraturaInfo]:
    return [
        _voce(1, codice_voce="A.6.1", descrizione="Posa in opera della pavimentazione con disegno a correre"),
        _voce(2, codice_voce="A.6.2", descrizione="Posa in opera di parquet prefinito a correre incollato o flottante"),
        _voce(3, codice_voce="A.6.3", descrizione="Posa in opera dei rivestimenti formati da 20 a 60 cm"),
        _voce(4, codice_voce="A.6.4", descrizione="Posa in opera dei rivestimenti formati da 65 a 120 cm"),
        _voce(5, codice_voce="A.6.5", descrizione="Posa in opera dei rivestimenti MAXI LASTRA"),
        _voce(6, codice_voce="A.6.6", descrizione="Posa in opera di mosaico"),
        _voce(7, codice_voce="A.6.7", descrizione="Posa in opera di battiscopa in legno mediante l'ausilio di chiodini", um="ml"),
        _voce(8, codice_voce="A.6.8", descrizione="Posa in opera di battiscopa in ceramica", um="ml"),
        _voce(9, codice_voce="A.6.9", descrizione="Arrotatura, levigatura e lucidatura di pavimenti in marmo"),
        _voce(10, codice_voce="A.6.10", descrizione="Levigatura e Lucidatura di pavimenti in parquet"),
        _voce(11, codice_voce="A.6.11", descrizione="Taglio porta blindata per allarme", um="ac"),
    ]


class TestProponiAssegnazioneA6Intera:
    def test_a62_produce_tre_righe_parquet_laminato_vinilico(self):
        righe = proponi_assegnazione(_voci_a6())
        opzioni = {r.opzione_proposta for r in righe if r.codice_voce == "A.6.2"}
        assert opzioni == {"parquet", "laminato", "vinilico_lvt"}
        assert all(r.asse_proposto == "tipo_pavimento" for r in righe if r.codice_voce == "A.6.2")

    def test_a67_battiscopa_legno_quattro_opzioni(self):
        righe = proponi_assegnazione(_voci_a6())
        opzioni = {r.opzione_proposta for r in righe if r.codice_voce == "A.6.7"}
        assert opzioni == {"parquet", "laminato", "vinilico_lvt", "moquette"}

    def test_a68_battiscopa_ceramica_tre_opzioni(self):
        righe = proponi_assegnazione(_voci_a6())
        opzioni = {r.opzione_proposta for r in righe if r.codice_voce == "A.6.8"}
        assert opzioni == {"gres", "maxi_lastra", "mosaico"}

    def test_a610_solo_parquet(self):
        righe = proponi_assegnazione(_voci_a6())
        righe_a610 = [r for r in righe if r.codice_voce == "A.6.10"]
        assert len(righe_a610) == 1
        assert righe_a610[0].opzione_proposta == "parquet"

    def test_a69_asse_escludi_sempre(self):
        righe = proponi_assegnazione(_voci_a6())
        righe_a69 = [r for r in righe if r.codice_voce == "A.6.9"]
        assert len(righe_a69) == 1
        assert righe_a69[0].asse_proposto == "escludi_sempre"
        assert righe_a69[0].opzione_proposta is None

    def test_a63_a64_asse_finitura_base_medio_alto(self):
        righe = proponi_assegnazione(_voci_a6())
        opzioni_63 = {r.opzione_proposta for r in righe if r.codice_voce == "A.6.3"}
        opzioni_64 = {r.opzione_proposta for r in righe if r.codice_voce == "A.6.4"}
        assert opzioni_63 == {"base", "medio"}
        assert opzioni_64 == {"alto"}
        assert all(r.asse_proposto == "finitura" for r in righe if r.codice_voce in ("A.6.3", "A.6.4"))
        assert all(
            r.famiglia_alternativa == "posa_rivestimento_A6" for r in righe if r.codice_voce in ("A.6.3", "A.6.4")
        )

    def test_a61_fattore_pavimento_cinque_opzioni_senza_moquette(self):
        righe = proponi_assegnazione(_voci_a6())
        righe_fattore = [r for r in righe if r.codice_voce == "A.6.1" and r.asse_proposto == "fattore_pavimento"]
        opzioni = {r.opzione_proposta for r in righe_fattore}
        assert opzioni == set(OPZIONI_CON_QUOTA_BAGNO_A6_1)
        assert "moquette" not in opzioni
        for r in righe_fattore:
            assert r.fattore_quantita == _FATTORE_BAGNO_PROPOSTO

    def test_a611_nessuna_riga_resta_comune(self):
        righe = proponi_assegnazione(_voci_a6())
        assert not any(r.codice_voce == "A.6.11" for r in righe)


class TestProponiAssegnazioneForniturePavimenti:
    def _voci_catalogo(self) -> list[VoceTaraturaInfo]:
        return [
            _voce(
                101, categoria_code="B-FINITURE", sottocategoria_codice=None, sottocategoria_nome="PAVIMENTI",
                famiglia="catalogo", descrizione="Vinilico multistrato LVT in listoni", um="mq",
            ),
            _voce(
                102, categoria_code="B-FINITURE", sottocategoria_codice=None, sottocategoria_nome="PAVIMENTI",
                famiglia="catalogo", descrizione="Pavimento in laminato antistatico", um="mq",
            ),
            _voce(
                103, categoria_code="B-FINITURE", sottocategoria_codice=None, sottocategoria_nome="PAVIMENTI",
                famiglia="catalogo", descrizione="Unilin sottofondo in schiuma senza barriera vapore", um="mq",
            ),
            _voce(
                104, categoria_code="B-FINITURE", sottocategoria_codice=None, sottocategoria_nome="PAVIMENTI",
                famiglia="catalogo", descrizione="Moquette in quadrotte autoposanti", um="mq",
            ),
            _voce(
                105, categoria_code="B-FINITURE", sottocategoria_codice=None, sottocategoria_nome="BATTISCOPA",
                famiglia="catalogo", descrizione="Zoccolino in legno massello", um="ml",
            ),
            _voce(
                106, categoria_code="B-FINITURE", sottocategoria_codice=None, sottocategoria_nome="BATTISCOPA",
                famiglia="catalogo", descrizione="Zoccolino in gres porcellanato", um="ml",
            ),
        ]

    def test_vinilico_governato_da_vinilico_lvt(self):
        righe = proponi_assegnazione(self._voci_catalogo())
        riga = next(r for r in righe if r.voce_id == 101)
        assert riga.asse_proposto == "tipo_pavimento"
        assert riga.opzione_proposta == "vinilico_lvt"
        assert riga.famiglia_alternativa == "fornitura_pavimento_vinilico"

    def test_laminato_governato_da_laminato(self):
        righe = proponi_assegnazione(self._voci_catalogo())
        riga = next(r for r in righe if r.voce_id == 102)
        assert riga.opzione_proposta == "laminato"
        assert riga.famiglia_alternativa == "fornitura_pavimento_laminato"

    def test_sottofondo_governato_da_laminato_famiglia_distinta(self):
        righe = proponi_assegnazione(self._voci_catalogo())
        riga = next(r for r in righe if r.voce_id == 103)
        assert riga.opzione_proposta == "laminato"
        assert riga.famiglia_alternativa == "sottofondo_laminato"

    def test_moquette_governata_da_moquette(self):
        righe = proponi_assegnazione(self._voci_catalogo())
        riga = next(r for r in righe if r.voce_id == 104)
        assert riga.opzione_proposta == "moquette"
        assert riga.famiglia_alternativa == "fornitura_pavimento_moquette"

    def test_zoccolino_legno_quattro_opzioni(self):
        righe = proponi_assegnazione(self._voci_catalogo())
        opzioni = {r.opzione_proposta for r in righe if r.voce_id == 105}
        assert opzioni == {"parquet", "laminato", "vinilico_lvt", "moquette"}

    def test_zoccolino_gres_tre_opzioni(self):
        righe = proponi_assegnazione(self._voci_catalogo())
        opzioni = {r.opzione_proposta for r in righe if r.voce_id == 106}
        assert opzioni == {"gres", "maxi_lastra", "mosaico"}

    def test_nessuna_voce_pavimento_resta_sempre_inclusa(self):
        righe = proponi_assegnazione(self._voci_catalogo())
        for voce_id in (101, 102, 103, 104):
            assert not any(r.voce_id == voce_id and r.asse_proposto == "sempre_inclusa" for r in righe)


class TestProponiAssegnazioneGresAPavimento:
    def test_gres_a_pavimento_famiglia_dedicata_e_fattore_bagno(self):
        voce = _voce(
            201,
            categoria_code="B-FINITURE",
            sottocategoria_codice=None,
            sottocategoria_nome="PAVIMENTI E RIVESTIMENTI GRES",
            famiglia="catalogo",
            descrizione="Fornitura gres porcellanato per pavimentazioni interne",
            um="mq",
            livello="medio",
        )
        righe = proponi_assegnazione([voce])

        riga_finitura = next(r for r in righe if r.asse_proposto == "finitura")
        assert riga_finitura.famiglia_alternativa == "fornitura_pavimento_gres"
        assert riga_finitura.opzione_proposta == "medio"

        righe_fattore = [r for r in righe if r.asse_proposto == "fattore_pavimento"]
        opzioni = {r.opzione_proposta for r in righe_fattore}
        assert opzioni == {o for o in OPZIONI_TIPO_PAVIMENTO if o != "gres"}
        for r in righe_fattore:
            assert r.fattore_quantita == _FATTORE_BAGNO_PROPOSTO
            assert r.famiglia_alternativa == "fornitura_pavimento_gres"

    def test_gres_rivestimento_resta_famiglia_finitura_sottocategoria(self):
        voce = _voce(
            202,
            categoria_code="B-FINITURE",
            sottocategoria_codice=None,
            sottocategoria_nome="PAVIMENTI E RIVESTIMENTI GRES",
            famiglia="catalogo",
            descrizione="Fornitura gres porcellanato per rivestimenti bagno",
            um="mq",
            livello="base",
        )
        righe = proponi_assegnazione([voce])

        riga = next(r for r in righe if r.voce_id == 202)
        assert riga.famiglia_alternativa == "finitura:PAVIMENTI E RIVESTIMENTI GRES"
        assert not any(r.asse_proposto == "fattore_pavimento" for r in righe)


class TestAggiornaFoglioAssi:
    @pytest.fixture()
    def session(self):
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        testing_session_local = sessione_di_test(engine)
        with testing_session_local() as s:
            seed(s, load_seed_data())
            yield s

    def test_conserva_decisione_e_note_su_chiave_identica(self, session):
        from scripts.genera_excel_taratura import _carica_voci_taratura

        wb = costruisci_workbook_taratura(session)
        ws = wb["assi_proposti"]
        header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
        idx = {n: i for i, n in enumerate(header)}
        prima_riga = next(ws.iter_rows(min_row=2, max_row=2))
        prima_riga[idx["decisione"]].value = "MODIFICATO"
        prima_riga[idx["note"]].value = "nota di Riccardo"
        voce_id = prima_riga[idx["voce_id"]].value
        asse = prima_riga[idx["asse_proposto"]].value
        opzione = prima_riga[idx["opzione_proposta"]].value

        info = _carica_voci_taratura(session)
        righe_nuove = proponi_assegnazione(list(info.values()))

        aggiornato = aggiorna_foglio_assi(wb, righe_nuove)
        ws_agg = aggiornato["assi_proposti"]
        header_agg = [c.value for c in next(ws_agg.iter_rows(min_row=1, max_row=1))]
        idx_agg = {n: i for i, n in enumerate(header_agg)}
        trovata = next(
            r
            for r in ws_agg.iter_rows(min_row=2, values_only=True)
            if r[idx_agg["voce_id"]] == voce_id
            and r[idx_agg["asse_proposto"]] == asse
            and r[idx_agg["opzione_proposta"]] == opzione
        )
        assert trovata[idx_agg["decisione"]] == "MODIFICATO"
        assert trovata[idx_agg["note"]] == "nota di Riccardo"

    def test_righe_nuove_bozza_accettata_ok_con_nota(self, session):
        from scripts.genera_excel_taratura import _NOTE_BOZZA_ACCETTATA, _carica_voci_taratura

        wb = costruisci_workbook_taratura(session)
        bozza = accetta_bozza(wb)

        info = _carica_voci_taratura(session)
        righe_nuove = proponi_assegnazione(list(info.values()))

        aggiornato = aggiorna_foglio_assi(bozza, righe_nuove)
        ws_agg = aggiornato["assi_proposti"]
        header_agg = [c.value for c in next(ws_agg.iter_rows(min_row=1, max_row=1))]
        idx_agg = {n: i for i, n in enumerate(header_agg)}
        for r in ws_agg.iter_rows(min_row=2, values_only=True):
            assert r[idx_agg["decisione"]] == "OK"
            assert r[idx_agg["note"]] == _NOTE_BOZZA_ACCETTATA

    def test_finitura_da_livello_sparita_fallisce_invece_di_perdere_le_decisioni(self, session):
        """WR-06 (review 09): il foglio vecchio ha righe 'finitura' derivate da
        voce.livello, la nuova proposta (DB con livello vuoto) nessuna ->
        ValueError, niente riscrittura silenziosa."""
        from scripts.genera_excel_taratura import _carica_voci_taratura

        wb = costruisci_workbook_taratura(session)
        bozza = accetta_bozza(wb)
        ws = bozza["assi_proposti"]
        header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
        riga_finitura = [None] * len(header)
        riga_finitura[header.index("voce_id")] = 999999
        riga_finitura[header.index("livello_attuale")] = "medio"
        riga_finitura[header.index("asse_proposto")] = "finitura"
        riga_finitura[header.index("opzione_proposta")] = "medio"
        riga_finitura[header.index("decisione")] = "OK"
        ws.append(riga_finitura)

        info = _carica_voci_taratura(session)
        righe_nuove = proponi_assegnazione(list(info.values()))
        assert not any(r.asse_proposto == "finitura" and r.livello_attuale for r in righe_nuove)

        with pytest.raises(ValueError, match="voce.livello"):
            aggiorna_foglio_assi(bozza, righe_nuove)

    def test_coefficienti_pro_invariato_byte_per_byte_nei_valori(self, session):
        from scripts.genera_excel_taratura import _carica_voci_taratura

        wb = costruisci_workbook_taratura(session)
        valori_prima = [[c.value for c in row] for row in wb["coefficienti_pro"].iter_rows()]

        info = _carica_voci_taratura(session)
        righe_nuove = proponi_assegnazione(list(info.values()))
        aggiornato = aggiorna_foglio_assi(wb, righe_nuove)

        valori_dopo = [[c.value for c in row] for row in aggiornato["coefficienti_pro"].iter_rows()]
        assert valori_prima == valori_dopo
