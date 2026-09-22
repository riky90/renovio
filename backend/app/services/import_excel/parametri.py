"""Handler di import della risorsa `parametri` (piano 08-06, CUR-01/CUR-02).

Re-importa i cinque fogli scritti da `export_excel/parametri.py`:
`moltiplicatori`, `listino_categoria`, `extra`, `coefficienti_pro`,
`forfait_arredo`. Regole non negoziabili, applicate identiche sui cinque
fogli:

- risoluzione per `id` PRIMA della chiave naturale (D-03); un `id`
  inesistente e' uno scarto descritto, mai un insert con id diverso;
- riga senza `id` = record nuovo (D-04), tranne per `moltiplicatori`
  (tipo x categoria) e `listino_categoria` (listino x categoria): sono
  coppie vincolate, si risolvono per chiave naturale composta e si creano
  solo se entrambi i codici padre esistono, altrimenti scarto;
- campo assente dal foglio = campo non toccato (CUR-02); `#CANCELLA#' e'
  ammesso SOLO sulle colonne nullable di `coefficienti_pro`
  (`coefficiente_qta_per_mq`, `domanda_mirata_key`, `default_conteggio`) —
  su ogni altra colonna produce uno scarto descritto, mai un tentativo di
  scrivere NULL su una colonna NOT NULL;
- NESSUNA eliminazione, su nessuno dei cinque fogli (D-10);
- `iva_pct` del foglio `listino_categoria` scrive su `Categoria.iva_pct`
  (colonna condivisa da tutti i listini), non su `ListinoCategoria` che
  non ha quella colonna;
- bound numerici coerenti con le PATCH admin esistenti
  (`routers/admin/coefficienti.py`, `routers/admin/listini.py`): un valore
  fuori bound e' uno scarto, non un update.

IL PUNTO CHE CONTA DI PIU' (CLAUDE.md regola di dominio #1 + CUR-02 +
D-13): `coefficiente_impresa` si scrive SOLO se presente nel file caricato
E solo se `is_admin` e' True — vedi `_forse_aggiungi_margine`/
`_forse_aggiorna_margine`, i SOLI due punti del file in cui questo nome di
colonna compare in scrittura. Il file di default (senza quella colonna)
per la regola della cella assente significa "non toccare": ricaricare
l'export normale non azzera mai il margine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from openpyxl.workbook import Workbook
from sqlalchemy.orm import Session

from app.models.arredo import ForfaitArredo
from app.models.catalogo import Categoria, Extra, LivelloFinitura, Moltiplicatore, TipoRistrutturazione
from app.models.dettaglio_pro import CoefficienteQuantitaVoce, Voce
from app.models.domanda import OpzioneDomanda
from app.models.listino import Listino, ListinoCategoria
from app.schemas.admin_import import DiffRigaOut, RigaPiattaIn
from app.schemas.admin_upload import ScartoRowOut
from app.services.import_excel.flat import foglio_mancante, leggi_foglio_piatto
from app.services.import_excel.registry import registra

RISORSA = "parametri"

FOGLIO_MOLTIPLICATORI = "moltiplicatori"
FOGLIO_LISTINO_CATEGORIA = "listino_categoria"
FOGLIO_EXTRA = "extra"
FOGLIO_COEFF_PRO = "coefficienti_pro"
FOGLIO_FORFAIT = "forfait_arredo"

# Colonne ammesse in lettura per foglio. Le colonne di contesto in sola
# lettura (listino_nome/voce_descrizione/opzione_etichetta) sono
# deliberatamente ESCLUSE: `leggi_foglio_piatto` le ignora silenziosamente,
# stesso effetto di "colonna nota ma non importabile" senza codice speciale.
COLONNE_MOLTIPLICATORI = {"id", "tipo_code", "categoria_code", "valore"}
COLONNE_LISTINO_CATEGORIA = {"id", "listino_id", "categoria_code", "base_eur_mq", "iva_pct", "coefficiente_impresa"}
COLONNE_EXTRA = {"id", "nome", "importo", "iva_pct", "tipo_calcolo", "attivo"}
COLONNE_COEFF_PRO = {"id", "voce_id", "tipo_code", "coefficiente_qta_per_mq", "domanda_mirata_key", "default_conteggio"}
COLONNE_FORFAIT = {"id", "opzione_id", "livello_code", "eur_min", "eur_max", "attivo"}

# Uniche colonne nullable a database fra quelle importabili: le sole su cui
# #CANCELLA# ha effetto (D-09). Su ogni altra colonna il token e' uno
# scarto descritto — vedi `_campi_non_annullabili`.
_CAMPI_NULLABLE_PER_FOGLIO: dict[str, set[str]] = {
    FOGLIO_MOLTIPLICATORI: set(),
    FOGLIO_LISTINO_CATEGORIA: set(),
    FOGLIO_EXTRA: set(),
    FOGLIO_COEFF_PRO: {"coefficiente_qta_per_mq", "domanda_mirata_key", "default_conteggio"},
    FOGLIO_FORFAIT: set(),
}

_MODEL = {
    FOGLIO_MOLTIPLICATORI: Moltiplicatore,
    FOGLIO_LISTINO_CATEGORIA: ListinoCategoria,
    FOGLIO_EXTRA: Extra,
    FOGLIO_COEFF_PRO: CoefficienteQuantitaVoce,
    FOGLIO_FORFAIT: ForfaitArredo,
}

# Nome della colonna margine. Definito qui una sola volta e riusato SOLO in
# due posti: la lettura di anteprima sotto (`_risolvi_listino_categoria`,
# che NON scrive mai a database — il diff e' sempre di sola lettura) e le
# due funzioni `_forse_aggiungi_margine`/`_forse_aggiorna_margine` piu' in
# basso, i SOLI punti del file in cui questa colonna viene effettivamente
# scritta, entrambi dietro `is_admin` (regola di dominio #1 CLAUDE.md).
CAMPO_MARGINE = "coefficiente_impresa"


@dataclass
class _Risoluzione:
    """Esito della risoluzione di una riga contro il database. `scarto`
    None e' successo. `esistente` None + `valori_creazione` popolato =
    record nuovo; `esistente` non-None = record da aggiornare con
    `campi_aggiornati` (solo i campi presenti e validi, D-09/CUR-02).
    `campi_extra` porta scritture collaterali (iva_pct -> Categoria)."""

    scarto: ScartoRowOut | None = None
    esistente: object | None = None
    valori_creazione: dict[str, object] | None = None
    campi_aggiornati: dict[str, object] = field(default_factory=dict)
    campi_extra: dict[str, object] = field(default_factory=dict)
    chiave_descr: str = ""
    # Valore del margine letto dal file, SOLO per l'anteprima del diff (mai
    # scritto da qui: il diff e' sempre di sola lettura). None se la
    # colonna e' assente dal file o il valore e' fuori bound.
    margine_preview: object | None = None


def _decimal(valore: object) -> Decimal | None:
    try:
        return Decimal(str(valore))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _campi_non_annullabili(r: RigaPiattaIn) -> list[str]:
    nullable = _CAMPI_NULLABLE_PER_FOGLIO.get(r.foglio, set())
    return sorted(c for c in r.campi_da_cancellare if c not in nullable)


# --- moltiplicatori ---------------------------------------------------------


def _risolvi_moltiplicatore(db: Session, r: RigaPiattaIn) -> _Risoluzione:
    validati: dict[str, object] = {}
    if "valore" in r.valori:
        valore = _decimal(r.valori["valore"])
        if valore is None:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"moltiplicatori: valore non numerico ({r.valori['valore']!r})"))
        if valore <= 0:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="moltiplicatori: valore deve essere maggiore di zero"))
        validati["valore"] = valore

    if r.id is not None:
        riga_db = db.get(Moltiplicatore, int(r.id))
        if riga_db is None:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"moltiplicatori: id {r.id} non trovato"))
        return _Risoluzione(
            esistente=riga_db, campi_aggiornati=validati,
            chiave_descr=f"{riga_db.tipo_code} x {riga_db.categoria_code}",
        )

    tipo_code = r.valori.get("tipo_code")
    categoria_code = r.valori.get("categoria_code")
    if not tipo_code or not categoria_code:
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="moltiplicatori: riga senza id richiede tipo_code e categoria_code"))
    if db.get(TipoRistrutturazione, tipo_code) is None or db.get(Categoria, categoria_code) is None:
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"moltiplicatori: tipo_code o categoria_code inesistente ({tipo_code}/{categoria_code})"))

    riga_db = db.query(Moltiplicatore).filter_by(tipo_code=tipo_code, categoria_code=categoria_code).one_or_none()
    chiave_descr = f"{tipo_code} x {categoria_code}"
    if riga_db is not None:
        return _Risoluzione(esistente=riga_db, campi_aggiornati=validati, chiave_descr=chiave_descr)
    if "valore" not in validati:
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="moltiplicatori: riga nuova senza 'valore'"))
    return _Risoluzione(
        valori_creazione={"tipo_code": tipo_code, "categoria_code": categoria_code, **validati},
        chiave_descr=chiave_descr,
    )


# --- listino_categoria -------------------------------------------------------


def _risolvi_listino_categoria(db: Session, r: RigaPiattaIn) -> _Risoluzione:
    validati: dict[str, object] = {}
    campi_extra: dict[str, object] = {}

    # Lettura di SOLA anteprima (mai una scrittura): il diff deve poter
    # mostrare all'admin che il margine cambierebbe, la decisione di
    # scriverlo davvero resta in apply(), dietro is_admin.
    margine_preview: Decimal | None = None
    if CAMPO_MARGINE in r.valori:
        v = _decimal(r.valori[CAMPO_MARGINE])
        if v is not None and 0 < v <= 1:
            margine_preview = v

    if "base_eur_mq" in r.valori:
        v = _decimal(r.valori["base_eur_mq"])
        if v is None:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="listino_categoria: base_eur_mq non numerico"))
        if v <= 0:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="listino_categoria: base_eur_mq deve essere maggiore di zero"))
        validati["base_eur_mq"] = v

    if "iva_pct" in r.valori:
        v = _decimal(r.valori["iva_pct"])
        if v is None:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="listino_categoria: iva_pct non numerico"))
        if v < 0 or v >= 1:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="listino_categoria: iva_pct fuori bound [0,1)"))
        campi_extra["iva_pct"] = v  # su Categoria, non su ListinoCategoria — vedi docstring di modulo

    if r.id is not None:
        riga_db = db.get(ListinoCategoria, int(r.id))
        if riga_db is None:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"listino_categoria: id {r.id} non trovato"))
        return _Risoluzione(
            esistente=riga_db, campi_aggiornati=validati, campi_extra=campi_extra,
            chiave_descr=f"listino={riga_db.listino_id} categoria={riga_db.categoria_code}",
            margine_preview=margine_preview,
        )

    listino_id_raw = r.valori.get("listino_id")
    categoria_code = r.valori.get("categoria_code")
    if not listino_id_raw or not categoria_code:
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="listino_categoria: riga senza id richiede listino_id e categoria_code"))
    listino_id = int(listino_id_raw) if str(listino_id_raw).strip().lstrip("-").isdigit() else None
    if listino_id is None:
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="listino_categoria: listino_id non numerico"))
    if db.get(Listino, listino_id) is None or db.get(Categoria, categoria_code) is None:
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"listino_categoria: listino_id o categoria_code inesistente ({listino_id}/{categoria_code})"))

    riga_db = db.query(ListinoCategoria).filter_by(listino_id=listino_id, categoria_code=categoria_code).one_or_none()
    chiave_descr = f"listino={listino_id} categoria={categoria_code}"
    if riga_db is not None:
        return _Risoluzione(
            esistente=riga_db, campi_aggiornati=validati, campi_extra=campi_extra,
            chiave_descr=chiave_descr, margine_preview=margine_preview,
        )
    if "base_eur_mq" not in validati:
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="listino_categoria: riga nuova senza base_eur_mq"))
    return _Risoluzione(
        valori_creazione={"listino_id": listino_id, "categoria_code": categoria_code, **validati},
        campi_extra=campi_extra,
        chiave_descr=chiave_descr,
        margine_preview=margine_preview,
    )


# --- extra -------------------------------------------------------------------


def _risolvi_extra(db: Session, r: RigaPiattaIn) -> _Risoluzione:
    """`id` == `Extra.code` (PK testuale): a differenza degli altri fogli
    non esiste una chiave naturale alternativa, quindi una riga senza `id`
    non e' un record nuovo (D-04) ma un vero scarto — non c'e' nessun modo
    di sapere quale codice assegnare a un extra mai visto."""
    validati: dict[str, object] = {}

    if "importo" in r.valori:
        v = _decimal(r.valori["importo"])
        if v is None:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="extra: importo non numerico"))
        if v < 0:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="extra: importo deve essere maggiore o uguale a zero"))
        validati["importo"] = v

    if "iva_pct" in r.valori:
        v = _decimal(r.valori["iva_pct"])
        if v is None:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="extra: iva_pct non numerico"))
        if v < 0 or v >= 1:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="extra: iva_pct fuori bound [0,1)"))
        validati["iva_pct"] = v

    if "nome" in r.valori:
        nome = str(r.valori["nome"]).strip()
        if not nome:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="extra: nome vuoto"))
        validati["nome"] = nome

    if "tipo_calcolo" in r.valori:
        tipo_calcolo = str(r.valori["tipo_calcolo"]).strip()
        if not tipo_calcolo:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="extra: tipo_calcolo vuoto"))
        validati["tipo_calcolo"] = tipo_calcolo

    if "attivo" in r.valori:
        validati["attivo"] = bool(r.valori["attivo"])

    if r.id is None:
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="extra: riga senza id — il codice e' sempre richiesto, non ha una chiave naturale alternativa"))

    code = r.id
    riga_db = db.get(Extra, code)
    if riga_db is not None:
        return _Risoluzione(esistente=riga_db, campi_aggiornati=validati, chiave_descr=f"extra {code}")

    mancanti = {"nome", "importo", "iva_pct"} - validati.keys()
    if mancanti:
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"extra: riga nuova (codice {code}) senza i campi richiesti: {', '.join(sorted(mancanti))}"))
    return _Risoluzione(
        valori_creazione={"code": code, "tipo_calcolo": "fisso", "attivo": True, **validati},
        chiave_descr=f"extra {code}",
    )


# --- coefficienti_pro ---------------------------------------------------------


def _risolvi_coeff_pro(db: Session, r: RigaPiattaIn) -> _Risoluzione:
    validati: dict[str, object] = {}

    if "coefficiente_qta_per_mq" in r.valori:
        v = _decimal(r.valori["coefficiente_qta_per_mq"])
        if v is None:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="coefficienti_pro: coefficiente_qta_per_mq non numerico"))
        if v < 0:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="coefficienti_pro: coefficiente_qta_per_mq deve essere maggiore o uguale a zero"))
        validati["coefficiente_qta_per_mq"] = v

    if "domanda_mirata_key" in r.valori:
        chiave = str(r.valori["domanda_mirata_key"]).strip()
        if not chiave:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="coefficienti_pro: domanda_mirata_key vuota"))
        validati["domanda_mirata_key"] = chiave

    if "default_conteggio" in r.valori:
        try:
            conteggio = int(r.valori["default_conteggio"])
        except (TypeError, ValueError):
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="coefficienti_pro: default_conteggio non intero"))
        if conteggio < 0:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="coefficienti_pro: default_conteggio deve essere maggiore o uguale a zero"))
        validati["default_conteggio"] = conteggio

    # #CANCELLA# sulle tre colonne nullable: gia' filtrato a monte da
    # `_campi_non_annullabili` per ogni altra colonna del foglio.
    for campo in ("coefficiente_qta_per_mq", "domanda_mirata_key", "default_conteggio"):
        if campo in r.campi_da_cancellare:
            validati[campo] = None

    if r.id is not None:
        riga_db = db.get(CoefficienteQuantitaVoce, int(r.id))
        if riga_db is None:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"coefficienti_pro: id {r.id} non trovato"))
        return _Risoluzione(
            esistente=riga_db, campi_aggiornati=validati,
            chiave_descr=f"voce={riga_db.voce_id} tipo={riga_db.tipo_code}",
        )

    voce_id_raw = r.valori.get("voce_id")
    tipo_code = r.valori.get("tipo_code")
    if not voce_id_raw or not tipo_code:
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="coefficienti_pro: riga senza id richiede voce_id e tipo_code"))
    voce_id = int(voce_id_raw) if str(voce_id_raw).strip().lstrip("-").isdigit() else None
    if voce_id is None:
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="coefficienti_pro: voce_id non numerico"))
    if db.get(Voce, voce_id) is None or db.get(TipoRistrutturazione, tipo_code) is None:
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"coefficienti_pro: voce_id o tipo_code inesistente ({voce_id}/{tipo_code})"))

    riga_db = db.query(CoefficienteQuantitaVoce).filter_by(voce_id=voce_id, tipo_code=tipo_code).one_or_none()
    chiave_descr = f"voce={voce_id} tipo={tipo_code}"
    if riga_db is not None:
        return _Risoluzione(esistente=riga_db, campi_aggiornati=validati, chiave_descr=chiave_descr)
    return _Risoluzione(
        valori_creazione={"voce_id": voce_id, "tipo_code": tipo_code, **validati},
        chiave_descr=chiave_descr,
    )


# --- forfait_arredo -----------------------------------------------------------


def _risolvi_forfait(db: Session, r: RigaPiattaIn) -> _Risoluzione:
    validati: dict[str, object] = {}

    if "eur_min" in r.valori:
        v = _decimal(r.valori["eur_min"])
        if v is None:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="forfait_arredo: eur_min non numerico"))
        if v < 0:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="forfait_arredo: eur_min deve essere maggiore o uguale a zero"))
        validati["eur_min"] = v

    if "eur_max" in r.valori:
        v = _decimal(r.valori["eur_max"])
        if v is None:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="forfait_arredo: eur_max non numerico"))
        if v < 0:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="forfait_arredo: eur_max deve essere maggiore o uguale a zero"))
        validati["eur_max"] = v

    if "attivo" in r.valori:
        validati["attivo"] = bool(r.valori["attivo"])

    if r.id is not None:
        riga_db = db.get(ForfaitArredo, int(r.id))
        if riga_db is None:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"forfait_arredo: id {r.id} non trovato"))
        eur_min_finale = validati.get("eur_min", riga_db.eur_min)
        eur_max_finale = validati.get("eur_max", riga_db.eur_max)
        if eur_min_finale > eur_max_finale:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="forfait_arredo: eur_min non puo' superare eur_max"))
        return _Risoluzione(
            esistente=riga_db, campi_aggiornati=validati,
            chiave_descr=f"opzione={riga_db.opzione_id} livello={riga_db.livello_code}",
        )

    opzione_id_raw = r.valori.get("opzione_id")
    livello_code = r.valori.get("livello_code")
    if not opzione_id_raw or not livello_code:
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="forfait_arredo: riga senza id richiede opzione_id e livello_code"))
    opzione_id = int(opzione_id_raw) if str(opzione_id_raw).strip().lstrip("-").isdigit() else None
    if opzione_id is None:
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="forfait_arredo: opzione_id non numerico"))
    if db.get(OpzioneDomanda, opzione_id) is None or db.get(LivelloFinitura, livello_code) is None:
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"forfait_arredo: opzione_id o livello_code inesistente ({opzione_id}/{livello_code})"))

    riga_db = db.query(ForfaitArredo).filter_by(opzione_id=opzione_id, livello_code=livello_code).one_or_none()
    chiave_descr = f"opzione={opzione_id} livello={livello_code}"
    if riga_db is not None:
        return _Risoluzione(esistente=riga_db, campi_aggiornati=validati, chiave_descr=chiave_descr)
    mancanti = {"eur_min", "eur_max"} - validati.keys()
    if mancanti:
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"forfait_arredo: riga nuova senza i campi richiesti: {', '.join(sorted(mancanti))}"))
    if validati["eur_min"] > validati["eur_max"]:
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="forfait_arredo: eur_min non puo' superare eur_max"))
    return _Risoluzione(
        valori_creazione={"opzione_id": opzione_id, "livello_code": livello_code, "attivo": True, **validati},
        chiave_descr=chiave_descr,
    )


_RESOLVER = {
    FOGLIO_MOLTIPLICATORI: _risolvi_moltiplicatore,
    FOGLIO_LISTINO_CATEGORIA: _risolvi_listino_categoria,
    FOGLIO_EXTRA: _risolvi_extra,
    FOGLIO_COEFF_PRO: _risolvi_coeff_pro,
    FOGLIO_FORFAIT: _risolvi_forfait,
}


# --- parse -------------------------------------------------------------------


def _to_riga_in(rp, foglio: str) -> RigaPiattaIn:
    valori: dict[str, object] = {}
    cancella: list[str] = []
    for campo, valore in rp.valori.items():
        if valore is None:
            cancella.append(campo)
        else:
            valori[campo] = valore
    return RigaPiattaIn(
        foglio=foglio,
        id=str(rp.id) if rp.id is not None else None,
        valori=valori,
        campi_da_cancellare=cancella,
    )


def parse(wb: Workbook) -> tuple[list[RigaPiattaIn], list[ScartoRowOut]]:
    righe: list[RigaPiattaIn] = []
    scarti: list[ScartoRowOut] = []

    fogli = (
        (FOGLIO_MOLTIPLICATORI, COLONNE_MOLTIPLICATORI, True),
        (FOGLIO_LISTINO_CATEGORIA, COLONNE_LISTINO_CATEGORIA, True),
        (FOGLIO_EXTRA, COLONNE_EXTRA, False),
        (FOGLIO_COEFF_PRO, COLONNE_COEFF_PRO, True),
        (FOGLIO_FORFAIT, COLONNE_FORFAIT, True),
    )
    for foglio, colonne, id_numerico in fogli:
        mancante = foglio_mancante(wb, foglio)
        if mancante is not None:
            scarti.append(mancante)
            continue
        righe_piatte, scarti_foglio = leggi_foglio_piatto(
            wb, foglio, colonne_ammesse=colonne, id_numerico=id_numerico
        )
        scarti.extend(scarti_foglio)
        righe.extend(_to_riga_in(rp, foglio) for rp in righe_piatte)

    return righe, scarti


# --- diff ----------------------------------------------------------------------


def _campi_modificati_da(esistente: object, validati: dict[str, object]) -> dict[str, tuple[object, object]]:
    cambiati: dict[str, tuple[object, object]] = {}
    for campo, nuovo in validati.items():
        precedente = getattr(esistente, campo)
        if precedente != nuovo:
            cambiati[campo] = (precedente, nuovo)
    return cambiati


def diff(
    db: Session, righe: list[RigaPiattaIn]
) -> tuple[list[DiffRigaOut], list[DiffRigaOut], list[ScartoRowOut]]:
    nuove: list[DiffRigaOut] = []
    modificate: list[DiffRigaOut] = []
    scarti: list[ScartoRowOut] = []

    for r in righe:
        non_annullabili = _campi_non_annullabili(r)
        if non_annullabili:
            scarti.append(
                ScartoRowOut(
                    riga=0,
                    motivo=f"{r.foglio}: campo non annullabile con #CANCELLA#: {', '.join(non_annullabili)}",
                )
            )
            continue

        resolver = _RESOLVER.get(r.foglio)
        if resolver is None:
            scarti.append(ScartoRowOut(riga=0, motivo=f"foglio non riconosciuto: {r.foglio}"))
            continue

        ris = resolver(db, r)
        if ris.scarto is not None:
            scarti.append(ris.scarto)
            continue

        if ris.esistente is None:
            # Valori NATIVI (non stringificati): il client re-invia questo
            # stesso dict come `RigaPiattaIn.valori` in /confirm (round-trip
            # stateless) — un bool stringificato a mano ("False") tornerebbe
            # truthy in Python (bool("False") == True). Pydantic serializza
            # comunque i Decimal come stringa in JSON, stesso pattern del
            # resto del progetto (Decimal-as-string al confine API).
            valori_nuovi = dict(ris.valori_creazione or {})
            campi_modificati = list((ris.valori_creazione or {}).keys())
            for campo, valore in ris.campi_extra.items():
                valori_nuovi[campo] = valore
                campi_modificati.append(campo)
            if ris.margine_preview is not None:
                valori_nuovi[CAMPO_MARGINE] = ris.margine_preview
                campi_modificati.append(CAMPO_MARGINE)
            nuove.append(
                DiffRigaOut(
                    foglio=r.foglio, id=r.id, chiave_descr=ris.chiave_descr, nuova=True,
                    campi_modificati=campi_modificati, valori_precedenti={}, valori_nuovi=valori_nuovi,
                )
            )
            continue

        cambiati = _campi_modificati_da(ris.esistente, ris.campi_aggiornati)
        if ris.campi_extra:
            categoria_code = getattr(ris.esistente, "categoria_code", None)
            categoria = db.get(Categoria, categoria_code) if categoria_code else None
            if categoria is not None:
                for campo, nuovo in ris.campi_extra.items():
                    precedente = getattr(categoria, campo)
                    if precedente != nuovo:
                        cambiati[campo] = (precedente, nuovo)
        if ris.margine_preview is not None:
            # Sola anteprima (D-06 apply(), non qui, decide se scrivere davvero).
            precedente = getattr(ris.esistente, CAMPO_MARGINE)
            if precedente != ris.margine_preview:
                cambiati[CAMPO_MARGINE] = (precedente, ris.margine_preview)

        if not cambiati:
            continue  # nessun campo presente e' cambiato: riga non riportata (D-09)

        modificate.append(
            DiffRigaOut(
                foglio=r.foglio, id=r.id, chiave_descr=ris.chiave_descr, nuova=False,
                campi_modificati=list(cambiati.keys()),
                # Valori nativi, stesso motivo del ramo "nuova" sopra.
                valori_precedenti={k: v[0] for k, v in cambiati.items()},
                valori_nuovi={k: v[1] for k, v in cambiati.items()},
            )
        )

    return nuove, modificate, scarti


# --- apply ---------------------------------------------------------------------

# Le SOLE due funzioni del file che SCRIVONO `coefficiente_impresa` — vedi
# `CAMPO_MARGINE` e la docstring di modulo. Il resolver sopra lo LEGGE
# per l'anteprima del diff (mai una scrittura, D-06/CUR-02); qui, e solo
# qui, il valore raggiunge davvero il database, e solo dietro `is_admin`.


def _forse_aggiungi_margine(r: RigaPiattaIn, valori_creazione: dict[str, object], *, is_admin: bool) -> None:
    if not is_admin or CAMPO_MARGINE not in r.valori:
        return
    margine = _decimal(r.valori[CAMPO_MARGINE])
    if margine is not None and 0 < margine <= 1:
        valori_creazione[CAMPO_MARGINE] = margine


def _forse_aggiorna_margine(riga_db: ListinoCategoria, r: RigaPiattaIn, *, is_admin: bool) -> None:
    if not is_admin or CAMPO_MARGINE not in r.valori:
        return
    margine = _decimal(r.valori[CAMPO_MARGINE])
    if margine is not None and 0 < margine <= 1:
        setattr(riga_db, CAMPO_MARGINE, margine)


def apply(
    db: Session,
    nuove: list[RigaPiattaIn],
    modificate: list[RigaPiattaIn],
    *,
    is_admin: bool,
) -> int:
    applicate = 0

    for r in [*nuove, *modificate]:
        if _campi_non_annullabili(r):
            continue

        resolver = _RESOLVER.get(r.foglio)
        if resolver is None:
            continue

        # Ririsolve sempre (round-trip stateless): non si fida del diff
        # calcolato in precedenza, stesso principio di difesa in profondita'
        # di `listino_upload_service._resolve_per_id`.
        ris = resolver(db, r)
        if ris.scarto is not None:
            continue

        if ris.campi_extra:
            categoria_code = (
                ris.esistente.categoria_code if ris.esistente is not None
                else (ris.valori_creazione or {}).get("categoria_code")
            )
            categoria = db.get(Categoria, categoria_code) if categoria_code else None
            if categoria is not None:
                for campo, valore in ris.campi_extra.items():
                    setattr(categoria, campo, valore)

        if ris.esistente is None:
            valori_creazione = dict(ris.valori_creazione or {})
            if r.foglio == FOGLIO_LISTINO_CATEGORIA:
                _forse_aggiungi_margine(r, valori_creazione, is_admin=is_admin)
                if CAMPO_MARGINE not in valori_creazione:
                    # colonna NOT NULL: senza margine non si puo' creare una
                    # riga nuova (limite noto, non esercitato dai test di
                    # questo piano — vedi SUMMARY).
                    continue
            db.add(_MODEL[r.foglio](**valori_creazione))
        else:
            for campo, valore in ris.campi_aggiornati.items():
                setattr(ris.esistente, campo, valore)
            if r.foglio == FOGLIO_LISTINO_CATEGORIA:
                _forse_aggiorna_margine(ris.esistente, r, is_admin=is_admin)

        applicate += 1

    return applicate


class _ParametriHandler:
    """Oggetto minimale che espone le tre funzioni del modulo come
    attributi — soddisfa `ImportHandler` per struttura (Protocol), senza
    bisogno di una classe con logica propria."""

    parse = staticmethod(parse)
    diff = staticmethod(diff)
    apply = staticmethod(apply)


registra(RISORSA, _ParametriHandler())
