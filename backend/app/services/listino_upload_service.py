"""Upload Excel listino a due passi (ADM-01, D-18/D-19/D-20/D-13/D-24):
`validate_upload` (dimensione/estensione, PRIMA di aprire il workbook) +
`parse_computo` (openpyxl hardened, ogni riga malformata diventa uno
scarto invece di sollevare, riusa `computo_parsing`) + `resolve_destinazione`
(listino esistente O nuova citta) + `compute_diff` (confronto per chiave
naturale, NIENTE scritture) + `apply_diff_idempotent` (upsert per chiave
naturale, MAI DELETE di righe assenti dal file — D-24).

Due rami di destinazione (D-13):
- **esistente**: `listino_id` gia' presente — il diff confronta contro lo
  stato DB reale di quel listino.
- **nuova_citta**: NESSUNA scrittura in preview (il set di confronto e'
  vuoto, quindi ogni riga risulta "nuova" — T-04-42); in confirm crea
  `Listino` + `ComuneListino` (stesso pattern di
  `routers/admin/listini.py::crea_listino`) PRIMA di upsertare
  Sottocategoria/Voce.

Scope dati: SOLO `Sottocategoria`/`Voce` (dettaglio Pro). L'upload NON
tocca `ListinoCategoria` (base_eur_mq/coefficiente_impresa, motore Free):
quel ritocco resta un percorso CRUD separato e deliberato
(`routers/admin/listini.py`, 04-02), lo stesso pattern gia' testato in
`test_admin_listini.py::TestCreazioneListinoECitta` — coerente con D-10
(Voce non ha MAI colonne di margine, quindi l'upload non puo' e non deve
scrivere `coefficiente_impresa`).
"""

from __future__ import annotations

import io
from datetime import datetime
from decimal import Decimal

import openpyxl
from openpyxl.utils.exceptions import InvalidFileException
from slugify import slugify
from sqlalchemy.orm import Session

from app.models.catalogo import ComuneListino
from app.models.dettaglio_pro import Sottocategoria, Voce
from app.models.listino import Listino
from app.schemas.admin_upload import (
    DiffRowOut,
    ScartoRowOut,
    UploadTargetEsistente,
    UploadTargetNuovaCitta,
    VoceRigaIn,
)
from app.services.computo_parsing import extract_a_edile, extract_catalogo
from app.services.export_excel.workbook import TOKEN_CANCELLA
from app.services.import_excel.flat import foglio_mancante, leggi_foglio_piatto
from app.services.import_excel.registry import riga_modificata_dopo_export

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10MB (D-20)
CATALOGO_SHEETS = {
    "B-FINITURE": "B-FINITURE",
    "C- SERRAMENTI PORTE  ": "C-SERRAMENTI",
    "D- PRODOTTI": "D-PRODOTTI",
}

# Formato piatto (08-01/08-03): unico foglio dati, header a 12 colonne.
FLAT_SHEET_VOCI = "voci"
FLAT_COLONNE_VOCI = {
    "id",
    "categoria_code",
    "sottocategoria_codice",
    "sottocategoria_nome",
    "sottocategoria_famiglia",
    "sottocategoria_ordine",
    "codice",
    "descrizione",
    "um",
    "prezzo_unitario_cliente",
    "ordine",
    "livello",
}
# Colonne nullable a database fra quelle del formato piatto (Sottocategoria/
# Voce): sono le UNICHE su cui TOKEN_CANCELLA ha effetto. Su un campo non
# nullable il token produce uno scarto descritto (D-19), mai un tentativo di
# scrivere NULL su una colonna NOT NULL.
_CAMPI_NULLABLE_PIATTO = {"sottocategoria_codice", "codice", "livello"}
# Campi obbligatori per creare una Voce NUOVA (riga senza id, D-04): senza,
# un insert produrrebbe una riga con placeholder mai intesi come dato reale.
_CAMPI_RICHIESTI_RIGA_NUOVA = {
    "categoria_code",
    "sottocategoria_nome",
    "sottocategoria_famiglia",
    "descrizione",
    "um",
    "prezzo_unitario_cliente",
}
# Placeholder usati SOLO per soddisfare la validazione pydantic quando un
# campo e' assente dalla riga piatta: mai scritti a database, perche' ogni
# consumatore (compute_diff, gli applicatori id-based) li ignora in base a
# `campi_presenti` (D-09) — vedi docstring di VoceRigaIn.
_PLACEHOLDER_TESTO = "-"
_PLACEHOLDER_PREZZO = Decimal("0.01")


class UploadValidationError(ValueError):
    """Errore di validazione upload (dimensione/estensione/file illeggibile)
    — sempre gestito dal router come 400, mai come 500 (Pitfall 1)."""


def validate_upload(filename: str | None, size_bytes: int) -> None:
    """Valida SOLO `.xlsx` e dimensione <= 10MB, PRIMA di aprire il
    workbook (D-20). Nessuna eccezione openpyxl deve raggiungere questo
    punto: qui operiamo solo su nome file e byte grezzi."""
    if not filename or not filename.lower().endswith(".xlsx"):
        raise UploadValidationError("Solo file .xlsx sono ammessi")
    if size_bytes <= 0:
        raise UploadValidationError("File vuoto")
    if size_bytes > MAX_UPLOAD_BYTES:
        raise UploadValidationError("File troppo grande (limite 10MB)")


def _sotto_key(riga: VoceRigaIn) -> tuple[str, str | None, str | None]:
    """Chiave naturale sottocategoria: (categoria_code, codice-o-nome) —
    stessa regola di `scripts/seed.py::_upsert_sottocategoria`."""
    if riga.sottocategoria_codice is not None:
        return (riga.categoria_code, riga.sottocategoria_codice, None)
    return (riga.categoria_code, None, riga.sottocategoria_nome)


def _voce_key(riga: VoceRigaIn) -> tuple[str, str | None, str | None]:
    """Chiave naturale voce, ANCORATA alla chiave sottocategoria (non solo
    all'id, che non esiste ancora in un diff non applicato): (sotto_key,
    codice-o-descrizione) — stessa regola di `_upsert_voce`."""
    sotto_key = _sotto_key(riga)
    if riga.codice is not None:
        return (*sotto_key, riga.codice)
    return (*sotto_key, riga.descrizione)


def parse_computo(file_bytes: bytes) -> tuple[list[VoceRigaIn], list[ScartoRowOut]]:
    """Apre il workbook (no eval formule, `data_only=True`) e produce righe
    voce piatte pronte per il diff. Ogni eccezione — apertura workbook,
    foglio mancante, riga malformata — diventa uno scarto strutturato
    (D-19), MAI un'eccezione che raggiunge l'HTTP layer come 500."""
    scarti: list[ScartoRowOut] = []

    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True, read_only=True)
    except (InvalidFileException, KeyError, OSError, *zip_error_types()) as exc:
        raise UploadValidationError(f"File .xlsx non leggibile: {exc}") from exc

    righe: list[VoceRigaIn] = []
    raw_scarti: list[dict] = []

    if "A-EDILE" in wb.sheetnames:
        for sotto in extract_a_edile(wb["A-EDILE"], raw_scarti):
            righe.extend(_sotto_dict_to_righe(sotto, raw_scarti))
    else:
        raw_scarti.append({"riga": 0, "motivo": "foglio 'A-EDILE' mancante"})

    for sheet_name, categoria_code in CATALOGO_SHEETS.items():
        if sheet_name in wb.sheetnames:
            for sotto in extract_catalogo(wb[sheet_name], categoria_code, raw_scarti):
                righe.extend(_sotto_dict_to_righe(sotto, raw_scarti))
        else:
            raw_scarti.append({"riga": 0, "motivo": f"foglio '{sheet_name}' mancante"})

    for entry in raw_scarti:
        scarti.append(ScartoRowOut(riga=entry["riga"], motivo=entry["motivo"]))

    return righe, scarti


def _campo_testo(valori: dict[str, object], campo: str, default: str | None) -> str | None:
    if campo not in valori:
        return default
    valore = valori[campo]
    return None if valore is None else str(valore)


def _campo_intero(valori: dict[str, object], campo: str, default: int = 0) -> int:
    if campo not in valori or valori[campo] is None:
        return default
    return int(valori[campo])  # type: ignore[arg-type]


def parse_flat_listino(file_bytes: bytes) -> tuple[list[VoceRigaIn], list[ScartoRowOut]]:
    """Legge il foglio `voci` del formato piatto (08-01) e produce righe
    pronte per `compute_diff`/`apply_diff_idempotent`. Non tocca il
    database: risolve solo bytes -> `VoceRigaIn`, esattamente come
    `parse_computo`, che resta invariata.

    Ogni campo assente dalla riga (cella vuota o colonna rimossa) riceve un
    placeholder che soddisfa la validazione pydantic ma non viene MAI letto
    a valle: `VoceRigaIn.campi_presenti` elenca solo i nomi-campo reali, e
    sia `compute_diff` sia gli applicatori id-based di
    `apply_diff_idempotent` ignorano tutto cio' che non vi compare (D-09).
    """
    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    except (InvalidFileException, KeyError, OSError, *zip_error_types()) as exc:
        raise UploadValidationError(f"File .xlsx non leggibile: {exc}") from exc

    mancante = foglio_mancante(wb, FLAT_SHEET_VOCI)
    if mancante is not None:
        return [], [mancante]

    righe_piatte, scarti = leggi_foglio_piatto(wb, FLAT_SHEET_VOCI, colonne_ammesse=FLAT_COLONNE_VOCI)

    righe: list[VoceRigaIn] = []
    for rp in righe_piatte:
        valori = rp.valori

        campi_non_annullabili_toccati = [
            campo for campo, valore in valori.items() if valore is None and campo not in _CAMPI_NULLABLE_PIATTO
        ]
        if campi_non_annullabili_toccati:
            scarti.append(
                ScartoRowOut(
                    riga=rp.numero_riga,
                    motivo=(
                        f"campo non annullabile con {TOKEN_CANCELLA}: "
                        f"{', '.join(sorted(campi_non_annullabili_toccati))}"
                    ),
                )
            )
            continue

        if rp.id is None:
            mancanti = _CAMPI_RICHIESTI_RIGA_NUOVA - valori.keys()
            if mancanti:
                scarti.append(
                    ScartoRowOut(
                        riga=rp.numero_riga,
                        motivo=f"riga nuova (senza id) senza i campi richiesti: {', '.join(sorted(mancanti))}",
                    )
                )
                continue

        prezzo_raw = valori.get("prezzo_unitario_cliente")
        try:
            prezzo = Decimal(str(prezzo_raw)) if prezzo_raw is not None else _PLACEHOLDER_PREZZO
        except Exception as exc:  # noqa: BLE001 - prezzo malformato diventa uno scarto, mai un 500
            scarti.append(ScartoRowOut(riga=rp.numero_riga, motivo=f"prezzo non numerico: {prezzo_raw!r}"))
            continue

        # Regola di business (D-19/D-20), preservata identica a
        # `_sotto_dict_to_righe`: SOLO per una riga nuova (senza id) il
        # prezzo deve essere > 0. Una riga esistente re-importata a 0 e' il
        # suo stato reale a database (voce non ancora quotata) — bloccarla
        # romperebbe il round-trip a vuoto (D-12) per ogni listino che ne
        # contiene una.
        if rp.id is None and prezzo <= 0:
            scarti.append(
                ScartoRowOut(riga=rp.numero_riga, motivo="riga nuova con prezzo non superiore a zero")
            )
            continue

        try:
            righe.append(
                VoceRigaIn(
                    id=rp.id,
                    categoria_code=_campo_testo(valori, "categoria_code", _PLACEHOLDER_TESTO) or _PLACEHOLDER_TESTO,
                    sottocategoria_codice=_campo_testo(valori, "sottocategoria_codice", None),
                    sottocategoria_nome=_campo_testo(valori, "sottocategoria_nome", _PLACEHOLDER_TESTO)
                    or _PLACEHOLDER_TESTO,
                    sottocategoria_famiglia=_campo_testo(valori, "sottocategoria_famiglia", _PLACEHOLDER_TESTO)
                    or _PLACEHOLDER_TESTO,
                    sottocategoria_ordine=_campo_intero(valori, "sottocategoria_ordine"),
                    codice=_campo_testo(valori, "codice", None),
                    descrizione=_campo_testo(valori, "descrizione", _PLACEHOLDER_TESTO) or _PLACEHOLDER_TESTO,
                    um=_campo_testo(valori, "um", _PLACEHOLDER_TESTO) or _PLACEHOLDER_TESTO,
                    prezzo_unitario_cliente=prezzo,
                    ordine=_campo_intero(valori, "ordine"),
                    livello=_campo_testo(valori, "livello", None),
                    campi_presenti=set(valori.keys()),
                )
            )
        except Exception as exc:  # noqa: BLE001 - riga malformata diventa uno scarto, mai un 500
            scarti.append(ScartoRowOut(riga=rp.numero_riga, motivo=str(exc)))

    return righe, scarti


def zip_error_types() -> tuple[type[Exception], ...]:
    """`openpyxl.load_workbook` su un .xlsx corrotto solleva anche
    `zipfile.BadZipFile` (un file non-zip rinominato .xlsx) — isolato in
    una funzione per un `except` leggibile senza importare `zipfile` a
    livello di modulo per un solo uso."""
    import zipfile

    return (zipfile.BadZipFile,)


def _sotto_dict_to_righe(sotto: dict, raw_scarti: list[dict]) -> list[VoceRigaIn]:
    """Converte le voci gia' classificate (header/UM/prezzo grammaticalmente
    validi, garantito da `computo_parsing.append_voce`) in `VoceRigaIn`,
    applicando qui la regola di BUSINESS dell'upload (prezzo > 0, D-19/D-20)
    — non nella classificazione pura, per non regredire
    `extract_dettaglio_pro.py` che accetta prezzo 0.0 come dato reale del
    file (voci non ancora quotate). Righe che violano la regola di business
    diventano scarti invece di sollevare (Pitfall 1)."""
    righe: list[VoceRigaIn] = []
    for voce in sotto["voci"]:
        try:
            prezzo = Decimal(str(voce["prezzo_unitario_cliente"]))
            # VoceRigaIn accetta prezzo=0 per il round-trip del formato
            # piatto (08-03, D-12): la regola di business "un prezzo
            # caricato da un computo va scartato se non e' > 0" va quindi
            # applicata qui esplicitamente, non piu' delegata al vincolo
            # pydantic (che ora e' ge=0, condiviso con il formato piatto).
            if prezzo <= 0:
                raise ValueError("prezzo deve essere maggiore di zero")
            righe.append(
                VoceRigaIn(
                    categoria_code=sotto["categoria_code"],
                    sottocategoria_codice=sotto.get("codice"),
                    sottocategoria_nome=sotto["nome"],
                    sottocategoria_famiglia=sotto["famiglia"],
                    sottocategoria_ordine=sotto.get("ordine", 0),
                    codice=voce.get("codice"),
                    descrizione=voce["descrizione"],
                    um=voce["um"],
                    prezzo_unitario_cliente=prezzo,
                    ordine=voce.get("ordine", 0),
                )
            )
        except Exception as exc:  # noqa: BLE001 - qualunque riga malformata diventa uno scarto, mai un 500
            raw_scarti.append({"riga": 0, "motivo": f"{voce.get('descrizione', '')[:120]}: {exc}"})
    return righe


def resolve_destinazione(
    db: Session, target: UploadTargetEsistente | UploadTargetNuovaCitta
) -> tuple[Listino | None, str]:
    """Ramo 'esistente': risolve il Listino (404-friendly ValueError se
    assente). Ramo 'nuova_citta': ritorna (None, descr) — NESSUNA
    scrittura qui, il Listino nasce solo in confirm (T-04-42)."""
    if isinstance(target, UploadTargetEsistente):
        listino = db.get(Listino, target.listino_id)
        if listino is None:
            raise UploadValidationError("Listino di destinazione non trovato")
        return listino, f"Listino esistente: {listino.nome}"
    return None, f"Nuova città: {target.citta}"


# Campi diffabili: mappa nome-campo-riga -> nome-attributo sull'entita' ORM
# corrispondente. Estende il diff oltre il solo prezzo (era il comportamento
# storico) a tutti i campi trasportati dal file — necessario perche' il
# round-trip a vuoto (D-12) sia dimostrato da un conteggio vero, non solo dal
# prezzo che per costruzione non cambia mai in un file appena riscaricato.
_CAMPI_DIFF_VOCE = {
    "codice": "codice",
    "descrizione": "descrizione",
    "um": "um",
    "prezzo_unitario_cliente": "prezzo_unitario_cliente",
    "ordine": "ordine",
    "livello": "livello",
}
_CAMPI_DIFF_SOTTOCATEGORIA = {
    "categoria_code": "categoria_code",
    "sottocategoria_codice": "codice",
    "sottocategoria_nome": "nome",
    "sottocategoria_famiglia": "famiglia",
    "sottocategoria_ordine": "ordine",
}


def compute_diff(
    db: Session, righe: list[VoceRigaIn], listino: Listino | None, generato_il: datetime | None = None
) -> tuple[list[DiffRowOut], list[DiffRowOut], list[ScartoRowOut]]:
    """Confronta `righe` con lo stato DB del listino destinazione — NIENTE
    scritture qui. Ramo nuova città: `listino` e' None -> stato di
    confronto vuoto -> tutte le righe sono 'nuove'.

    Risoluzione (D-03/T-08-23): se `riga.id` e' valorizzato, la voce si
    risolve PRIMA per id, vincolato al listino di destinazione — un id
    fuori dal listino (o inesistente) diventa uno scarto descritto, mai un
    update silenzioso su un'altra riga. Se l'id manca, vale la chiave
    naturale esistente (`_voce_key`).

    Il confronto per campo rispetta `riga.campi_presenti` (D-09): un campo
    assente dalla riga non entra mai in `campi_modificati`, qualunque cosa
    dica il valore placeholder sull'istanza. `campi_presenti is None`
    (righe di `parse_computo`) equivale a "tutti i campi sono presenti" —
    il comportamento storico.
    """
    per_chiave: dict[tuple, Voce] = {}
    per_id: dict[int, tuple[Voce, Sottocategoria]] = {}
    if listino is not None:
        rows = (
            db.query(Voce, Sottocategoria)
            .join(Sottocategoria, Voce.sottocategoria_id == Sottocategoria.id)
            .filter(Sottocategoria.listino_id == listino.id)
            .all()
        )
        for voce, sotto in rows:
            sotto_key = (
                sotto.categoria_code,
                sotto.codice,
                None if sotto.codice is not None else sotto.nome,
            )
            key = (*sotto_key, voce.codice if voce.codice is not None else voce.descrizione)
            per_chiave[key] = voce
            per_id[voce.id] = (voce, sotto)

    nuove: list[DiffRowOut] = []
    modificate: list[DiffRowOut] = []
    scarti: list[ScartoRowOut] = []

    for riga in righe:
        voce: Voce | None = None
        sotto: Sottocategoria | None = None

        if riga.id is not None:
            match = per_id.get(riga.id)
            if match is None:
                scarti.append(
                    ScartoRowOut(riga=0, motivo=f"id {riga.id} non trovato nel listino di destinazione")
                )
                continue
            voce, sotto = match
        else:
            voce = per_chiave.get(_voce_key(riga))

        if voce is None:
            nuove.append(DiffRowOut(riga=riga, valore_precedente=None))
            continue

        campi_confrontabili = riga.campi_presenti if riga.campi_presenti is not None else set(_CAMPI_DIFF_VOCE) | set(
            _CAMPI_DIFF_SOTTOCATEGORIA
        )
        campi_modificati: list[str] = []
        for campo_riga, campo_voce in _CAMPI_DIFF_VOCE.items():
            if campo_riga not in campi_confrontabili:
                continue
            if getattr(riga, campo_riga) != getattr(voce, campo_voce):
                campi_modificati.append(campo_riga)
        if sotto is not None:
            for campo_riga, campo_sotto in _CAMPI_DIFF_SOTTOCATEGORIA.items():
                if campo_riga not in campi_confrontabili:
                    continue
                if getattr(riga, campo_riga) != getattr(sotto, campo_sotto):
                    campi_modificati.append(campo_riga)

        if campi_modificati:
            modificate.append(
                DiffRowOut(
                    riga=riga,
                    valore_precedente=voce.prezzo_unitario_cliente,
                    campi_modificati=campi_modificati,
                    riga_modificata_dopo_export=riga_modificata_dopo_export(voce, generato_il),
                )
            )
        # nessun campo presente e' cambiato: riga non riportata nel diff (nessuna azione da fare)

    return nuove, modificate, scarti


def _upsert_sottocategoria(db: Session, listino_id: int, riga: VoceRigaIn) -> Sottocategoria:
    """Upsert idempotente per chiave naturale (listino_id, categoria_code,
    codice-o-nome) — stessa regola di `scripts/seed.py`."""
    query = db.query(Sottocategoria).filter_by(listino_id=listino_id, categoria_code=riga.categoria_code)
    query = (
        query.filter_by(codice=riga.sottocategoria_codice)
        if riga.sottocategoria_codice is not None
        else query.filter_by(codice=None, nome=riga.sottocategoria_nome)
    )
    sotto = query.one_or_none()
    if sotto is None:
        sotto = Sottocategoria(
            listino_id=listino_id,
            categoria_code=riga.categoria_code,
            codice=riga.sottocategoria_codice,
            nome=riga.sottocategoria_nome,
            famiglia=riga.sottocategoria_famiglia,
            ordine=riga.sottocategoria_ordine,
        )
        db.add(sotto)
        db.flush()
    else:
        sotto.nome = riga.sottocategoria_nome
        sotto.famiglia = riga.sottocategoria_famiglia
        sotto.ordine = riga.sottocategoria_ordine
    return sotto


def _upsert_voce(db: Session, sotto: Sottocategoria, riga: VoceRigaIn) -> Voce:
    """Upsert per chiave naturale (sottocategoria_id, codice-o-descrizione)
    — MAI un DELETE di righe assenti dal file (D-24).

    `voce.livello` NON compare qui, ed e' deliberato. Questa funzione
    sovrascrive incondizionatamente i campi che tocca; il file Excel del
    computo non ha una colonna livello e non l'avra', quindi se `livello`
    entrasse nel giro ogni ri-caricamento del listino azzererebbe la curatela
    dei livelli fatta a mano dall'admin — e con tutti i livelli a NULL il
    motore Pro torna a sommare i cataloghi di alternative. Il livello si cura
    solo da `routers/admin/dettaglio_pro.py`. Test di regressione:
    `tests/test_dettaglio_pro_livelli.py::test_upload_excel_non_azzera_livello`.
    """
    query = db.query(Voce).filter_by(sottocategoria_id=sotto.id)
    query = query.filter_by(codice=riga.codice) if riga.codice is not None else query.filter_by(
        codice=None, descrizione=riga.descrizione
    )
    voce = query.one_or_none()
    if voce is None:
        voce = Voce(
            sottocategoria_id=sotto.id,
            codice=riga.codice,
            descrizione=riga.descrizione,
            um=riga.um,
            prezzo_unitario_cliente=riga.prezzo_unitario_cliente,
            ordine=riga.ordine,
        )
        db.add(voce)
        db.flush()
    else:
        voce.descrizione = riga.descrizione
        voce.um = riga.um
        voce.prezzo_unitario_cliente = riga.prezzo_unitario_cliente
        voce.ordine = riga.ordine
    return voce


def _resolve_per_id(db: Session, listino_id: int, voce_id: int) -> tuple[Voce, Sottocategoria] | None:
    """Risolve una `Voce` per id, vincolata al listino di destinazione
    (T-08-23): un id di un altro listino non deve mai risultare un match."""
    return (
        db.query(Voce, Sottocategoria)
        .join(Sottocategoria, Voce.sottocategoria_id == Sottocategoria.id)
        .filter(Sottocategoria.listino_id == listino_id, Voce.id == voce_id)
        .one_or_none()
    )


def _applica_voce(voce: Voce, riga: VoceRigaIn) -> None:
    """Applica alla `Voce` gia' risolta per id SOLO i campi presenti nella
    riga (D-09/CUR-02): un campo assente non viene toccato. Un campo
    marcato con `TOKEN_CANCELLA` e' gia' stato tradotto in `None` dal
    parser (`parse_flat_listino`), che garantisce a monte che questo accada
    solo per colonne nullable a database — qui si applica senza rivalidare."""
    presenti = riga.campi_presenti or set()
    for campo in ("codice", "descrizione", "um", "prezzo_unitario_cliente", "ordine", "livello"):
        if campo in presenti:
            setattr(voce, campo, getattr(riga, campo))


def _applica_sottocategoria(sotto: Sottocategoria, riga: VoceRigaIn) -> None:
    """Applica alla `Sottocategoria` gia' risolta (via la Voce per id) SOLO
    i campi presenti nella riga — stessa disciplina di `_applica_voce`."""
    presenti = riga.campi_presenti or set()
    for campo_riga, campo_sotto in (
        ("sottocategoria_codice", "codice"),
        ("sottocategoria_nome", "nome"),
        ("sottocategoria_famiglia", "famiglia"),
        ("sottocategoria_ordine", "ordine"),
    ):
        if campo_riga in presenti:
            setattr(sotto, campo_sotto, getattr(riga, campo_riga))


def _upsert_comune(db: Session, nome: str, listino_id: int) -> None:
    """Mappa (idempotente) un comune sul listino: crea la riga ComuneListino
    se assente, altrimenti ne aggiorna solo il listino_id. Mai distruttivo."""
    slug = slugify(nome)
    comune = db.query(ComuneListino).filter_by(comune_slug=slug).one_or_none()
    if comune is None:
        db.add(ComuneListino(comune_nome=nome, comune_slug=slug, listino_id=listino_id))
    else:
        comune.comune_nome = nome
        comune.listino_id = listino_id


def apply_diff_idempotent(
    db: Session,
    target: UploadTargetEsistente | UploadTargetNuovaCitta,
    nuove: list[VoceRigaIn],
    modificate: list[VoceRigaIn],
    comuni_extra: list[str] | None = None,
) -> tuple[int, int]:
    """Applica l'upsert (mai un DELETE implicito, D-24). Ramo nuova città:
    crea Listino + ComuneListino PRIMA dell'upsert voci (D-13) — stesso
    pattern di `routers/admin/listini.py::crea_listino`, idempotente sulla
    mappatura comune_slug. Ritorna (listino_id, righe_importate)."""
    if isinstance(target, UploadTargetNuovaCitta):
        listino = db.query(Listino).filter_by(citta_riferimento=target.citta).one_or_none()
        if listino is None:
            listino = Listino(
                nome=target.citta,
                citta_riferimento=target.citta,
                is_default=target.is_default,
            )
            db.add(listino)
            db.flush()

        _upsert_comune(db, target.citta, listino.id)
        listino_id = listino.id
    else:
        listino = db.get(Listino, target.listino_id)
        if listino is None:
            raise UploadValidationError("Listino di destinazione non trovato")
        listino_id = listino.id

    # Comuni aggiuntivi mappati sullo stesso listino, in un solo passaggio.
    for nome in comuni_extra or []:
        nome = nome.strip()
        if nome:
            _upsert_comune(db, nome, listino_id)

    righe_importate = 0
    for riga in [*nuove, *modificate]:
        if riga.id is not None:
            # Risoluzione per id (D-03): la riga viene dal formato piatto e
            # gia' e' stata validata da compute_diff (id nel listino di
            # destinazione). Qui e' difesa in profondita', non il percorso
            # normale di validazione — se il match non c'e' piu' (stato
            # cambiato fra preview e confirm), la riga non scrive nulla
            # invece di sollevare un errore a meta' del batch.
            match = _resolve_per_id(db, listino_id, riga.id)
            if match is None:
                continue
            voce, sotto = match
            _applica_sottocategoria(sotto, riga)
            _applica_voce(voce, riga)
        else:
            sotto = _upsert_sottocategoria(db, listino_id, riga)
            _upsert_voce(db, sotto, riga)
        righe_importate += 1

    return listino_id, righe_importate
