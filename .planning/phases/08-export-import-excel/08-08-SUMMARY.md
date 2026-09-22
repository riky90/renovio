---
phase: 08-export-import-excel
plan: 08
subsystem: api
tags: [sqlalchemy, alembic, fastapi, pydantic, react-query, excel-import]

# Dependency graph
requires:
  - phase: 08-export-import-excel (08-01)
    provides: "export_excel/workbook.py::nuovo_workbook — timestamp ISO 8601 UTC in ISTRUZIONI!B4"
  - phase: 08-export-import-excel (08-03)
    provides: "import_excel/flat.py::leggi_timestamp_export — legge il timestamp, finora inconsumato"
  - phase: 08-export-import-excel (08-06)
    provides: "registro HANDLER, contratto generico DiffRigaOut/DiffPiattoOut, DiffPreviewTable.tsx condivisa"
  - phase: 08-export-import-excel (08-07)
    provides: "handler lead, permesso per risorsa"
provides:
  - "updated_at su Sottocategoria/Voce/CoefficienteQuantitaVoce/Moltiplicatore/Extra/Categoria/ListinoCategoria/ForfaitArredo/Lead — server_default+onupdate=func.now(), migrazione 0019"
  - "services/import_excel/registry.py::riga_modificata_dopo_export(esistente, generato_il) — helper condiviso da parametri.py/lead.py/listino_upload_service.py, confronto naive->aware, mai un'eccezione"
  - "DiffRigaOut.riga_modificata_dopo_export / DiffRowOut.riga_modificata_dopo_export — campo additivo, default False"
  - "DiffPreviewOut.generato_il — equivalente di DiffPiattoOut.generato_il per il percorso /upload-listino"
  - "DiffPreviewTable.tsx: badge ambra 'Cambiata dopo l'export' + banner riassuntivo, Conferma import mai bloccato"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Helper di staleness centralizzato in registry.py (non duplicato in ogni handler): legge updated_at dall'oggetto ORM gia' caricato dal resolver per il diff (T-08-72, zero query aggiuntive per riga), normalizza naive->aware assumendo UTC (stesso pattern di dependencies/auth.py::get_current_user), None su esistente O generato_il produce sempre False (T-08-71, mai un'eccezione)"
    - "Il flag e' scritto SOLO nel ramo diff dei tre percorsi (parametri.py, lead.py, listino_upload_service.compute_diff), mai letto in nessun apply/apply_diff_idempotent: verificato meccanicamente con grep, non a occhio"

key-files:
  created:
    - backend/alembic/versions/0019_updated_at_curatela.py
    - backend/tests/test_import_stale.py
  modified:
    - backend/app/models/dettaglio_pro.py
    - backend/app/models/catalogo.py
    - backend/app/models/listino.py
    - backend/app/models/arredo.py
    - backend/app/models/lead.py
    - backend/app/schemas/admin_import.py
    - backend/app/schemas/admin_upload.py
    - backend/app/services/import_excel/registry.py
    - backend/app/services/import_excel/parametri.py
    - backend/app/services/import_excel/lead.py
    - backend/app/services/listino_upload_service.py
    - backend/app/routers/admin/import_excel.py
    - backend/app/routers/admin/upload_listino.py
    - frontend/src/api/admin/importExcel.ts
    - frontend/src/api/admin/uploadListino.ts
    - frontend/src/components/admin/DiffPreviewTable.tsx
    - frontend/src/components/admin/FlatImportDialog.tsx
    - frontend/src/components/admin/ExcelUploadDialog.tsx

key-decisions:
  - "Migrazione 0019 con nove op.add_column/op.drop_column letterali (non un loop), per soddisfare l'acceptance criterion meccanico grep -c == 9 su entrambe le funzioni"
  - "riga_modificata_dopo_export calcolato SOLO nel ramo 'modificate' di ogni diff: il ramo 'nuova' non ha un esistente con cui confrontare updated_at, resta sempre False per costruzione (nessun caso speciale da scrivere)"
  - "DiffPreviewOut (percorso /upload-listino) riceve generato_il come campo NUOVO, a differenza di DiffPiattoOut che lo aveva gia' da 08-06 — colmato il buco per rendere il banner disponibile identico su entrambi i dialog"
  - "ExcelUploadDialog.tsx risultava gia' privo dei tre hex ambra cablati (#FCD34D/#FFFBEB/#B45309) citati dal piano/UI-SPEC: verificato con grep prima di agire, nota gia' stale rispetto al codice reale (probabilmente sistemata durante 08-06) — nessuna azione necessaria su quel punto"

requirements-completed: [CUR-01]

duration: ~70min
completed: 2026-09-22
---

# Phase 08 Plan 08: Guardia di staleness sull'import Excel (D-11) Summary

**`updated_at` sulle nove tabelle curate (migrazione 0019, server_default all'istante della migrazione) e confronto con il timestamp di generazione del file: ogni riga del diff import che e' stata modificata a database DOPO l'export porta ora `riga_modificata_dopo_export`, mostrato come badge ambra + banner riassuntivo nella preview condivisa — mai un blocco duro, la decisione resta dell'admin.**

## Performance

- **Duration:** ~70 min (dalla lettura del piano al commit finale)
- **Completed:** 2026-09-22
- **Tasks:** 3/3 completati
- **Files modified:** 20 (2 creati, 18 modificati)

## Accomplishments

- **Migrazione 0019**: `updated_at` (`server_default=func.now()`, `onupdate=func.now()`) su `Sottocategoria`/`Voce`/`CoefficienteQuantitaVoce` (`dettaglio_pro.py`), `Moltiplicatore`/`Extra`/`Categoria` (`catalogo.py`), `ListinoCategoria` (`listino.py`), `ForfaitArredo` (`arredo.py`), `Lead` (`lead.py`) — nove `add_column` additivi, applicata (`alembic current` → `0019 (head)`), righe esistenti popolate all'istante della migrazione (anteriore a qualunque export futuro: il primo re-import non marca tutto come superato, verificato dal test 1 del piano stesso)
- **Helper condiviso** `registry.py::riga_modificata_dopo_export(esistente, generato_il)`: legge `updated_at` dall'oggetto ORM gia' caricato dal resolver (zero query aggiuntive per riga, T-08-72), normalizza naive→aware assumendo UTC (stesso pattern di `dependencies/auth.py`), `None` su uno dei due argomenti produce sempre `False` senza eccezioni (T-08-71)
- `DiffRigaOut`/`DiffRowOut` estesi in modo additivo (`riga_modificata_dopo_export: bool = False`); `DiffPreviewOut` (percorso `/upload-listino`) guadagna `generato_il`, equivalente di `DiffPiattoOut.generato_il` gia' esistente
- `parametri.py`, `lead.py` (via `ImportHandler.diff`) e `listino_upload_service.compute_diff` calcolano il flag SOLO nel ramo "modificate" — verificato meccanicamente che nessun `apply`/`apply_diff_idempotent` lo legga (grep, non ispezione)
- Frontend: `DiffPreviewTable.tsx` mostra un secondo badge ambra "Cambiata dopo l'export" (gap-1 con "Modificata") e un banner riassuntivo con conteggio + data export, visibile solo se almeno una riga e' stale; "Conferma import" resta sempre abilitato — D-11 ha scartato il blocco duro, l'implementazione non lo reintroduce
- 4 test in `test_import_stale.py`: riga marcata con conteggio esatto (una riga stale + una modificata-ma-non-stale, verificato che siano esattamente 1), file senza timestamp che non marca nulla, `/confirm` non bloccato da un avviso, stesso comportamento sul percorso `/upload-listino` separato

## Task Commits

Ogni task committato atomicamente:

1. **Task 1: updated_at sulle tabelle curate, migrazione 0019 applicata** - `8368c9c` (feat)
2. **Task 2: marcatura riga per riga delle righe superate** - `4895dd4` (feat)
3. **Task 3: badge ambra e banner nella preview condivisa** - `e5b03b5` (feat)

**Plan metadata:** committed separately by orchestrator (worktree mode — STATE.md/ROADMAP.md non toccati da questo agente)

## Files Created/Modified

- `backend/alembic/versions/0019_updated_at_curatela.py` - Nove `add_column`/`drop_column` espliciti (non un loop, per il criterio grep meccanico)
- `backend/app/models/{dettaglio_pro,catalogo,listino,arredo,lead}.py` - `updated_at` sulle nove classi curate
- `backend/app/schemas/admin_import.py` / `admin_upload.py` - `riga_modificata_dopo_export` additivo; `DiffPreviewOut.generato_il` nuovo
- `backend/app/services/import_excel/registry.py` - Helper `riga_modificata_dopo_export()`, `ImportHandler.diff` esteso con `generato_il`
- `backend/app/services/import_excel/parametri.py` / `lead.py` - Consumano il helper nel ramo modificate
- `backend/app/services/listino_upload_service.py` - `compute_diff` esteso con `generato_il`
- `backend/app/routers/admin/import_excel.py` / `upload_listino.py` - Leggono `leggi_timestamp_export(wb)` e lo passano al diff
- `backend/tests/test_import_stale.py` - 4 test (dettagliati sopra)
- `frontend/src/api/admin/importExcel.ts` / `uploadListino.ts` - Tipi client estesi
- `frontend/src/components/admin/DiffPreviewTable.tsx` - Badge + banner
- `frontend/src/components/admin/FlatImportDialog.tsx` / `ExcelUploadDialog.tsx` - Mapping `staleAfterExport`/`generatoIl`

## Decisions Made

Vedi `key-decisions` in frontmatter — sintesi:
- Migrazione con nove chiamate letterali invece di un loop, per il criterio d'uscita meccanico del piano
- Flag calcolato solo nel ramo "modificate" (il ramo "nuova" non ha un `esistente` con cui confrontare)
- `DiffPreviewOut.generato_il` aggiunto ex novo (mancava, a differenza di `DiffPiattoOut`)
- Nessuna azione sugli hex ambra in `ExcelUploadDialog.tsx`: gia' migrati ai token da un piano precedente della fase, verificato con grep prima di agire invece di assumere lo stato descritto dal piano

## Deviations from Plan

Nessuna deviazione Rule 1-4: il piano descriveva alcuni hex ambra cablati residui in `ExcelUploadDialog.tsx` (citati sia nel testo del piano che in `08-PATTERNS.md`/UI-SPEC) che in realta' non esistevano piu' nel codice al momento dell'esecuzione — verificato con `grep -rn "#FCD34D\|#FFFBEB\|#B45309" frontend/src/` (zero risultati) prima di modificare qualunque file, invece di assumere la descrizione del piano. Nessuna azione necessaria, nessun file toccato per questo punto specifico.

## Known Limitations

- Verifica manuale a schermo (badge ambra + banner con un file davvero superato) non eseguita in questo agente isolato: nessun ambiente backend con dati reali/browser disponibile nel worktree, coerente con la limitazione gia' documentata nei piani precedenti della fase (08-06, 08-07). Verificato invece con: 4 test pytest dedicati che contano (incluso il conteggio esatto "una riga marcata, le altre no"), suite completa 517 passed/5 skipped (era 513/5 prima di questo piano — le sole 4 differenze sono i nuovi test), `npx tsc -b` pulito.

## Issues Encountered

- Worktree partito da una base indietro rispetto alla head attesa (`f011ed4` invece di `44195d6`): `git reset --hard 44195d6...` eseguito come da protocollo prima di qualunque lettura/scrittura, working tree pulito, nessun commit locale perso.
- `backend/.venv`/`frontend/node_modules` assenti in questo worktree (gitignored): risolto con due symlink locali verso le cartelle del repo principale, stessa soluzione dei piani precedenti della fase, nessun impatto sul contenuto dei commit (verificato con `git status --short` prima di ogni commit).

## User Setup Required

None - nessuna configurazione di servizio esterno richiesta.

## Next Phase Readiness

- **Fase 08 completa: 8/8 piani.** Nessun piano successivo dipende da questo (`affects: []`) — e' l'ultimo anello della guardia D-11 avviata da 08-01 (timestamp scritto) e 08-03 (timestamp letto, finora inconsumato).
- Suite completa verde (517 passed/5 skipped), nessuna regressione sui piani precedenti della fase (import parametri/lead, round-trip listino).
- Ventotto+ commit restano in attesa di push su questo progetto (vedi STATE.md): il push a `main` e la migrazione 0019 su Render restano a fine milestone, come da nota di ambiente del `CLAUDE.md` di progetto.

---
*Phase: 08-export-import-excel*
*Completed: 2026-09-22*
