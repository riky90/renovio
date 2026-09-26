"""applica_taratura.py (09-07-PLAN.md Task 1): applica_assi() ripetibile che
ricostruisce da zero, dalle decisioni del file di taratura (D-08), gli
effetti Pro a bersaglio naturale sulle cinque domande gestite
(finitura/tipo_pavimento/bagni/porte/condizionatori), lasciando intatto tutto
il resto (Free compreso). Su decisioni e JSON sintetici: nessun numero di
taratura cablato come verita'."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine

from app.db import Base
from scripts.genera_excel_taratura import AsseDeciso, DecisioniTaratura
from scripts.applica_taratura import (
    applica_assi,
    risolvi_chiave_naturale,
)
from scripts.seed import load_seed_data, seed
from tests.session_factory import sessione_di_test

CHIAVE_GRES_BASE = {
    "categoria_code": "B-FINITURE",
    "sottocategoria": "PAVIMENTI E RIVESTIMENTI GRES",
    "voce": "Gres base",
}
CHIAVE_A6_1 = {"categoria_code": "A-EDILE", "sottocategoria": "A.6", "voce": "A.6.1"}
CHIAVE_A0_3 = {"categoria_code": "A-EDILE", "sottocategoria": "A.0", "voce": "A.0.3"}


def _seed_domande_sintetico() -> dict:
    return {
        "domande": [
            {
                "code": "finitura",
                "opzioni": [
                    {"code": "base", "effetti": []},
                    {"code": "medio", "effetti": []},
                    {"code": "alto", "effetti": []},
                ],
            },
            {
                "code": "tipo_pavimento",
                "opzioni": [
                    {"code": "gres", "effetti": []},
                    {"code": "parquet", "effetti": []},
                    {"code": "maxi_lastra", "effetti": []},
                    {"code": "mosaico", "effetti": []},
                ],
            },
            {
                "code": "bagni",
                "opzioni": [
                    {
                        "code": "valore",
                        "effetti": [
                            {
                                "tipo_effetto": "eur_per_scostamento",
                                "target_categoria_code": "A-EDILE",
                                "valore": "1900",
                            },
                            {
                                "tipo_effetto": "quantita_per_unita",
                                "valore": 1,
                                "target_voce": dict(CHIAVE_A0_3),
                            },
                        ],
                    }
                ],
            },
        ]
    }


def _riga(
    *,
    voce_id: int,
    asse: str,
    opzione: str | None = None,
    valore_per_unita: Decimal | None = None,
    fattore_quantita: Decimal | None = None,
    famiglia: str = "comune",
    decisione: str = "OK",
    note: str = "",
) -> AsseDeciso:
    return AsseDeciso(
        voce_id=voce_id,
        asse=asse,
        opzione=opzione,
        valore_per_unita=valore_per_unita,
        fattore_quantita=fattore_quantita,
        famiglia_alternativa=famiglia,
        decisione=decisione,
        note=note,
    )


def _decisioni(assi: list[AsseDeciso], stato: str = "bozza-accettata") -> DecisioniTaratura:
    return DecisioniTaratura(stato=stato, coefficienti=[], assi=assi, dati={})


class TestApplicaAssiFinitura:
    def test_includi_sullopzione_indicata(self):
        decisioni = _decisioni([_riga(voce_id=1, asse="finitura", opzione="medio")])
        chiavi = {1: dict(CHIAVE_GRES_BASE)}

        risultato = applica_assi(decisioni, _seed_domande_sintetico(), chiavi)

        finitura = next(d for d in risultato.seed_domande["domande"] if d["code"] == "finitura")
        medio = next(o for o in finitura["opzioni"] if o["code"] == "medio")
        assert medio["effetti"] == [{"tipo_effetto": "includi", "target_voce": CHIAVE_GRES_BASE}]
        base = next(o for o in finitura["opzioni"] if o["code"] == "base")
        assert base["effetti"] == []

    def test_no_non_compare_nel_risultato(self):
        """leggi_decisioni scarta le righe NO: applica_assi non le vede mai,
        quindi un effetto preesistente sulla stessa opzione sparisce se non
        rientra fra le decisioni passate."""
        seed_domande = _seed_domande_sintetico()
        finitura = next(d for d in seed_domande["domande"] if d["code"] == "finitura")
        medio = next(o for o in finitura["opzioni"] if o["code"] == "medio")
        medio["effetti"] = [{"tipo_effetto": "includi", "target_voce": dict(CHIAVE_GRES_BASE)}]

        decisioni = _decisioni([])  # nessuna riga approvata: la voce NO e' assente
        risultato = applica_assi(decisioni, seed_domande, chiavi={})

        finitura_out = next(d for d in risultato.seed_domande["domande"] if d["code"] == "finitura")
        medio_out = next(o for o in finitura_out["opzioni"] if o["code"] == "medio")
        assert medio_out["effetti"] == []


class TestApplicaAssiStepper:
    def test_valore_per_unita_sostituisce_effetto_09_02(self):
        decisioni = _decisioni(
            [_riga(voce_id=3, asse="bagni", valore_per_unita=Decimal("2"), famiglia="stepper_bagni")]
        )
        chiavi = {3: dict(CHIAVE_A0_3)}

        risultato = applica_assi(decisioni, _seed_domande_sintetico(), chiavi)

        bagni = next(d for d in risultato.seed_domande["domande"] if d["code"] == "bagni")
        valore = next(o for o in bagni["opzioni"] if o["code"] == "valore")
        quantita = [e for e in valore["effetti"] if e["tipo_effetto"] == "quantita_per_unita"]
        assert quantita == [
            {"tipo_effetto": "quantita_per_unita", "valore": 2.0, "target_voce": CHIAVE_A0_3}
        ]
        # un solo effetto quantita_per_unita per voce/opzione, mai due
        assert len(quantita) == 1

    def test_effetti_senza_bersaglio_naturale_restano_identici(self):
        decisioni = _decisioni([])
        seed_domande = _seed_domande_sintetico()

        risultato = applica_assi(decisioni, seed_domande, chiavi={})

        bagni = next(d for d in risultato.seed_domande["domande"] if d["code"] == "bagni")
        valore = next(o for o in bagni["opzioni"] if o["code"] == "valore")
        liberi = [e for e in valore["effetti"] if e["tipo_effetto"] == "eur_per_scostamento"]
        assert liberi == [
            {"tipo_effetto": "eur_per_scostamento", "target_categoria_code": "A-EDILE", "valore": "1900"}
        ]
        # e sono usciti anche dal quantita_per_unita preesistente (bersaglio naturale)
        quantita = [e for e in valore["effetti"] if e["tipo_effetto"] == "quantita_per_unita"]
        assert quantita == []


class TestApplicaAssiFattorePavimento:
    def test_produce_includi_e_fattore_quantita_su_tutte_le_opzioni_non_gres(self):
        decisioni = _decisioni(
            [
                _riga(
                    voce_id=10,
                    asse="fattore_pavimento",
                    opzione="parquet",
                    fattore_quantita=Decimal("0.12"),
                    famiglia="posa_pavimento_A6",
                )
            ]
        )
        chiavi = {10: dict(CHIAVE_A6_1)}

        risultato = applica_assi(decisioni, _seed_domande_sintetico(), chiavi)

        tipo_pav = next(d for d in risultato.seed_domande["domande"] if d["code"] == "tipo_pavimento")
        parquet = next(o for o in tipo_pav["opzioni"] if o["code"] == "parquet")
        tipi = {e["tipo_effetto"] for e in parquet["effetti"]}
        assert tipi == {"includi", "fattore_quantita"}
        fattore = next(e for e in parquet["effetti"] if e["tipo_effetto"] == "fattore_quantita")
        assert fattore["valore"] == 0.12
        assert fattore["target_voce"] == CHIAVE_A6_1

    def test_famiglia_bagno_distinta_dalla_famiglia_principale(self):
        decisioni = _decisioni(
            [
                _riga(
                    voce_id=10,
                    asse="fattore_pavimento",
                    opzione="parquet",
                    fattore_quantita=Decimal("0.12"),
                    famiglia="posa_pavimento_A6",
                ),
                _riga(voce_id=11, asse="tipo_pavimento", opzione="parquet", famiglia="posa_pavimento_A6"),
            ]
        )
        chiavi = {
            10: dict(CHIAVE_A6_1),
            11: {"categoria_code": "A-EDILE", "sottocategoria": "A.6", "voce": "A.6.2"},
        }

        risultato = applica_assi(decisioni, _seed_domande_sintetico(), chiavi)

        famiglie = {(f["voce"], f["famiglia"]) for f in risultato.famiglie}
        assert ("A.6.1", "posa_pavimento_A6:bagno") in famiglie
        assert ("A.6.2", "posa_pavimento_A6") in famiglie


class TestApplicaAssiEscludiSempre:
    def test_escludi_su_tutte_e_tre_le_opzioni_di_finitura(self):
        decisioni = _decisioni(
            [_riga(voce_id=20, asse="escludi_sempre", famiglia="sanitari_vaso")]
        )
        chiave = {"categoria_code": "B-FINITURE", "sottocategoria": "RUBINETTERIE", "voce": "Vaso extra"}
        chiavi = {20: chiave}

        risultato = applica_assi(decisioni, _seed_domande_sintetico(), chiavi)

        finitura = next(d for d in risultato.seed_domande["domande"] if d["code"] == "finitura")
        for opzione in finitura["opzioni"]:
            assert opzione["effetti"] == [{"tipo_effetto": "escludi", "target_voce": chiave}]


class TestApplicaAssiSempreInclusa:
    def test_nessun_effetto_creato(self):
        decisioni = _decisioni([_riga(voce_id=30, asse="sempre_inclusa", famiglia="comune")])
        chiavi = {30: {"categoria_code": "B-FINITURE", "sottocategoria": "PRODOTTI", "voce": "Accessorio"}}

        risultato = applica_assi(decisioni, _seed_domande_sintetico(), chiavi)

        for domanda in risultato.seed_domande["domande"]:
            for opzione in domanda.get("opzioni", []):
                assert opzione.get("effetti", []) == [] or all(
                    e.get("target_voce") != chiavi[30] for e in opzione["effetti"]
                )
        # ma la voce entra comunque nella lista famiglie (per il conteggio)
        assert any(f["voce"] == "Accessorio" for f in risultato.famiglie)


class TestApplicaAssiStatoEIdempotenza:
    def test_stato_riportato(self):
        decisioni = _decisioni([], stato="bozza-accettata")
        risultato = applica_assi(decisioni, _seed_domande_sintetico(), chiavi={})
        assert risultato.stato == "bozza-accettata"

    def test_da_compilare_solleva_errore(self):
        decisioni = _decisioni([], stato="da-compilare")
        with pytest.raises(ValueError):
            applica_assi(decisioni, _seed_domande_sintetico(), chiavi={})

    def test_idempotenza_applicando_due_volte(self):
        decisioni = _decisioni(
            [
                _riga(voce_id=1, asse="finitura", opzione="medio"),
                _riga(voce_id=3, asse="bagni", valore_per_unita=Decimal("2"), famiglia="stepper_bagni"),
            ]
        )
        chiavi = {1: dict(CHIAVE_GRES_BASE), 3: dict(CHIAVE_A0_3)}

        primo = applica_assi(decisioni, _seed_domande_sintetico(), chiavi)
        secondo = applica_assi(decisioni, primo.seed_domande, chiavi)

        assert primo.seed_domande == secondo.seed_domande

    def test_righe_modificato_tracciate(self):
        decisioni = _decisioni(
            [_riga(voce_id=1, asse="finitura", opzione="medio", decisione="MODIFICATO", note="corretto a mano")]
        )
        risultato = applica_assi(decisioni, _seed_domande_sintetico(), {1: dict(CHIAVE_GRES_BASE)})
        assert len(risultato.modificate) == 1
        assert "MODIFICATO" in risultato.modificate[0]


class TestRisolviChiaveNaturale:
    @pytest.fixture()
    def session(self):
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        testing_session_local = sessione_di_test(engine)
        with testing_session_local() as s:
            seed(s, load_seed_data())
            yield s

    def test_risolve_voce_con_codice(self, session):
        from app.models.dettaglio_pro import Voce

        voce = session.query(Voce).filter(Voce.codice.isnot(None)).first()
        assert voce is not None

        chiave = risolvi_chiave_naturale(session, voce.id)

        assert chiave is not None
        assert chiave["voce"] == voce.codice

    def test_risolve_voce_senza_codice_usa_descrizione(self, session):
        from app.models.dettaglio_pro import Voce

        voce = session.query(Voce).filter(Voce.codice.is_(None)).first()
        assert voce is not None

        chiave = risolvi_chiave_naturale(session, voce.id)

        assert chiave is not None
        assert chiave["voce"] == voce.descrizione

    def test_voce_inesistente_torna_none(self, session):
        assert risolvi_chiave_naturale(session, 10**9) is None
