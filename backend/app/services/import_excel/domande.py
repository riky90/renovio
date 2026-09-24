"""Handler di import della risorsa `domande` (piano 08.1-05, CUR-01/CUR-02).

Re-importa i cinque fogli scritti da `export_excel/domande.py`: `domande`,
`opzioni`, `effetti`, `attese`, `derivazioni`. Eredita le regole gia' valide
per `parametri`/`lead` (D-01, D-03, D-04, D-09, D-10, D-11, D-12) e ne
aggiunge una propria a questa fase: `attiva` si cambia dal file (D-30), ma
la guardia D-28 (`verifica_dipendenze_opzione`, dal piano 08.1-01) vale
identica anche qui — come scarto descritto, mai come eccezione che blocca
l'intero import.

Ordine di dipendenza in `apply()` (non l'ordine dei fogli nel file):
`domande` -> `opzioni` -> `effetti` -> `attese` -> `derivazioni`, con
`db.flush()` dopo ogni scrittura, cosi' una domanda o un'opzione create
nello stesso `apply()` sono gia' visibili alle righe successive che le
referenziano (`domanda_code`, `opzione_code`).

NESSUNA eliminazione, su nessuno dei cinque fogli (D-10): `apply()` non
tocca mai una riga per toglierla, e la transazione (commit/rollback) resta
al router generico (`routers/admin/import_excel.py`), invariato.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation

from openpyxl.workbook import Workbook
from sqlalchemy.orm import Session

from app.models.domanda import (
    AttesaImmobile,
    DerivazioneRisposta,
    Domanda,
    EffettoOpzione,
    OpzioneDomanda,
)
from app.schemas.admin_import import DiffRigaOut, RigaPiattaIn
from app.schemas.admin_upload import ScartoRowOut
from app.services.catalogo_domande import (
    assicura_opzione_valore,
    azzera_altri_default,
    valida_visibilita,
    verifica_dipendenze_opzione,
)
from app.services.effetti import CONTROLLI, TIER_FREE, TIER_PRO, EffettoNonValido, valida_effetto
from app.services.import_excel.flat import foglio_mancante, leggi_foglio_piatto, valore_booleano
from app.services.import_excel.registry import (
    campi_nulli_in_valori,
    registra,
    riga_modificata_dopo_export,
)

RISORSA = "domande"

FOGLIO_DOMANDE = "domande"
FOGLIO_OPZIONI = "opzioni"
FOGLIO_EFFETTI = "effetti"
FOGLIO_ATTESE = "attese"
FOGLIO_DERIVAZIONI = "derivazioni"

# Colonne ammesse in lettura per foglio. Le colonne di contesto in sola
# lettura (domanda_testo, bersaglio, regola) sono deliberatamente ESCLUSE:
# `leggi_foglio_piatto` le ignora silenziosamente. `domanda_code` e
# `opzione_code` del foglio `effetti` sono INCLUSE (a differenza del loro
# ruolo puramente informativo nell'export): servono da riferimento al
# genitore per le righe nuove, che non hanno un `opzione_id`.
COLONNE_DOMANDE = {
    "id", "testo", "help", "tipo_controllo", "gruppo", "ordine", "tier_minimo",
    "attributo_code", "obbligatoria", "visibile_se_domanda_code",
    "visibile_se_opzione_code", "attiva",
}
COLONNE_OPZIONI = {
    "id", "domanda_code", "code", "etichetta", "descrizione", "immagine_url",
    "is_default", "ordine", "attiva",
}
COLONNE_EFFETTI = {
    "id", "opzione_id", "domanda_code", "opzione_code", "tipo_effetto",
    "target_categoria_code", "target_sottocategoria_id", "target_voce_id",
    "tipo_code", "valore", "attivo",
}
COLONNE_ATTESE = {"id", "attributo_code", "fascia_mq_min", "fascia_mq_max", "valore_atteso", "attiva"}
COLONNE_DERIVAZIONI = {
    "id", "domanda_code", "quando_opzione_code", "da_domanda_code",
    "da_opzione_code", "opzione_code", "attiva",
}

# Uniche colonne nullable a database fra quelle importabili: le sole su cui
# #CANCELLA# ha effetto (D-09). Su ogni altra colonna il token e' uno
# scarto descritto.
_CAMPI_NULLABLE_PER_FOGLIO: dict[str, set[str]] = {
    FOGLIO_DOMANDE: {"help", "attributo_code", "visibile_se_domanda_code", "visibile_se_opzione_code"},
    FOGLIO_OPZIONI: {"descrizione", "immagine_url"},
    FOGLIO_EFFETTI: {"tipo_code", "valore"},
    FOGLIO_ATTESE: set(),
    FOGLIO_DERIVAZIONI: set(),
}

_MODEL = {
    FOGLIO_DOMANDE: Domanda,
    FOGLIO_OPZIONI: OpzioneDomanda,
    FOGLIO_EFFETTI: EffettoOpzione,
    FOGLIO_ATTESE: AttesaImmobile,
    FOGLIO_DERIVAZIONI: DerivazioneRisposta,
}


@dataclass
class _Risoluzione:
    """Esito della risoluzione di una riga contro il database, stessa forma
    di `import_excel/parametri.py::_Risoluzione` (senza `campi_extra`: nessun
    foglio di questa risorsa scrive su una tabella diversa dalla propria)."""

    scarto: ScartoRowOut | None = None
    esistente: object | None = None
    valori_creazione: dict[str, object] | None = None
    campi_aggiornati: dict[str, object] = field(default_factory=dict)
    chiave_descr: str = ""


def _decimal(valore: object) -> Decimal | None:
    try:
        return Decimal(str(valore))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _intero(valore: object) -> int | None:
    """Come `import_excel/parametri.py::_intero`: mai un'eccezione, `None`
    e' 'non convertibile'. Copia locale deliberata (mai un import di nomi
    privati da `parametri.py`, per non accoppiare due risorse indipendenti)."""
    try:
        return int(str(valore).strip())
    except (TypeError, ValueError):
        return None


def _campi_non_annullabili(r: RigaPiattaIn) -> list[str]:
    nullable = _CAMPI_NULLABLE_PER_FOGLIO.get(r.foglio, set())
    return sorted(c for c in r.campi_da_cancellare if c not in nullable)


def _campi_modificati_da(esistente: object, validati: dict[str, object]) -> dict[str, tuple[object, object]]:
    cambiati: dict[str, tuple[object, object]] = {}
    for campo, nuovo in validati.items():
        precedente = getattr(esistente, campo)
        if precedente != nuovo:
            cambiati[campo] = (precedente, nuovo)
    return cambiati


# --- domande -----------------------------------------------------------------


def _risolvi_domanda(db: Session, r: RigaPiattaIn) -> _Risoluzione:
    """`id` = `Domanda.code`. Un `id` mai visto crea una domanda nuova con
    quel codice — anche un codice cambiato a mano nel file diventa cosi'
    una domanda nuova (mai una rinomina, che il PATCH non ammette): la
    vecchia resta intatta e la nuova compare come tale in anteprima."""
    if r.id is None or not str(r.id).strip():
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="domande: il codice e' sempre richiesto"))
    code = str(r.id).strip()

    validati: dict[str, object] = {}

    if "testo" in r.valori:
        testo = str(r.valori["testo"]).strip()
        if not (1 <= len(testo) <= 300):
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"domande {code}: testo fuori bound (1-300 caratteri)"))
        validati["testo"] = testo

    if "help" in r.valori:
        help_ = str(r.valori["help"]).strip()
        if len(help_) > 500:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"domande {code}: help troppo lungo (max 500 caratteri)"))
        validati["help"] = help_

    if "tipo_controllo" in r.valori:
        tipo_controllo = str(r.valori["tipo_controllo"]).strip()
        if tipo_controllo not in CONTROLLI:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"domande {code}: tipo_controllo sconosciuto ({tipo_controllo!r}). Ammessi: {', '.join(sorted(CONTROLLI))}"))
        validati["tipo_controllo"] = tipo_controllo

    if "gruppo" in r.valori:
        gruppo = str(r.valori["gruppo"]).strip()
        if len(gruppo) > 64:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"domande {code}: gruppo troppo lungo (max 64 caratteri)"))
        validati["gruppo"] = gruppo

    if "ordine" in r.valori:
        ordine = _intero(r.valori["ordine"])
        if ordine is None or not (0 <= ordine <= 10_000):
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"domande {code}: ordine non valido ({r.valori['ordine']!r}), atteso un intero fra 0 e 10000"))
        validati["ordine"] = ordine

    if "tier_minimo" in r.valori:
        tier_minimo = str(r.valori["tier_minimo"]).strip()
        if tier_minimo not in (TIER_FREE, TIER_PRO):
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"domande {code}: tier_minimo sconosciuto ({tier_minimo!r}). Ammessi: {TIER_FREE}, {TIER_PRO}"))
        validati["tier_minimo"] = tier_minimo

    if "attributo_code" in r.valori:
        attributo_code = str(r.valori["attributo_code"]).strip()
        if len(attributo_code) > 32:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"domande {code}: attributo_code troppo lungo (max 32 caratteri)"))
        validati["attributo_code"] = attributo_code

    if "obbligatoria" in r.valori:
        obbligatoria = valore_booleano(r.valori["obbligatoria"])
        if obbligatoria is None:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"domande {code}: obbligatoria non interpretabile come booleano ({r.valori['obbligatoria']!r})"))
        validati["obbligatoria"] = obbligatoria

    if "visibile_se_domanda_code" in r.valori:
        v = str(r.valori["visibile_se_domanda_code"]).strip()
        if len(v) > 64:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"domande {code}: visibile_se_domanda_code troppo lungo (max 64 caratteri)"))
        validati["visibile_se_domanda_code"] = v

    if "visibile_se_opzione_code" in r.valori:
        v = str(r.valori["visibile_se_opzione_code"]).strip()
        if len(v) > 64:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"domande {code}: visibile_se_opzione_code troppo lungo (max 64 caratteri)"))
        validati["visibile_se_opzione_code"] = v

    if "attiva" in r.valori:
        attiva = valore_booleano(r.valori["attiva"])
        if attiva is None:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"domande {code}: attiva non interpretabile come booleano ({r.valori['attiva']!r})"))
        validati["attiva"] = attiva

    # #CANCELLA# sulle quattro colonne nullable: gia' filtrato a monte da
    # `_campi_non_annullabili` per ogni altra colonna del foglio.
    for campo in ("help", "attributo_code", "visibile_se_domanda_code", "visibile_se_opzione_code"):
        if campo in r.campi_da_cancellare:
            validati[campo] = None

    riga_db = db.get(Domanda, code)

    vis_domanda_finale = validati.get(
        "visibile_se_domanda_code", riga_db.visibile_se_domanda_code if riga_db is not None else None
    )
    vis_opzione_finale = validati.get(
        "visibile_se_opzione_code", riga_db.visibile_se_opzione_code if riga_db is not None else None
    )
    motivo_vis = valida_visibilita(db, code, vis_domanda_finale, vis_opzione_finale)
    if motivo_vis is not None:
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"domande {code}: {motivo_vis}"))

    if riga_db is not None:
        return _Risoluzione(esistente=riga_db, campi_aggiornati=validati, chiave_descr=code)

    mancanti = {"testo", "tipo_controllo"} - validati.keys()
    if mancanti:
        return _Risoluzione(
            scarto=ScartoRowOut(riga=0, motivo=f"domande: riga nuova (codice {code}) senza i campi richiesti: {', '.join(sorted(mancanti))}")
        )

    return _Risoluzione(valori_creazione={"code": code, **validati}, chiave_descr=code)


# --- opzioni -------------------------------------------------------------------


def _risolvi_opzione(db: Session, r: RigaPiattaIn) -> _Risoluzione:
    validati: dict[str, object] = {}

    if "etichetta" in r.valori:
        etichetta = str(r.valori["etichetta"]).strip()
        if not (1 <= len(etichetta) <= 200):
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="opzioni: etichetta fuori bound (1-200 caratteri)"))
        validati["etichetta"] = etichetta

    if "descrizione" in r.valori:
        descrizione = str(r.valori["descrizione"]).strip()
        if len(descrizione) > 500:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="opzioni: descrizione troppo lunga (max 500 caratteri)"))
        validati["descrizione"] = descrizione

    if "immagine_url" in r.valori:
        immagine_url = str(r.valori["immagine_url"]).strip()
        if len(immagine_url) > 500:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="opzioni: immagine_url troppo lunga (max 500 caratteri)"))
        validati["immagine_url"] = immagine_url

    if "is_default" in r.valori:
        is_default = valore_booleano(r.valori["is_default"])
        if is_default is None:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"opzioni: is_default non interpretabile come booleano ({r.valori['is_default']!r})"))
        validati["is_default"] = is_default

    if "ordine" in r.valori:
        ordine = _intero(r.valori["ordine"])
        if ordine is None or not (0 <= ordine <= 10_000):
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"opzioni: ordine non valido ({r.valori['ordine']!r}), atteso un intero fra 0 e 10000"))
        validati["ordine"] = ordine

    attiva_presente = "attiva" in r.valori
    if attiva_presente:
        attiva = valore_booleano(r.valori["attiva"])
        if attiva is None:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"opzioni: attiva non interpretabile come booleano ({r.valori['attiva']!r})"))
        validati["attiva"] = attiva

    # #CANCELLA# sulle due colonne nullable.
    for campo in ("descrizione", "immagine_url"):
        if campo in r.campi_da_cancellare:
            validati[campo] = None

    if r.id is not None:
        riga_id = _intero(r.id)
        if riga_id is None:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"opzioni: id non numerico ({r.id!r})"))
        riga_db = db.get(OpzioneDomanda, riga_id)
        if riga_db is None:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"opzioni: id {r.id} non trovato"))

        if "domanda_code" in r.valori and str(r.valori["domanda_code"]).strip() != riga_db.domanda_code:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"opzioni: id {r.id} non puo' cambiare domanda_code"))
        if "code" in r.valori and str(r.valori["code"]).strip() != riga_db.code:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"opzioni: id {r.id} non puo' cambiare code"))

        is_default_finale = validati.get("is_default", riga_db.is_default)
        attiva_finale = validati.get("attiva", riga_db.attiva)

        if riga_db.attiva and attiva_presente and not validati["attiva"]:
            motivo = verifica_dipendenze_opzione(db, riga_db, is_default=validati.get("is_default"))
            if motivo is not None:
                return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"opzioni: {motivo}"))

        if is_default_finale and not attiva_finale:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="opzioni: un'opzione non attiva non puo' essere la risposta predefinita"))

        return _Risoluzione(
            esistente=riga_db, campi_aggiornati=validati,
            chiave_descr=f"{riga_db.domanda_code}.{riga_db.code}",
        )

    domanda_code_raw = r.valori.get("domanda_code")
    code_raw = r.valori.get("code")
    if not domanda_code_raw or not code_raw:
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="opzioni: riga senza id richiede domanda_code e code"))
    domanda_code = str(domanda_code_raw).strip()
    code = str(code_raw).strip()
    if db.get(Domanda, domanda_code) is None:
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"opzioni: domanda_code inesistente ({domanda_code})"))

    chiave_descr = f"{domanda_code}.{code}"
    esistente_naturale = db.query(OpzioneDomanda).filter_by(domanda_code=domanda_code, code=code).one_or_none()
    if esistente_naturale is not None:
        return _Risoluzione(esistente=esistente_naturale, campi_aggiornati=validati, chiave_descr=chiave_descr)

    if "etichetta" not in validati:
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"opzioni: riga nuova ({chiave_descr}) senza etichetta"))

    return _Risoluzione(
        valori_creazione={"domanda_code": domanda_code, "code": code, **validati},
        chiave_descr=chiave_descr,
    )


# --- effetti -------------------------------------------------------------------

_CAMPI_IDENTITA_EFFETTO_TESTUALE = ("target_categoria_code",)
_CAMPI_IDENTITA_EFFETTO_NUMERICO = ("opzione_id", "target_sottocategoria_id", "target_voce_id")


def _risolvi_effetto(db: Session, r: RigaPiattaIn) -> _Risoluzione:
    validati: dict[str, object] = {}

    if "tipo_code" in r.valori:
        tipo_code = str(r.valori["tipo_code"]).strip()
        if len(tipo_code) > 32:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="effetti: tipo_code troppo lungo (max 32 caratteri)"))
        validati["tipo_code"] = tipo_code

    if "valore" in r.valori:
        valore = _decimal(r.valori["valore"])
        if valore is None:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="effetti: valore non numerico"))
        if not (Decimal("-1000000") <= valore <= Decimal("1000000")):
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="effetti: valore fuori bound (-1000000, 1000000)"))
        validati["valore"] = valore

    if "attivo" in r.valori:
        attivo = valore_booleano(r.valori["attivo"])
        if attivo is None:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"effetti: attivo non interpretabile come booleano ({r.valori['attivo']!r})"))
        validati["attivo"] = attivo

    # #CANCELLA# sulle due colonne nullable.
    for campo in ("tipo_code", "valore"):
        if campo in r.campi_da_cancellare:
            validati[campo] = None

    if r.id is not None:
        riga_id = _intero(r.id)
        if riga_id is None:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"effetti: id non numerico ({r.id!r})"))
        riga_db = db.get(EffettoOpzione, riga_id)
        if riga_db is None:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"effetti: id {r.id} non trovato"))

        for campo in _CAMPI_IDENTITA_EFFETTO_NUMERICO:
            if campo not in r.valori:
                continue
            if _intero(r.valori[campo]) != getattr(riga_db, campo):
                return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="effetti: tipo e bersaglio non si cambiano: crea un effetto nuovo"))
        for campo in _CAMPI_IDENTITA_EFFETTO_TESTUALE:
            if campo not in r.valori:
                continue
            valore_file = str(r.valori[campo]).strip() or None
            if valore_file != getattr(riga_db, campo):
                return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="effetti: tipo e bersaglio non si cambiano: crea un effetto nuovo"))
        if "tipo_effetto" in r.valori and str(r.valori["tipo_effetto"]).strip() != riga_db.tipo_effetto:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="effetti: tipo e bersaglio non si cambiano: crea un effetto nuovo"))

        # WR-01: identita' (bersaglio/tipo) invariata, ma il `valore` puo'
        # essere cambiato dal file. La stessa regola che PATCH applica
        # (test_patch_valore_negativo_su_moltiplicatore_rifiutato) deve
        # valere anche qui, non solo sulla creazione: altrimenti un file
        # Excel bypassa un vincolo che l'API rifiuta.
        valore_finale = validati.get("valore", riga_db.valore)
        try:
            valida_effetto(
                db,
                riga_db.tipo_effetto,
                categoria_code=riga_db.target_categoria_code,
                sottocategoria_id=riga_db.target_sottocategoria_id,
                voce_id=riga_db.target_voce_id,
                valore=valore_finale,
            )
        except EffettoNonValido as exc:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"effetti: {exc}"))

        return _Risoluzione(esistente=riga_db, campi_aggiornati=validati, chiave_descr=f"effetto {riga_id}")

    opzione = None
    opzione_id_raw = r.valori.get("opzione_id")
    if opzione_id_raw is not None:
        opzione_id = _intero(opzione_id_raw)
        if opzione_id is None:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"effetti: opzione_id non numerico ({opzione_id_raw!r})"))
        opzione = db.get(OpzioneDomanda, opzione_id)
        if opzione is None:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"effetti: opzione_id {opzione_id} non trovato"))
    else:
        domanda_code = r.valori.get("domanda_code")
        opzione_code = r.valori.get("opzione_code")
        if not domanda_code or not opzione_code:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="effetti: riga senza id richiede opzione_id oppure domanda_code e opzione_code"))
        opzione = (
            db.query(OpzioneDomanda)
            .filter_by(domanda_code=str(domanda_code).strip(), code=str(opzione_code).strip())
            .one_or_none()
        )
        if opzione is None:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"effetti: nessuna opzione {domanda_code}/{opzione_code}"))

    tipo_effetto_raw = r.valori.get("tipo_effetto")
    if not tipo_effetto_raw:
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="effetti: riga nuova senza tipo_effetto"))
    tipo_effetto = str(tipo_effetto_raw).strip()

    target_categoria_code_raw = r.valori.get("target_categoria_code")
    target_categoria_code = str(target_categoria_code_raw).strip() if target_categoria_code_raw else None
    target_sottocategoria_id = (
        _intero(r.valori["target_sottocategoria_id"]) if r.valori.get("target_sottocategoria_id") is not None else None
    )
    target_voce_id = _intero(r.valori["target_voce_id"]) if r.valori.get("target_voce_id") is not None else None

    try:
        valida_effetto(
            db,
            tipo_effetto,
            categoria_code=target_categoria_code,
            sottocategoria_id=target_sottocategoria_id,
            voce_id=target_voce_id,
            valore=validati.get("valore"),
        )
    except EffettoNonValido as exc:
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"effetti: {exc}"))

    valori_creazione: dict[str, object] = {"opzione_id": opzione.id, "tipo_effetto": tipo_effetto}
    if target_categoria_code is not None:
        valori_creazione["target_categoria_code"] = target_categoria_code
    if target_sottocategoria_id is not None:
        valori_creazione["target_sottocategoria_id"] = target_sottocategoria_id
    if target_voce_id is not None:
        valori_creazione["target_voce_id"] = target_voce_id
    valori_creazione.update(validati)

    return _Risoluzione(
        valori_creazione=valori_creazione,
        chiave_descr=f"{opzione.domanda_code}.{opzione.code} -> {tipo_effetto}",
    )


# --- attese --------------------------------------------------------------------


def _risolvi_attesa(db: Session, r: RigaPiattaIn) -> _Risoluzione:
    validati: dict[str, object] = {}

    if "fascia_mq_max" in r.valori:
        v = _intero(r.valori["fascia_mq_max"])
        if v is None or not (0 <= v <= 10_000):
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"attese: fascia_mq_max non valida ({r.valori['fascia_mq_max']!r})"))
        validati["fascia_mq_max"] = v

    if "valore_atteso" in r.valori:
        v = _decimal(r.valori["valore_atteso"])
        if v is None or not (0 <= v <= 10_000):
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="attese: valore_atteso non valido"))
        validati["valore_atteso"] = v

    if "attiva" in r.valori:
        attiva = valore_booleano(r.valori["attiva"])
        if attiva is None:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"attese: attiva non interpretabile come booleano ({r.valori['attiva']!r})"))
        validati["attiva"] = attiva

    if r.id is not None:
        riga_id = _intero(r.id)
        if riga_id is None:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"attese: id non numerico ({r.id!r})"))
        riga_db = db.get(AttesaImmobile, riga_id)
        if riga_db is None:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"attese: id {r.id} non trovato"))

        if "attributo_code" in r.valori and str(r.valori["attributo_code"]).strip() != riga_db.attributo_code:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="attese: attributo_code non si cambia su una riga esistente"))
        if "fascia_mq_min" in r.valori and _intero(r.valori["fascia_mq_min"]) != riga_db.fascia_mq_min:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="attese: fascia_mq_min non si cambia su una riga esistente"))

        fascia_max_finale = validati.get("fascia_mq_max", riga_db.fascia_mq_max)
        if fascia_max_finale < riga_db.fascia_mq_min:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="attese: fascia_mq_max non puo' essere inferiore a fascia_mq_min"))

        return _Risoluzione(
            esistente=riga_db, campi_aggiornati=validati,
            chiave_descr=f"{riga_db.attributo_code} [{riga_db.fascia_mq_min}-{riga_db.fascia_mq_max}]",
        )

    attributo_code_raw = r.valori.get("attributo_code")
    fascia_mq_min_raw = r.valori.get("fascia_mq_min")
    if not attributo_code_raw or fascia_mq_min_raw is None:
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="attese: riga senza id richiede attributo_code e fascia_mq_min"))
    attributo_code = str(attributo_code_raw).strip()
    if len(attributo_code) > 32:
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="attese: attributo_code troppo lungo (max 32 caratteri)"))
    fascia_mq_min = _intero(fascia_mq_min_raw)
    if fascia_mq_min is None or not (0 <= fascia_mq_min <= 10_000):
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"attese: fascia_mq_min non valida ({fascia_mq_min_raw!r})"))

    chiave_descr = f"{attributo_code} [{fascia_mq_min}-?]"
    riga_db = db.query(AttesaImmobile).filter_by(attributo_code=attributo_code, fascia_mq_min=fascia_mq_min).one_or_none()
    if riga_db is not None:
        return _Risoluzione(esistente=riga_db, campi_aggiornati=validati, chiave_descr=chiave_descr)

    mancanti = {"fascia_mq_max", "valore_atteso"} - validati.keys()
    if mancanti:
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"attese: riga nuova ({chiave_descr}) senza i campi richiesti: {', '.join(sorted(mancanti))}"))
    if validati["fascia_mq_max"] < fascia_mq_min:
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="attese: fascia_mq_max non puo' essere inferiore a fascia_mq_min"))

    return _Risoluzione(
        valori_creazione={"attributo_code": attributo_code, "fascia_mq_min": fascia_mq_min, **validati},
        chiave_descr=chiave_descr,
    )


# --- derivazioni ---------------------------------------------------------------


def _valida_codici_derivazione(
    db: Session, domanda_code: str, quando_opzione_code: str, da_domanda_code: str,
    da_opzione_code: str, opzione_code: str,
) -> str | None:
    if db.get(Domanda, domanda_code) is None:
        return f"domanda_code {domanda_code!r} inesistente"
    if db.get(Domanda, da_domanda_code) is None:
        return f"da_domanda_code {da_domanda_code!r} inesistente"
    if db.query(OpzioneDomanda).filter_by(domanda_code=domanda_code, code=quando_opzione_code).one_or_none() is None:
        return f"quando_opzione_code {quando_opzione_code!r} inesistente per la domanda {domanda_code!r}"
    if db.query(OpzioneDomanda).filter_by(domanda_code=da_domanda_code, code=da_opzione_code).one_or_none() is None:
        return f"da_opzione_code {da_opzione_code!r} inesistente per la domanda {da_domanda_code!r}"
    if db.query(OpzioneDomanda).filter_by(domanda_code=domanda_code, code=opzione_code).one_or_none() is None:
        return f"opzione_code {opzione_code!r} inesistente per la domanda {domanda_code!r}"
    return None


def _risolvi_derivazione(db: Session, r: RigaPiattaIn) -> _Risoluzione:
    validati: dict[str, object] = {}

    if "opzione_code" in r.valori:
        opzione_code = str(r.valori["opzione_code"]).strip()
        if not opzione_code or len(opzione_code) > 64:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="derivazioni: opzione_code non valido"))
        validati["opzione_code"] = opzione_code

    if "attiva" in r.valori:
        attiva = valore_booleano(r.valori["attiva"])
        if attiva is None:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"derivazioni: attiva non interpretabile come booleano ({r.valori['attiva']!r})"))
        validati["attiva"] = attiva

    if r.id is not None:
        riga_id = _intero(r.id)
        if riga_id is None:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"derivazioni: id non numerico ({r.id!r})"))
        riga_db = db.get(DerivazioneRisposta, riga_id)
        if riga_db is None:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"derivazioni: id {r.id} non trovato"))

        for campo in ("domanda_code", "quando_opzione_code", "da_domanda_code", "da_opzione_code"):
            if campo not in r.valori:
                continue
            if str(r.valori[campo]).strip() != getattr(riga_db, campo):
                return _Risoluzione(
                    scarto=ScartoRowOut(
                        riga=0,
                        motivo="derivazioni: l'identita' della derivazione (domanda/opzione trigger/sorgente) non si cambia su una riga esistente",
                    )
                )

        opzione_code_finale = validati.get("opzione_code", riga_db.opzione_code)
        motivo = _valida_codici_derivazione(
            db, riga_db.domanda_code, riga_db.quando_opzione_code, riga_db.da_domanda_code,
            riga_db.da_opzione_code, opzione_code_finale,
        )
        if motivo is not None:
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"derivazioni: {motivo}"))

        return _Risoluzione(
            esistente=riga_db, campi_aggiornati=validati,
            chiave_descr=f"{riga_db.domanda_code}={riga_db.quando_opzione_code} <- {riga_db.da_domanda_code}={riga_db.da_opzione_code}",
        )

    domanda_code_raw = r.valori.get("domanda_code")
    quando_opzione_code_raw = r.valori.get("quando_opzione_code")
    da_domanda_code_raw = r.valori.get("da_domanda_code")
    da_opzione_code_raw = r.valori.get("da_opzione_code")
    if not all([domanda_code_raw, quando_opzione_code_raw, da_domanda_code_raw, da_opzione_code_raw]):
        return _Risoluzione(
            scarto=ScartoRowOut(riga=0, motivo="derivazioni: riga senza id richiede domanda_code, quando_opzione_code, da_domanda_code e da_opzione_code")
        )
    domanda_code = str(domanda_code_raw).strip()
    quando_opzione_code = str(quando_opzione_code_raw).strip()
    da_domanda_code = str(da_domanda_code_raw).strip()
    da_opzione_code = str(da_opzione_code_raw).strip()

    opzione_code = validati.get("opzione_code")
    if not opzione_code:
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="derivazioni: riga nuova senza opzione_code"))

    chiave_descr = f"{domanda_code}={quando_opzione_code} <- {da_domanda_code}={da_opzione_code}"

    motivo = _valida_codici_derivazione(db, domanda_code, quando_opzione_code, da_domanda_code, da_opzione_code, opzione_code)
    if motivo is not None:
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"derivazioni: {motivo}"))

    riga_db = (
        db.query(DerivazioneRisposta)
        .filter_by(
            domanda_code=domanda_code, quando_opzione_code=quando_opzione_code,
            da_domanda_code=da_domanda_code, da_opzione_code=da_opzione_code,
        )
        .one_or_none()
    )
    if riga_db is not None:
        campi_aggiornati = {"opzione_code": opzione_code}
        if "attiva" in validati:
            campi_aggiornati["attiva"] = validati["attiva"]
        return _Risoluzione(esistente=riga_db, campi_aggiornati=campi_aggiornati, chiave_descr=chiave_descr)

    return _Risoluzione(
        valori_creazione={
            "domanda_code": domanda_code,
            "quando_opzione_code": quando_opzione_code,
            "da_domanda_code": da_domanda_code,
            "da_opzione_code": da_opzione_code,
            "opzione_code": opzione_code,
        },
        chiave_descr=chiave_descr,
    )


_RESOLVER = {
    FOGLIO_DOMANDE: _risolvi_domanda,
    FOGLIO_OPZIONI: _risolvi_opzione,
    FOGLIO_EFFETTI: _risolvi_effetto,
    FOGLIO_ATTESE: _risolvi_attesa,
    FOGLIO_DERIVAZIONI: _risolvi_derivazione,
}

# Ordine di dipendenza per apply(): mai l'ordine dei fogli nel file.
_ORDINE_APPLY = (FOGLIO_DOMANDE, FOGLIO_OPZIONI, FOGLIO_EFFETTI, FOGLIO_ATTESE, FOGLIO_DERIVAZIONI)


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
        (FOGLIO_DOMANDE, COLONNE_DOMANDE, False),
        (FOGLIO_OPZIONI, COLONNE_OPZIONI, True),
        (FOGLIO_EFFETTI, COLONNE_EFFETTI, True),
        (FOGLIO_ATTESE, COLONNE_ATTESE, True),
        (FOGLIO_DERIVAZIONI, COLONNE_DERIVAZIONI, True),
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


def diff(
    db: Session, righe: list[RigaPiattaIn], generato_il: datetime | None = None
) -> tuple[list[DiffRigaOut], list[DiffRigaOut], list[ScartoRowOut]]:
    nuove: list[DiffRigaOut] = []
    modificate: list[DiffRigaOut] = []
    scarti: list[ScartoRowOut] = []
    chiavi_nuove: set[tuple[str, str]] = set()

    for r in righe:
        nulli = campi_nulli_in_valori(r)
        if nulli:
            scarti.append(
                ScartoRowOut(
                    riga=0,
                    motivo=(
                        f"{r.foglio}: valore nullo in 'valori' per {', '.join(nulli)} — "
                        "una cancellazione va dichiarata in 'campi_da_cancellare'"
                    ),
                )
            )
            continue

        non_annullabili = _campi_non_annullabili(r)
        if non_annullabili:
            scarti.append(
                ScartoRowOut(riga=0, motivo=f"{r.foglio}: campo non annullabile con #CANCELLA#: {', '.join(non_annullabili)}")
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
            chiave = (r.foglio, ris.chiave_descr)
            if chiave in chiavi_nuove:
                scarti.append(
                    ScartoRowOut(
                        riga=0,
                        motivo=(
                            f"{r.foglio}: il file contiene piu' di una riga nuova per "
                            f"{ris.chiave_descr} — tieni una sola riga per quella combinazione"
                        ),
                    )
                )
                continue
            chiavi_nuove.add(chiave)

            valori_nuovi = dict(ris.valori_creazione or {})
            campi_modificati = list((ris.valori_creazione or {}).keys())
            nuove.append(
                DiffRigaOut(
                    foglio=r.foglio, id=r.id, chiave_descr=ris.chiave_descr, nuova=True,
                    campi_modificati=campi_modificati, valori_precedenti={}, valori_nuovi=valori_nuovi,
                )
            )
            continue

        cambiati = _campi_modificati_da(ris.esistente, ris.campi_aggiornati)
        if not cambiati:
            continue  # nessun campo presente e' cambiato: riga non riportata (D-09)

        modificate.append(
            DiffRigaOut(
                foglio=r.foglio, id=r.id, chiave_descr=ris.chiave_descr, nuova=False,
                campi_modificati=list(cambiati.keys()),
                valori_precedenti={k: v[0] for k, v in cambiati.items()},
                valori_nuovi={k: v[1] for k, v in cambiati.items()},
                riga_modificata_dopo_export=riga_modificata_dopo_export(ris.esistente, generato_il),
            )
        )

    return nuove, modificate, scarti


# --- apply ---------------------------------------------------------------------


def apply(
    db: Session,
    nuove: list[RigaPiattaIn],
    modificate: list[RigaPiattaIn],
    *,
    is_admin: bool,
) -> int:
    """Ririsolve ogni riga (round-trip stateless) e applica in ordine di
    dipendenza (`_ORDINE_APPLY`), non nell'ordine del file: prima `domande`,
    poi `opzioni`, poi `effetti`/`attese`/`derivazioni`, con `db.flush()`
    dopo ogni scrittura cosi' le righe successive vedono lo stato gia'
    scritto (guardia D-28 compresa). Nessuna eliminazione e nessuna
    transazione in questo modulo: il commit unico lo fa il router."""
    applicate = 0

    righe_per_foglio: dict[str, list[RigaPiattaIn]] = {f: [] for f in _ORDINE_APPLY}
    for r in [*nuove, *modificate]:
        if r.foglio in righe_per_foglio:
            righe_per_foglio[r.foglio].append(r)

    for foglio in _ORDINE_APPLY:
        resolver = _RESOLVER[foglio]
        for r in righe_per_foglio[foglio]:
            if campi_nulli_in_valori(r) or _campi_non_annullabili(r):
                continue

            # Ririsolve sempre (round-trip stateless): non si fida del diff
            # calcolato in precedenza.
            ris = resolver(db, r)
            if ris.scarto is not None:
                continue

            tipo_controllo_prima = None
            if ris.esistente is None:
                riga_scritta = _MODEL[foglio](**(ris.valori_creazione or {}))
                db.add(riga_scritta)
                db.flush()
                era_nuova = True
            else:
                if foglio == FOGLIO_DOMANDE:
                    tipo_controllo_prima = ris.esistente.tipo_controllo
                for campo, valore in ris.campi_aggiornati.items():
                    setattr(ris.esistente, campo, valore)
                db.flush()
                riga_scritta = ris.esistente
                era_nuova = False

            if foglio == FOGLIO_DOMANDE:
                tipo_controllo_cambiato = (
                    "tipo_controllo" in ris.campi_aggiornati and ris.campi_aggiornati["tipo_controllo"] != tipo_controllo_prima
                )
                if era_nuova or tipo_controllo_cambiato:
                    assicura_opzione_valore(db, riga_scritta)

            if foglio == FOGLIO_OPZIONI and getattr(riga_scritta, "is_default", False):
                azzera_altri_default(db, riga_scritta)

            applicate += 1

    return applicate


class _DomandeHandler:
    """Oggetto minimale che espone le tre funzioni del modulo come
    attributi — soddisfa `ImportHandler` per struttura (Protocol), stesso
    pattern di `import_excel/parametri.py::_ParametriHandler`."""

    ruolo_richiesto = "admin"

    parse = staticmethod(parse)
    diff = staticmethod(diff)
    apply = staticmethod(apply)


registra(RISORSA, _DomandeHandler())
