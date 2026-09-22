---
phase: 08-export-import-excel
plan: 01
subsystem: api
tags: [openpyxl, fastapi, sqlalchemy, alembic, react-query, blob-download]

# Dependency graph
requires:
  - phase: 04-lead-pannello-admin
    provides: "CRUD listini/prezzi esistente (routers/admin/listini.py), require_admin, StreamingResponse+Content-Disposition per download file (pdf_service.py/dettaglio_pro.py)"
provides:
  - "Tabella export_log (audit chi/cosa/quando/righe/margine), migrata e applicata (0018)"
  - "Package services/export_excel/ con shell condivisa (workbook.py: ISTRUZIONI/AVVISO, #CANCELLA#, timestamp B4, build_filename, serializza)"
  - "GET /api/v1/admin/listini/{id}/export.xlsx — export piatto del listino, solo admin, con riga di audit"
  - "frontend/src/api/admin/exportExcel.ts::scaricaExcel(path) — download blob generico riusabile da ogni pagina admin"
affects: [08-02, 08-03, 08-04, 08-05, 08-06, 08-07, 08-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "services/export_excel/workbook.py come shell condivisa: ogni export della Fase 08 (domande/parametri/lead) chiama nuovo_workbook/scrivi_foglio_dati/build_filename/serializza invece di reimplementare ISTRUZIONI/AVVISO/timestamp"
    - "Decimal -> float nelle celle Excel (documentato in workbook.py), non stringa: mantiene le celle modificabili come numeri in Excel"
    - "riga export_log scritta PRIMA del return della StreamingResponse, nella stessa richiesta, mai in un try/except che la inghiotta"
    - "frontend: una sola scaricaExcel(path) generica in api/admin/exportExcel.ts, le pagine passano il proprio path invece di funzioni dedicate per risorsa"

key-files:
  created:
    - backend/app/models/export_log.py
    - backend/alembic/versions/0018_export_log.py
    - backend/app/schemas/admin_export.py
    - backend/app/services/export_excel/__init__.py
    - backend/app/services/export_excel/workbook.py
    - backend/app/services/export_excel/listino.py
    - backend/tests/test_export_excel_listino.py
    - frontend/src/api/admin/exportExcel.ts
  modified:
    - backend/app/models/__init__.py
    - backend/app/routers/admin/listini.py
    - frontend/src/api/admin/uploadListino.ts
    - frontend/src/pages/admin/ListiniPage.tsx

key-decisions:
  - "Decimal serializzato come float nelle celle (non stringa): prezzi a 2 decimali, celle restano numeriche e modificabili in Excel; round-trip esatto verificato nel piano 08-03"
  - "extractErrorDetail di uploadListino.ts esportata e generalizzata (rimosso il verbo HTTP cablato nel messaggio di fallback) per essere riusata da exportExcel.ts senza duplicare ApiError"
  - "Timestamp di generazione a coordinata fissa B4 (etichetta A4) nel foglio ISTRUZIONI, cosi' il re-import di 08-08 lo rilegge deterministicamente"

patterns-established:
  - "Pattern export Excel: nuovo_workbook(con_margine) -> scrivi_foglio_dati(...) -> build_filename(slug, con_margine) -> serializza(wb), poi ExportLog scritto prima del return"
  - "Pattern frontend download: scaricaExcel(path) generico con stato isPending su useMutation, toast di errore fisso, mai una funzione per risorsa"

requirements-completed: [CUR-01, CUR-04]

# Metrics
duration: ~25min
completed: 2026-09-22
---

# Phase 08 Plan 01: Export Excel del listino + audit dei download Summary

**Endpoint `GET /admin/listini/{id}/export.xlsx` che genera un workbook piatto (foglio ISTRUZIONI + foglio voci a 12 colonne, nessun dato di margine) e traccia ogni download in una nuova tabella `export_log`, con bottone "Scarica listino" nel pannello admin.**

## Performance

- **Duration:** ~25 min (stima da timestamp dei commit, avvio non cronometrato esplicitamente)
- **Completed:** 2026-09-22T12:26:26Z
- **Tasks:** 3/3 completati
- **Files modified:** 12 (8 creati, 4 modificati)

## Accomplishments
- Tabella `export_log` (chi/cosa/quando/righe/margine) migrata e applicata: `alembic current` a `0018 (head)`, tabella verificata via `sqlite_master`, seed intatto
- Shell del workbook condivisa (`export_excel/workbook.py`) pronta per i 4 export della Fase 08: foglio `ISTRUZIONI` con `#CANCELLA#` e timestamp a cella fissa, foglio `AVVISO` opzionale per la variante con margine
- `GET /api/v1/admin/listini/{id}/export.xlsx` — export piatto di 191 voci reali del listino RE, solo admin (403 altrimenti, senza scrivere log), ogni download riuscito registra una riga `export_log`
- Toolbar `/admin/listini` allineata al contratto UI: Scarica listino · Carica file · Aggiungi listino

## Task Commits

Ogni task committato atomicamente:

1. **Task 1: tabella export_log, migrazione 0018 e migrazione applicata** - `be8bdb6` (feat)
2. **Task 2: shell del workbook, export del listino e riga di audit** - `4a98e62` (feat)
3. **Task 3: client di download blob e bottone Scarica listino** - `38bb8b3` (feat)

## Files Created/Modified
- `backend/app/models/export_log.py` - Modello `ExportLog` (id/user_id/risorsa/righe/include_margine/created_at)
- `backend/app/models/__init__.py` - Registrazione `ExportLog` (import + `__all__`)
- `backend/alembic/versions/0018_export_log.py` - Migrazione additiva `create_table("export_log")`, applicata
- `backend/app/schemas/admin_export.py` - `ExportLogOut`, definito una volta per tutta la Fase 08
- `backend/app/services/export_excel/__init__.py` - Docstring di package, nessun import condiviso forzato
- `backend/app/services/export_excel/workbook.py` - `TOKEN_CANCELLA`, `MIME_XLSX`, `nuovo_workbook`, `scrivi_foglio_dati`, `build_filename`, `serializza`
- `backend/app/services/export_excel/listino.py` - `build_workbook_listino(db, listino_id) -> (bytes, int)`
- `backend/app/routers/admin/listini.py` - `GET /{listino_id}/export.xlsx`, scrive `ExportLog` prima della risposta
- `backend/tests/test_export_excel_listino.py` - 5 test: 200/MIME/Content-Disposition, ISTRUZIONI+#CANCELLA#+timestamp+header voci, conteggio righe vs DB, 403 senza log, riga di audit dopo download
- `frontend/src/api/admin/exportExcel.ts` - `scaricaExcel(path)` generico, blob + filename da `Content-Disposition`
- `frontend/src/api/admin/uploadListino.ts` - `extractErrorDetail` esportata e generalizzata
- `frontend/src/pages/admin/ListiniPage.tsx` - Bottone "Scarica listino" (nuovo) + rinomina "Carica listino da Excel" → "Carica file"

## Decisions Made
- `Decimal` scritto come `float` nelle celle Excel (non stringa): documentato in `workbook.py`, mantiene le celle numeriche/modificabili in Excel; il round-trip esatto e' verificato nel piano 08-03
- `extractErrorDetail` di `uploadListino.ts` esportata e generalizzata (messaggio di fallback senza verbo HTTP cablato) per essere riusata da `exportExcel.ts` senza duplicare `ApiError`
- Timestamp di generazione scritto a coordinata fissa `B4` (etichetta `A4`) nel foglio `ISTRUZIONI`, per una lettura deterministica nel re-import di 08-08

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Generalizzato il messaggio di fallback di `extractErrorDetail`**
- **Found during:** Task 3 (client di download blob)
- **Issue:** `extractErrorDetail` in `uploadListino.ts` produceva `POST ${path} fallita con status ${status}` cablato — riusarla tal quale per una `GET` (il download blob) avrebbe prodotto un messaggio che dichiara il verbo HTTP sbagliato
- **Fix:** Messaggio di fallback reso method-agnostic (`Richiesta a ${path} fallita con status ${status}`), funzione esportata e importata da `exportExcel.ts` invece di duplicare la logica
- **Files modified:** frontend/src/api/admin/uploadListino.ts, frontend/src/api/admin/exportExcel.ts
- **Verification:** `npx tsc -b --pretty false` pulito; nessun test frontend asserisce la stringa esatta del vecchio messaggio
- **Committed in:** `38bb8b3` (Task 3 commit)

**2. [Rule 3 - Blocking] Symlink locale a `.venv`/`node_modules` condivisi per eseguire test e build in questo worktree**
- **Found during:** Task 1 (setup ambiente prima della migrazione)
- **Issue:** Il worktree non ha un proprio `backend/.venv` ne' `frontend/node_modules` (entrambi gitignored, mai creati per questo agente isolato) — nessun comando del piano (`alembic`, `pytest`, `tsc`) eseguibile senza
- **Fix:** Creati due symlink locali al worktree (`backend/.venv` → venv del repo principale, `frontend/node_modules` → node_modules del repo principale), entrambi gitignored e non tracciati — nessun impatto sul contenuto del commit
- **Files modified:** nessuno (symlink fuori da git, verificato con `git status --short --ignored`)
- **Verification:** `alembic heads`/`pytest`/`tsc -b` eseguono correttamente attraverso il symlink
- **Committed in:** N/A (non tracciato da git)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Nessuno scope creep. Il fix del messaggio di errore e' una correzione di correttezza minima; il symlink e' un aggiustamento locale d'ambiente per eseguire la verifica richiesta dal piano, non tocca il contenuto dei commit.

## Issues Encountered
- La base del worktree era indietro rispetto alla head attesa (`6503b09`) al momento dello startup: `git reset --hard` eseguito come da protocollo, prima di qualunque lettura/scrittura, nessun impatto sul lavoro (nessun commit locale preesistente perso).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `services/export_excel/workbook.py` e' pronto per essere riusato dai piani 08-02..08-08 (export domande/parametri/lead, variante con margine `con_margine=True`) senza modifiche al file condiviso
- `frontend/src/api/admin/exportExcel.ts::scaricaExcel` e' pronto per essere richiamato da altre pagine admin con il proprio path, senza nuove funzioni dedicate
- `export_log`/`ExportLogOut` pronti per la sezione "Download registrati" del piano che tocca `LeadDashboardPage.tsx` (UI-SPEC §D)
- Nessun blocco noto per i piani successivi della Fase 08

---
*Phase: 08-export-import-excel*
*Completed: 2026-09-22*

## Self-Check: PASSED

Tutti i file dichiarati creati/modificati esistono su disco; tutti e quattro i commit
(`be8bdb6`, `4a98e62`, `38bb8b3`, `a96d6bd`) presenti in `git log --oneline`.
