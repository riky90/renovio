"""Bersagli a chiave naturale nel seed del catalogo Pro (09-02 Task 1).

Copre `_risolvi_bersaglio_naturale` e `seed_domande` con dati costruiti nel
test (non il JSON reale, che arriva nel Task 2). Sessione in memoria + seed
completo come in `test_seed.py`, cosi' sottocategorie/voci del listino di
default esistono davvero quando si risolve un bersaglio naturale.
"""

import pytest
from sqlalchemy import create_engine

from app.db import Base
from app.models.domanda import Domanda, EffettoOpzione, OpzioneDomanda
from app.models.dettaglio_pro import Sottocategoria, Voce
from app.models.listino import Listino
from app.services.effetti import valida_effetto
from scripts.seed import load_domande_data, load_seed_data, seed, seed_domande
from tests.session_factory import sessione_di_test


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)
    with testing_session_local() as s:
        seed(s, load_seed_data())
        yield s


def _domanda_con_effetto(code: str, opzione_code: str, e_data: dict) -> dict:
    return {
        "domande": [
            {
                "code": code,
                "testo": "domanda di test",
                "tipo_controllo": "scelta_singola",
                "opzioni": [
                    {
                        "code": opzione_code,
                        "etichetta": "Opzione di test",
                        "effetti": [e_data],
                    }
                ],
            }
        ]
    }


def test_target_voce_con_codice_risolve_id_reale(session):
    """target_voce con codice esplicito (A.6.2, A-EDILE) risolve alla voce vera."""
    voce_reale = (
        session.query(Voce)
        .join(Sottocategoria)
        .filter(Sottocategoria.categoria_code == "A-EDILE", Voce.codice == "A.6.2")
        .one()
    )
    data = _domanda_con_effetto(
        "test_target_voce",
        "opt1",
        {
            "tipo_effetto": "includi",
            "target_voce": {
                "categoria_code": "A-EDILE",
                "sottocategoria": "A.6",
                "voce": "A.6.2",
            },
        },
    )
    non_risolti = seed_domande(session, data)

    assert non_risolti == 0
    effetto = session.query(EffettoOpzione).join(OpzioneDomanda).filter(
        OpzioneDomanda.domanda_code == "test_target_voce"
    ).one()
    assert effetto.target_voce_id == voce_reale.id


def test_target_sottocategoria_per_nome_senza_codice(session):
    """target_sottocategoria risolve per nome esatto (B-FINITURE / PAVIMENTI
    PARQUET). Dalla v3 la sottocategoria ha anche un codice (`B.3`): il nome
    resta una chiave valida, perche' il JSON degli effetti la cita cosi'."""
    sotto_reale = (
        session.query(Sottocategoria)
        .filter_by(categoria_code="B-FINITURE", nome="PAVIMENTI PARQUET")
        .one()
    )
    data = _domanda_con_effetto(
        "test_target_sotto",
        "opt1",
        {
            "tipo_effetto": "includi",
            "target_sottocategoria": {
                "categoria_code": "B-FINITURE",
                "sottocategoria": "PAVIMENTI PARQUET",
            },
        },
    )
    non_risolti = seed_domande(session, data)

    assert non_risolti == 0
    effetto = session.query(EffettoOpzione).join(OpzioneDomanda).filter(
        OpzioneDomanda.domanda_code == "test_target_sotto"
    ).one()
    assert effetto.target_sottocategoria_id == sotto_reale.id


def test_voce_senza_codice_risolve_per_descrizione_esatta(session):
    """Una voce di catalogo si risolve per descrizione esatta dentro la
    sottocategoria, anche ora che ha un codice stabile (v3, `B.3.n`)."""
    voce_reale = (
        session.query(Voce)
        .join(Sottocategoria)
        .filter(
            Sottocategoria.categoria_code == "B-FINITURE",
            Sottocategoria.nome == "PAVIMENTI PARQUET",
        )
        .first()
    )
    assert voce_reale is not None
    data = _domanda_con_effetto(
        "test_target_voce_desc",
        "opt1",
        {
            "tipo_effetto": "includi",
            "target_voce": {
                "categoria_code": "B-FINITURE",
                "sottocategoria": "PAVIMENTI PARQUET",
                "voce": voce_reale.descrizione,
            },
        },
    )
    non_risolti = seed_domande(session, data)

    assert non_risolti == 0
    effetto = session.query(EffettoOpzione).join(OpzioneDomanda).filter(
        OpzioneDomanda.domanda_code == "test_target_voce_desc"
    ).one()
    assert effetto.target_voce_id == voce_reale.id


def test_bersaglio_naturale_inesistente_viene_saltato_senza_eccezione(session):
    """Un bersaglio naturale che non esiste viene saltato in silenzio (il seed
    gira al boot) e conta come non risolto — nessuna eccezione."""
    data = _domanda_con_effetto(
        "test_target_rotto",
        "opt1",
        {
            "tipo_effetto": "includi",
            "target_voce": {
                "categoria_code": "A-EDILE",
                "sottocategoria": "A.6",
                "voce": "A.6.999-inesistente",
            },
        },
    )
    non_risolti = seed_domande(session, data)

    assert non_risolti == 1
    count = session.query(EffettoOpzione).join(OpzioneDomanda).filter(
        OpzioneDomanda.domanda_code == "test_target_rotto"
    ).count()
    assert count == 0


def test_seed_due_volte_e_idempotente_sui_bersagli_naturali(session):
    """Due esecuzioni consecutive di seed() (che chiama seed_domande sul JSON
    reale, privo di bersagli naturali oggi) producono lo stesso numero di righe
    effetto_opzione anche quando si aggiungono a mano effetti Pro a bersaglio
    naturale fra le due chiamate a seed_domande."""
    data = _domanda_con_effetto(
        "test_target_idempotente",
        "opt1",
        {
            "tipo_effetto": "includi",
            "target_voce": {
                "categoria_code": "A-EDILE",
                "sottocategoria": "A.6",
                "voce": "A.6.2",
            },
        },
    )
    seed_domande(session, data)
    count_dopo_primo = session.query(EffettoOpzione).count()

    seed_domande(session, data)
    count_dopo_secondo = session.query(EffettoOpzione).count()

    assert count_dopo_primo == count_dopo_secondo


def test_senza_listino_default_bersaglio_naturale_si_salta(session):
    """Senza listino di default, gli effetti con bersaglio naturale si saltano
    (non_risolti conta) invece di far fallire il seed."""
    session.query(Listino).filter_by(is_default=True).update({"is_default": False})
    session.flush()

    data = _domanda_con_effetto(
        "test_target_senza_listino",
        "opt1",
        {
            "tipo_effetto": "includi",
            "target_voce": {
                "categoria_code": "A-EDILE",
                "sottocategoria": "A.6",
                "voce": "A.6.2",
            },
        },
    )
    non_risolti = seed_domande(session, data)

    assert non_risolti == 1


def test_effetto_senza_bersaglio_naturale_passa_invariato(session):
    """Un effetto con target_categoria_code / target_sottocategoria_id /
    target_voce_id espliciti (come oggi, nessuna chiave target_voce/
    target_sottocategoria) non passa dalla risoluzione e si crea come sempre."""
    data = _domanda_con_effetto(
        "test_target_esplicito",
        "opt1",
        {
            "tipo_effetto": "moltiplicatore_categoria",
            "target_categoria_code": "A-EDILE",
            "valore": 1.05,
        },
    )
    non_risolti = seed_domande(session, data)

    assert non_risolti == 0


# --- Task 2: catalogo Pro sul JSON reale + esclusione dal wizard -----------


class TestCatalogoProSulJsonReale:
    """Il seed() della fixture ha gia' caricato il JSON reale
    (`load_seed_data()`), che include il catalogo domande. Qui si verifica il
    comportamento atteso su un DB nuovo seminato da zero."""

    def test_finitura_ha_almeno_21_effetti_includi_7_per_opzione(self, session):
        """21 (7 per opzione) e' il minimo garantito dalla migrazione delle 21
        voci gres livellate a mano (09-02/09-03/09-04); da 09-07 la curatela
        del file di taratura (D-08) puo' aggiungere altre voci allo stesso
        asse (famiglie di alternative sanitari/porte/condizionatori assegnate
        per fascia di prezzo) — il numero esatto e' una decisione di
        taratura, non una verita' cablata qui (D-05)."""
        finitura = session.get(Domanda, "finitura")
        assert finitura is not None
        assert finitura.tier_minimo == "pro"
        assert finitura.tipo_controllo == "scelta_singola"
        assert finitura.gruppo == "configuratore_pro"

        opzioni = (
            session.query(OpzioneDomanda).filter_by(domanda_code="finitura").all()
        )
        codici = {o.code for o in opzioni}
        assert codici == {"base", "medio", "alto"}

        medio = next(o for o in opzioni if o.code == "medio")
        assert medio.is_default is True

        totale = 0
        for o in opzioni:
            count = (
                session.query(EffettoOpzione)
                .filter_by(opzione_id=o.id, tipo_effetto="includi")
                .count()
            )
            assert count >= 7, f"opzione {o.code} ha {count} effetti includi, attesi almeno 7"
            totale += count
        assert totale >= 21

    def test_tipo_pavimento_ha_almeno_1_effetto_includi_per_la_sua_posa_principale(self, session):
        """Ogni opzione governa almeno la sua posa A.6 principale (parquet/
        maxi_lastra/mosaico -> A.6.2/.5/.6 sempre, per costruzione). A.6.1
        (gres) e' un caso speciale da 09-07 (D-02): NON e' bersaglio di
        alcun `includi`, nemmeno sulla sua opzione "gres" — resta sempre
        inclusa (non governata da alcun asse), mentre parquet/maxi_lastra/
        mosaico la riducono via `fattore_quantita` alla sola quota bagno.
        Un `includi` la renderebbe bersaglio di piu' di un'opzione
        (gres + le altre) e romperebbe il conteggio per-asse di CFG-02
        (09-03), che assume bersagli disgiunti fra opzioni."""
        tipo_pavimento = session.get(Domanda, "tipo_pavimento")
        assert tipo_pavimento is not None
        assert tipo_pavimento.tier_minimo == "pro"
        assert tipo_pavimento.tipo_controllo == "scelta_singola"
        assert tipo_pavimento.gruppo == "configuratore_pro"

        opzioni = (
            session.query(OpzioneDomanda)
            .filter_by(domanda_code="tipo_pavimento")
            .all()
        )
        codici = {o.code for o in opzioni}
        assert codici == {
            "gres",
            "parquet",
            "maxi_lastra",
            "mosaico",
            "laminato",
            "vinilico_lvt",
            "moquette",
        }

        gres = next(o for o in opzioni if o.code == "gres")
        assert gres.is_default is True

        # Le tre opzioni aggiunte dal 09-10 (G1) condividono la posa A.6.2 con
        # parquet (D-08, bersagli condivisi); moquette non ha una posa A.6
        # principale dedicata (resta sulla posa generica A.6.1).
        attese_voce = {
            "parquet": "A.6.2",
            "maxi_lastra": "A.6.5",
            "mosaico": "A.6.6",
            "laminato": "A.6.2",
            "vinilico_lvt": "A.6.2",
        }
        a6_1 = session.query(Voce).filter_by(codice="A.6.1").one()

        for o in opzioni:
            effetti_includi = (
                session.query(EffettoOpzione)
                .filter_by(opzione_id=o.id, tipo_effetto="includi")
                .all()
            )
            voci_includi = {e.target_voce_id for e in effetti_includi}
            assert a6_1.id not in voci_includi, f"A.6.1 non deve essere bersaglio di includi su {o.code!r}"
            if o.code in attese_voce:
                voci_codici = {session.get(Voce, vid).codice for vid in voci_includi}
                assert attese_voce[o.code] in voci_codici

        # D-02: il bagno resta sempre gres, ridotto alla sua quota su ogni
        # opzione diversa dal gres — TRANNE moquette, che non ha una posa
        # dedicata e usa A.6.1 a quantita' piena (decisione 09-09).
        for opzione_non_gres in ("parquet", "maxi_lastra", "mosaico", "laminato", "vinilico_lvt"):
            o = next(x for x in opzioni if x.code == opzione_non_gres)
            fattori = (
                session.query(EffettoOpzione)
                .filter_by(opzione_id=o.id, tipo_effetto="fattore_quantita", target_voce_id=a6_1.id)
                .all()
            )
            assert len(fattori) == 1, f"opzione {opzione_non_gres!r} deve avere un fattore_quantita su A.6.1"

        moquette = next(o for o in opzioni if o.code == "moquette")
        fattori_moquette = (
            session.query(EffettoOpzione)
            .filter_by(opzione_id=moquette.id, tipo_effetto="fattore_quantita", target_voce_id=a6_1.id)
            .all()
        )
        assert fattori_moquette == [], "moquette non deve avere fattore_quantita su A.6.1"

    def test_stepper_bagni_porte_condizionatori_hanno_quantita_per_unita(self, session):
        for code in ("bagni", "porte", "condizionatori"):
            opzione = (
                session.query(OpzioneDomanda)
                .filter_by(domanda_code=code, code="valore")
                .one()
            )
            effetti = (
                session.query(EffettoOpzione)
                .filter_by(opzione_id=opzione.id, tipo_effetto="quantita_per_unita")
                .all()
            )
            assert len(effetti) > 0, f"{code} non ha effetti quantita_per_unita"
            for e in effetti:
                assert e.valore == 1
                assert e.target_voce_id is not None

    def test_seed_domande_sul_json_reale_ritorna_zero_non_risolti(self, session):
        non_risolti = seed_domande(session, load_domande_data())
        assert non_risolti == 0

    def test_ogni_effetto_pro_seminato_passa_valida_effetto(self, session):
        for code in ("finitura", "tipo_pavimento", "bagni", "porte", "condizionatori"):
            opzioni = session.query(OpzioneDomanda).filter_by(domanda_code=code).all()
            for o in opzioni:
                for e in session.query(EffettoOpzione).filter_by(opzione_id=o.id).all():
                    valida_effetto(
                        session,
                        e.tipo_effetto,
                        categoria_code=e.target_categoria_code,
                        sottocategoria_id=e.target_sottocategoria_id,
                        voce_id=e.target_voce_id,
                        valore=e.valore,
                    )

    def test_nessuna_domanda_pro_oltre_finitura_e_tipo_pavimento(self, session):
        """D-01: il nucleo Pro di questa fase e' solo finitura + tipo_pavimento
        (i tre stepper esistevano gia' come domande Free)."""
        codici_pro = {
            d.code
            for d in session.query(Domanda).filter_by(tier_minimo="pro").all()
        }
        assert codici_pro == {"finitura", "tipo_pavimento"}
