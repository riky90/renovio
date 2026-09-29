"""applica_taratura.py (09-07-PLAN.md Task 1): applica_assi() ripetibile che
ricostruisce da zero, dalle decisioni del file di taratura (D-08), gli
effetti Pro a bersaglio naturale sulle cinque domande gestite
(finitura/tipo_pavimento/bagni/porte/condizionatori), lasciando intatto tutto
il resto (Free compreso). Su decisioni e JSON sintetici: nessun numero di
taratura cablato come verita'."""

from __future__ import annotations

from pathlib import Path
import json
import shutil
import sqlite3
import sys
from decimal import Decimal

import pytest
from sqlalchemy import create_engine

from app.db import Base
from scripts.genera_excel_taratura import AsseDeciso, CoeffDeciso, DecisioniTaratura
import scripts.applica_taratura as applica_taratura_mod
from scripts.applica_taratura import (
    DATO_PER_CLASSE,
    applica_assi,
    applica_coefficienti,
    calcola_classi,
    emetti_migrazione,
    risolvi_chiave_naturale,
)
from scripts.seed import load_seed_data, seed
from tests.session_factory import sessione_di_test


def _seed_domande_pavimenti_estesi() -> dict:
    """Come `_seed_domande_sintetico()` ma con le opzioni laminato/vinilico_lvt/
    moquette dell'asse tipo_pavimento (09-09-PLAN.md, G1/G2): serve ai test dei
    bersagli condivisi e del gres a pavimento, che il fixture originale (solo
    gres/parquet/maxi_lastra/mosaico) non copre."""
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
                    {"code": "laminato", "effetti": []},
                    {"code": "vinilico_lvt", "effetti": []},
                    {"code": "moquette", "effetti": []},
                ],
            },
        ]
    }

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
    def test_produce_solo_fattore_quantita_mai_includi(self):
        """D-02: A.6.1 (quota bagno) NON diventa bersaglio di un `includi` su
        parquet/maxi_lastra/mosaico — se lo fosse, sarebbe bersaglio di PIU'
        di un'opzione dell'asse tipo_pavimento (gres + parquet) e romperebbe
        il conteggio per-asse di CFG-02 (09-03), che assume bersagli
        disgiunti. Resta NON governata (sempre inclusa, regola 4 di
        effetti.py); solo la sua QUANTITA' cambia via fattore_quantita."""
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
        assert tipi == {"fattore_quantita"}
        fattore = next(e for e in parquet["effetti"] if e["tipo_effetto"] == "fattore_quantita")
        assert fattore["valore"] == 0.12
        assert fattore["target_voce"] == CHIAVE_A6_1

    def test_la_stessa_voce_non_riceve_includi_nemmeno_dalla_sua_riga_gres_gemella(self):
        """La riga 'tipo_pavimento'->gres della stessa voce (A.6.1, presente
        nel file di taratura reale accanto alle 3 righe fattore_pavimento)
        viene SALTATA: se avesse un includi solo su gres, sceglierne un altro
        la escluderebbe (il bug di governance che questa regola evita)."""
        decisioni = _decisioni(
            [
                _riga(voce_id=10, asse="tipo_pavimento", opzione="gres", famiglia="posa_pavimento_A6"),
                _riga(
                    voce_id=10,
                    asse="fattore_pavimento",
                    opzione="parquet",
                    fattore_quantita=Decimal("0.12"),
                    famiglia="posa_pavimento_A6",
                ),
            ]
        )
        chiavi = {10: dict(CHIAVE_A6_1)}

        risultato = applica_assi(decisioni, _seed_domande_sintetico(), chiavi)

        tipo_pav = next(d for d in risultato.seed_domande["domande"] if d["code"] == "tipo_pavimento")
        for opzione in tipo_pav["opzioni"]:
            includi = [e for e in opzione["effetti"] if e["tipo_effetto"] == "includi"]
            assert includi == [], f"opzione {opzione['code']!r} non deve avere includi per A.6.1"

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


class TestApplicaAssiDeduplicaFamiglia:
    def test_piu_voci_sulla_stessa_opzione_tengono_solo_la_prima(self):
        """Bug scoperto sui dati reali (fornitura_pavimento_parquet, battiscopa):
        la bozza 09-01 assegna piu' voci alla STESSA opzione della STESSA
        famiglia di alternative. Senza deduplica torna a sommarle (il bug che
        la fase chiude); qui restano tutte GOVERNATE (escluse quando un'altra
        opzione e' scelta) ma solo la prima (voce_id minore) resta INCLUSA."""
        decisioni = _decisioni(
            [
                _riga(voce_id=101, asse="tipo_pavimento", opzione="parquet", famiglia="battiscopa"),
                _riga(voce_id=102, asse="tipo_pavimento", opzione="parquet", famiglia="battiscopa"),
                _riga(voce_id=103, asse="tipo_pavimento", opzione="parquet", famiglia="battiscopa"),
            ]
        )
        chiavi = {
            101: {"categoria_code": "B-FINITURE", "sottocategoria": "BATTISCOPA", "voce": "Zoccolino A"},
            102: {"categoria_code": "B-FINITURE", "sottocategoria": "BATTISCOPA", "voce": "Zoccolino B"},
            103: {"categoria_code": "B-FINITURE", "sottocategoria": "BATTISCOPA", "voce": "Zoccolino C"},
        }

        risultato = applica_assi(decisioni, _seed_domande_sintetico(), chiavi)

        tipo_pav = next(d for d in risultato.seed_domande["domande"] if d["code"] == "tipo_pavimento")
        parquet = next(o for o in tipo_pav["opzioni"] if o["code"] == "parquet")

        includi_targets = {e["target_voce"]["voce"] for e in parquet["effetti"] if e["tipo_effetto"] == "includi"}
        escludi_targets = {e["target_voce"]["voce"] for e in parquet["effetti"] if e["tipo_effetto"] == "escludi"}

        assert includi_targets == {"Zoccolino A", "Zoccolino B", "Zoccolino C"}
        assert escludi_targets == {"Zoccolino B", "Zoccolino C"}
        assert len(risultato.modificate) == 2

    def test_finitura_sku_variety_non_viene_deduplicata(self):
        """La famiglia 'finitura:<sottocategoria>' (varieta' di SKU migrata da
        voce.livello) NON va deduplicata: e' comportamento intenzionale gia'
        verificato dalla 09-03."""
        decisioni = _decisioni(
            [
                _riga(voce_id=201, asse="finitura", opzione="medio", famiglia="finitura:GRES"),
                _riga(voce_id=202, asse="finitura", opzione="medio", famiglia="finitura:GRES"),
            ]
        )
        chiavi = {
            201: {"categoria_code": "B-FINITURE", "sottocategoria": "GRES", "voce": "Gres A"},
            202: {"categoria_code": "B-FINITURE", "sottocategoria": "GRES", "voce": "Gres B"},
        }

        risultato = applica_assi(decisioni, _seed_domande_sintetico(), chiavi)

        finitura = next(d for d in risultato.seed_domande["domande"] if d["code"] == "finitura")
        medio = next(o for o in finitura["opzioni"] if o["code"] == "medio")
        assert medio["effetti"] == [
            {"tipo_effetto": "includi", "target_voce": chiavi[201]},
            {"tipo_effetto": "includi", "target_voce": chiavi[202]},
        ]


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


class TestApplicaAssiFalsoPositivoGerarchica:
    def test_famiglia_alternativa_su_voce_gerarchica_viene_ignorata(self):
        """Bug scoperto sui dati reali: il match per parola-chiave delle sei
        famiglie sanitari_*/porte_apertura/condizionatori_marca cattura anche
        righe A-EDILE gerarchiche (rimozioni/montaggi) che menzionano
        "bidet"/"doccia"/"condizionatore" nel testo, non prodotti alternativi.
        Marcata come gerarchica, la riga viene ignorata: nessun effetto,
        resta sempre inclusa (comportamento pre-09-07)."""
        decisioni = _decisioni(
            [_riga(voce_id=40, asse="finitura", opzione="base", famiglia="sanitari_bidet")]
        )
        chiavi = {40: {"categoria_code": "A-EDILE", "sottocategoria": "A.0", "voce": "A.0.3"}}

        risultato = applica_assi(
            decisioni, _seed_domande_sintetico(), chiavi, sottocategorie_gerarchiche=frozenset({40})
        )

        finitura = next(d for d in risultato.seed_domande["domande"] if d["code"] == "finitura")
        for opzione in finitura["opzioni"]:
            assert opzione["effetti"] == []
        assert any("IGNORATA" in m for m in risultato.modificate)
        assert not any(f["voce"] == "A.0.3" for f in risultato.famiglie)

    def test_famiglia_alternativa_su_voce_catalogo_non_viene_ignorata(self):
        """Stessa famiglia, ma la voce e' 'catalogo' (non nell'insieme
        gerarchico passato): resta un effetto normale."""
        decisioni = _decisioni(
            [_riga(voce_id=41, asse="finitura", opzione="base", famiglia="sanitari_bidet")]
        )
        chiavi = {41: {"categoria_code": "B-FINITURE", "sottocategoria": "RUBINETTERIE", "voce": "Bidet vero"}}

        risultato = applica_assi(
            decisioni, _seed_domande_sintetico(), chiavi, sottocategorie_gerarchiche=frozenset()
        )

        finitura = next(d for d in risultato.seed_domande["domande"] if d["code"] == "finitura")
        base = next(o for o in finitura["opzioni"] if o["code"] == "base")
        assert base["effetti"] == [{"tipo_effetto": "includi", "target_voce": chiavi[41]}]


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


# --- Task 1 (09-06-PLAN.md): applica_coefficienti / calcola_classi ----------

CHIAVE_VOCE_PAVIMENTO = {
    "categoria_code": "B-FINITURE",
    "sottocategoria": "PAVIMENTI",
    "voce": "Voce pavimento",
}
CHIAVE_VOCE_PAVIMENTO_2 = {
    "categoria_code": "B-FINITURE",
    "sottocategoria": "PAVIMENTI",
    "voce": "Voce pavimento 2",
}
CHIAVE_VOCE_CONTEGGIO_MIRATO = {
    "categoria_code": "A-EDILE",
    "sottocategoria": "A.0",
    "voce": "A.0.3",
}


def _seed_dettaglio_sintetico() -> dict:
    return {
        "listino": {"nome": "Reggio Emilia"},
        "sottocategorie": [
            {
                "categoria_code": "B-FINITURE",
                "codice": None,
                "nome": "PAVIMENTI",
                "famiglia": "catalogo",
                "voci": [
                    {
                        "codice": None,
                        "descrizione": "Voce pavimento",
                        "um": "mq",
                        "prezzo_unitario_cliente": 40.0,
                        "coefficienti": {
                            "leggera": {"coefficiente_qta_per_mq": 0.24},
                            "moderata": {"coefficiente_qta_per_mq": 0.42},
                            "totale": {"coefficiente_qta_per_mq": 0.6},
                        },
                    },
                    {
                        "codice": None,
                        "descrizione": "Voce pavimento 2",
                        "um": "mq",
                        "prezzo_unitario_cliente": 42.0,
                        "coefficienti": {
                            "leggera": {"coefficiente_qta_per_mq": 0.24},
                            "moderata": {"coefficiente_qta_per_mq": 0.42},
                            "totale": {"coefficiente_qta_per_mq": 0.6},
                        },
                    },
                ],
            },
            {
                "categoria_code": "A-EDILE",
                "codice": "A.0",
                "nome": "Allestimento di cantiere",
                "famiglia": "gerarchica",
                "voci": [
                    {
                        "codice": "A.0.3",
                        "descrizione": "Rimozione sanitari bagno",
                        "um": "cad",
                        "prezzo_unitario_cliente": 40.0,
                        "coefficienti": {
                            "leggera": {"domanda_mirata_key": "bagni", "default_conteggio": 1},
                            "moderata": {"domanda_mirata_key": "bagni", "default_conteggio": 1},
                            "totale": {"domanda_mirata_key": "bagni", "default_conteggio": 1},
                        },
                    }
                ],
            },
        ],
    }


def _coeff_deciso(
    *, voce_id: int, tipo_code: str, coefficiente: str | None = None,
    conteggio: int | None = None, decisione: str = "OK", note: str = "",
) -> CoeffDeciso:
    return CoeffDeciso(
        voce_id=voce_id,
        tipo_code=tipo_code,
        coefficiente_qta_per_mq=Decimal(coefficiente) if coefficiente is not None else None,
        default_conteggio=conteggio,
        decisione=decisione,
        note=note,
    )


def _decisioni_coeff(coefficienti: list[CoeffDeciso], stato: str = "bozza-accettata", dati: dict | None = None) -> DecisioniTaratura:
    return DecisioniTaratura(stato=stato, coefficienti=coefficienti, assi=[], dati=dati or {})


class TestApplicaCoefficienti:
    def test_ok_scrive_il_valore_proposto(self):
        decisioni = _decisioni_coeff(
            [_coeff_deciso(voce_id=1, tipo_code="totale", coefficiente="0.85", decisione="OK")]
        )
        chiavi = {1: dict(CHIAVE_VOCE_PAVIMENTO)}

        nuovo, saltate = applica_coefficienti(decisioni, _seed_dettaglio_sintetico(), chiavi)

        voce = nuovo["sottocategorie"][0]["voci"][0]
        assert voce["coefficienti"]["totale"]["coefficiente_qta_per_mq"] == 0.85
        assert saltate == []

    def test_attuale_scrive_il_valore_attuale_non_cambia(self):
        decisioni = _decisioni_coeff(
            [_coeff_deciso(voce_id=1, tipo_code="totale", coefficiente="0.6", decisione="ATTUALE")]
        )
        chiavi = {1: dict(CHIAVE_VOCE_PAVIMENTO)}

        nuovo, _ = applica_coefficienti(decisioni, _seed_dettaglio_sintetico(), chiavi)

        voce = nuovo["sottocategorie"][0]["voci"][0]
        assert voce["coefficienti"]["totale"]["coefficiente_qta_per_mq"] == 0.6

    def test_modificato_scrive_il_valore_scritto_a_mano(self):
        decisioni = _decisioni_coeff(
            [_coeff_deciso(voce_id=1, tipo_code="totale", coefficiente="1.1", decisione="MODIFICATO", note="corretto")]
        )
        chiavi = {1: dict(CHIAVE_VOCE_PAVIMENTO)}

        nuovo, _ = applica_coefficienti(decisioni, _seed_dettaglio_sintetico(), chiavi)

        voce = nuovo["sottocategorie"][0]["voci"][0]
        assert voce["coefficienti"]["totale"]["coefficiente_qta_per_mq"] == 1.1

    def test_domanda_mirata_key_non_viene_persa_quando_si_scrive_default_conteggio(self):
        decisioni = _decisioni_coeff(
            [_coeff_deciso(voce_id=3, tipo_code="totale", conteggio=2, decisione="ATTUALE")]
        )
        chiavi = {3: dict(CHIAVE_VOCE_CONTEGGIO_MIRATO)}

        nuovo, _ = applica_coefficienti(decisioni, _seed_dettaglio_sintetico(), chiavi)

        voce = nuovo["sottocategorie"][1]["voci"][0]
        assert voce["coefficienti"]["totale"]["domanda_mirata_key"] == "bagni"
        assert voce["coefficienti"]["totale"]["default_conteggio"] == 2

    def test_voce_non_risolta_a_db_viene_segnalata_e_saltata(self):
        decisioni = _decisioni_coeff(
            [_coeff_deciso(voce_id=999, tipo_code="totale", coefficiente="0.85")]
        )
        originale = _seed_dettaglio_sintetico()

        nuovo, saltate = applica_coefficienti(decisioni, originale, chiavi={})

        assert len(saltate) == 1
        assert "999" in saltate[0]
        assert nuovo == originale

    def test_voce_non_presente_nel_seed_viene_segnalata_e_saltata(self):
        decisioni = _decisioni_coeff(
            [_coeff_deciso(voce_id=1, tipo_code="totale", coefficiente="0.85")]
        )
        chiavi = {1: {"categoria_code": "B-FINITURE", "sottocategoria": "SPARITA", "voce": "Non esiste"}}
        originale = _seed_dettaglio_sintetico()

        nuovo, saltate = applica_coefficienti(decisioni, originale, chiavi)

        assert len(saltate) == 1
        assert nuovo == originale

    def test_valore_negativo_solleva_errore(self):
        decisioni = _decisioni_coeff(
            [_coeff_deciso(voce_id=1, tipo_code="totale", coefficiente="-0.1")]
        )
        chiavi = {1: dict(CHIAVE_VOCE_PAVIMENTO)}

        with pytest.raises(ValueError):
            applica_coefficienti(decisioni, _seed_dettaglio_sintetico(), chiavi)

    def test_default_conteggio_negativo_solleva_errore(self):
        decisioni = _decisioni_coeff(
            [_coeff_deciso(voce_id=3, tipo_code="totale", conteggio=-1)]
        )
        chiavi = {3: dict(CHIAVE_VOCE_CONTEGGIO_MIRATO)}

        with pytest.raises(ValueError):
            applica_coefficienti(decisioni, _seed_dettaglio_sintetico(), chiavi)

    def test_idempotenza_applicando_due_volte(self):
        decisioni = _decisioni_coeff(
            [_coeff_deciso(voce_id=1, tipo_code="totale", coefficiente="0.85", decisione="OK")]
        )
        chiavi = {1: dict(CHIAVE_VOCE_PAVIMENTO)}

        primo, _ = applica_coefficienti(decisioni, _seed_dettaglio_sintetico(), chiavi)
        secondo, _ = applica_coefficienti(decisioni, primo, chiavi)

        assert primo == secondo

    def test_non_presente_nel_seed_non_solleva_eccezione(self):
        """Non un'eccezione: la voce viene solo segnalata (stessa disciplina
        del seed, D-24)."""
        decisioni = _decisioni_coeff(
            [_coeff_deciso(voce_id=1234, tipo_code="totale", coefficiente="0.85")]
        )
        _, saltate = applica_coefficienti(decisioni, _seed_dettaglio_sintetico(), chiavi={})
        assert saltate  # nessuna eccezione, solo segnalazione


class TestCalcolaClassi:
    def test_mediana_delle_voci_della_stessa_classe(self):
        decisioni = _decisioni_coeff(
            [
                _coeff_deciso(voce_id=1, tipo_code="totale", coefficiente="0.7"),
                _coeff_deciso(voce_id=2, tipo_code="totale", coefficiente="0.9"),
            ]
        )
        chiavi_classe = {1: "pavimento", 2: "pavimento"}

        classi = calcola_classi(decisioni, chiavi_classe)

        assert classi["pavimento"]["totale"] == "0.8"

    def test_classe_senza_voci_decise_usa_il_fallback_proposta_per_classe(self):
        decisioni = _decisioni_coeff([])
        classi = calcola_classi(decisioni, chiavi_classe={})

        # PROPOSTA_PER_CLASSE["battiscopa"] = 0.9, TIPO_FACTOR["totale"] = 1.0
        assert classi["battiscopa"]["totale"] == "0.9"
        assert len(classi) >= 9

    def test_bozza_accettata_riproduce_proposta_per_classe_x_tipo_factor(self):
        """Con decisioni tutte OK sulla bozza (ogni voce della classe ha lo
        stesso valore proposto), calcola_classi() riproduce esattamente
        PROPOSTA_PER_CLASSE x TIPO_FACTOR per ogni tipo."""
        decisioni = _decisioni_coeff(
            [
                _coeff_deciso(voce_id=1, tipo_code="totale", coefficiente="0.85"),
                _coeff_deciso(voce_id=1, tipo_code="moderata", coefficiente="0.595"),
                _coeff_deciso(voce_id=1, tipo_code="leggera", coefficiente="0.34"),
            ]
        )
        chiavi_classe = {1: "pavimento"}

        classi = calcola_classi(decisioni, chiavi_classe)

        assert Decimal(classi["pavimento"]["totale"]) == Decimal("0.85")
        assert Decimal(classi["pavimento"]["moderata"]) == Decimal("0.595")
        assert Decimal(classi["pavimento"]["leggera"]) == Decimal("0.34")

    def test_dato_richiesto_sovrascrive_la_mediana_per_tutti_i_tipi(self):
        decisioni = _decisioni_coeff(
            [_coeff_deciso(voce_id=1, tipo_code="totale", coefficiente="0.7")],
            dati={"quota_calpestabile": "0.95"},
        )
        chiavi_classe = {1: "pavimento"}

        classi = calcola_classi(decisioni, chiavi_classe)

        assert Decimal(classi["pavimento"]["totale"]) == Decimal("0.95")
        assert Decimal(classi["pavimento"]["moderata"]) == Decimal("0.665")
        assert Decimal(classi["pavimento"]["leggera"]) == Decimal("0.38")

    def test_dato_richiesto_con_testo_non_numerico_viene_ignorato(self):
        decisioni = _decisioni_coeff(
            [_coeff_deciso(voce_id=1, tipo_code="totale", coefficiente="0.7")],
            dati={"mq_rivestimento_bagno": "circa 20 m2 per bagno su un appartamento di riferimento"},
        )
        classi = calcola_classi(decisioni, chiavi_classe={})

        # non numerico: nessuna sovrascrittura, resta il fallback PROPOSTA_PER_CLASSE
        assert classi["rivestimento"]["totale"] == "0.25"

    def test_tutti_i_codici_dato_per_classe_sono_classi_valide(self):
        from app.services.computo_parsing import PROPOSTA_PER_CLASSE

        for classe in DATO_PER_CLASSE.values():
            assert classe in PROPOSTA_PER_CLASSE


# --- Task 3 (09-06-PLAN.md): emetti_migrazione + wiring CLI -----------------

CHIAVE_A6_1_MIGR = {"categoria_code": "A-EDILE", "sottocategoria": "A.6", "voce": "A.6.1"}
CHIAVE_GRES_MIGR = {"categoria_code": "B-FINITURE", "sottocategoria": "GRES", "voce": "Gres base"}


def _dettaglio_con_coefficiente(valore_totale: float) -> dict:
    return {
        "sottocategorie": [
            {
                "categoria_code": "A-EDILE",
                "codice": "A.6",
                "nome": "A.6",
                "voci": [
                    {
                        "codice": "A.6.1",
                        "descrizione": "Posa pavimentazione",
                        "coefficienti": {
                            "leggera": {"coefficiente_qta_per_mq": valore_totale * 0.4},
                            "moderata": {"coefficiente_qta_per_mq": valore_totale * 0.7},
                            "totale": {"coefficiente_qta_per_mq": valore_totale},
                        },
                    }
                ],
            }
        ]
    }


def _domande_con_effetti(*, includi_opzione: str | None, quantita_valore: float | None, con_escludi: bool) -> dict:
    effetti_finitura_medio = []
    effetti_finitura_alto = []
    if includi_opzione == "medio":
        effetti_finitura_medio.append({"tipo_effetto": "includi", "target_voce": dict(CHIAVE_GRES_MIGR)})
    elif includi_opzione == "alto":
        effetti_finitura_alto.append({"tipo_effetto": "includi", "target_voce": dict(CHIAVE_GRES_MIGR)})
    if con_escludi:
        effetti_finitura_medio.append({"tipo_effetto": "escludi", "target_voce": dict(CHIAVE_A6_1_MIGR)})

    effetti_bagni_valore = []
    if quantita_valore is not None:
        effetti_bagni_valore.append(
            {"tipo_effetto": "quantita_per_unita", "valore": quantita_valore, "target_voce": dict(CHIAVE_A6_1_MIGR)}
        )

    return {
        "domande": [
            {
                "code": "finitura",
                "opzioni": [
                    {"code": "base", "effetti": []},
                    {"code": "medio", "effetti": effetti_finitura_medio},
                    {"code": "alto", "effetti": effetti_finitura_alto},
                ],
            },
            {
                "code": "bagni",
                "opzioni": [{"code": "valore", "effetti": effetti_bagni_valore}],
            },
        ]
    }


class TestEmettiMigrazione:
    def test_nessuna_differenza_non_emette_nulla(self, tmp_path):
        dettaglio = _dettaglio_con_coefficiente(0.6)
        domande = _domande_con_effetti(includi_opzione="medio", quantita_valore=1.0, con_escludi=False)

        percorso = emetti_migrazione(dettaglio, dettaglio, domande, domande, tmp_path, "slug")

        assert percorso is None
        assert list(tmp_path.glob("*.py")) == []

    def test_diff_coefficiente_produce_file_con_costanti_corrette(self, tmp_path):
        base = _dettaglio_con_coefficiente(0.6)
        nuovo = _dettaglio_con_coefficiente(0.85)
        domande = _domande_con_effetti(includi_opzione="medio", quantita_valore=1.0, con_escludi=False)

        percorso = emetti_migrazione(base, nuovo, domande, domande, tmp_path, "coeff_slug")

        assert percorso is not None
        assert percorso.name == "0001_coeff_slug.py"
        codice = percorso.read_text(encoding="utf-8")
        modulo = {}
        exec(compile(codice, str(percorso), "exec"), modulo)
        assert modulo["revision"] == "0001"
        assert modulo["down_revision"] is None
        assert len(modulo["_COEFFICIENTI"]) == 3  # leggera/moderata/totale, tutte scalate
        riga = next(r for r in modulo["_COEFFICIENTI"] if r[3] == "totale")
        assert riga[:3] == ("A-EDILE", "A.6", "A.6.1")
        assert riga[4] == "coefficiente_qta_per_mq"
        assert riga[5] == pytest.approx(0.6)
        assert riga[6] == pytest.approx(0.85)
        assert modulo["_VALORI_EFFETTO"] == ()
        assert modulo["_INCLUDI_SPOSTATI"] == ()
        assert modulo["_EFFETTI_RIMOSSI"] == ()

    def test_revision_e_down_revision_dalla_testa_esistente(self, tmp_path):
        (tmp_path / "0021_qualcosa.py").write_text("revision = '0021'\n", encoding="utf-8")
        base = _dettaglio_con_coefficiente(0.6)
        nuovo = _dettaglio_con_coefficiente(0.85)
        domande = _domande_con_effetti(includi_opzione="medio", quantita_valore=1.0, con_escludi=False)

        percorso = emetti_migrazione(base, nuovo, domande, domande, tmp_path, "slug")

        assert percorso.name == "0022_slug.py"
        codice = percorso.read_text(encoding="utf-8")
        modulo = {}
        exec(compile(codice, str(percorso), "exec"), modulo)
        assert modulo["revision"] == "0022"
        assert modulo["down_revision"] == "0021"

    def test_includi_spostato(self, tmp_path):
        dettaglio = _dettaglio_con_coefficiente(0.6)
        base_domande = _domande_con_effetti(includi_opzione="medio", quantita_valore=None, con_escludi=False)
        nuovo_domande = _domande_con_effetti(includi_opzione="alto", quantita_valore=None, con_escludi=False)

        percorso = emetti_migrazione(dettaglio, dettaglio, base_domande, nuovo_domande, tmp_path, "slug")

        codice = percorso.read_text(encoding="utf-8")
        modulo = {}
        exec(compile(codice, str(percorso), "exec"), modulo)
        assert modulo["_COEFFICIENTI"] == ()
        assert len(modulo["_INCLUDI_SPOSTATI"]) == 1
        d_code, chiave_voce, opz_vecchia, opz_nuova = modulo["_INCLUDI_SPOSTATI"][0]
        assert d_code == "finitura"
        assert chiave_voce == ("B-FINITURE", "GRES", "Gres base")
        assert opz_vecchia == "medio"
        assert opz_nuova == "alto"

    def test_effetto_rimosso_quando_manca_nel_nuovo(self, tmp_path):
        dettaglio = _dettaglio_con_coefficiente(0.6)
        base_domande = _domande_con_effetti(includi_opzione="medio", quantita_valore=2.0, con_escludi=True)
        nuovo_domande = _domande_con_effetti(includi_opzione="medio", quantita_valore=None, con_escludi=False)

        percorso = emetti_migrazione(dettaglio, dettaglio, base_domande, nuovo_domande, tmp_path, "slug")

        codice = percorso.read_text(encoding="utf-8")
        modulo = {}
        exec(compile(codice, str(percorso), "exec"), modulo)
        tipi_rimossi = {riga[2] for riga in modulo["_EFFETTI_RIMOSSI"]}
        assert "quantita_per_unita" in tipi_rimossi
        assert "escludi" in tipi_rimossi

    def test_valore_effetto_cambiato(self, tmp_path):
        dettaglio = _dettaglio_con_coefficiente(0.6)
        base_domande = _domande_con_effetti(includi_opzione="medio", quantita_valore=1.0, con_escludi=False)
        nuovo_domande = _domande_con_effetti(includi_opzione="medio", quantita_valore=3.0, con_escludi=False)

        percorso = emetti_migrazione(dettaglio, dettaglio, base_domande, nuovo_domande, tmp_path, "slug")

        codice = percorso.read_text(encoding="utf-8")
        modulo = {}
        exec(compile(codice, str(percorso), "exec"), modulo)
        assert len(modulo["_VALORI_EFFETTO"]) == 1
        riga = modulo["_VALORI_EFFETTO"][0]
        assert riga[0] == "bagni"
        assert riga[1] == "valore"
        assert riga[2] == "quantita_per_unita"
        assert riga[3] == ("A-EDILE", "A.6", "A.6.1")
        assert riga[5] == pytest.approx(1.0)
        assert riga[6] == pytest.approx(3.0)

    def test_costanti_sempre_presenti_anche_vuote(self, tmp_path):
        dettaglio_base = _dettaglio_con_coefficiente(0.6)
        dettaglio_nuovo = _dettaglio_con_coefficiente(0.85)
        domande = _domande_con_effetti(includi_opzione=None, quantita_valore=None, con_escludi=False)

        percorso = emetti_migrazione(dettaglio_base, dettaglio_nuovo, domande, domande, tmp_path, "slug")

        codice = percorso.read_text(encoding="utf-8")
        for costante in ("_COEFFICIENTI", "_VALORI_EFFETTO", "_INCLUDI_SPOSTATI", "_EFFETTI_RIMOSSI"):
            assert costante in codice

    def test_nessun_open_json_load_openpyxl_coefficiente_impresa_nel_modulo_emesso(self, tmp_path):
        base = _dettaglio_con_coefficiente(0.6)
        nuovo = _dettaglio_con_coefficiente(0.85)
        domande = _domande_con_effetti(includi_opzione="medio", quantita_valore=1.0, con_escludi=True)

        percorso = emetti_migrazione(base, nuovo, domande, domande, tmp_path, "slug")

        codice = percorso.read_text(encoding="utf-8")
        assert "open(" not in codice
        assert "json.load" not in codice
        assert "openpyxl" not in codice
        assert "coefficiente_impresa" not in codice
        compile(codice, str(percorso), "exec")  # deve compilare


class TestMainArgomentiMigrazione:
    def test_migrazione_legge_git_show_con_base_rev_e_passa_slug(self, tmp_path, monkeypatch):
        """Wiring CLI di main(): --migrazione/--slug/--base-rev, con `git show`
        sostituito da monkeypatch (nessun accesso vero al repo)."""
        backend_dir = tmp_path / "backend"
        seed_data_dir = backend_dir / "seed_data"
        seed_data_dir.mkdir(parents=True)
        (seed_data_dir / "seed-domande.json").write_text(json.dumps({"domande": []}), encoding="utf-8")
        (seed_data_dir / "seed-dettaglio-pro.json").write_text(json.dumps({"sottocategorie": []}), encoding="utf-8")
        versions_dir = backend_dir / "alembic" / "versions"
        versions_dir.mkdir(parents=True)
        (versions_dir / "0021_fake.py").write_text("revision = '0021'\n", encoding="utf-8")
        (tmp_path / "docs").mkdir()

        monkeypatch.setattr(applica_taratura_mod, "_BACKEND_DIR", backend_dir)

        class _FakeSession:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        monkeypatch.setattr("app.db.SessionLocal", lambda: _FakeSession())

        decisioni_vuote = DecisioniTaratura(stato="bozza-accettata", coefficienti=[], assi=[], dati={})
        monkeypatch.setattr(applica_taratura_mod, "leggi_decisioni", lambda wb: decisioni_vuote)
        monkeypatch.setattr(applica_taratura_mod.openpyxl, "load_workbook", lambda *a, **k: object())

        chiamate: dict = {"git_show": []}

        class _FakeResult:
            def __init__(self, stdout: str) -> None:
                self.stdout = stdout

        def _fake_run(cmd, cwd, capture_output, text, encoding, check):
            assert encoding == "utf-8"  # su Windows il default cp1252 produce mojibake
            rev_path = cmd[2]
            chiamate["git_show"].append(rev_path)
            if "seed-domande" in rev_path:
                return _FakeResult(json.dumps({"domande": []}))
            return _FakeResult(json.dumps({"sottocategorie": []}))

        monkeypatch.setattr("subprocess.run", _fake_run)

        def _fake_emetti_migrazione(base_dettaglio, nuovo_dettaglio, base_domande, nuovo_domande, versions_dir_arg, slug):
            chiamate["slug"] = slug
            chiamate["versions_dir"] = versions_dir_arg
            return None

        monkeypatch.setattr(applica_taratura_mod, "emetti_migrazione", _fake_emetti_migrazione)

        monkeypatch.setattr(
            sys,
            "argv",
            ["applica_taratura.py", "--migrazione", "--slug", "mia_slug", "--base-rev", "abc123"],
        )

        applica_taratura_mod.main()

        assert chiamate["slug"] == "mia_slug"
        assert any(p == "abc123:backend/seed_data/seed-domande.json" for p in chiamate["git_show"])
        assert any(p == "abc123:backend/seed_data/seed-dettaglio-pro.json" for p in chiamate["git_show"])
        assert chiamate["versions_dir"] == versions_dir

    def test_senza_migrazione_non_chiama_emetti_migrazione(self, tmp_path, monkeypatch):
        backend_dir = tmp_path / "backend"
        seed_data_dir = backend_dir / "seed_data"
        seed_data_dir.mkdir(parents=True)
        (seed_data_dir / "seed-domande.json").write_text(json.dumps({"domande": []}), encoding="utf-8")
        (seed_data_dir / "seed-dettaglio-pro.json").write_text(json.dumps({"sottocategorie": []}), encoding="utf-8")
        (tmp_path / "docs").mkdir()

        monkeypatch.setattr(applica_taratura_mod, "_BACKEND_DIR", backend_dir)

        class _FakeSession:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        monkeypatch.setattr("app.db.SessionLocal", lambda: _FakeSession())

        decisioni_vuote = DecisioniTaratura(stato="bozza-accettata", coefficienti=[], assi=[], dati={})
        monkeypatch.setattr(applica_taratura_mod, "leggi_decisioni", lambda wb: decisioni_vuote)
        monkeypatch.setattr(applica_taratura_mod.openpyxl, "load_workbook", lambda *a, **k: object())

        chiamato = {"emesso": False}

        def _fake_emetti_migrazione(*args, **kwargs):
            chiamato["emesso"] = True
            return None

        monkeypatch.setattr(applica_taratura_mod, "emetti_migrazione", _fake_emetti_migrazione)
        monkeypatch.setattr(sys, "argv", ["applica_taratura.py"])

        applica_taratura_mod.main()

        assert chiamato["emesso"] is False
        assert list((backend_dir / "alembic").glob("**/*.py")) == []


def test_migrazioni_generate_senza_mojibake():
    """Le migrazioni emesse da applica_taratura incorporano descrizioni di voce
    lette via `git show`: se l'output fosse decodificato con la codepage di
    Windows (cp1252) invece che UTF-8, "×" diventerebbe "Ã—" e le chiavi
    naturali non si risolverebbero piu' sul DB (effetti mai rimossi,
    coefficienti mai aggiornati)."""
    versions = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    for percorso in versions.glob("*taratura*.py"):
        testo = percorso.read_text(encoding="utf-8")
        for marcatore in ("Ã", "â€", "âˆ"):
            assert marcatore not in testo, f"{percorso.name}: mojibake {marcatore!r}"


# --- 09-09-PLAN.md Task 2: bersagli condivisi, gres a pavimento, fail-loud -


class TestApplicaAssiBersagliCondivisi:
    def test_tre_opzioni_stessa_voce_tre_includi_nessuna_sovrascrittura(self):
        decisioni = _decisioni(
            [
                _riga(voce_id=50, asse="tipo_pavimento", opzione="parquet", famiglia="posa_pavimento_A6"),
                _riga(voce_id=50, asse="tipo_pavimento", opzione="laminato", famiglia="posa_pavimento_A6"),
                _riga(voce_id=50, asse="tipo_pavimento", opzione="vinilico_lvt", famiglia="posa_pavimento_A6"),
            ]
        )
        chiave = {"categoria_code": "A-EDILE", "sottocategoria": "A.6", "voce": "A.6.2"}
        chiavi = {50: chiave}

        risultato = applica_assi(decisioni, _seed_domande_pavimenti_estesi(), chiavi)

        tipo_pav = next(d for d in risultato.seed_domande["domande"] if d["code"] == "tipo_pavimento")
        for opzione_code in ("parquet", "laminato", "vinilico_lvt"):
            opzione = next(o for o in tipo_pav["opzioni"] if o["code"] == opzione_code)
            includi = [e for e in opzione["effetti"] if e["tipo_effetto"] == "includi"]
            assert includi == [{"tipo_effetto": "includi", "target_voce": chiave}]


class TestApplicaAssiGresAPavimentoFinituraEFattore:
    """G1/G2: la fornitura gres a pavimento ha SIA una riga finitura (che deve
    creare un includi normale) SIA righe fattore_pavimento (quota bagno);
    solo le righe tipo_pavimento di una voce con quota bagno restano senza
    includi (A.6.1), mai le righe finitura."""

    def test_finitura_includi_e_fattore_pavimento_coesistono(self):
        decisioni = _decisioni(
            [
                _riga(voce_id=60, asse="finitura", opzione="medio", famiglia="fornitura_pavimento_gres"),
                _riga(
                    voce_id=60,
                    asse="fattore_pavimento",
                    opzione="parquet",
                    fattore_quantita=Decimal("0.12"),
                    famiglia="fornitura_pavimento_gres",
                ),
                _riga(
                    voce_id=60,
                    asse="fattore_pavimento",
                    opzione="laminato",
                    fattore_quantita=Decimal("0.12"),
                    famiglia="fornitura_pavimento_gres",
                ),
            ]
        )
        chiave = {
            "categoria_code": "B-FINITURE",
            "sottocategoria": "PAVIMENTI E RIVESTIMENTI GRES",
            "voce": "Gres pavimentazione",
        }
        chiavi = {60: chiave}

        risultato = applica_assi(decisioni, _seed_domande_pavimenti_estesi(), chiavi)

        finitura = next(d for d in risultato.seed_domande["domande"] if d["code"] == "finitura")
        medio = next(o for o in finitura["opzioni"] if o["code"] == "medio")
        includi = [e for e in medio["effetti"] if e["tipo_effetto"] == "includi"]
        assert includi == [{"tipo_effetto": "includi", "target_voce": chiave}]

        tipo_pav = next(d for d in risultato.seed_domande["domande"] if d["code"] == "tipo_pavimento")
        for opzione_code in ("parquet", "laminato"):
            opzione = next(o for o in tipo_pav["opzioni"] if o["code"] == opzione_code)
            fattore = [e for e in opzione["effetti"] if e["tipo_effetto"] == "fattore_quantita"]
            assert fattore == [{"tipo_effetto": "fattore_quantita", "valore": 0.12, "target_voce": chiave}]
            includi_tp = [e for e in opzione["effetti"] if e["tipo_effetto"] == "includi"]
            assert includi_tp == []

    def test_famiglia_bagno_su_riga_finitura(self):
        decisioni = _decisioni(
            [
                _riga(voce_id=61, asse="finitura", opzione="alto", famiglia="fornitura_pavimento_gres"),
                _riga(
                    voce_id=61,
                    asse="fattore_pavimento",
                    opzione="mosaico",
                    fattore_quantita=Decimal("0.12"),
                    famiglia="fornitura_pavimento_gres",
                ),
            ]
        )
        chiavi = {
            61: {
                "categoria_code": "B-FINITURE",
                "sottocategoria": "PAVIMENTI E RIVESTIMENTI GRES",
                "voce": "Gres alto",
            }
        }

        risultato = applica_assi(decisioni, _seed_domande_pavimenti_estesi(), chiavi)

        famiglie = {(f["voce"], f["famiglia"]) for f in risultato.famiglie}
        assert ("Gres alto", "fornitura_pavimento_gres:bagno") in famiglie

    def test_dedup_gres_a_pavimento_per_livello_solo_una_viva(self):
        decisioni = _decisioni(
            [
                _riga(voce_id=70, asse="finitura", opzione="alto", famiglia="fornitura_pavimento_gres"),
                _riga(
                    voce_id=70,
                    asse="fattore_pavimento",
                    opzione="parquet",
                    fattore_quantita=Decimal("0.12"),
                    famiglia="fornitura_pavimento_gres",
                ),
                _riga(voce_id=71, asse="finitura", opzione="alto", famiglia="fornitura_pavimento_gres"),
                _riga(
                    voce_id=71,
                    asse="fattore_pavimento",
                    opzione="parquet",
                    fattore_quantita=Decimal("0.12"),
                    famiglia="fornitura_pavimento_gres",
                ),
            ]
        )
        chiavi = {
            70: {
                "categoria_code": "B-FINITURE",
                "sottocategoria": "PAVIMENTI E RIVESTIMENTI GRES",
                "voce": "Gres alto livello 6",
            },
            71: {
                "categoria_code": "B-FINITURE",
                "sottocategoria": "PAVIMENTI E RIVESTIMENTI GRES",
                "voce": "Gres alto livello 7",
            },
        }

        risultato = applica_assi(decisioni, _seed_domande_pavimenti_estesi(), chiavi)

        finitura = next(d for d in risultato.seed_domande["domande"] if d["code"] == "finitura")
        alto = next(o for o in finitura["opzioni"] if o["code"] == "alto")
        includi = {e["target_voce"]["voce"] for e in alto["effetti"] if e["tipo_effetto"] == "includi"}
        escludi = {e["target_voce"]["voce"] for e in alto["effetti"] if e["tipo_effetto"] == "escludi"}
        assert includi == {"Gres alto livello 6", "Gres alto livello 7"}
        assert escludi == {"Gres alto livello 7"}


class TestApplicaAssiOpzioneSconosciuta:
    def test_opzione_assente_solleva_value_error_con_domanda_e_opzione(self):
        decisioni = _decisioni(
            [_riga(voce_id=80, asse="tipo_pavimento", opzione="terracotta", famiglia="posa_pavimento_A6")]
        )
        chiavi = {80: {"categoria_code": "A-EDILE", "sottocategoria": "A.6", "voce": "A.6.2"}}

        with pytest.raises(ValueError) as exc_info:
            applica_assi(decisioni, _seed_domande_pavimenti_estesi(), chiavi)
        assert "tipo_pavimento" in str(exc_info.value)
        assert "terracotta" in str(exc_info.value)
        assert "seed-domande.json" in str(exc_info.value)


class TestRecordEffettiBersagliCondivisi:
    def test_una_opzione_in_piu_non_sposta_ne_rimuove(self):
        base = _domande_con_effetti(includi_opzione="medio", quantita_valore=None, con_escludi=False)
        nuovo = json.loads(json.dumps(base))
        finitura_nuovo = next(d for d in nuovo["domande"] if d["code"] == "finitura")
        alto = next(o for o in finitura_nuovo["opzioni"] if o["code"] == "alto")
        alto["effetti"].append({"tipo_effetto": "includi", "target_voce": dict(CHIAVE_GRES_MIGR)})

        base_idx = applica_taratura_mod._record_effetti(base)
        nuovo_idx = applica_taratura_mod._record_effetti(nuovo)

        chiave_voce = ("B-FINITURE", "GRES", "Gres base")
        assert base_idx["includi"][("finitura", chiave_voce)] == frozenset({"medio"})
        assert nuovo_idx["includi"][("finitura", chiave_voce)] == frozenset({"medio", "alto"})

    def test_emetti_migrazione_bersaglio_condiviso_nessun_diff(self, tmp_path):
        dettaglio = _dettaglio_con_coefficiente(0.6)
        base = _domande_con_effetti(includi_opzione="medio", quantita_valore=None, con_escludi=False)
        nuovo = json.loads(json.dumps(base))
        finitura_nuovo = next(d for d in nuovo["domande"] if d["code"] == "finitura")
        alto = next(o for o in finitura_nuovo["opzioni"] if o["code"] == "alto")
        alto["effetti"].append({"tipo_effetto": "includi", "target_voce": dict(CHIAVE_GRES_MIGR)})

        percorso = emetti_migrazione(dettaglio, dettaglio, base, nuovo, tmp_path, "slug")

        assert percorso is None

    def test_emetti_migrazione_includi_rimosso_quando_lopzione_sparisce(self, tmp_path):
        dettaglio = _dettaglio_con_coefficiente(0.6)
        base = _domande_con_effetti(includi_opzione="medio", quantita_valore=None, con_escludi=False)
        nuovo = _domande_con_effetti(includi_opzione=None, quantita_valore=None, con_escludi=False)

        percorso = emetti_migrazione(dettaglio, dettaglio, base, nuovo, tmp_path, "slug")

        codice = percorso.read_text(encoding="utf-8")
        modulo = {}
        exec(compile(codice, str(percorso), "exec"), modulo)
        assert modulo["_INCLUDI_SPOSTATI"] == ()
        tipi_rimossi = {(riga[0], riga[1], riga[2]) for riga in modulo["_EFFETTI_RIMOSSI"]}
        assert ("finitura", "medio", "includi") in tipi_rimossi


def _versions_root_e_config(tmp_path, monkeypatch) -> tuple[Path, "object"]:
    """Copia `alembic/` (catena reale, testa attuale) in una directory
    temporanea e porta un SQLite usa-e-getta alla testa: base sicura su cui
    scrivere ed eseguire una migrazione sintetica (0022 esistente MAI
    modificata)."""
    from alembic import command
    from alembic.config import Config
    from app.config import settings as app_settings

    backend_dir = Path(__file__).resolve().parents[1]
    alembic_tmp = tmp_path / "alembic_guardia"
    shutil.copytree(backend_dir / "alembic", alembic_tmp)

    db_path = tmp_path / "guardia.db"
    monkeypatch.setattr(app_settings, "DATABASE_URL", f"sqlite:///{db_path}")
    config = Config()
    config.set_main_option("script_location", str(alembic_tmp))
    command.upgrade(config, "head")

    return alembic_tmp, config, db_path


class TestTemplateGuardiaCatalogoPresente:
    """Il template di migrazione (_catalogo_presente + guardia in upgrade()):
    fail-loud quando il catalogo e' presente e una chiave naturale non si
    risolve, no-op silenzioso su un DB vergine (nessuna domanda citata
    presente)."""

    def test_catalogo_presente_e_chiave_non_risolta_solleva_runtime_error(self, tmp_path, monkeypatch):
        from alembic import command

        alembic_tmp, config, db_path = _versions_root_e_config(tmp_path, monkeypatch)

        connessione = sqlite3.connect(db_path)
        try:
            connessione.execute(
                "INSERT INTO domanda (code, testo, tipo_controllo) VALUES ('bagni', 'Numero di bagni', 'stepper')"
            )
            connessione.execute(
                "INSERT INTO opzione_domanda (domanda_code, code, etichetta) VALUES ('bagni', 'valore', 'Valore')"
            )
            connessione.commit()
        finally:
            connessione.close()

        dettaglio = _dettaglio_con_coefficiente(0.6)
        base = _domande_con_effetti(includi_opzione="medio", quantita_valore=1.0, con_escludi=False)
        nuovo = _domande_con_effetti(includi_opzione="medio", quantita_valore=3.0, con_escludi=False)
        percorso = emetti_migrazione(dettaglio, dettaglio, base, nuovo, alembic_tmp / "versions", "guardia")
        assert percorso is not None
        revisione = percorso.stem.split("_")[0]

        with pytest.raises(RuntimeError, match="risolte"):
            command.upgrade(config, revisione)

    def test_soli_coefficienti_con_voce_bersaglio_alterata_solleva_runtime_error(self, tmp_path, monkeypatch):
        """WR-05 (review 09): una migrazione che tocca solo `_COEFFICIENTI`
        non cita domande, ma con il catalogo voci presente una chiave non
        risolta deve comunque fallire rumorosamente."""
        from alembic import command

        alembic_tmp, config, db_path = _versions_root_e_config(tmp_path, monkeypatch)

        connessione = sqlite3.connect(db_path)
        try:
            connessione.execute(
                "INSERT INTO categoria (code, nome, ordine, iva_pct, livello_selezionabile, nel_totale_lavori)"
                " VALUES ('A-EDILE', 'Edile', 1, 0.10, 0, 1)"
            )
            connessione.execute(
                "INSERT INTO listino (id, nome, citta_riferimento, valuta, is_default, attivo)"
                " VALUES (1, 'Reggio Emilia', 'Reggio Emilia', 'EUR', 1, 1)"
            )
            connessione.execute(
                "INSERT INTO sottocategoria (id, listino_id, categoria_code, codice, nome, famiglia, ordine)"
                " VALUES (1, 1, 'A-EDILE', 'A.6', 'A.6', 'catalogo', 1)"
            )
            # voce bersaglio con il codice alterato (drift): 'A.6.1' non si risolve
            connessione.execute(
                "INSERT INTO voce (sottocategoria_id, codice, descrizione, um, prezzo_unitario_cliente, ordine)"
                " VALUES (1, 'A.6.1-alterata', 'Posa pavimentazione', 'mq', 20.00, 1)"
            )
            connessione.commit()
        finally:
            connessione.close()

        domande = _domande_con_effetti(includi_opzione="medio", quantita_valore=1.0, con_escludi=False)
        percorso = emetti_migrazione(
            _dettaglio_con_coefficiente(0.6),
            _dettaglio_con_coefficiente(0.9),
            domande,
            domande,
            alembic_tmp / "versions",
            "soli_coefficienti",
        )
        assert percorso is not None
        revisione = percorso.stem.split("_")[0]

        with pytest.raises(RuntimeError, match="risolte"):
            command.upgrade(config, revisione)

    def test_nessuna_domanda_citata_presente_e_no_op(self, tmp_path, monkeypatch):
        from alembic import command

        alembic_tmp, config, _db_path = _versions_root_e_config(tmp_path, monkeypatch)
        # Nessuna domanda 'bagni' seminata: DB vergine su questo fronte, il
        # seed create-if-missing creerebbe tutto al prossimo boot (D-41).

        dettaglio = _dettaglio_con_coefficiente(0.6)
        base = _domande_con_effetti(includi_opzione="medio", quantita_valore=1.0, con_escludi=False)
        nuovo = _domande_con_effetti(includi_opzione="medio", quantita_valore=3.0, con_escludi=False)
        percorso = emetti_migrazione(dettaglio, dettaglio, base, nuovo, alembic_tmp / "versions", "guardia")
        assert percorso is not None
        revisione = percorso.stem.split("_")[0]

        command.upgrade(config, revisione)  # non deve sollevare
