"""Handler di import della risorsa `lead` (piano 08-07, CUR-01/CUR-02/CUR-04).

**Deroga dichiarata a D-04** (vedi obiettivo del piano 08-07): `Lead.user_id`
e' una FK non nullable verso l'utente che ha generato la stima, e non esiste
nel file nessuna informazione da cui ricavarla — inventarla vorrebbe dire
attribuire un contatto a un utente a caso. Una riga senza `id` non crea un
lead (a differenza degli altri fogli di 08-06): diventa uno scarto descritto,
sempre. Questo handler non produce MAI righe "nuove" (`diff()` ritorna
sempre `[]` come primo elemento).

Risoluzione SOLO per `id` (T-08-61): il lead non ha una chiave naturale — due
persone possono chiamarsi uguale e scrivere due volte, un `id` inesistente e'
uno scarto descritto.

`CAMPI_MODIFICABILI` (T-08-60) e' l'unico insieme scrivibile da file:
qualunque altra colonna del foglio presente nel file con un valore DIVERSO
da quello a database blocca l'INTERA riga con uno scarto — il file non
riscrive dati di contatto o totali. La stessa colonna con lo stesso valore
letto dal DB non e' un errore: e' il caso normale del round-trip a vuoto,
dove l'export riporta tutte le colonne (anche quelle non modificabili).

`stato` e' limitato agli stessi valori ammessi dalla UI/PATCH esistente
(`routers/admin/lead.py`, `frontend/.../LeadDashboardPage.tsx`) — un valore
fuori dominio e' uno scarto. `#CANCELLA#` e' ammesso solo su `nota` e
`referente_id` (nullable a database); su `stato` (non nullable) e' uno
scarto. NESSUNA eliminazione, mai (D-10, T-08-64).

Permesso per risorsa (T-08-62): `ruolo_richiesto = "staff"` — stesso gate
della `PATCH /{lead_id}` esistente (`require_staff`), non un ruolo piu'
stretto: il perimetro dell'import segue quello della pagina da cui si carica
il file (D-26).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation

from openpyxl.workbook import Workbook
from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.schemas.admin_import import DiffRigaOut, RigaPiattaIn
from app.schemas.admin_upload import ScartoRowOut
from app.services.import_excel.flat import foglio_mancante, leggi_foglio_piatto
from app.services.import_excel.registry import registra, riga_modificata_dopo_export

RISORSA = "lead"
FOGLIO_LEAD = "lead"

# Le sole tre colonne scrivibili da file (T-08-60). Ogni altra colonna del
# foglio e' in lettura SOLO per il confronto col database (vedi
# `_valori_uguali`/`_risolvi` sotto), mai per essere scritta.
CAMPI_MODIFICABILI = {"stato", "nota", "referente_id"}

# Tutte le colonne del foglio scritto da `export_excel/lead.py::COLONNE_LEAD`,
# meno `id` (letta a parte da `leggi_foglio_piatto`). Servono TUTTE in
# lettura — anche quelle non modificabili — per poter rilevare un tentativo
# di riscrittura (T-08-60), non solo per applicare le tre modificabili.
COLONNE_LEAD = {
    "id", "created_at", "nome", "email", "telefono", "preferenza_contatto",
    "fascia_oraria", "messaggio", "citta", "mq", "tipo",
    "totale_min", "totale_max", "referente_id", "email_inviata",
    "stato", "nota",
}

# Uniche colonne nullable a database fra le modificabili: le sole su cui
# #CANCELLA# ha effetto (D-09). `stato` non e' nullable (default "nuovo").
_CAMPI_NULLABLE = {"nota", "referente_id"}

# Stessi valori ammessi dalla UI/PATCH esistente (frontend LeadDashboardPage,
# routers/admin/lead.py) — non esiste un enum a database (String(16) libero),
# quindi il dominio e' dichiarato qui, unico punto.
STATI_AMMESSI = {"nuovo", "gestito"}

# Colonne del foglio confrontate col database SOLO in lettura (mai scritte):
# qualunque valore diverso da quello a database blocca la riga.
_CAMPI_NON_MODIFICABILI = COLONNE_LEAD - CAMPI_MODIFICABILI


def _decimal(valore: object) -> Decimal | None:
    try:
        return Decimal(str(valore))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _valori_uguali(campo: str, valore_db: object, valore_file: object) -> bool:
    """Confronto onesto per tipo (T-08-60): un valore che non si riesce a
    normalizzare NON e' mai considerato uguale — un falso 'uguale'
    lascerebbe passare silenziosamente un tentativo di riscrittura."""
    if campo in ("totale_min", "totale_max"):
        a, b = _decimal(valore_db), _decimal(valore_file)
        return a is not None and b is not None and a == b
    if campo == "mq":
        try:
            return int(valore_db) == int(valore_file)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return False
    if campo == "email_inviata":
        return bool(valore_db) == bool(valore_file)
    if campo == "created_at":
        # `Lead.created_at` e' un `datetime`, il file porta la sua
        # `isoformat()` (vedi export_excel/lead.py) — confronto via
        # isoformat su entrambi i lati, mai str(datetime) (formato diverso:
        # spazio invece di 'T' come separatore).
        db_iso = valore_db.isoformat() if isinstance(valore_db, datetime) else str(valore_db).strip()
        file_iso = str(valore_file).strip()
        return db_iso == file_iso
    a = "" if valore_db is None else str(valore_db).strip()
    b = "" if valore_file is None else str(valore_file).strip()
    return a == b


def _campi_non_annullabili(r: RigaPiattaIn) -> list[str]:
    return sorted(c for c in r.campi_da_cancellare if c not in _CAMPI_NULLABLE)


@dataclass
class _Risoluzione:
    scarto: ScartoRowOut | None = None
    esistente: Lead | None = None
    campi_aggiornati: dict[str, object] = field(default_factory=dict)
    chiave_descr: str = ""


def _risolvi(db: Session, r: RigaPiattaIn) -> _Risoluzione:
    if r.id is None:
        return _Risoluzione(
            scarto=ScartoRowOut(riga=0, motivo="Riga senza id: i lead non si creano da file")
        )

    try:
        lead_id = int(r.id)
    except (TypeError, ValueError):
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"lead: id non numerico ({r.id!r})"))

    riga_db = db.get(Lead, lead_id)
    if riga_db is None:
        return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"lead: id {lead_id} non trovato"))

    for campo in _CAMPI_NON_MODIFICABILI:
        if campo not in r.valori:
            continue
        valore_db = getattr(riga_db, campo)
        valore_file = r.valori[campo]
        if not _valori_uguali(campo, valore_db, valore_file):
            return _Risoluzione(
                scarto=ScartoRowOut(
                    riga=0,
                    motivo=(
                        f"lead {lead_id}: il campo '{campo}' non e' modificabile da file "
                        "e il valore proposto diverge dal database"
                    ),
                )
            )

    validati: dict[str, object] = {}

    if "stato" in r.valori:
        stato = str(r.valori["stato"]).strip()
        if stato not in STATI_AMMESSI:
            return _Risoluzione(
                scarto=ScartoRowOut(riga=0, motivo=f"lead {lead_id}: stato fuori dominio ({stato!r})")
            )
        validati["stato"] = stato

    if "nota" in r.valori:
        validati["nota"] = str(r.valori["nota"])

    if "referente_id" in r.valori:
        try:
            validati["referente_id"] = int(r.valori["referente_id"])
        except (TypeError, ValueError):
            return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"lead {lead_id}: referente_id non numerico"))

    # #CANCELLA#: solo su nota/referente_id (nullable) — `_campi_non_annullabili`
    # ha gia' scartato la riga a monte se il token compariva su `stato`.
    if "nota" in r.campi_da_cancellare:
        validati["nota"] = None
    if "referente_id" in r.campi_da_cancellare:
        validati["referente_id"] = None

    return _Risoluzione(
        esistente=riga_db, campi_aggiornati=validati, chiave_descr=f"{riga_db.nome} <{riga_db.email}>"
    )


# --- parse -------------------------------------------------------------------


def parse(wb: Workbook) -> tuple[list[RigaPiattaIn], list[ScartoRowOut]]:
    mancante = foglio_mancante(wb, FOGLIO_LEAD)
    if mancante is not None:
        return [], [mancante]

    righe_piatte, scarti = leggi_foglio_piatto(wb, FOGLIO_LEAD, colonne_ammesse=COLONNE_LEAD)

    righe: list[RigaPiattaIn] = []
    for rp in righe_piatte:
        if rp.id is None:
            # Deroga a D-04 (vedi docstring di modulo): una riga senza id
            # non e' un record nuovo, e' sempre uno scarto.
            scarti.append(
                ScartoRowOut(riga=rp.numero_riga, motivo="Riga senza id: i lead non si creano da file")
            )
            continue
        valori: dict[str, object] = {}
        cancella: list[str] = []
        for campo, valore in rp.valori.items():
            if valore is None:
                cancella.append(campo)
            else:
                valori[campo] = valore
        righe.append(
            RigaPiattaIn(foglio=FOGLIO_LEAD, id=str(rp.id), valori=valori, campi_da_cancellare=cancella)
        )

    return righe, scarti


# --- diff ----------------------------------------------------------------------


def _campi_modificati_da(esistente: Lead, validati: dict[str, object]) -> dict[str, tuple[object, object]]:
    cambiati: dict[str, tuple[object, object]] = {}
    for campo, nuovo in validati.items():
        precedente = getattr(esistente, campo)
        if precedente != nuovo:
            cambiati[campo] = (precedente, nuovo)
    return cambiati


def diff(
    db: Session, righe: list[RigaPiattaIn], generato_il: datetime | None = None
) -> tuple[list[DiffRigaOut], list[DiffRigaOut], list[ScartoRowOut]]:
    modificate: list[DiffRigaOut] = []
    scarti: list[ScartoRowOut] = []

    for r in righe:
        non_annullabili = _campi_non_annullabili(r)
        if non_annullabili:
            scarti.append(
                ScartoRowOut(
                    riga=0,
                    motivo=f"lead: campo non annullabile con #CANCELLA#: {', '.join(non_annullabili)}",
                )
            )
            continue

        ris = _risolvi(db, r)
        if ris.scarto is not None:
            scarti.append(ris.scarto)
            continue

        assert ris.esistente is not None  # per costruzione: _risolvi non torna mai un 'nuovo'
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

    # Sempre [] come "nuove": i lead non si creano da file (deroga a D-04).
    return [], modificate, scarti


# --- apply ---------------------------------------------------------------------


def apply(
    db: Session,
    nuove: list[RigaPiattaIn],
    modificate: list[RigaPiattaIn],
    *,
    is_admin: bool,
) -> int:
    """`nuove` e sempre vuoto per questa risorsa (deroga a D-04) — il
    parametro resta per soddisfare `ImportHandler` (Protocol). `is_admin`
    non e' usato: non esiste su questa risorsa una colonna is_admin-gated
    come `coefficiente_impresa` in `parametri.py`, il permesso di riga e'
    gia' verificato dal router (`ruolo_richiesto = "staff"`)."""
    del nuove, is_admin
    applicate = 0

    for r in modificate:
        if _campi_non_annullabili(r):
            continue

        # Ririsolve sempre (round-trip stateless): non si fida del diff
        # calcolato in precedenza, stesso principio di `parametri.py`.
        ris = _risolvi(db, r)
        if ris.scarto is not None or ris.esistente is None:
            continue

        for campo, valore in ris.campi_aggiornati.items():
            setattr(ris.esistente, campo, valore)
        applicate += 1

    return applicate


class _LeadHandler:
    """Oggetto minimale che espone le tre funzioni del modulo come
    attributi — soddisfa `ImportHandler` per struttura (Protocol), stesso
    pattern di `_ParametriHandler` in `parametri.py`."""

    ruolo_richiesto = "staff"

    parse = staticmethod(parse)
    diff = staticmethod(diff)
    apply = staticmethod(apply)


registra(RISORSA, _LeadHandler())
