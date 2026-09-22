---
phase: 08-export-import-excel
plan: 03
subsystem: api
tags: [openpyxl, fastapi, sqlalchemy, pydantic, excel-roundtrip]

# Dependency graph
requires:
  - phase: 08-export-import-excel
    provides: "Shell condivisa export_excel/workbook.py (TOKEN_CANCELLA, ISTRUZIONI, timestamp B4) ed export_excel/listino.py::build_workbook_listino (piano 08-01)"
provides:
  - "Package services/import_excel/ con flat.py: lettore generico del formato piatto, riusabile dai re-import 08-04..08-08"
  - "VoceRigaIn.id/livello/campi_presenti e DiffRowOut.campi_modificati (schema esteso in modo additivo)"
  - "listino_upload_service.parse_flat_listino, risoluzione per id in compute_diff/apply_diff_idempotent, dispatch nel router POST /admin/upload-listino/preview"
  - "test_export_import_roundtrip.py: 8 test che dimostrano D-12 (round-trip a vuoto = due conteggi a zero)"
affects: [08-04, 08-05, 08-06, 08-07, 08-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "VoceRigaIn.campi_presenti: None = tutti i campi presenti (legacy parse_computo), set esplicito = solo i campi che la riga porta con se' (formato piatto) — ogni consumatore (compute_diff, applicatori id-based) ignora cio' che non vi compare (D-09/CUR-02)"
    - "Risoluzione identita': se riga.id e' valorizzato si risolve per id (vincolato al listino di destinazione, T-08-23) PRIMA della chiave naturale; id assente -> chiave naturale esistente"
    - "Placeholder mai letti: i campi assenti da una riga piatta ricevono un valore fittizio solo per soddisfare pydantic, mai scritto a database perche' escluso da campi_presenti"
    - "prezzo_unitario_cliente: Field(ge=0) sullo schema condiviso, con la regola di business 'prezzo > 0' spostata esplicitamente nei due punti che la richiedono (_sotto_dict_to_righe per ogni riga computo, parse_flat_listino per le sole righe nuove) — una riga esistente re-importata a 0 e' il suo stato reale, non un errore"

key-files:
  created:
    - backend/app/services/import_excel/__init__.py
    - backend/app/services/import_excel/flat.py
    - backend/tests/test_export_import_roundtrip.py
  modified:
    - backend/app/schemas/admin_upload.py
    - backend/app/services/listino_upload_service.py
    - backend/app/routers/admin/upload_listino.py

key-decisions:
  - "campi_presenti come set[str] | None su VoceRigaIn (non un secondo sentinella per la cancellazione): None=legacy tutti-presenti, set esplicito per il formato piatto; il valore None dentro il set gia' rappresenta #CANCELLA# per i campi nullable"
  - "Risoluzione per id bypassa completamente _upsert_sottocategoria/_upsert_voce (chiave naturale): una riga con id usa _resolve_per_id + applicatori _applica_voce/_applica_sottocategoria dedicati, cosi' un campo sottocategoria assente non rischia di far ripartire una ricerca per chiave naturale con placeholder"
  - "prezzo_unitario_cliente rilassato a ge=0 sullo schema condiviso, con la regola business (>0) riportata esplicitamente in _sotto_dict_to_righe e in parse_flat_listino (solo righe nuove) — scoperto dal test del round-trip a vuoto sul seed reale, che contiene voci a prezzo 0"

requirements-completed: [CUR-01, CUR-02]

# Metrics
duration: ~30min
completed: 2026-09-22
---

# Phase 08 Plan 03: Import Excel del listino (round-trip export -> import) Summary

**Lettore del formato piatto (`import_excel/flat.py`) e instradamento nello stesso endpoint `POST /admin/upload-listino/preview`: il file scaricato da `/admin/listini` si ricarica dal bottone "Carica file" esistente, con risoluzione per id, diff su tutti i campi e round-trip a vuoto dimostrato da 8 test che contano (D-12).**

## Performance

- **Duration:** ~30 min (dalla lettura del piano al commit finale)
- **Completed:** 2026-09-22T15:07:05+02:00
- **Tasks:** 3/3 completati
- **Files modified:** 6 (3 creati, 3 modificati)

## Accomplishments
- `import_excel/flat.py`: lettore generico del formato piatto (`e_formato_piatto`, `leggi_timestamp_export`, `leggi_foglio_piatto`, `foglio_mancante`, `RigaPiatta`) — distingue cella vuota (campo non toccato) da `#CANCELLA#` (valore `None`), non conosce il database
- Schema esteso in modo additivo: `VoceRigaIn.id`/`livello`/`campi_presenti`, `DiffRowOut.campi_modificati` — round-trip stateless del client `/confirm` invariato
- `parse_flat_listino` + risoluzione per id in `compute_diff`/`apply_diff_idempotent`: lo stesso endpoint accetta computo originale e formato piatto, un id fuori dal listino di destinazione diventa uno scarto (T-08-23), nessun `DELETE` in nessun ramo (D-10/D-24)
- `test_export_import_roundtrip.py`: 8 test che contano — round-trip a vuoto (`len(nuove)==0 and len(modificate)==0`), preservazione di tutti i campi (incluso `livello` curato), colonna assente non azzera, `#CANCELLA#` azzera solo quel campo, nessuna eliminazione su import parziale, riga senza id crea una voce nuova, id inesistente finisce negli scarti, computo originale ancora accettato via `/preview`
- Bug reale scoperto dal test del round-trip a vuoto (deviazione Rule 1, dettagliata sotto): il seed di Reggio Emilia contiene voci a prezzo 0, e il vincolo `gt=0` le trasformava sempre in scarto

## Task Commits

Ogni task committato atomicamente:

1. **Task 1: lettore del formato piatto** - `01c51a9` (feat)
2. **Task 2: risoluzione per id, diff su tutti i campi, instradamento nel router** - `f3b36ae` (feat)
3. **Task 3: il test che conta — round-trip a vuoto e non-azzeramento multi-campo** - `071540a` (test, include il fix Rule 1 sul vincolo prezzo scoperto dal test stesso)

## Files Created/Modified
- `backend/app/services/import_excel/__init__.py` - Docstring di package
- `backend/app/services/import_excel/flat.py` - Lettore del formato piatto: riconoscimento (`e_formato_piatto`), timestamp, header, token `#CANCELLA#`, scarti descritti (foglio mancante, riga vuota, id non numerico)
- `backend/app/schemas/admin_upload.py` - `VoceRigaIn.id`/`livello`/`campi_presenti` (convenzione documentata nel docstring di modulo), `DiffRowOut.campi_modificati`, `prezzo_unitario_cliente` rilassato a `ge=0`
- `backend/app/services/listino_upload_service.py` - `parse_flat_listino`, `compute_diff` esteso (risoluzione per id + scarti + diff multi-campo, ritorna 3 valori), `_resolve_per_id`/`_applica_voce`/`_applica_sottocategoria` (applicatori id-based, presence-aware), `apply_diff_idempotent` dirama sul ramo id/chiave-naturale, regola di business "prezzo>0" riportata esplicitamente in `_sotto_dict_to_righe` e nel ramo riga-nuova di `parse_flat_listino`
- `backend/app/routers/admin/upload_listino.py` - `preview_upload` carica il workbook una volta e instrada con `e_formato_piatto`; nessuna modifica al frontend
- `backend/tests/test_export_import_roundtrip.py` - 8 test (dettagliati sopra)

## Decisions Made
- `campi_presenti: set[str] | None` scelto come UNICA convenzione di presenza (non un sentinella separato per la cancellazione): `None` = comportamento legacy "tutti i campi presenti" (righe di `parse_computo`), un set esplicito per il formato piatto — un valore `None` dentro il set gia' rappresenta la richiesta di cancellazione per i campi nullable, senza bisogno di un secondo meccanismo
- Le righe con `id` valorizzato bypassano interamente `_upsert_sottocategoria`/`_upsert_voce` (chiave naturale): userebbero placeholder come chiave di ricerca se un campo sottocategoria non fosse presente nella riga, rischiando di creare sottocategorie fantasma. La risoluzione per id usa applicatori dedicati (`_applica_voce`/`_applica_sottocategoria`) che toccano solo `campi_presenti`
- `prezzo_unitario_cliente` da `gt=0` a `ge=0` sullo schema condiviso — la regola di business "un prezzo caricato da file deve essere > 0" resta intatta ma spostata a runtime nei due punti che la richiedono davvero (dettagliato in Deviazioni)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Vincolo `Field(gt=0)` su `prezzo_unitario_cliente` rompeva il round-trip a vuoto sul seed reale**
- **Found during:** Task 3, primo test (`test_roundtrip_a_vuoto_non_produce_modifiche`) — fallito su dati reali del seed di Reggio Emilia, non su un caso sintetico
- **Issue:** Il seed contiene legittimamente voci a prezzo 0 ("non ancora quotate", gia' documentato nel docstring esistente di `_sotto_dict_to_righe`). Il vincolo pydantic `Field(gt=0)` su `VoceRigaIn.prezzo_unitario_cliente` rifiutava la costruzione della riga per QUALUNQUE voce con quel prezzo, trasformandola sempre in uno scarto — anche quando il file ricaricato era identico a quello appena scaricato. Violava D-12 (round-trip a vuoto = zero scarti/modifiche) per ogni listino con almeno una voce a prezzo 0, che e' il caso reale.
- **Fix:** Vincolo rilassato a `Field(ge=0)` sullo schema condiviso; la regola di business "il prezzo caricato da un file deve essere > 0" e' stata resa esplicita a runtime nei due soli punti dove serve davvero: `_sotto_dict_to_righe` (ogni riga del formato computo, comportamento identico a prima) e `parse_flat_listino` (solo per le righe NUOVE, senza id — una riga ESISTENTE re-importata a 0 e' il suo stato reale a database, non un errore da segnalare)
- **Files modified:** backend/app/schemas/admin_upload.py, backend/app/services/listino_upload_service.py
- **Verification:** `test_roundtrip_a_vuoto_non_produce_modifiche` passa sul seed reale; l'intera suite di verifica del piano (`test_export_import_roundtrip.py`, `test_upload_listino.py`, `test_dettaglio_pro_livelli.py`, `test_export_excel_listino.py`, `test_seed.py`) resta verde — 62 test, nessuna regressione sulla regola "prezzo=0 scartato" per righe nuove del computo (`test_riga_malformata_scartata_resto_importato` ancora verde)
- **Committed in:** `071540a` (commit del Task 3)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Nessuno scope creep — il fix tocca gli stessi due file gia' dichiarati in `files_modified` del piano (schemas/admin_upload.py, listino_upload_service.py) ed e' stato scoperto e risolto interamente dentro il flusso di verifica del piano stesso (il test di Task 3 che doveva dimostrarlo).

## Issues Encountered
- Ambiente worktree: `backend/.venv` non esisteva in questo worktree (gitignored, mai creato per questo agente isolato). Creato un symlink locale a `backend/.venv` del repo principale con `ln -s` (nessun impatto sul contenuto dei commit, verificato con `git status --short`).
- Base del worktree indietro rispetto alla head attesa (`f011ed4` invece di `e44a471`) al momento dello startup: `git reset --hard` eseguito come da protocollo, prima di qualunque lettura/scrittura, nessun commit locale perso.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `services/import_excel/flat.py` e' pronto per essere riusato dai re-import dei piani 08-04..08-08 (domande, parametri, lead): stesso `e_formato_piatto`/`leggi_foglio_piatto` per ogni foglio dati, senza duplicare la logica di riconoscimento
- La convenzione `VoceRigaIn.campi_presenti` (None=tutti presenti, set esplicito=solo i reali) e' il pattern da riusare per ogni schema `*RigaIn` dei prossimi import, se seguono lo stesso bisogno di CUR-02
- Nessun blocco noto per i piani successivi della Fase 08

---
*Phase: 08-export-import-excel*
*Completed: 2026-09-22*

## Self-Check: PASSED

Tutti i file dichiarati creati/modificati esistono su disco; tutti e tre i
commit (`01c51a9`, `f3b36ae`, `071540a`) presenti in `git log --oneline`.
