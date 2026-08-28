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

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10MB (D-20)
CATALOGO_SHEETS = {
    "B-FINITURE": "B-FINITURE",
    "C- SERRAMENTI PORTE  ": "C-SERRAMENTI",
    "D- PRODOTTI": "D-PRODOTTI",
}


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
                    prezzo_unitario_cliente=Decimal(str(voce["prezzo_unitario_cliente"])),
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


def compute_diff(
    db: Session, righe: list[VoceRigaIn], listino: Listino | None
) -> tuple[list[DiffRowOut], list[DiffRowOut]]:
    """Confronta `righe` con lo stato DB del listino destinazione per
    chiave naturale — NIENTE scritture qui. Ramo nuova città: `listino` e'
    None -> stato di confronto vuoto -> tutte le righe sono 'nuove'."""
    existing: dict[tuple, Decimal] = {}
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
            existing[key] = voce.prezzo_unitario_cliente

    nuove: list[DiffRowOut] = []
    modificate: list[DiffRowOut] = []
    for riga in righe:
        key = _voce_key(riga)
        if key not in existing:
            nuove.append(DiffRowOut(riga=riga, valore_precedente=None))
            continue
        valore_precedente = existing[key]
        if valore_precedente != riga.prezzo_unitario_cliente:
            modificate.append(DiffRowOut(riga=riga, valore_precedente=valore_precedente))
        # prezzo invariato: riga non riportata nel diff (nessuna azione da fare)

    return nuove, modificate


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
    — MAI un DELETE di righe assenti dal file (D-24)."""
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
        sotto = _upsert_sottocategoria(db, listino_id, riga)
        _upsert_voce(db, sotto, riga)
        righe_importate += 1

    return listino_id, righe_importate
