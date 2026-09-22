---
phase: 08-export-import-excel
plan: 06
subsystem: api
tags: [openpyxl, fastapi, sqlalchemy, pydantic, react-query, excel-import]

# Dependency graph
requires:
  - phase: 08-export-import-excel (08-03)
    provides: "services/import_excel/flat.py: e_formato_piatto, leggi_timestamp_export, leggi_foglio_piatto, TOKEN_CANCELLA riesportato"
  - phase: 08-export-import-excel (08-04)
    provides: "services/export_excel/parametri.py::build_workbook_parametri — header esatti dei cinque fogli, colonne di contesto in sola lettura"
provides:
  - "Percorso di import generico per risorsa: POST /admin/import-excel/{risorsa}/preview|confirm, registro HANDLER (services/import_excel/registry.py), unico punto di estensione per 08-07/08-08"
  - "Handler parametri (services/import_excel/parametri.py): re-importa i cinque fogli di 08-04 con risoluzione per id, nessuna eliminazione, coefficiente_impresa scritto solo se presente E is_admin"
  - "FlatImportDialog.tsx: dialog di import a tre passi senza passo destinazione, riusabile dalle risorse successive"
  - "DiffPreviewTable.tsx: tabella di preview del diff estratta da ExcelUploadDialog, condivisa"
  - "leggi_foglio_piatto(..., id_numerico=False): supporto a PK testuali (Extra.code) nel lettore generico del formato piatto"
affects: [08-07, 08-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Registro HANDLER[risorsa] -> ImportHandler come unico punto di estensione: risolvi_handler solleva RisorsaImportSconosciuta (mai getattr/costruzione dinamica di nome modulo su input utente, T-08-52)"
    - "Risoluzione a Risoluzione (dataclass): ogni foglio ha un _risolvi_* che ritorna scarto | esistente+campi_aggiornati | valori_creazione, riusato identico da diff() (sola lettura) e apply() (scrittura, ririsolve sempre — round-trip stateless, mai fidarsi del diff precedente)"
    - "Scrittura del margine isolata in due sole funzioni is_admin-gated (_forse_aggiungi_margine/_forse_aggiorna_margine): il resolver LEGGE coefficiente_impresa solo per l'anteprima del diff, non lo scrive mai — le uniche scritture restano nei due punti dedicati"
    - "Valori nativi (non stringificati a mano) in DiffRigaOut.valori_nuovi/precedenti: pydantic serializza Decimal come stringa di default (stesso pattern del resto del progetto), un bool stringificato a mano si romperebbe al round-trip (bool(\"False\") == True in Python)"

key-files:
  created:
    - backend/app/schemas/admin_import.py
    - backend/app/services/import_excel/registry.py
    - backend/app/services/import_excel/parametri.py
    - backend/app/routers/admin/import_excel.py
    - backend/tests/test_import_parametri.py
    - frontend/src/api/admin/importExcel.ts
    - frontend/src/components/admin/DiffPreviewTable.tsx
    - frontend/src/components/admin/FlatImportDialog.tsx
  modified:
    - backend/app/services/import_excel/flat.py
    - backend/app/routers/admin/__init__.py
    - frontend/src/components/admin/ExcelUploadDialog.tsx
    - frontend/src/pages/admin/CoefficientiPage.tsx

key-decisions:
  - "leggi_foglio_piatto esteso con id_numerico=False (Rule 3, blocking): Extra.code e' una PK testuale ('CSE_CSP', 'pratiche'), forzare int() l'avrebbe scartata SEMPRE come 'id non numerico' — senza questa modifica il foglio extra sarebbe stato impossibile da re-importare"
  - "Il diff mostra coefficiente_impresa in sola lettura (margine_preview su _Risoluzione) anche se il resolver non lo scrive mai: senza questo, un client che ricostruisce RigaPiattaIn da valori_nuovi non avrebbe mai potuto proporre il cambio margine in preview, pur potendolo applicare — scoperto dal test 3 (con margine)"
  - "extra: una riga senza id e' uno scarto, non un record nuovo (D-04 non si applica): a differenza di moltiplicatori/listino_categoria (chiave naturale composta disponibile), Extra.code E' l'id — non esiste un modo di assegnare un codice a un extra mai visto senza una colonna dedicata che il foglio non ha"
  - "Creazione di una riga listino_categoria nuova SENZA coefficiente_impresa nel file: la colonna e' NOT NULL, quindi senza margine (o senza is_admin) la riga non si crea — limite noto, non esercitato dagli 8 test del piano (che modificano righe esistenti, sempre presenti dal seed)"

patterns-established:
  - "Import generico per risorsa: {risorsa} nel path, dispatch via registro, mai una route per risorsa — 08-07/08-08 aggiungono una voce a HANDLER, non un nuovo router"
  - "DiffPreviewTable component condiviso fra i dialog di import: un futuro badge di stato si scrive in un posto, non in due copie che divergono"

requirements-completed: [CUR-01, CUR-02, CUR-03]

duration: ~55min
completed: 2026-09-22
---

# Phase 08 Plan 06: Import Excel dei parametri del motore Summary

**Percorso di import generico per risorsa (`POST /admin/import-excel/{risorsa}/preview|confirm`, registro `HANDLER`) con il primo handler completo — i cinque fogli dei parametri del motore (moltiplicatori, listino_categoria, extra, coefficienti_pro, forfait_arredo) re-importabili con risoluzione per id, nessuna eliminazione, e `coefficiente_impresa` scritto solo se presente nel file E l'utente e' admin.**

## Performance

- **Duration:** ~55 min (dalla lettura del piano al commit finale)
- **Completed:** 2026-09-22
- **Tasks:** 3/3 completati
- **Files modified:** 12 (8 creati, 4 modificati)

## Accomplishments
- `services/import_excel/registry.py`: `HANDLER` come unico punto di estensione, `risolvi_handler` risponde 404 descritto su risorsa sconosciuta — nessuna costruzione dinamica di nome modulo/`getattr` su input utente (T-08-52)
- `services/import_excel/parametri.py`: handler completo dei cinque fogli — risoluzione per id prima della chiave naturale (D-03), riga senza id crea un record nuovo tranne per le coppie vincolate moltiplicatori/listino_categoria (che richiedono entrambi i codici padre), `#CANCELLA#` ammesso solo sulle tre colonne nullable di `coefficienti_pro`, zero `db.delete` nel file, `iva_pct` scritto su `Categoria` non su `ListinoCategoria`
- **Il punto che conta di piu'**: `coefficiente_impresa` si scrive SOLO nelle due funzioni `_forse_aggiungi_margine`/`_forse_aggiorna_margine`, entrambe dietro `is_admin` — un file di default (senza quella colonna) non azzera mai il margine, provato da `test_file_senza_margine_non_azzera_il_coefficiente` che confronta TUTTI i coefficienti prima/dopo, non solo uno
- `routers/admin/import_excel.py`: due route generiche, `validate_upload`+`zip_error_types` prima di `load_workbook` (D-20), file del computo originale rifiutato con 400 descritto (ha il suo endpoint dedicato)
- 8 test che contano in `test_import_parametri.py`: round-trip a vuoto sui cinque fogli, file senza margine che non lo azzera, file con margine che lo aggiorna, modifica moltiplicatore via Excel, nessuna eliminazione su import parziale, forfait arredo modificabile (chiude il buco storico — 18 forfait prima curabili solo dal seed), 403 non-admin, file del computo rifiutato
- Frontend: `FlatImportDialog` (tre passi, senza passo destinazione) + `DiffPreviewTable` (estratta e condivisa con `ExcelUploadDialog`, token ambra invece di hex cablati) + bottone "Carica file" su `/admin/coefficienti`

## Task Commits

Ogni task committato atomicamente:

1. **Task 1: handler dei parametri e registro degli import** - `04f3f9e` (feat)
2. **Task 2: endpoint generico di import e test che contano** - `03c4ec4` (feat)
3. **Task 3: dialog di import del formato piatto e bottone Carica file** - `7625f17` (feat)

**Plan metadata:** committed separately by orchestrator (worktree mode — STATE.md/ROADMAP.md non toccati da questo agente)

## Files Created/Modified
- `backend/app/schemas/admin_import.py` - Contratto generico `RigaPiattaIn`/`DiffRigaOut`/`DiffPiattoOut`/`ConfirmPiattoIn`, riusabile da ogni risorsa importabile
- `backend/app/services/import_excel/registry.py` - `HANDLER`, `registra`, `risolvi_handler`, `RisorsaImportSconosciuta`
- `backend/app/services/import_excel/parametri.py` - Handler dei cinque fogli parametri: resolver per foglio, `parse`/`diff`/`apply`, scrittura del margine isolata e is_admin-gated
- `backend/app/services/import_excel/flat.py` - `leggi_foglio_piatto(..., id_numerico=False)` per PK testuali (deviazione Rule 3)
- `backend/app/routers/admin/import_excel.py` - `POST /{risorsa}/preview` e `/confirm`, dispatch via registro
- `backend/app/routers/admin/__init__.py` - Subrouter registrato
- `backend/tests/test_import_parametri.py` - 8 test (dettagliati sopra)
- `frontend/src/api/admin/importExcel.ts` - Client `previewImport`/`confirmImport`
- `frontend/src/components/admin/DiffPreviewTable.tsx` - Tabella di preview condivisa, estratta da `ExcelUploadDialog`
- `frontend/src/components/admin/FlatImportDialog.tsx` - Dialog a tre passi senza passo destinazione
- `frontend/src/components/admin/ExcelUploadDialog.tsx` - Usa `DiffPreviewTable` invece della tabella inline
- `frontend/src/pages/admin/CoefficientiPage.tsx` - Bottone "Carica file", invalidazione delle cinque query tab a import riuscito

## Decisions Made
Vedi `key-decisions` in frontmatter — sintesi:
- `id_numerico=False` aggiunto a `leggi_foglio_piatto` per il foglio `extra` (PK testuale `Extra.code`)
- Il diff mostra il margine in sola lettura (`margine_preview`), la scrittura resta isolata e is_admin-gated in `apply()`
- Riga `extra` senza id e' uno scarto (non un record nuovo): il codice E' l'identita', non esiste chiave naturale alternativa
- Valori nativi (non stringificati) in `DiffRigaOut`: evita il bug `bool("False") == True`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `leggi_foglio_piatto` forzava `int(id)` su ogni foglio, rompendo il foglio `extra`**
- **Found during:** Task 1, progettazione del resolver `extra`
- **Issue:** `Extra.code` (es. `"CSE_CSP"`, `"pratiche"`) e' la colonna `id` del foglio `extra` nell'export (08-04). `leggi_foglio_piatto` (08-03) tentava sempre `int(id_raw)`, che avrebbe scartato OGNI riga del foglio con "id non numerico" — il foglio sarebbe stato impossibile da re-importare.
- **Fix:** Aggiunto il parametro `id_numerico: bool = True` a `leggi_foglio_piatto`; quando `False`, `RigaPiatta.id` resta la stringa grezza. L'handler parametri lo passa `False` solo per il foglio `extra`.
- **Files modified:** `backend/app/services/import_excel/flat.py`
- **Verification:** `test_import_parametri.py` (8/8 verdi, inclusi i test che esercitano il foglio extra indirettamente tramite round-trip); `test_export_import_roundtrip.py`/`test_upload_listino.py` (consumatori esistenti di `leggi_foglio_piatto` con `id_numerico` default) restano verdi
- **Committed in:** `04f3f9e` (Task 1)

**2. [Rule 1 - Bug] Il diff non mostrava mai il cambio di `coefficiente_impresa`, e i valori venivano stringificati a mano**
- **Found during:** Task 2, `test_file_con_margine_aggiorna_il_coefficiente`
- **Issue:** Il resolver `_risolvi_listino_categoria` non calcolava mai un cambiamento sul margine (disegno originale: nessuna scrittura al di fuori delle due funzioni is_admin-gated significava anche nessuna visibilita' in preview) — un client che ricostruisce `RigaPiattaIn` da `DiffRigaOut.valori_nuovi` non avrebbe mai potuto proporre il cambio margine in `/confirm`, pur essendo autorizzato a farlo. Inoltre `valori_nuovi`/`valori_precedenti` stringificavano ogni valore con `str(v)`: `str(False)` = `"False"`, e `bool("False")` in Python e' `True` — un bool cambiato via Excel sarebbe tornato sempre `True` dopo il round-trip client.
- **Fix:** Aggiunto `margine_preview` a `_Risoluzione` (letto dal resolver per la sola anteprima, mai scritto da qui — le due funzioni `_forse_aggiungi_margine`/`_forse_aggiorna_margine` restano l'unico punto di scrittura, is_admin-gated); rimossa la stringificazione manuale, i dict passano valori nativi (Decimal/bool/int/str) che pydantic serializza correttamente.
- **Files modified:** `backend/app/services/import_excel/parametri.py`
- **Verification:** Tutti gli 8 test di `test_import_parametri.py` verdi, incluso il test 3 (margine) che prima falliva su entrambi i sintomi
- **Committed in:** `03c4ec4` (Task 2)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Entrambi i fix erano necessari per la correttezza del round-trip stateless dichiarato dal piano stesso (il client re-invia `valori_nuovi`); nessuno scope creep, tocca solo i file gia' dichiarati o strettamente collegati (`flat.py`, riusato da 08-03).

## Known Limitations

- Creare una riga `listino_categoria` NUOVA (nessuna corrispondenza per id/chiave naturale) richiede che il file contenga `coefficiente_impresa` (colonna `NOT NULL`) E che l'utente sia admin — senza, la riga non si crea silenziosamente (nessuno scarto restituito da `apply()`, che non riporta scarti per protocollo). Non esercitato dagli 8 test del piano, che modificano sempre righe esistenti dal seed. Il caso reale (aggiungere una nuova categoria a un listino) resta gestibile via CRUD (`/admin/listini`).
- La risoluzione per chiave naturale senza `id` (moltiplicatori/listino_categoria) richiede che il file porti i codici della coppia (`tipo_code`+`categoria_code` o `listino_id`+`categoria_code`) anche per una riga di sola modifica: se un admin svuota manualmente la cella `id` di una riga esistente MA il file non porta anche quei codici (perche' non cambiati), la riga si ririsolve correttamente solo se i codici sono comunque presenti nel file scaricato (lo sono sempre, dato che l'export li scrive sempre) — nessun impatto nel flusso normale download→modifica→ricarica.

## Issues Encountered
- Worktree partito da una base indietro rispetto alla head attesa: `git reset --hard fd3c8ec...` eseguito come da protocollo prima di qualunque lettura/scrittura.
- Nessun `backend/.venv`/`frontend/node_modules` propri nel worktree (gitignored): creati due symlink locali (`ln -s`) al venv/node_modules del repo principale, stessa soluzione dei piani precedenti della fase, nessun impatto sul contenuto dei commit (verificato con `git status --short`).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Il registro `HANDLER`/`risolvi_handler` e l'endpoint generico sono pronti per 08-07 (import lead): aggiungere una voce al registro, non una route
- `FlatImportDialog`/`DiffPreviewTable` sono pronti per essere riusati identici dalla risorsa successiva
- Il piano 08-08 (guardia stale su `updated_at`) puo' aggiungere il badge "Cambiata dopo l'export" in `DiffPreviewTable.tsx`, un punto solo
- Nessun blocco noto per i piani successivi della Fase 08

---
*Phase: 08-export-import-excel*
*Completed: 2026-09-22*
