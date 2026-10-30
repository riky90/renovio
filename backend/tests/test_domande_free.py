"""Catalogo domande + motore Free parametrico (0014).

Tre cose vanno dimostrate, non sperate:

  1. NEUTRALITA' — il layer a riposo non muove un euro. `risposte=None` (layer
     spento) e `risposte={}` (layer acceso, tutte le domande sui loro default)
     devono produrre lo stesso identico numero dell'oracolo primario
     47.251-69.473. Senza questo, ogni stima gia' salvata cambierebbe valore.
  2. DISCIPLINA DEL DATO — la neutralita' regge solo se l'opzione di default di
     ogni domanda non porta effetti. E' una regola di curatela, quindi va
     verificata sul seed e non lasciata alla buona volonta' di chi lo modifica.
  3. ARITMETICA — moltiplicatori prima degli additivi, correzioni sullo
     SCOSTAMENTO e non sul valore assoluto, moltiplicatore 0 che azzera la
     categoria e ne salta la coda.

Oracoli derivati dal seed RE (85 m2, tipo=totale), tutti esatti:
    A-EDILE  300 x 1.00 x 85 = 25.500  + IVA 10%  -> 28.050  -> [22.440, 33.660]
    B        130 x 1.00 x 85 = 11.050  + IVA 22%  -> 13.481  -> [10.785, 16.177]
    C         90 x 1.00 x 85 =  7.650  + IVA 10%  ->  8.415  -> [ 6.732, 10.098]
    D         60 x 1.00 x 85 =  5.100  + IVA 10%  ->  5.610  -> [ 4.488,  6.732]
    extra fissi 2.806 -> totale [47.251, 69.473]
"""

from decimal import Decimal

import pytest
from sqlalchemy import create_engine

from app.db import Base
from app.models.domanda import AttesaImmobile, Domanda, EffettoOpzione, OpzioneDomanda
from app.services.city_resolver import resolve_listino
from app.services.effetti import (
    TIPI_EFFETTO_FREE,
    EffettoNonValido,
    attese_per_mq,
    risolvi_effetti_free,
    valida_effetto,
)
from app.services.estimation import EstimationService
from scripts.seed import load_seed_data, seed
from tests.computo_spento import catalogo_v2
from tests.session_factory import sessione_di_test


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)
    with testing_session_local() as s:
        seed(s, load_seed_data())
        # Aritmetica del percorso EUR/m2 + effetti (ripiego senza regole)
        # sul catalogo nella forma v2: vedi tests/computo_spento.py.
        catalogo_v2(s)
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
    assert result.totale_min == Decimal("47251")
    assert result.totale_max == Decimal("69473")


def test_risposte_vuote_sono_identiche_a_layer_spento(session, listino):
    """Il layer ACCESO ma senza risposte cade sui default, che sono neutri.

    E' la prova che il wizard puo' andare in produzione senza cambiare il
    prezzo di nessuna stima gia' fatta.
    """
    spento = _stima(session, listino, risposte=None)
    acceso = _stima(session, listino, risposte={})

    assert acceso.totale_min == spento.totale_min == Decimal("47251")
    assert acceso.totale_max == spento.totale_max == Decimal("69473")
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

    assert result.totale_min == Decimal("47251")
    assert result.totale_max == Decimal("69473")


# --- 2. disciplina del dato -------------------------------------------------


def test_nessuna_opzione_di_default_porta_effetti(session):
    """La neutralita' e' una proprieta' dei DATI, non del codice.

    Se un domani qualcuno mette un moltiplicatore sull'opzione di default di
    una domanda, ogni stima gia' salvata cambia valore in silenzio. Questo test
    e' il posto in cui quella modifica si ferma.

    Filtrato ai soli effetti FREE (Fase 09): un `includi` Pro sull'opzione di
    default (finitura=medio, tipo_pavimento=gres) e' il meccanismo stesso con
    cui il default resta "senza alternative sommate" (D-07) — non una
    correzione di prezzo silenziosa come un `moltiplicatore_categoria`. La
    disciplina qui protetta e' quella del layer Free, non del Pro.
    """
    colpevoli = (
        session.query(OpzioneDomanda.domanda_code, OpzioneDomanda.code)
        .join(EffettoOpzione, EffettoOpzione.opzione_id == OpzioneDomanda.id)
        .filter(
            OpzioneDomanda.is_default.is_(True),
            EffettoOpzione.tipo_effetto.in_(sorted(TIPI_EFFETTO_FREE)),
        )
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


def test_opzione_disattivata_non_applica_i_suoi_effetti(session):
    """D-27: spegnere un'opzione deve spegnere anche i suoi effetti, non solo
    nasconderla dal wizard — altrimenti una risposta che il client non mostra
    piu' continuerebbe silenziosamente a correggere il prezzo."""
    accesa = risolvi_effetti_free(
        session, mq=85, tipo="totale", risposte={"anno_costruzione": "pre_1980"}
    )
    assert any(
        a.opzione_code == "pre_1980" and a.applicato for a in accesa.applicati
    ), "l'opzione accesa deve avere almeno un effetto applicato"

    opzione = (
        session.query(OpzioneDomanda)
        .filter_by(domanda_code="anno_costruzione", code="pre_1980")
        .one()
    )
    opzione.attiva = False
    session.flush()

    spenta = risolvi_effetti_free(
        session, mq=85, tipo="totale", risposte={"anno_costruzione": "pre_1980"}
    )
    assert not any(a.opzione_code == "pre_1980" for a in spenta.applicati)


def test_attesa_disattivata_non_fa_piu_da_baseline(session):
    """D-40: un'attesa spenta smette di coprire la fascia, sia come default del
    wizard sia come baseline dello scostamento nel motore."""
    prima = attese_per_mq(session, 85)
    assert "bagni" in prima

    riga = (
        session.query(AttesaImmobile)
        .filter(
            AttesaImmobile.attributo_code == "bagni",
            AttesaImmobile.fascia_mq_min <= 85,
            AttesaImmobile.fascia_mq_max >= 85,
        )
        .one()
    )
    riga.attiva = False
    session.flush()

    dopo = attese_per_mq(session, 85)
    assert "bagni" not in dopo


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
    """pre_1980 -> A-EDILE x1.10: 28.050 x 1.10 = 30.855 -> [24.684, 37.026].

    La classe energetica e' dichiarata a mano (`c`, la neutra) per ISOLARE il
    moltiplicatore dell'eta': senza, l'anno dedurrebbe anche la classe (0017) e
    il test misurerebbe due effetti credendo di misurarne uno.
    """
    result = _stima(
        session,
        listino,
        risposte={"anno_costruzione": "pre_1980", "classe_energetica_attuale": "c"},
    )

    assert _cat(result, "A-EDILE").totale_min == Decimal("24684")
    assert _cat(result, "A-EDILE").totale_max == Decimal("37026")


def test_eur_mq_additivo(session, listino):
    """obiettivo classe B -> +80 EUR/m2 su A-EDILE.

    25.500 + 80 x 85 = 32.300 + IVA 10% -> 35.530 -> [28.424, 42.636]

    L'euro/m2 stava sull'opzione `tre_piu` di `efficientamento` finche' quella
    domanda era una scelta a tre valori. Ora e' un filtro si-no che apre il
    punto di arrivo: stessa aritmetica, un'altra riga di catalogo.
    """
    result = _stima(
        session,
        listino,
        risposte={"efficientamento": "si", "classe_energetica_obiettivo": "b"},
    )

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
        risposte={
            "anno_costruzione": "pre_1980",
            "classe_energetica_attuale": "c",
            "efficientamento": "si",
            "classe_energetica_obiettivo": "b",
        },
    )

    lordo_atteso = Decimal("34850") * Decimal("1.10")  # + IVA 10%
    assert _cat(result, "A-EDILE").totale_min == Decimal("30668")  # 38335 x 0.8
    assert _cat(result, "A-EDILE").totale_max == Decimal("46002")  # 38335 x 1.2
    assert lordo_atteso == Decimal("38335.00")


def test_effetto_per_tipo_di_ristrutturazione(session, listino):
    """`tipo_code` sull'effetto: rifare il riscaldamento pesa su una
    ristrutturazione leggera e non su una totale, dove e' gia' nel prezzo base.

    leggera: 300 x 0.25 x 85 = 6.375 x 1.16 = 7.395 + IVA -> 8.134,5 -> [6.914, 9.355]
    (range della leggera +/-15% dal 2026-10-30, TAR-01)
    """
    leggera_base = _stima(session, listino, tipo="leggera", risposte={})
    leggera = _stima(session, listino, tipo="leggera", risposte={"impianti": ["termico"]})
    totale_base = _stima(session, listino, tipo="totale", risposte={})
    totale = _stima(session, listino, tipo="totale", risposte={"impianti": ["termico"]})

    assert _cat(leggera, "A-EDILE").totale_min == Decimal("6914")
    assert _cat(leggera, "A-EDILE").totale_max == Decimal("9355")
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
    "baseline dichiarata e mancante", che invece si salta.

    Il filtro `muri_lavori` va dichiarato: la domanda vive sotto di esso, e una
    risposta a una domanda invisibile non pesa (vedi
    `test_risposta_a_domanda_filtrata_non_pesa`)."""
    base = _stima(session, listino, risposte={})
    result = _stima(
        session, listino, risposte={"muri_lavori": "si", "muri_da_recuperare": 40}
    )

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

    assert result.totale_min == Decimal("47251")
    assert result.totale_max == Decimal("69473")


def test_codice_opzione_inesistente_cade_sul_default(session, listino):
    result = _stima(session, listino, risposte={"anno_costruzione": "nel_futuro"})

    assert result.totale_min == Decimal("47251")


def test_toggle_mandato_come_booleano_non_diventa_una_quantita(session, listino):
    """In Python `True` e' un `int`. Un toggle mandato come booleano deve cadere
    sul default, non essere letto come il numero 1."""
    result = _stima(session, listino, risposte={"ascensore": True})

    assert result.totale_min == Decimal("47251")


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
    assert gate_chiuso.totale_min == Decimal("47251")

    gate_aperto = _stima(
        session,
        listino,
        risposte={"tipo_immobile": "villetta_singola", "efficientamento": "tre_piu"},
    )
    assert gate_aperto.totale_min > Decimal("47251")


# --- validazione admin ------------------------------------------------------


def test_valida_effetto_accetta_una_riga_corretta(session):
    valida_effetto(
        session, "moltiplicatore_categoria", categoria_code="A-EDILE", valore=Decimal("1.1")
    )
    valida_effetto(session, "escludi", categoria_code="C-SERRAMENTI")


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
def test_valida_effetto_rifiuta_le_righe_incoerenti(session, kwargs, atteso):
    tipo = kwargs.pop("tipo_effetto")
    with pytest.raises(EffettoNonValido, match=atteso):
        valida_effetto(session, tipo, **kwargs)


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


def test_seed_non_riscrive_una_domanda_curata_dal_pannello(session):
    """D-41: il catalogo domande e' del pannello, non del seed. Un testo
    corretto a mano, una domanda disattivata e un'opzione disattivata devono
    restare come li ha lasciati l'admin dopo un riavvio del container —
    altrimenti ogni deploy su Render annulla la curatela fatta da
    `/admin/domande` o dall'Excel di questa fase."""
    domanda = session.get(Domanda, "anno_costruzione")
    domanda.testo = "Testo modificato a mano"
    domanda.attiva = False
    opzione = (
        session.query(OpzioneDomanda)
        .filter_by(domanda_code="anno_costruzione", code="pre_1980")
        .one()
    )
    opzione.attiva = False
    session.flush()

    seed(session, load_seed_data())

    session.refresh(domanda)
    session.refresh(opzione)
    assert domanda.testo == "Testo modificato a mano"
    assert domanda.attiva is False
    assert opzione.attiva is False


def test_seed_crea_ancora_domande_e_opzioni_mancanti(session):
    """Create-if-missing non vuol dire "mai piu' creato": un'opzione del JSON
    assente dal database (cancellata a mano in sessione, come potrebbe
    succedere in un ambiente di sviluppo) torna al prossimo boot."""
    opzione = (
        session.query(OpzioneDomanda)
        .filter_by(domanda_code="anno_costruzione", code="pre_1980")
        .one()
    )
    session.query(EffettoOpzione).filter_by(opzione_id=opzione.id).delete()
    session.delete(opzione)
    session.flush()

    assert (
        session.query(OpzioneDomanda)
        .filter_by(domanda_code="anno_costruzione", code="pre_1980")
        .one_or_none()
        is None
    )

    seed(session, load_seed_data())

    ricreata = (
        session.query(OpzioneDomanda)
        .filter_by(domanda_code="anno_costruzione", code="pre_1980")
        .one_or_none()
    )
    assert ricreata is not None


# --- derivazione fra risposte (0017) ----------------------------------------


def test_derivazione_deduce_la_classe_dallanno_dichiarato(session, listino):
    """Chi non sa la classe energetica ma dichiara l'anno ottiene la stessa
    stima di chi la classe l'ha dichiarata a mano.

    E' il senso della tabella `derivazione_risposta`: da li' in poi nessun
    consumatore distingue una risposta dedotta da una digitata.
    """
    dedotta = _stima(session, listino, risposte={"anno_costruzione": "pre_1980"})
    dichiarata = _stima(
        session,
        listino,
        risposte={"anno_costruzione": "pre_1980", "classe_energetica_attuale": "g"},
    )

    assert dedotta.totale_min == dichiarata.totale_min
    assert dedotta.totale_max == dichiarata.totale_max


def test_derivazione_non_scatta_sul_default_dellanno(session, listino):
    """L'invariante che la derivazione NON deve rompere.

    `anno_costruzione` ha a sua volta un default (`1980_1990`). Se la deduzione
    partisse dalla risposta RISOLTA invece che da quella data, un utente che
    non tocca niente si vedrebbe applicare un moltiplicatore dedotto da un anno
    che non ha mai dichiarato — cioe' il default smetterebbe di essere neutro e
    l'oracolo primario cambierebbe in silenzio.
    """
    assert _stima(session, listino, risposte={}).totale_min == Decimal("47251")
    assert _stima(session, listino, risposte={"locali": 3}).totale_min == Decimal("47251")


def test_derivazione_non_sovrascrive_una_risposta_data(session, listino):
    """Si deduce solo cio' che l'utente non sa: `non_so` e' il trigger, e una
    classe dichiarata resta quella dichiarata anche se l'anno direbbe altro."""
    con_classe = _stima(
        session,
        listino,
        risposte={"anno_costruzione": "pre_1980", "classe_energetica_attuale": "c"},
    )
    dedotta = _stima(session, listino, risposte={"anno_costruzione": "pre_1980"})

    # `c` e' la classe neutra, `g` no: se la deduzione avesse sovrascritto la
    # risposta data, i due numeri coinciderebbero.
    assert con_classe.totale_min < dedotta.totale_min


# --- filtro e importo fisso -------------------------------------------------


def test_risposta_a_domanda_filtrata_non_pesa(session, listino):
    """Le domande sui muri vivono sotto il filtro `muri_lavori`. Rispondere
    alla domanda figlia senza aprire il filtro non deve cambiare il prezzo:
    altrimenti un client che manda uno stato vecchio farebbe pagare lavori che
    l'utente ha tolto."""
    base = _stima(session, listino, risposte={})
    filtrata = _stima(session, listino, risposte={"muri_da_rifare_mq": 40})
    aperta = _stima(
        session, listino, risposte={"muri_lavori": "si", "muri_da_rifare_mq": 40}
    )

    assert filtrata.totale_min == base.totale_min
    assert aperta.totale_min > base.totale_min


def test_filtro_aperto_senza_quantita_resta_neutro(session, listino):
    """Aprire il filtro non costa nulla di per se': i m2 sono a zero."""
    base = _stima(session, listino, risposte={})
    aperto = _stima(session, listino, risposte={"muri_lavori": "si"})

    assert aperto.totale_min == base.totale_min
    assert aperto.totale_max == base.totale_max


def test_eur_fisso_non_scala_coi_metri_quadri(session, listino):
    """La ragione per cui `eur_fisso_categoria` esiste.

    Un impianto fotovoltaico costa quello che costa. Spinto dentro
    `eur_mq_categoria` costerebbe il doppio in una casa grande il doppio, che e'
    falso e si vede a occhio nella prima prova su 200 m2.
    """
    risposte_si = {"efficientamento": "si"}
    risposte_fv = {"efficientamento": "si", "interventi_efficientamento": ["fotovoltaico"]}

    def delta(mq):
        senza = _cat(_stima(session, listino, mq=mq, risposte=risposte_si), "A-EDILE")
        con = _cat(_stima(session, listino, mq=mq, risposte=risposte_fv), "A-EDILE")
        return con.totale_min - senza.totale_min

    assert delta(85) == delta(200)
    assert delta(85) > 0


def test_cappotto_scala_coi_metri_quadri(session, listino):
    """Controprova del test precedente: il cappotto e' genuinamente a m2, e
    deve comportarsi in modo OPPOSTO all'importo fisso. Senza questo test,
    `eur_fisso_categoria` passerebbe anche se qualcuno lo applicasse a tutto."""
    risposte_si = {"efficientamento": "si"}
    risposte_cappotto = {
        "efficientamento": "si",
        "interventi_efficientamento": ["cappotto_esterno"],
    }

    def delta(mq):
        senza = _cat(_stima(session, listino, mq=mq, risposte=risposte_si), "A-EDILE")
        con = _cat(_stima(session, listino, mq=mq, risposte=risposte_cappotto), "A-EDILE")
        return con.totale_min - senza.totale_min

    assert delta(200) > delta(85)
