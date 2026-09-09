"""Idempotent seed: loads `docs/seed-coefficienti-base.json` (+ 03-02:
`docs/seed-dettaglio-pro.json`) into the DB.

Upserts by natural key so re-running never duplicates rows:
  listino by nome, categoria by code, listino_categoria by
  (listino_id, categoria_code), tipo_ristrutturazione by code,
  moltiplicatore by (tipo_code, categoria_code), extra by code,
  comune_listino by comune_slug, sottocategoria by
  (listino_id, categoria_code, codice-o-nome), voce by
  (sottocategoria_id, codice-o-descrizione), coefficiente_qta_voce by
  (voce_id, tipo_code).

Dettaglio Pro esteso nella STESSA funzione `seed()` (D-03/D-12/Pitfall 5):
mai un secondo script di seed, per non lasciare il DB a meta' seminato dopo
un reset locale.

Run: `uv run python scripts/seed.py` (from backend/).
"""

from __future__ import annotations

import json
import sys
from datetime import date as _date
from decimal import Decimal
from pathlib import Path

from slugify import slugify
from sqlalchemy.orm import Session

# Allow `python scripts/seed.py` direct execution (not just `-m scripts.seed`):
# ensure backend/ (parent of scripts/) is importable as the `app` package root.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import app.models  # noqa: E402, F401 - registers all ORM entities on Base.metadata
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.models.bonus import (  # noqa: E402
    AliquotaBonus,
    BonusCategoria,
    BonusExtra,
    BonusFiscale,
)
from app.models.catalogo import (  # noqa: E402
    Categoria,
    ComuneListino,
    Extra,
    LivelloFinitura,
    Moltiplicatore,
    TipoRistrutturazione,
)
from app.models.dettaglio_pro import CoefficienteQuantitaVoce, Sottocategoria, Voce  # noqa: E402
from app.models.listino import Listino, ListinoCategoria  # noqa: E402
from app.models.testo import Testo  # noqa: E402

# I dati seed vivono in DUE posizioni possibili:
#  1) backend/seed_data/ — copia inclusa nell'immagine Docker (build context =
#     backend/, quindi docs/ alla root del repo NON e' raggiungibile in prod);
#  2) docs/ alla root del repo — sorgente storica usata in dev locale.
# Si preferisce la copia backend-local (prod) con fallback a docs/ (dev).
def _resolve_seed(filename: str) -> Path:
    local = _BACKEND_DIR / "seed_data" / filename
    if local.exists():
        return local
    return _BACKEND_DIR.parent / "docs" / filename


SEED_JSON_PATH = _resolve_seed("seed-coefficienti-base.json")
# Dati dettaglio Pro (03-02, D-03): stesso listino RE, estensione dello stesso seed idempotente.
SEED_DETTAGLIO_PRO_JSON_PATH = _resolve_seed("seed-dettaglio-pro.json")

CATEGORIA_NOMI = {
    "A-EDILE": "Edile",
    "B-FINITURE": "Finiture",
    "C-SERRAMENTI": "Serramenti/Porte",
    "D-PRODOTTI": "Prodotti",
}
CATEGORIA_ORDINE = {"A-EDILE": 1, "B-FINITURE": 2, "C-SERRAMENTI": 3, "D-PRODOTTI": 4}

# Dove il livello di finitura ha senso. A-EDILE resta FUORI: demolizioni,
# impianti e massetti dipendono dal TIPO di ristrutturazione, non dal gusto del
# cliente. Vive qui e finisce in tabella (`categoria.livello_selezionabile`)
# invece di essere un `if code == "A-EDILE"` sparso nel motore.
CATEGORIA_LIVELLO_SELEZIONABILE = {
    "A-EDILE": False,
    "B-FINITURE": True,
    "C-SERRAMENTI": True,
    "D-PRODOTTI": True,
}

# I tre livelli di finitura. `medio` e' il default applicato quando l'utente non
# sceglie: e' la scelta piu' difendibile su una stima pre-sopralluogo.
LIVELLI_FINITURA = [
    {"code": "base", "nome": "Entry level", "ordine": 1, "is_default": False,
     "descrizione": "Materiali di serie, buon rapporto qualita/prezzo."},
    {"code": "medio", "nome": "Medio", "ordine": 2, "is_default": True,
     "descrizione": "Materiali di fascia media, la scelta piu' frequente."},
    {"code": "alto", "nome": "Lusso", "ordine": 3, "is_default": False,
     "descrizione": "Materiali di pregio e finiture su misura."},
]

# Internal margin coefficient per category (foglio `listini` del computo).
# SEGRETO server-side: mai esposto al client (D-11 / CLAUDE.md). Mappatura
# fissata in 01-RESEARCH.md Open Question 1 (A1): A->0.65, B->0.6, C->0.55, D->0.5.
COEFFICIENTE_IMPRESA = {
    "A-EDILE": Decimal("0.65"),
    "B-FINITURE": Decimal("0.6"),
    "C-SERRAMENTI": Decimal("0.55"),
    "D-PRODOTTI": Decimal("0.5"),
}

TIPO_NOMI = {"leggera": "Leggera", "moderata": "Moderata", "totale": "Totale"}
TIPO_ORDINE = {"leggera": 1, "moderata": 2, "totale": 3}

EXTRA_NOMI = {"CSE_CSP": "CSE/CSP", "pratiche": "Pratiche amministrative"}
# Provisional default (D-12 / A3), admin-editable in a later phase.
EXTRA_IVA_PCT = Decimal("0.22")

# RE aliases the free-text city input must resolve without fallback (D-06/D-07,
# Pitfall 6). "Reggio Emilia" also covers case-insensitive variants (slugify
# lowercases); "Reggio nell'Emilia" is a distinct slug and needs its own row.
RE_ALIASES = ["Reggio Emilia", "Reggio nell'Emilia"]

# Testi/disclaimer iniziali (D-14): valori identici agli hardcoded attuali,
# migrati in tabella Testo. Scope v1 SOLO backend-owned (04-RESEARCH.md Open
# Question 1) — nessuna chiave per il fallback referente D-05 (Pitfall 5).
# --- Bonus fiscali (0011) --------------------------------------------------
# NORMATIVA 2026 verificata su fonti aggiornate. Le aliquote CALANO dal 2027:
# per questo la riga 2027 e' gia' seminata oggi, con `valido_dal`. Il passaggio
# d'anno non deve richiedere un deploy — e' un dato, non un rilascio.
#
# Barriere architettoniche 75%: SCADUTO il 31/12/2025. Dal 2026 quegli
# interventi rientrano nel bonus ristrutturazione, quindi non c'e' una riga
# dedicata. Questo commento esiste perche' la sua assenza non sembri una
# dimenticanza.
BONUS_FISCALI = [
    {
        "code": "RISTRUTTURAZIONE",
        "nome": "Bonus ristrutturazione",
        "descrizione": (
            "Detrazione IRPEF sugli interventi di recupero edilizio, in 10 quote annuali."
        ),
        "ordine": 1,
        "attivo": True,
    },
    {
        "code": "ECOBONUS",
        "nome": "Ecobonus",
        "descrizione": (
            "Detrazione sugli interventi di riqualificazione energetica "
            "(serramenti, schermature, coibentazioni), in 10 quote annuali."
        ),
        "ordine": 2,
        "attivo": True,
    },
    {
        # Seminato ma SPENTO: serve un input dedicato (la spesa per l'arredo),
        # che il form non raccoglie. Acceso il giorno che quell'input esiste.
        "code": "MOBILI",
        "nome": "Bonus mobili",
        "descrizione": "Detrazione sull'acquisto di mobili e grandi elettrodomestici.",
        "ordine": 3,
        "attivo": False,
    },
    {
        # Seminato ma SPENTO: serve la classe di rischio sismico dell'immobile.
        "code": "SISMABONUS",
        "nome": "Sismabonus",
        "descrizione": "Detrazione sugli interventi di riduzione del rischio sismico.",
        "ordine": 4,
        "attivo": False,
    },
]

_DAL_2026 = _date(2026, 1, 1)
_AL_2026 = _date(2026, 12, 31)
_DAL_2027 = _date(2027, 1, 1)

ALIQUOTE_BONUS = [
    # --- 2026 -------------------------------------------------------------
    {"bonus_code": "RISTRUTTURAZIONE", "destinazione": "prima_casa", "aliquota_pct": "0.50",
     "tetto_spesa_eur": "96000", "tetto_modalita": "per_unita_immobiliare", "rate_annuali": 10,
     "valido_dal": _DAL_2026, "valido_al": _AL_2026,
     "note": "Abitazione principale, 2026."},
    {"bonus_code": "RISTRUTTURAZIONE", "destinazione": "altro", "aliquota_pct": "0.36",
     "tetto_spesa_eur": "96000", "tetto_modalita": "per_unita_immobiliare", "rate_annuali": 10,
     "valido_dal": _DAL_2026, "valido_al": _AL_2026,
     "note": "Immobili diversi dall'abitazione principale, 2026."},
    {"bonus_code": "ECOBONUS", "destinazione": "prima_casa", "aliquota_pct": "0.50",
     "tetto_spesa_eur": "60000", "tetto_modalita": "per_intervento", "rate_annuali": 10,
     "valido_dal": _DAL_2026, "valido_al": _AL_2026,
     "note": "Massimale serramenti/schermature. Cappotto 60.000, climatizzazione 30.000, "
             "riqualificazione globale 100.000: da differenziare quando la stima "
             "distinguera' i singoli interventi."},
    {"bonus_code": "ECOBONUS", "destinazione": "altro", "aliquota_pct": "0.36",
     "tetto_spesa_eur": "60000", "tetto_modalita": "per_intervento", "rate_annuali": 10,
     "valido_dal": _DAL_2026, "valido_al": _AL_2026, "note": None},
    # --- dal 2027: aliquote ridotte, gia' a DB ----------------------------
    {"bonus_code": "RISTRUTTURAZIONE", "destinazione": "prima_casa", "aliquota_pct": "0.36",
     "tetto_spesa_eur": "96000", "tetto_modalita": "per_unita_immobiliare", "rate_annuali": 10,
     "valido_dal": _DAL_2027, "valido_al": None,
     "note": "Aliquota ridotta dal 2027. Da riverificare: dal 2028 e' previsto anche un "
             "abbassamento del tetto di spesa."},
    {"bonus_code": "RISTRUTTURAZIONE", "destinazione": "altro", "aliquota_pct": "0.30",
     "tetto_spesa_eur": "96000", "tetto_modalita": "per_unita_immobiliare", "rate_annuali": 10,
     "valido_dal": _DAL_2027, "valido_al": None, "note": "Aliquota ridotta dal 2027."},
    {"bonus_code": "ECOBONUS", "destinazione": "prima_casa", "aliquota_pct": "0.36",
     "tetto_spesa_eur": "60000", "tetto_modalita": "per_intervento", "rate_annuali": 10,
     "valido_dal": _DAL_2027, "valido_al": None, "note": "Aliquota ridotta dal 2027."},
    {"bonus_code": "ECOBONUS", "destinazione": "altro", "aliquota_pct": "0.30",
     "tetto_spesa_eur": "60000", "tetto_modalita": "per_intervento", "rate_annuali": 10,
     "valido_dal": _DAL_2027, "valido_al": None, "note": "Aliquota ridotta dal 2027."},
    # Bonus spenti: le aliquote esistono comunque, cosi' accenderli e' un flag.
    {"bonus_code": "MOBILI", "destinazione": "prima_casa", "aliquota_pct": "0.50",
     "tetto_spesa_eur": "5000", "tetto_modalita": "per_unita_immobiliare", "rate_annuali": 10,
     "valido_dal": _DAL_2026, "valido_al": None, "note": "Spento: manca l'input spesa mobili."},
    {"bonus_code": "SISMABONUS", "destinazione": "prima_casa", "aliquota_pct": "0.50",
     "tetto_spesa_eur": None, "tetto_modalita": None, "rate_annuali": 10,
     "valido_dal": _DAL_2026, "valido_al": None, "note": "Spento: manca la classe di rischio."},
]

# Quale spesa alimenta quale bonus. La somma delle quote per categoria sui
# bonus ATTIVI deve stare entro 1, altrimenti la stessa spesa verrebbe
# detratta due volte (verificato da test_bonus.py e da un 409 lato admin).
BONUS_CATEGORIE = [
    {"bonus_code": "RISTRUTTURAZIONE", "categoria_code": "A-EDILE", "quota": "1"},
    {"bonus_code": "RISTRUTTURAZIONE", "categoria_code": "B-FINITURE", "quota": "1"},
    {"bonus_code": "RISTRUTTURAZIONE", "categoria_code": "D-PRODOTTI", "quota": "1"},
    # I serramenti vanno sull'ECOBONUS, non sul bonus ristrutturazione.
    {"bonus_code": "ECOBONUS", "categoria_code": "C-SERRAMENTI", "quota": "1"},
]

# Quali EXTRA alimentano quale bonus. CSE/CSP (sicurezza in cantiere) e
# pratiche amministrative sono prestazioni tecniche connesse all'intervento e
# rientrano nella spesa detraibile del bonus ristrutturazione: sono elencati
# qui e non sommati d'ufficio perche' la detraibilita' di un extra e' curatela
# fiscale, e un extra futuro non detraibile deve poter restare fuori senza
# toccare il codice. Stesso vincolo delle categorie: somma delle quote per
# extra sui bonus attivi entro 1.
BONUS_EXTRA = [
    {"bonus_code": "RISTRUTTURAZIONE", "extra_code": "CSE_CSP", "quota": "1"},
    {"bonus_code": "RISTRUTTURAZIONE", "extra_code": "pratiche", "quota": "1"},
]

TESTI_INIZIALI = {
    "disclaimer_fallback_citta": (
        "Stima basata sul listino di Reggio Emilia, non ancora tarata su {citta}."
    ),
    "email_conferma_lead_subject": "Conferma richiesta contatto professionista",
    # Contenuto minimo non negoziabile: capienza IRPEF, 10 rate, bonifico
    # parlante + ENEA, "non e' consulenza fiscale". Modificabile da admin (il
    # seed non lo sovrascrive piu' — vedi seed_testi), ma non rimovibile dalla
    # UI: viaggia dentro `BonusOut`.
    "disclaimer_bonus": (
        "Gli importi delle detrazioni sono una stima commerciale, non consulenza fiscale: verificali sempre con il tuo commercialista prima di impegnarti in una spesa. La detrazione si recupera in 10 quote annuali di pari importo e solo entro la capienza IRPEF: se l'imposta lorda dell'anno e' inferiore alla rata, la parte eccedente si perde e non e' recuperabile negli anni successivi. Per averne diritto servono il pagamento con bonifico parlante e gli adempimenti previsti (per l'ecobonus, la comunicazione ENEA entro 90 giorni dalla fine dei lavori). Gli importi qui indicati derivano da una stima pre-sopralluogo e sono espressi a range."
    ),
}


def _dec(value: int | float | str) -> Decimal:
    return Decimal(str(value))


def load_seed_data(path: Path = SEED_JSON_PATH) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_dettaglio_pro_data(path: Path = SEED_DETTAGLIO_PRO_JSON_PATH) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _upsert_sottocategoria(session: Session, listino: Listino, sotto_data: dict) -> Sottocategoria:
    """Upsert idempotente per chiave naturale (listino_id, categoria_code,
    codice-o-nome — D-03/Pitfall 1: codice nullable per B/C/D)."""
    categoria_code = sotto_data["categoria_code"]
    codice = sotto_data.get("codice")
    nome = sotto_data["nome"]
    query = session.query(Sottocategoria).filter_by(listino_id=listino.id, categoria_code=categoria_code)
    query = query.filter_by(codice=codice) if codice is not None else query.filter_by(codice=None, nome=nome)
    sotto = query.one_or_none()
    if sotto is None:
        sotto = Sottocategoria(
            listino_id=listino.id,
            categoria_code=categoria_code,
            codice=codice,
            nome=nome,
            famiglia=sotto_data["famiglia"],
            ordine=sotto_data.get("ordine", 0),
        )
        session.add(sotto)
        session.flush()
    else:
        sotto.nome = nome
        sotto.famiglia = sotto_data["famiglia"]
        sotto.ordine = sotto_data.get("ordine", 0)
    return sotto


def _upsert_voce(session: Session, sotto: Sottocategoria, voce_data: dict) -> Voce:
    """Upsert per chiave naturale (sottocategoria_id, codice-o-descrizione).

    `livello` segue una regola DIVERSA dagli altri campi: si scrive solo se la
    chiave e' presente nel JSON di seed. Il motivo e' lo stesso di `seed_testi`
    (che il seed a ogni boot del container aveva gia' morso una volta): il
    livello delle voci e' curatela dell'admin dal pannello, non un dato che il
    seed possiede. Un `voce.livello = voce_data.get("livello")` incondizionato
    riporterebbe a NULL tutta la classificazione a ogni deploy — e con tutti i
    livelli a NULL il motore torna a sommare i cataloghi, cioe' il bug che
    questa feature esiste per chiudere."""
    codice = voce_data.get("codice")
    descrizione = voce_data["descrizione"]
    query = session.query(Voce).filter_by(sottocategoria_id=sotto.id)
    query = query.filter_by(codice=codice) if codice is not None else query.filter_by(codice=None, descrizione=descrizione)
    voce = query.one_or_none()
    if voce is None:
        voce = Voce(
            sottocategoria_id=sotto.id,
            codice=codice,
            descrizione=descrizione,
            um=voce_data["um"],
            prezzo_unitario_cliente=_dec(voce_data["prezzo_unitario_cliente"]),
            ordine=voce_data.get("ordine", 0),
            livello=voce_data.get("livello"),
        )
        session.add(voce)
        session.flush()
    else:
        voce.descrizione = descrizione
        voce.um = voce_data["um"]
        voce.prezzo_unitario_cliente = _dec(voce_data["prezzo_unitario_cliente"])
        voce.ordine = voce_data.get("ordine", 0)
        if "livello" in voce_data:
            voce.livello = voce_data["livello"]
    return voce


def _upsert_coefficiente_qta(session: Session, voce: Voce, tipo_code: str, coeff_data: dict) -> None:
    """Upsert per chiave naturale (voce_id, tipo_code)."""
    coeff = session.query(CoefficienteQuantitaVoce).filter_by(voce_id=voce.id, tipo_code=tipo_code).one_or_none()
    coefficiente_qta_per_mq = coeff_data.get("coefficiente_qta_per_mq")
    domanda_mirata_key = coeff_data.get("domanda_mirata_key")
    default_conteggio = coeff_data.get("default_conteggio")
    if coeff is None:
        coeff = CoefficienteQuantitaVoce(
            voce_id=voce.id,
            tipo_code=tipo_code,
            coefficiente_qta_per_mq=_dec(coefficiente_qta_per_mq) if coefficiente_qta_per_mq is not None else None,
            domanda_mirata_key=domanda_mirata_key,
            default_conteggio=default_conteggio,
        )
        session.add(coeff)
    else:
        coeff.coefficiente_qta_per_mq = _dec(coefficiente_qta_per_mq) if coefficiente_qta_per_mq is not None else None
        coeff.domanda_mirata_key = domanda_mirata_key
        coeff.default_conteggio = default_conteggio


def seed_dettaglio_pro(session: Session, listino: Listino, data: dict | None = None) -> None:
    """Idempotent upsert dei dati dettaglio Pro (sottocategoria/voce/
    coefficiente_qta_voce), stesso listino del seed Free (D-12: Free e Pro
    leggono lo STESSO listino per citta). Chiamata da `seed()` — NON un
    secondo script (D-12/Pitfall 5)."""
    data = data or load_dettaglio_pro_data()
    for sotto_data in data["sottocategorie"]:
        sotto = _upsert_sottocategoria(session, listino, sotto_data)
        session.flush()
        for voce_data in sotto_data["voci"]:
            voce = _upsert_voce(session, sotto, voce_data)
            session.flush()
            for tipo_code, coeff_data in voce_data.get("coefficienti", {}).items():
                _upsert_coefficiente_qta(session, voce, tipo_code, coeff_data)


def seed_bonus(session: Session) -> None:
    """Upsert idempotente di bonus, aliquote e mapping (categoria|extra)->bonus.
    Chiamata da `seed()` — mai un secondo script (D-12/Pitfall 5).

    Chiavi naturali: `bonus_fiscale.code` (PK), `aliquota_bonus`
    (bonus_code, destinazione, valido_dal), `bonus_categoria`
    (bonus_code, categoria_code), `bonus_extra` (bonus_code, extra_code).
    Nessun DELETE: una riga aggiunta a mano
    dall'admin non viene mai rimossa dal seed."""
    for dati in BONUS_FISCALI:
        row = session.get(BonusFiscale, dati["code"])
        if row is None:
            row = BonusFiscale(code=dati["code"])
            session.add(row)
        row.nome = dati["nome"]
        row.descrizione = dati["descrizione"]
        row.ordine = dati["ordine"]
        row.attivo = dati["attivo"]
    session.flush()

    for dati in ALIQUOTE_BONUS:
        row = (
            session.query(AliquotaBonus)
            .filter_by(
                bonus_code=dati["bonus_code"],
                destinazione=dati["destinazione"],
                valido_dal=dati["valido_dal"],
            )
            .one_or_none()
        )
        if row is None:
            row = AliquotaBonus(
                bonus_code=dati["bonus_code"],
                destinazione=dati["destinazione"],
                valido_dal=dati["valido_dal"],
            )
            session.add(row)
        row.aliquota_pct = _dec(dati["aliquota_pct"])
        row.tetto_spesa_eur = (
            _dec(dati["tetto_spesa_eur"]) if dati["tetto_spesa_eur"] is not None else None
        )
        row.tetto_modalita = dati["tetto_modalita"]
        row.rate_annuali = dati["rate_annuali"]
        row.valido_al = dati["valido_al"]
        row.note = dati["note"]
    session.flush()

    for dati in BONUS_CATEGORIE:
        row = (
            session.query(BonusCategoria)
            .filter_by(bonus_code=dati["bonus_code"], categoria_code=dati["categoria_code"])
            .one_or_none()
        )
        if row is None:
            row = BonusCategoria(
                bonus_code=dati["bonus_code"], categoria_code=dati["categoria_code"]
            )
            session.add(row)
        row.quota_ammissibile_pct = _dec(dati["quota"])

    for dati in BONUS_EXTRA:
        row = (
            session.query(BonusExtra)
            .filter_by(bonus_code=dati["bonus_code"], extra_code=dati["extra_code"])
            .one_or_none()
        )
        if row is None:
            row = BonusExtra(bonus_code=dati["bonus_code"], extra_code=dati["extra_code"])
            session.add(row)
        row.quota_ammissibile_pct = _dec(dati["quota"])


def seed_livelli_finitura(session: Session) -> None:
    """Upsert idempotente dei livelli di finitura (chiave naturale: `code`, che
    e' la PK). Chiamata da `seed()` — mai un secondo script (D-12/Pitfall 5).

    A differenza di `seed_testi`, qui l'upsert SOVRASCRIVE: nome, ordine e
    default dei tre livelli sono struttura del prodotto, non contenuto
    editoriale dell'admin. Cio' che l'admin cura e' l'assegnazione dei livelli
    alle VOCI (`voce.livello`), e quella il seed rispetta: vedi la regola
    condizionale in `_upsert_voce`."""
    for dati in LIVELLI_FINITURA:
        row = session.get(LivelloFinitura, dati["code"])
        if row is None:
            row = LivelloFinitura(code=dati["code"])
            session.add(row)
        row.nome = dati["nome"]
        row.ordine = dati["ordine"]
        row.descrizione = dati["descrizione"]
        row.is_default = dati["is_default"]


def seed_testi(session: Session) -> None:
    """Create-if-missing dei testi/disclaimer iniziali (D-14) nella tabella
    Testo, per chiave naturale (`chiave` e' gia' la PK). Chiamata da `seed()`
    — STESSA funzione idempotente, non un secondo script (D-12/Pitfall 5).

    ATTENZIONE: qui NON si aggiorna il valore di una riga esistente. `seed()`
    gira a ogni boot del container (Dockerfile CMD), quindi un upsert che
    riscrive `valore` riporterebbe ogni testo modificato dal pannello admin
    al default cablato a ogni deploy. I testi sono contenuto editoriale
    dell'admin: il seed li crea, non li possiede."""
    import datetime as _dt

    for chiave, valore in TESTI_INIZIALI.items():
        row = session.get(Testo, chiave)
        if row is None:
            row = Testo(chiave=chiave, valore=valore, updated_at=_dt.datetime.now(_dt.timezone.utc))
            session.add(row)
        # else: riga gia' presente -> non si tocca (vedi docstring).


def seed(session: Session, data: dict | None = None) -> Listino:
    """Idempotent upsert of the full RE dataset. Safe to call repeatedly."""
    data = data or load_seed_data()

    # 1. listino (RE, is_default=True)
    listino = session.query(Listino).filter_by(nome="Reggio Emilia").one_or_none()
    if listino is None:
        listino = Listino(
            nome="Reggio Emilia",
            citta_riferimento="Reggio Emilia",
            valuta=data.get("valuta", "EUR"),
        )
        session.add(listino)
        session.flush()
    listino.is_default = True
    listino.attivo = True

    # 2. categoria (4)
    for code, iva in data["iva_categoria"].items():
        cat = session.query(Categoria).filter_by(code=code).one_or_none()
        if cat is None:
            cat = Categoria(code=code, nome=CATEGORIA_NOMI[code], ordine=CATEGORIA_ORDINE[code], iva_pct=_dec(iva))
            session.add(cat)
        else:
            cat.nome = CATEGORIA_NOMI[code]
            cat.ordine = CATEGORIA_ORDINE[code]
            cat.iva_pct = _dec(iva)
        cat.livello_selezionabile = CATEGORIA_LIVELLO_SELEZIONABILE.get(code, False)
    session.flush()

    # 3. listino_categoria (4): base_eur_mq (prezzo cliente) + coefficiente_impresa (segreto)
    for code, base in data["base_eur_mq"].items():
        lc = session.query(ListinoCategoria).filter_by(listino_id=listino.id, categoria_code=code).one_or_none()
        if lc is None:
            lc = ListinoCategoria(
                listino_id=listino.id,
                categoria_code=code,
                base_eur_mq=_dec(base),
                coefficiente_impresa=COEFFICIENTE_IMPRESA[code],
            )
            session.add(lc)
        else:
            lc.base_eur_mq = _dec(base)
            lc.coefficiente_impresa = COEFFICIENTE_IMPRESA[code]

    # 4. tipo_ristrutturazione (3)
    for code, range_pct in data["range_pct_tipo"].items():
        tipo = session.query(TipoRistrutturazione).filter_by(code=code).one_or_none()
        if tipo is None:
            tipo = TipoRistrutturazione(
                code=code, nome=TIPO_NOMI[code], ordine=TIPO_ORDINE[code], range_pct=_dec(range_pct)
            )
            session.add(tipo)
        else:
            tipo.nome = TIPO_NOMI[code]
            tipo.ordine = TIPO_ORDINE[code]
            tipo.range_pct = _dec(range_pct)
    session.flush()

    # 5. moltiplicatore (12 = 3 tipi x 4 categorie)
    for tipo_code, categorie in data["moltiplicatori_tipo"].items():
        for categoria_code, valore in categorie.items():
            m = (
                session.query(Moltiplicatore)
                .filter_by(tipo_code=tipo_code, categoria_code=categoria_code)
                .one_or_none()
            )
            if m is None:
                m = Moltiplicatore(tipo_code=tipo_code, categoria_code=categoria_code, valore=_dec(valore))
                session.add(m)
            else:
                m.valore = _dec(valore)

    # 6. extra (2: CSE_CSP, pratiche)
    for code, importo in data["extra"].items():
        extra = session.query(Extra).filter_by(code=code).one_or_none()
        if extra is None:
            extra = Extra(code=code, nome=EXTRA_NOMI.get(code, code), importo=_dec(importo), iva_pct=EXTRA_IVA_PCT)
            session.add(extra)
        else:
            extra.nome = EXTRA_NOMI.get(code, code)
            extra.importo = _dec(importo)
            extra.iva_pct = EXTRA_IVA_PCT

    # 7. comune_listino: RE aliases -> RE listino (Pitfall 6)
    for alias in RE_ALIASES:
        slug = slugify(alias)
        comune = session.query(ComuneListino).filter_by(comune_slug=slug).one_or_none()
        if comune is None:
            comune = ComuneListino(comune_nome=alias, comune_slug=slug, listino_id=listino.id)
            session.add(comune)
        else:
            comune.comune_nome = alias
            comune.listino_id = listino.id

    session.flush()

    # 8. dettaglio Pro (sottocategoria/voce/coefficiente_qta_voce) — stesso
    # listino RE, stessa funzione seed() idempotente (D-03/D-12/Pitfall 5).
    seed_dettaglio_pro(session, listino)

    # 9. livelli di finitura (0010) — stessa funzione seed() idempotente.
    seed_livelli_finitura(session)

    # 10. bonus fiscali (0011) — stessa funzione seed() idempotente.
    seed_bonus(session)

    # 11. testi/disclaimer (D-14) — stessa funzione seed() idempotente.
    seed_testi(session)

    session.commit()
    return listino


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        listino = seed(session)
        print(f"Seed completato: listino '{listino.nome}' (is_default={listino.is_default}).")


if __name__ == "__main__":
    main()
