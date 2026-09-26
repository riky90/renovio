"""risolvi_effetti_pro() (09-03-PLAN.md Task 2): assi di scelta come dati.

Il resolver Pro riusa `risolvi_scelte()` (default, derivazioni, visibilita')
e vi aggiunge la lettura dei quattro effetti Pro dal catalogo. Qui si
verifica il resolver isolato, voce per voce di comportamento — il test di
conteggio end-to-end (CFG-02) vive in test_dettaglio_pro_alternative.py.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine

from app.db import Base
from app.models.dettaglio_pro import Sottocategoria, Voce
from app.models.domanda import Domanda, EffettoOpzione, OpzioneDomanda
from app.services.effetti import (
    DOMANDA_FINITURA,
    TIER_FREE,
    TIER_PRO,
    TIPO_ESCLUDI,
    TIPO_FATTORE_QUANTITA,
    TIPO_INCLUDI,
    TIPO_QUANTITA_PER_UNITA,
    attese_per_mq,
    risolvi_effetti_pro,
    risolvi_scelte,
)
from scripts.seed import load_seed_data, seed
from tests.session_factory import sessione_di_test


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)
    with testing_session_local() as s:
        seed(s, load_seed_data())
        yield s


def _sotto_gres(session) -> Sottocategoria:
    return (
        session.query(Sottocategoria)
        .filter_by(categoria_code="B-FINITURE", nome="PAVIMENTI E RIVESTIMENTI GRES")
        .one()
    )


def _sotto_a6(session) -> Sottocategoria:
    return session.query(Sottocategoria).filter_by(categoria_code="A-EDILE", codice="A.6").one()


def _voce_a6(session, codice: str) -> Voce:
    sotto = _sotto_a6(session)
    return session.query(Voce).filter_by(sottocategoria_id=sotto.id, codice=codice).one()


def _voci_gres(session) -> list[Voce]:
    return session.query(Voce).filter_by(sottocategoria_id=_sotto_gres(session).id).all()


def _aggiungi_domanda(
    session,
    *,
    code: str,
    tipo_controllo: str = "scelta_singola",
    tier_minimo: str = TIER_PRO,
    attributo_code: str | None = None,
    visibile_se_domanda_code: str | None = None,
    visibile_se_opzione_code: str | None = None,
) -> Domanda:
    d = Domanda(
        code=code,
        testo=code,
        tipo_controllo=tipo_controllo,
        gruppo="test",
        ordine=999,
        tier_minimo=tier_minimo,
        attributo_code=attributo_code,
        visibile_se_domanda_code=visibile_se_domanda_code,
        visibile_se_opzione_code=visibile_se_opzione_code,
    )
    session.add(d)
    session.flush()
    return d


def _aggiungi_opzione(
    session, domanda: Domanda, *, code: str, is_default: bool = False, ordine: int = 1
) -> OpzioneDomanda:
    o = OpzioneDomanda(
        domanda_code=domanda.code,
        code=code,
        etichetta=code,
        is_default=is_default,
        ordine=ordine,
    )
    session.add(o)
    session.flush()
    return o


def _aggiungi_effetto(
    session,
    opzione: OpzioneDomanda,
    *,
    tipo_effetto: str,
    target_categoria_code: str | None = None,
    target_sottocategoria_id: int | None = None,
    target_voce_id: int | None = None,
    valore: Decimal | None = None,
    tipo_code: str | None = None,
    attivo: bool = True,
) -> EffettoOpzione:
    e = EffettoOpzione(
        opzione_id=opzione.id,
        tipo_effetto=tipo_effetto,
        target_categoria_code=target_categoria_code,
        target_sottocategoria_id=target_sottocategoria_id,
        target_voce_id=target_voce_id,
        valore=valore,
        tipo_code=tipo_code,
        attivo=attivo,
    )
    session.add(e)
    session.flush()
    return e


# --- risolvi_scelte(tiers=...) ----------------------------------------------


def test_risolvi_scelte_senza_tiers_e_identico_a_oggi(session):
    """Nessun chiamante esistente passa `tiers`: il comportamento Free non
    cambia (solo domande di quel tier)."""
    scelte_free = risolvi_scelte(session, risposte={}, tier=TIER_FREE)
    assert all(True for _ in scelte_free.domande)  # non lancia, forma invariata
    codici = {d.code for d in scelte_free.domande}
    assert DOMANDA_FINITURA not in codici


def test_risolvi_scelte_con_tiers_include_free_e_pro(session):
    scelte = risolvi_scelte(session, risposte={}, tiers=(TIER_FREE, TIER_PRO))
    codici = {d.code for d in scelte.domande}
    assert DOMANDA_FINITURA in codici
    assert "bagni" in codici


# --- includi su voce ---------------------------------------------------------


def test_opzione_scelta_con_includi_su_voce_va_in_voci_scelte(session):
    """D-02 (09-07): A.6.1 (la posa gres del bagno) NON e' piu' bersaglio di
    alcun `includi` su tipo_pavimento — resta sempre inclusa (regola 4,
    NON governata) e la sua quantita' scala via `fattore_quantita` sulle
    opzioni diverse da gres. Un `includi` la renderebbe bersaglio di due
    opzioni contemporaneamente e romperebbe CFG-02 (09-03)."""
    ris = risolvi_effetti_pro(session, mq=85, tipo="totale", risposte={"tipo_pavimento": "parquet"})

    voce_a62 = _voce_a6(session, "A.6.2")
    voce_a61 = _voce_a6(session, "A.6.1")

    asse = next(a for a in ris.assi if a.domanda_code == "tipo_pavimento")
    assert voce_a62.id in asse.voci_scelte
    assert voce_a62.id in asse.voci_governate
    assert voce_a61.id not in asse.voci_scelte
    assert voce_a61.id not in asse.voci_governate


def test_voce_inclusa_rispetta_lasse_tipo_pavimento(session):
    """A.6.1 non governata da alcun asse tipo_pavimento resta SEMPRE
    inclusa (regola 4), a prescindere dalla scelta — la sua quota bagno si
    regola con `fattore_quantita`, non con l'inclusione/esclusione."""
    ris = risolvi_effetti_pro(session, mq=85, tipo="totale", risposte={"tipo_pavimento": "parquet"})

    voce_a62 = _voce_a6(session, "A.6.2")
    voce_a61 = _voce_a6(session, "A.6.1")
    sotto = _sotto_a6(session)

    assert ris.voce_inclusa(voce_a62.id, sotto.id, "A-EDILE") is True
    assert ris.voce_inclusa(voce_a61.id, sotto.id, "A-EDILE") is True


# --- includi su sottocategoria -----------------------------------------------


def test_includi_su_sottocategoria_governa_tutte_le_sue_voci(session):
    """Domanda di test con un `includi` a bersaglio SOTTOCATEGORIA (non voce):
    tutte le voci della sottocategoria diventano governate, e scelte solo se
    l'opzione scelta punta quella sottocategoria."""
    sotto = _sotto_gres(session)
    voci = _voci_gres(session)
    assert voci, "il seed deve avere voci di gres"

    domanda = _aggiungi_domanda(session, code="test_sotto")
    opz_si = _aggiungi_opzione(session, domanda, code="si", is_default=True)
    opz_no = _aggiungi_opzione(session, domanda, code="no", ordine=2)
    _aggiungi_effetto(
        session, opz_si, tipo_effetto=TIPO_INCLUDI, target_sottocategoria_id=sotto.id
    )
    # Una seconda opzione con un altro bersaglio, cosi' la domanda ha
    # comunque un asse con due opzioni fra cui scegliere.
    altra_sotto = _sotto_a6(session)
    _aggiungi_effetto(
        session, opz_no, tipo_effetto=TIPO_INCLUDI, target_sottocategoria_id=altra_sotto.id
    )
    session.commit()

    ris = risolvi_effetti_pro(session, mq=85, tipo="totale", risposte={})

    asse = next(a for a in ris.assi if a.domanda_code == "test_sotto")
    assert all(v.id in asse.voci_governate for v in voci)
    assert sotto.id in asse.sottocategorie_governate
    # Default "si": la sottocategoria gres e' scelta.
    assert sotto.id in asse.sottocategorie_scelte
    assert all(v.id in asse.voci_scelte for v in voci)


# --- escludi ------------------------------------------------------------------


def test_escludi_vince_anche_su_una_voce_altrimenti_inclusa(session):
    voce = _voce_a6(session, "A.6.9")  # non governata da alcun asse del seed
    sotto = _sotto_a6(session)

    domanda = _aggiungi_domanda(session, code="test_escludi", tipo_controllo="toggle")
    opz = _aggiungi_opzione(session, domanda, code="si", is_default=True)
    _aggiungi_effetto(session, opz, tipo_effetto=TIPO_ESCLUDI, target_voce_id=voce.id)
    session.commit()

    ris = risolvi_effetti_pro(session, mq=85, tipo="totale", risposte={})

    assert voce.id in ris.escluse_voci
    assert ris.voce_inclusa(voce.id, sotto.id, "A-EDILE") is False


def test_escludi_su_categoria_e_sottocategoria(session):
    sotto = _sotto_gres(session)

    domanda_cat = _aggiungi_domanda(session, code="test_escludi_cat", tipo_controllo="toggle")
    opz_cat = _aggiungi_opzione(session, domanda_cat, code="si", is_default=True)
    _aggiungi_effetto(session, opz_cat, tipo_effetto=TIPO_ESCLUDI, target_categoria_code="D-PRODOTTI")

    domanda_sotto = _aggiungi_domanda(session, code="test_escludi_sotto", tipo_controllo="toggle")
    opz_sotto = _aggiungi_opzione(session, domanda_sotto, code="si", is_default=True)
    _aggiungi_effetto(
        session, opz_sotto, tipo_effetto=TIPO_ESCLUDI, target_sottocategoria_id=sotto.id
    )
    session.commit()

    ris = risolvi_effetti_pro(session, mq=85, tipo="totale", risposte={})

    assert "D-PRODOTTI" in ris.escluse_categorie
    assert sotto.id in ris.escluse_sottocategorie


def test_voce_non_governata_e_non_esclusa_e_inclusa(session):
    voce = _voce_a6(session, "A.6.9")
    sotto = _sotto_a6(session)

    ris = risolvi_effetti_pro(session, mq=85, tipo="totale", risposte={})

    assert ris.voce_inclusa(voce.id, sotto.id, "A-EDILE") is True


# --- quantita_per_unita -------------------------------------------------------


def test_quantita_per_unita_risposta_numerica_moltiplica_il_valore(session):
    voce = _voce_a6(session, "A.6.9")
    domanda = _aggiungi_domanda(
        session, code="test_qta", tipo_controllo="stepper", attributo_code="test_qta"
    )
    opz = _aggiungi_opzione(session, domanda, code="valore", is_default=True)
    _aggiungi_effetto(
        session, opz, tipo_effetto=TIPO_QUANTITA_PER_UNITA, target_voce_id=voce.id, valore=Decimal("2")
    )
    session.commit()

    ris = risolvi_effetti_pro(session, mq=85, tipo="totale", risposte={"test_qta": 3})

    assert ris.quantita_per_unita[voce.id] == Decimal("6")


def test_quantita_per_unita_due_effetti_sulla_stessa_voce_si_sommano(session):
    voce = _voce_a6(session, "A.6.9")
    domanda = _aggiungi_domanda(
        session, code="test_qta_somma", tipo_controllo="stepper", attributo_code="test_qta_somma"
    )
    opz = _aggiungi_opzione(session, domanda, code="valore", is_default=True)
    _aggiungi_effetto(
        session, opz, tipo_effetto=TIPO_QUANTITA_PER_UNITA, target_voce_id=voce.id, valore=Decimal("2")
    )
    _aggiungi_effetto(
        session, opz, tipo_effetto=TIPO_QUANTITA_PER_UNITA, target_voce_id=voce.id, valore=Decimal("1")
    )
    session.commit()

    ris = risolvi_effetti_pro(session, mq=85, tipo="totale", risposte={"test_qta_somma": 4})

    assert ris.quantita_per_unita[voce.id] == Decimal("12")  # 4*2 + 4*1


def test_quantita_per_unita_senza_risposta_usa_atteso(session):
    voce = _voce_a6(session, "A.6.9")
    domanda = _aggiungi_domanda(
        session, code="test_qta_atteso", tipo_controllo="stepper", attributo_code="bagni"
    )
    opz = _aggiungi_opzione(session, domanda, code="valore", is_default=True)
    _aggiungi_effetto(
        session, opz, tipo_effetto=TIPO_QUANTITA_PER_UNITA, target_voce_id=voce.id, valore=Decimal("1")
    )
    session.commit()

    atteso_bagni = attese_per_mq(session, 85)["bagni"]
    ris = risolvi_effetti_pro(session, mq=85, tipo="totale", risposte={})

    assert ris.quantita_per_unita[voce.id] == atteso_bagni


def test_quantita_per_unita_senza_atteso_non_produce_voce(session):
    voce = _voce_a6(session, "A.6.9")
    domanda = _aggiungi_domanda(
        session,
        code="test_qta_senza_atteso",
        tipo_controllo="stepper",
        attributo_code="attributo_inesistente",
    )
    opz = _aggiungi_opzione(session, domanda, code="valore", is_default=True)
    _aggiungi_effetto(
        session, opz, tipo_effetto=TIPO_QUANTITA_PER_UNITA, target_voce_id=voce.id, valore=Decimal("1")
    )
    session.commit()

    ris = risolvi_effetti_pro(session, mq=85, tipo="totale", risposte={})

    assert voce.id not in ris.quantita_per_unita
    traccia = next(
        a
        for a in ris.applicati
        if a.domanda_code == "test_qta_senza_atteso" and a.tipo_effetto == TIPO_QUANTITA_PER_UNITA
    )
    assert traccia.applicato is False
    assert traccia.nota


# --- fattore_quantita ---------------------------------------------------------


def test_fattore_quantita_su_voce_e_su_sottocategoria_si_moltiplicano(session):
    voce = _voce_a6(session, "A.6.9")
    sotto = _sotto_a6(session)

    domanda = _aggiungi_domanda(session, code="test_fattore", tipo_controllo="toggle")
    opz = _aggiungi_opzione(session, domanda, code="si", is_default=True)
    _aggiungi_effetto(
        session, opz, tipo_effetto=TIPO_FATTORE_QUANTITA, target_voce_id=voce.id, valore=Decimal("2")
    )
    _aggiungi_effetto(
        session,
        opz,
        tipo_effetto=TIPO_FATTORE_QUANTITA,
        target_sottocategoria_id=sotto.id,
        valore=Decimal("3"),
    )
    session.commit()

    ris = risolvi_effetti_pro(session, mq=85, tipo="totale", risposte={})

    assert ris.fattore(voce.id, sotto.id) == Decimal("6")


# --- tipo_code / attivo -------------------------------------------------------


def test_effetto_con_tipo_code_diverso_e_ignorato(session):
    voce = _voce_a6(session, "A.6.9")
    domanda = _aggiungi_domanda(session, code="test_tipo_code", tipo_controllo="toggle")
    opz = _aggiungi_opzione(session, domanda, code="si", is_default=True)
    _aggiungi_effetto(
        session,
        opz,
        tipo_effetto=TIPO_FATTORE_QUANTITA,
        target_voce_id=voce.id,
        valore=Decimal("5"),
        tipo_code="leggera",
    )
    session.commit()

    ris = risolvi_effetti_pro(session, mq=85, tipo="totale", risposte={})

    assert ris.fattori_voce.get(voce.id, Decimal("1")) == Decimal("1")


def test_opzione_non_attiva_e_ignorata(session):
    voce = _voce_a6(session, "A.6.9")
    domanda = _aggiungi_domanda(session, code="test_opz_inattiva", tipo_controllo="toggle")
    opz = _aggiungi_opzione(session, domanda, code="si", is_default=True)
    opz.attiva = False
    session.flush()
    _aggiungi_effetto(session, opz, tipo_effetto=TIPO_ESCLUDI, target_voce_id=voce.id)
    session.commit()

    ris = risolvi_effetti_pro(session, mq=85, tipo="totale", risposte={})

    assert voce.id not in ris.escluse_voci


def test_effetto_non_attivo_e_ignorato(session):
    voce = _voce_a6(session, "A.6.9")
    domanda = _aggiungi_domanda(session, code="test_effetto_inattivo", tipo_controllo="toggle")
    opz = _aggiungi_opzione(session, domanda, code="si", is_default=True)
    _aggiungi_effetto(session, opz, tipo_effetto=TIPO_ESCLUDI, target_voce_id=voce.id, attivo=False)
    session.commit()

    ris = risolvi_effetti_pro(session, mq=85, tipo="totale", risposte={})

    assert voce.id not in ris.escluse_voci


# --- riga malformata -----------------------------------------------------------


def test_effetto_includi_senza_bersaglio_tracciato_non_eccezione(session):
    domanda = _aggiungi_domanda(session, code="test_malformato")
    opz = _aggiungi_opzione(session, domanda, code="si", is_default=True)
    # Nessun target_voce_id, nessun target_sottocategoria_id: malformato.
    session.add(EffettoOpzione(opzione_id=opz.id, tipo_effetto=TIPO_INCLUDI, attivo=True))
    session.commit()

    ris = risolvi_effetti_pro(session, mq=85, tipo="totale", risposte={})  # non deve lanciare

    traccia = next(a for a in ris.applicati if a.domanda_code == "test_malformato")
    assert traccia.applicato is False
    assert traccia.nota


def test_escludi_senza_bersaglio_tracciato_non_eccezione(session):
    domanda = _aggiungi_domanda(session, code="test_escludi_malformato", tipo_controllo="toggle")
    opz = _aggiungi_opzione(session, domanda, code="si", is_default=True)
    session.add(EffettoOpzione(opzione_id=opz.id, tipo_effetto=TIPO_ESCLUDI, attivo=True))
    session.commit()

    ris = risolvi_effetti_pro(session, mq=85, tipo="totale", risposte={})  # non deve lanciare

    traccia = next(a for a in ris.applicati if a.domanda_code == "test_escludi_malformato")
    assert traccia.applicato is False
    assert traccia.nota


# --- visibilita' -----------------------------------------------------------


def test_domanda_non_visibile_non_governa_le_sue_voci(session):
    voce = _voce_a6(session, "A.6.9")

    gate = _aggiungi_domanda(session, code="test_gate", tipo_controllo="toggle")
    _aggiungi_opzione(session, gate, code="si", is_default=False)
    _aggiungi_opzione(session, gate, code="no", is_default=True, ordine=2)

    governata = _aggiungi_domanda(
        session,
        code="test_governata",
        tipo_controllo="toggle",
        visibile_se_domanda_code="test_gate",
        visibile_se_opzione_code="si",
    )
    opz = _aggiungi_opzione(session, governata, code="si", is_default=True)
    _aggiungi_effetto(session, opz, tipo_effetto=TIPO_INCLUDI, target_voce_id=voce.id)
    session.commit()

    # Nessuna risposta al gate -> resta sul default "no" -> "test_governata"
    # non e' visibile.
    ris = risolvi_effetti_pro(session, mq=85, tipo="totale", risposte={})

    codici_assi = {a.domanda_code for a in ris.assi}
    assert "test_governata" not in codici_assi
    sotto = _sotto_a6(session)
    assert ris.voce_inclusa(voce.id, sotto.id, "A-EDILE") is True


def test_nessun_import_del_motore_free():
    import inspect

    from app.services import effetti as modulo

    sorgente = inspect.getsource(modulo)
    righe_import = [r for r in sorgente.splitlines() if r.strip().startswith(("import ", "from "))]
    assert not any("estimation" in r for r in righe_import)
