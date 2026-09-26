"""Taratura Pro (09-01-PLAN.md, D-03/D-04/D-08): la bozza ragionata di
coefficienti (`proponi_coefficiente`), il generatore del file Excel di
taratura + il lettore delle decisioni compilate (`genera_excel_taratura.py`).

Nessun coefficiente impresa in nessuno dei due moduli (regola di dominio #1,
CLAUDE.md) — verificato qui anche con un test anti-leak dedicato.
"""

from __future__ import annotations

from decimal import Decimal

from app.services.computo_parsing import (
    PROPOSTA_PER_CLASSE,
    PropostaCoefficiente,
    TIPI,
    TIPO_FACTOR,
    proponi_coefficiente,
)


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
