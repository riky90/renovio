"""Endpoint generico di import Excel per risorsa (piano 08-06, CUR-01).

`POST /import-excel/{risorsa}/preview` (parse + diff, NIENTE scritture) e
`POST /import-excel/{risorsa}/confirm` (apply, round-trip stateless — il
client re-invia le righe proposte in preview). Il dispatch sulla risorsa
passa SEMPRE da `risolvi_handler` (registro di `services/import_excel/
registry.py`): una `{risorsa}` non registrata risponde 404 con messaggio
esplicito, mai una costruzione dinamica di nome modulo/`getattr` su input
utente (T-08-52).

Il permesso NON e' piu' un `require_admin` fisso (piano 08-07, T-08-62):
ogni route dipende solo da `Depends(get_current_user)`, poi
`_verifica_permesso` controlla il ruolo dichiarato dall'HANDLER RISOLTO
(`ImportHandler.ruolo_richiesto`) — `"admin"` richiede `ROLE_ADMIN`,
`"staff"` basta `STAFF_ROLES`. Il controllo avviene SEMPRE dopo aver
risolto la risorsa e SEMPRE prima di leggere il file caricato, cosi' un
non autorizzato non riesce nemmeno a far parsare un workbook al server. Il
ruolo dichiarato dal client non conta mai (ASVS V4): il perimetro
dell'import segue quello della pagina da cui si carica il file (D-26).

Il file caricato passa prima da `validate_upload` (10MB, `.xlsx`, D-20) e
poi da `zip_error_types()` per gli archivi corrotti — entrambi PRIMA di
`load_workbook`, stesso ordine di `upload_listino.py`. Il file del computo
originale (senza il foglio `ISTRUZIONI`) e' rifiutato con 400 descritto: ha
il suo endpoint dedicato (`/admin/upload-listino`), non questo generico
(D-01).
"""

from __future__ import annotations

import io
import logging

import openpyxl
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from openpyxl.utils.exceptions import InvalidFileException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dependencies.auth import ROLE_ADMIN, STAFF_ROLES, get_current_user, get_db
from app.models.user import User
from app.schemas.admin_import import ConfirmPiattoIn, DiffPiattoOut
from app.services.import_excel.flat import e_formato_piatto, leggi_timestamp_export
from app.services.import_excel.registry import ImportHandler, RisorsaImportSconosciuta, risolvi_handler
from app.services.listino_upload_service import UploadValidationError, validate_upload, zip_error_types

# Import per side-effect: registra le risorse in HANDLER (piano 08-06/08-07).
# Ogni risorsa futura (08-08) aggiunge qui la sua riga — mai una route
# nuova (T-08-52).
import app.services.import_excel.domande  # noqa: F401
import app.services.import_excel.lead  # noqa: F401
import app.services.import_excel.parametri  # noqa: F401

router = APIRouter(prefix="/import-excel", tags=["admin-import-excel"])

logger = logging.getLogger(__name__)

# Messaggio unico della rete di sicurezza sotto. Deliberatamente NON riporta
# `str(exc)` all'utente: il testo di un'eccezione puo' contenere un frammento
# di query o di riga, e su questa risorsa una riga di `listino_categoria`
# porta `coefficiente_impresa` (regola di dominio #1, mai verso il client).
# Il dettaglio completo va nel log del server, con traceback.
ERRORE_IMPREVISTO = (
    "Il file contiene una riga che il server non e' riuscito a elaborare. "
    "Nessuna modifica e' stata applicata. Controlla il file e riprova; se il "
    "problema persiste, segnala il caso all'assistenza tecnica."
)

# Un vincolo di database violato al commit e' un caso diverso e piu'
# diagnosticabile: quasi sempre due righe del file che insistono sullo
# stesso record. Anche qui niente `str(exc)`: il messaggio di un
# `IntegrityError` riporta la query e i parametri, e sulla risorsa
# `parametri` fra quei parametri puo' esserci `coefficiente_impresa`.
ERRORE_VINCOLO = (
    "Il file viola un vincolo di unicita' del database: probabilmente contiene "
    "due righe che descrivono lo stesso record. Nessuna modifica e' stata "
    "applicata. Correggi il file e ricarica."
)


def _verifica_permesso(handler: ImportHandler, user: User) -> None:
    """Gate per risorsa (T-08-62/T-08-63): il ruolo dichiarato
    dall'handler risolto, mai un valore fidato dal client."""
    if handler.ruolo_richiesto == "admin":
        if user.role != ROLE_ADMIN:
            raise HTTPException(403, "Accesso riservato")
    elif handler.ruolo_richiesto == "staff":
        if user.role not in STAFF_ROLES:
            raise HTTPException(403, "Accesso riservato")
    else:
        raise HTTPException(403, "Accesso riservato")


@router.post("/{risorsa}/preview", response_model=DiffPiattoOut)
async def preview_import(
    risorsa: str,
    file: UploadFile,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DiffPiattoOut:
    try:
        handler = risolvi_handler(risorsa)
    except RisorsaImportSconosciuta as exc:
        raise HTTPException(404, str(exc)) from exc

    _verifica_permesso(handler, user)

    content = await file.read()
    try:
        validate_upload(file.filename, len(content))
    except UploadValidationError as exc:
        raise HTTPException(400, str(exc)) from exc

    try:
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    except (InvalidFileException, KeyError, OSError, *zip_error_types()) as exc:
        raise HTTPException(400, f"File .xlsx non leggibile: {exc}") from exc

    if not e_formato_piatto(wb):
        raise HTTPException(400, "Il file non e' nel formato piatto di import: sembra il computo originale, che ha il suo endpoint dedicato (/admin/upload-listino)")

    generato_il = leggi_timestamp_export(wb)
    # Rete di sicurezza indipendente dai singoli resolver (CR-01): il
    # contratto dichiarato dagli handler e' che una riga malformata sia uno
    # scarto descritto, mai un 500 — ma quel contratto vale finche' ogni
    # conversione e' protetta, e basta dimenticarne una perche' un refuso in
    # una cella (`--5`) faccia cadere l'intero import con un 500 muto.
    # Qui la caduta diventa un 400 leggibile, e il traceback resta nel log.
    try:
        righe, scarti_parse = handler.parse(wb)
        nuove, modificate, scarti_diff = handler.diff(db, righe, generato_il)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — rete di sicurezza deliberata
        logger.exception("preview import fallita per la risorsa %s", risorsa)
        raise HTTPException(400, ERRORE_IMPREVISTO) from exc

    return DiffPiattoOut(
        risorsa=risorsa,
        nuove=nuove,
        modificate=modificate,
        scarti=[*scarti_parse, *scarti_diff],
        generato_il=generato_il,
    )


@router.post("/{risorsa}/confirm")
def confirm_import(
    risorsa: str,
    payload: ConfirmPiattoIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    try:
        handler = risolvi_handler(risorsa)
    except RisorsaImportSconosciuta as exc:
        raise HTTPException(404, str(exc)) from exc

    _verifica_permesso(handler, user)

    # IN-02: il body ripete la risorsa del path. Un disallineamento e' un
    # client confuso, e deve diventare un errore leggibile, non un import
    # silenzioso sulla risorsa del path.
    if payload.risorsa != risorsa:
        raise HTTPException(
            400,
            f"La risorsa del corpo ({payload.risorsa!r}) non corrisponde a quella dell'URL ({risorsa!r})",
        )

    # is_admin reale, non un True fisso (T-08-63): con il gate per risorsa
    # un consulente puo' raggiungere questo punto per la risorsa "lead",
    # e la scrittura di colonne is_admin-gated (oggi solo su "parametri",
    # dove ruolo_richiesto="admin" impedisce comunque al consulente di
    # arrivarci) deve riflettere il ruolo vero dell'utente, non l'assunzione
    # implicita del vecchio gate globale.
    # Stessa rete di sicurezza della preview (CR-01), con in piu' il
    # `rollback()`: `/confirm` scrive davvero, e una sessione lasciata in
    # stato sporco dopo un'eccezione contaminerebbe la richiesta successiva
    # che riusa la stessa connessione.
    try:
        righe_applicate = handler.apply(
            db, payload.nuove, payload.modificate, is_admin=(user.role == ROLE_ADMIN)
        )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        logger.exception("confirm import ha violato un vincolo per la risorsa %s", risorsa)
        raise HTTPException(400, ERRORE_VINCOLO) from exc
    except Exception as exc:  # noqa: BLE001 — rete di sicurezza deliberata
        db.rollback()
        logger.exception("confirm import fallita per la risorsa %s", risorsa)
        raise HTTPException(400, ERRORE_IMPREVISTO) from exc

    return {"righe_applicate": righe_applicate}
