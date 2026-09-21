"""Catalogo domande + motore Free parametrico (0014).

Tre cose vanno dimostrate, non sperate:

  1. NEUTRALITA' — il layer a riposo non muove un euro. `risposte=None` (layer
     spento) e `risposte={}` (layer acceso, tutte le domande sui loro default)
     devono produrre lo stesso identico numero dell'oracolo primario
     47.985-70.575. Senza questo, ogni stima gia' salvata cambierebbe valore.
  2. DISCIPLINA DEL DATO — la neutralita' regge solo se l'opzione di default di
     ogni domanda non porta effetti. E' una regola di curatela, quindi va
     verificata sul seed e non lasciata alla buona volonta' di chi lo modifica.
  3. ARITMETICA — moltiplicatori prima degli additivi, correzioni sullo
     SCOSTAMENTO e non sul valore assoluto, moltiplicatore 0 che azzera la
     categoria e ne salta la coda.

Oracoli derivati dal seed RE (85 m2, tipo=totale), tutti esatti:
    A-EDILE  300 x 1.00 x 85 = 25.500  + IVA 10%  -> 28.050  -> [22.440, 33.660]
    B        130 x 1.00 x 85 = 11.050  + IVA 22%  -> 13.481  -> [10.785, 16.177]
    C         90 x 1.00 x 85 =  7.650  + IVA 22%  ->  9.333  -> [ 7.466, 11.200]
    D         60 x 1.00 x 85 =  5.100  + IVA 10%  ->  5.610  -> [ 4.488,  6.732]
    extra fissi 2.806 -> totale [47.985, 70.575]
"""

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models.domanda import AttesaImmobile, Domanda, EffettoOpzione, OpzioneDomanda
from app.services.city_resolver import resolve_listino
from app.services.effetti import (
    EffettoNonValido,
    attese_per_mq,
    risolvi_effetti_free,
    valida_effetto,
)
from app.services.estimation import EstimationService
from scripts.seed import load_seed_data, seed


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine)
    with testing_session_local() as s:
        seed(s, load_seed_data())
        yield s


@pytest.fixture()
def listino(session):
    row, fallback = resolve_listino(session, "Reggio Emilia")
    assert fallback is False
    return row


def _cat(result, code):
    return next(c for c in result.categorie if c.code == code)


def _stima(session, listino, *, mq=85, tipo="totale", risposte=None):
    return EstimationService.compute(session, listino, mq=mq, tipo=tipo, risposte=risposte)


# --- 1. neutralita' ---------------------------------------------------------


def test_layer_spento_produce_loracolo_primario(session, listino):
    """`risposte=None` = come se il catalogo domande non esistesse."""
    result = _stima(session, listino)
    assert result.totale_min == Decimal("47985")
    assert result.totale_max == Decimal("70575")


def test_risposte_vuote_sono_identiche_a_layer_spento(session, listino):
    """Il layer ACCESO ma senza risposte cade sui default, che sono neutri.

    E' la prova che il wizard puo' andare in produzione senza cambiare il
    prezzo di nessuna stima gia' fatta.
    """
    spento = _stima(session, listino, risposte=None)
    acceso = _stima(session, listino, risposte={})

    assert acceso.totale_min == spento.totale_min == Decimal("47985")
    assert acceso.totale_max == spento.totale_max == Decimal("70575")
    for attesa, ottenuta in zip(spento.categorie, acceso.categorie):
        assert (attesa.code, attesa.totale_min, attesa.totale_max) == (
            ottenuta.code,
            ottenuta.totale_min,
            ottenuta.totale_max,
        )


def test_risposte_pari_agli_attesi_non_muovono_nulla(session, listino):
    """Rispondere esplicitamente "quello che e' normale" ha scostamento zero."""
    attese = attese_per_mq(session, 85)
    assert attese["bagni"] == Decimal("1.00")
    assert attese["locali"] == Decimal("3.00")

    risposte = {attributo: int(valore) for attributo, valore in attese.items()}
    result = _stima(session, listino, risposte=risposte)

    assert result.totale_min == Decimal("47985")
    assert result.totale_max == Decimal("70575")


# --- 2. disciplina del dato -------------------------------------------------


def test_nessuna_opzione_di_default_porta_effetti(session):
    """La neutralita' e' una proprieta' dei DATI, non del codice.

    Se un domani qualcuno mette un moltiplicatore sull'opzione di default di
    una domanda, ogni stima gia' salvata cambia valore in silenzio. Questo test
    e' il posto in cui quella modifica si ferma.
    """
    colpevoli = (
        session.query(OpzioneDomanda.domanda_code, OpzioneDomanda.code)
        .join(EffettoOpzione, EffettoOpzione.opzione_id == OpzioneDomanda.id)
        .filter(OpzioneDomanda.is_default.is_(True))
        .all()
    )
    assert colpevoli == [], (
        "Opzioni di default con effetti: "
        + ", ".join(f"{d}.{o}" for d, o in colpevoli)
        + ". Il default deve essere neutro."
    )


def test_ogni_scelta_singola_ha_esattamente_un_default(session):
    """Senza default una domanda non risposta non seleziona nulla; con due, il
    risultato dipenderebbe dall'ordine delle righe."""
    domande = (
        session.query(Domanda)
        .filter(Domanda.tipo_controllo.in_(["scelta_singola", "toggle"]))
        .all()
    )
    assert domande
    for d in domande:
        n = (
            session.query(OpzioneDomanda)
            .filter_by(domanda_code=d.code, is_default=True)
            .count()
        )
        assert n == 1, f"{d.code}: {n} opzioni di default"


def test_nessuna_tabella_del_catalogo_espone_il_coefficiente_impresa():
    """Regola non negoziabile #1, verificata sullo schema e non sulla fiducia."""
    vietate = {"coefficiente_impresa", "prezzo_impresa", "margine"}
    for modello in (Domanda, OpzioneDomanda, EffettoOpzione, AttesaImmobile):
        colonne = {c.name for c in modello.__table__.columns}
        assert not (colonne & vietate), f"{modello.__tablename__}: {colonne & vietate}"


# --- 3. aritmetica ----------------------------------------------------------


def test_scostamento_sui_bagni_muove_solo_le_categorie_bersaglio(session, listino):
    """3 bagni contro 1 atteso -> scostamento 2, su A-EDILE e D-PRODOTTI.

    A-EDILE  25.500 + 2 x 1.900 = 29.300 + IVA 10% -> 32.230 -> [25.784, 38.676]
    D        5.100 + 2 x 1.400  =  7.900 + IVA 10% ->  8.690 -> [ 6.952, 10.428]
    B e C non sono bersagli: devono restare al centesimo com'erano.
    """
    base = _stima(session, listino, risposte={})
    result = _stima(session, listino, risposte={"bagni": 3})

    assert _cat(result, "A-EDILE").totale_min == Decimal("25784")
    assert _cat(result, "A-EDILE").totale_max == Decimal("38676")
    assert _cat(result, "D-PRODOTTI").totale_min == Decimal("6952")
    assert _cat(result, "D-PRODOTTI").totale_max == Decimal("10428")

    for code in ("B-FINITURE", "C-SERRAMENTI"):
        assert _cat(result, code).totale_min == _cat(base, code).totale_min
        assert _cat(result, code).totale_max == _cat(base, code).totale_max


def test_scostamento_negativo_riduce(session, listino):
    """Le correzioni vanno in entrambe le direzioni: meno finestre dell'atteso
    costa meno. Un layer che sa solo aggiungere non e' una correzione, e' un
    ricarico."""
    base = _stima(session, listino, risposte={})
    meno = _stima(session, listino, risposte={"finestre": 2})

    assert _cat(meno, "C-SERRAMENTI").totale_min < _cat(base, "C-SERRAMENTI").totale_min


def test_moltiplicatore_su_categoria(session, listino):
    """pre_1980 -> A-EDILE x1.10: 28.050 x 1.10 = 30.855 -> [24.684, 37.026]."""
    result = _stima(session, listino, risposte={"anno_costruzione": "pre_1980"})

    assert _cat(result, "A-EDILE").totale_min == Decimal("24684")
    assert _cat(result, "A-EDILE").totale_max == Decimal("37026")


def test_eur_mq_additivo(session, listino):
    """efficientamento tre_piu -> +80 EUR/m2 su A-EDILE.

    25.500 + 80 x 85 = 32.300 + IVA 10% -> 35.530 -> [28.424, 42.636]
    """
    result = _stima(session, listino, risposte={"efficientamento": "tre_piu"})

    assert _cat(result, "A-EDILE").totale_min == Decimal("28424")
    assert _cat(result, "A-EDILE").totale_max == Decimal("42636")


def test_moltiplicatore_zero_azzera_e_salta_la_coda(session, listino):
    """"Non rifaccio i serramenti" azzera C, e lo scostamento sulle finestre
    NON riaccende la categoria da sotto.

    E' la regola dell'ordine di risoluzione: un moltiplicatore complessivo a 0
    salta i termini additivi, invece di lasciare una coda di correzioni su una
    categoria che l'utente ha escluso.
    """
    result = _stima(
        session, listino, risposte={"non_rifare": ["serramenti"], "finestre": 20}
    )

    c = _cat(result, "C-SERRAMENTI")
    assert c.totale_min == Decimal("0")
    assert c.totale_max == Decimal("0")


def test_moltiplicatori_prima_degli_additivi(session, listino):
    """L'euro/m2 dell'efficientamento non deve essere scalato dal
    moltiplicatore dell'eta' dell'immobile.

    Atteso: (25.500 x 1.10) + (80 x 85) = 28.050 + 6.800 = 34.850
    Se l'ordine fosse invertito uscirebbe (25.500 + 6.800) x 1.10 = 35.530,
    cioe' 680 EUR di imponibile in piu' senza che nessuno li abbia decisi.
    """
    result = _stima(
        session,
        listino,
        risposte={"anno_costruzione": "pre_1980", "efficientamento": "tre_piu"},
    )

    lordo_atteso = Decimal("34850") * Decimal("1.10")  # + IVA 10%
    assert _cat(result, "A-EDILE").totale_min == Decimal("30668")  # 38335 x 0.8
    assert _cat(result, "A-EDILE").totale_max == Decimal("46002")  # 38335 x 1.2
    assert lordo_atteso == Decimal("38335.00")


def test_effetto_per_tipo_di_ristrutturazione(session, listino):
    """`tipo_code` sull'effetto: rifare il riscaldamento pesa su una
    ristrutturazione leggera e non su una totale, dove e' gia' nel prezzo base.

    leggera: 300 x 0.25 x 85 = 6.375 x 1.16 = 7.395 + IVA -> 8.134,5 -> [7.321, 8.948]
    """
    leggera_base = _stima(session, listino, tipo="leggera", risposte={})
    leggera = _stima(session, listino, tipo="leggera", risposte={"impianti": ["termico"]})
    totale_base = _stima(session, listino, tipo="totale", risposte={})
    totale = _stima(session, listino, tipo="totale", risposte={"impianti": ["termico"]})

    assert _cat(leggera, "A-EDILE").totale_min == Decimal("7321")
    assert _cat(leggera, "A-EDILE").totale_max == Decimal("8948")
    assert _cat(leggera, "A-EDILE").totale_min > _cat(leggera_base, "A-EDILE").totale_min

    assert _cat(totale, "A-EDILE").totale_min == _cat(totale_base, "A-EDILE").totale_min


def test_scelta_multipla_compone_i_moltiplicatori(session, listino):
    """Due impianti scelti -> i due fattori si moltiplicano, non si sostituiscono."""
    uno = _stima(session, listino, tipo="leggera", risposte={"impianti": ["termico"]})
    due = _stima(
        session, listino, tipo="leggera", risposte={"impianti": ["termico", "elettrico"]}
    )

    assert _cat(due, "A-EDILE").totale_min > _cat(uno, "A-EDILE").totale_min


def test_attributo_senza_baseline_conta_dal_primo_metro(session, listino):
    """`muri_da_recuperare` non dichiara un `attributo_code`: la baseline e'
    zero per costruzione, quindi ogni m2 dichiarato pesa. E' diverso dal caso
    "baseline dichiarata e mancante", che invece si salta."""
    base = _stima(session, listino, risposte={})
    result = _stima(session, listino, risposte={"muri_da_recuperare": 40})

    # 25.500 + 40 x 28 = 26.620 + IVA 10% -> 29.282 -> [23.426, 35.138]
    assert _cat(result, "A-EDILE").totale_min == Decimal("23426")
    assert _cat(result, "A-EDILE").totale_max == Decimal("35138")
    assert _cat(base, "A-EDILE").totale_min == Decimal("22440")


# --- traccia e casi degeneri ------------------------------------------------


def test_baseline_dichiarata_ma_mancante_salta_leffetto_e_lo_dice(session, listino):
    """Se manca la riga di attesa per l'attributo, la correzione NON si applica.

    Meglio nessuna correzione che una correzione su una baseline inventata — ma
    il fatto deve restare visibile nella traccia, perche' e' un errore di
    curatela e l'anteprima admin e' il posto dove si vede.
    """
    session.query(AttesaImmobile).filter_by(attributo_code="bagni").delete()
    session.flush()

    risoluzione = risolvi_effetti_free(session, mq=85, tipo="totale", risposte={"bagni": 3})
    saltati = [e for e in risoluzione.applicati if not e.applicato]

    assert any(e.domanda_code == "bagni" for e in saltati)
    assert any("attesa" in (e.nota or "").lower() for e in saltati)
    assert "A-EDILE" not in risoluzione.correzioni or risoluzione.correzioni[
        "A-EDILE"
    ].eur_scostamento == Decimal("0")


def test_risposta_a_una_domanda_inesistente_viene_ignorata(session, listino):
    """Il client non e' fidato: una chiave sconosciuta non deve rompere nulla."""
    result = _stima(session, listino, risposte={"domanda_che_non_esiste": "qualunque"})

    assert result.totale_min == Decimal("47985")
    assert result.totale_max == Decimal("70575")


def test_codice_opzione_inesistente_cade_sul_default(session, listino):
    result = _stima(session, listino, risposte={"anno_costruzione": "nel_futuro"})

    assert result.totale_min == Decimal("47985")


def test_toggle_mandato_come_booleano_non_diventa_una_quantita(session, listino):
    """In Python `True` e' un `int`. Un toggle mandato come booleano deve cadere
    sul default, non essere letto come il numero 1."""
    result = _stima(session, listino, risposte={"ascensore": True})

    assert result.totale_min == Decimal("47985")


def test_traccia_riporta_contributo_e_unita(session):
    risoluzione = risolvi_effetti_free(session, mq=85, tipo="totale", risposte={"bagni": 3})
    bagni = [
        e for e in risoluzione.applicati if e.domanda_code == "bagni" and e.applicato
    ]

    assert bagni, "nessun effetto tracciato per i bagni"
    for e in bagni:
        assert e.unita == Decimal("2")
        assert e.contributo == e.unita * e.valore


def test_layer_spento_non_produce_traccia(session):
    assert risolvi_effetti_free(session, mq=85, tipo="totale", risposte=None).applicati == []


# --- visibilita' condizionale -----------------------------------------------


def test_domanda_gated_non_spara_se_il_gate_non_e_soddisfatto(session, listino):
    """Si aggancia `efficientamento` a un gate e si verifica che l'effetto
    sparisca quando il gate e' su un'altra risposta."""
    domanda = session.get(Domanda, "efficientamento")
    domanda.visibile_se_domanda_code = "tipo_immobile"
    domanda.visibile_se_opzione_code = "villetta_singola"
    session.flush()

    gate_chiuso = _stima(
        session,
        listino,
        risposte={"tipo_immobile": "appartamento", "efficientamento": "tre_piu"},
    )
    assert gate_chiuso.totale_min == Decimal("47985")

    gate_aperto = _stima(
        session,
        listino,
        risposte={"tipo_immobile": "villetta_singola", "efficientamento": "tre_piu"},
    )
    assert gate_aperto.totale_min > Decimal("47985")


# --- validazione admin ------------------------------------------------------


def test_valida_effetto_accetta_una_riga_corretta():
    valida_effetto(
        "moltiplicatore_categoria", categoria_code="A-EDILE", valore=Decimal("1.1")
    )
    valida_effetto("escludi", categoria_code="C-SERRAMENTI")


@pytest.mark.parametrize(
    "kwargs,atteso",
    [
        ({"tipo_effetto": "boh", "categoria_code": "A-EDILE"}, "sconosciuto"),
        ({"tipo_effetto": "escludi"}, "esattamente un bersaglio"),
        (
            {"tipo_effetto": "escludi", "categoria_code": "A-EDILE", "voce_id": 1},
            "esattamente un bersaglio",
        ),
        (
            {"tipo_effetto": "quantita_per_unita", "categoria_code": "A-EDILE", "valore": Decimal("1")},
            "non puo' puntare",
        ),
        ({"tipo_effetto": "eur_mq_categoria", "categoria_code": "A-EDILE"}, "richiede un valore"),
        (
            {"tipo_effetto": "moltiplicatore_categoria", "categoria_code": "A-EDILE", "valore": Decimal("-1")},
            "non puo' essere negativo",
        ),
    ],
)
def test_valida_effetto_rifiuta_le_righe_incoerenti(kwargs, atteso):
    tipo = kwargs.pop("tipo_effetto")
    with pytest.raises(EffettoNonValido, match=atteso):
        valida_effetto(tipo, **kwargs)


# --- seed -------------------------------------------------------------------


def test_seed_idempotente_non_duplica(session):
    prima = (
        session.query(Domanda).count(),
        session.query(OpzioneDomanda).count(),
        session.query(EffettoOpzione).count(),
        session.query(AttesaImmobile).count(),
    )
    seed(session, load_seed_data())
    dopo = (
        session.query(Domanda).count(),
        session.query(OpzioneDomanda).count(),
        session.query(EffettoOpzione).count(),
        session.query(AttesaImmobile).count(),
    )
    assert prima == dopo
    assert all(n > 0 for n in prima)


def test_seed_non_azzera_una_taratura_fatta_da_admin(session):
    """Il seed gira a ogni boot del container. Se possedesse i valori degli
    effetti, ogni deploy riporterebbe i coefficienti alla bozza cablata — lo
    stesso incidente che la regola condizionale su `voce.livello` evita."""
    effetto = (
        session.query(EffettoOpzione)
        .join(OpzioneDomanda, OpzioneDomanda.id == EffettoOpzione.opzione_id)
        .filter(OpzioneDomanda.domanda_code == "anno_costruzione")
        .first()
    )
    effetto.valore = Decimal("1.4200")
    attesa = session.query(AttesaImmobile).filter_by(attributo_code="bagni").first()
    attesa.valore_atteso = Decimal("2.00")
    session.flush()

    seed(session, load_seed_data())

    session.refresh(effetto)
    session.refresh(attesa)
    assert effetto.valore == Decimal("1.4200")
    assert attesa.valore_atteso == Decimal("2.00")


def test_seed_riscrive_invece_il_testo_di_una_domanda(session):
    """Il contrario del test precedente: testo e struttura sono del prodotto,
    non dell'admin, quindi il seed li riporta al valore dichiarato."""
    domanda = session.get(Domanda, "anno_costruzione")
    originale = domanda.testo
    domanda.testo = "Testo modificato a mano"
    session.flush()

    seed(session, load_seed_data())

    session.refresh(domanda)
    assert domanda.testo == originale
