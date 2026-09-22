---
phase: 08-export-import-excel
plan: 04
subsystem: api
tags: [openpyxl, fastapi, sqlalchemy, react-query, radix-dropdown-menu, radix-alert-dialog]

# Dependency graph
requires:
  - phase: 08-export-import-excel (08-01)
    provides: "Shell condivisa services/export_excel/workbook.py (ISTRUZIONI/AVVISO/build_filename/serializza), modello ExportLog con include_margine, pattern StreamingResponse+audit log, frontend scaricaExcel(path) generico"
  - phase: 08-export-import-excel (08-02)
    provides: "Sesta tab Anteprima su CoefficientiPage.tsx, moduli condivisi lib/adminCopy.ts e lib/tipoRistrutturazione.ts"
provides:
  - "GET /api/v1/admin/coefficienti/export.xlsx[?margine=true] — workbook a cinque fogli dei parametri del motore (moltiplicatori/listino_categoria/extra/coefficienti_pro/forfait_arredo)"
  - "build_workbook_parametri(db, con_margine) in backend/app/services/export_excel/parametri.py — coefficiente_impresa esiste SOLO nel ramo opt-in"
  - "Split-button 'Scarica parametri' su /admin/coefficienti con conferma ambra per la variante con margine"
  - "CRUD via export/import ora possibile su forfait_arredo (i 18 forfait, prima curabili solo dal seed, diventano un foglio Excel)"
affects: [08-06, 08-07, 08-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Anti-leak strutturale: la colonna sensibile si AGGIUNGE alla lista colonne solo nel ramo con_margine=True, mai filtrata a valle da una lista che gia' la conterrebbe — stesso principio di schemas/admin_coefficienti.py applicato a un file invece che a un Pydantic schema"
    - "AlertDialog non distruttivo in tono ambra (non variant=destructive) con autoFocus esplicito su AlertDialogCancel quando l'azione confermata espone un segreto — l'unico dialog del pannello dove Invio non deve mai confermare"
    - "Cache-Control: no-store su ogni StreamingResponse di export Excel (T-08-34), non solo sulla variante sensibile, per uniformita'"

key-files:
  created:
    - backend/app/services/export_excel/parametri.py
    - backend/tests/test_export_margine.py
  modified:
    - backend/app/routers/admin/coefficienti.py
    - frontend/src/pages/admin/CoefficientiPage.tsx

key-decisions:
  - "AlertDialogAction della variante con margine usa variant=\"outline\" (non il default primary) prima di sovrapporre le classi ambra: evita che bg-primary del variant default competa in specificita' CSS con bg-amber-bg passato via className (radix Slot concatena le classi, non le fa mergiare con tailwind-merge) — deviazione minima rispetto al testo letterale del piano, stesso risultato visivo richiesto (tono ambra, non primary/rosso)"
  - "Consulente creato nei test impostando User.role='consulente' direttamente via sessione DB dopo la registrazione, invece di passare da PATCH /admin/utenti (pattern piu' snello di test_admin_utenti.py, stesso comportamento effettivo verificato: require_admin legge il ruolo dal DB a ogni richiesta, non da un claim di sessione cacheato)"

patterns-established:
  - "Export multi-tabella con margine opt-in come contratto ripetibile: build_workbook_X(db, con_margine) + endpoint con query param + require_admin su entrambe le varianti + ExportLog.include_margine — stesso schema riusabile per un futuro export che abbia un segreto equivalente"

requirements-completed: [CUR-03]

duration: ~45min
completed: 2026-09-22
---

# Phase 08 Plan 04: Export parametri motore con margine opt-in Summary

**`GET /admin/coefficienti/export.xlsx[?margine=true]` — workbook a cinque fogli dei parametri del motore (moltiplicatori, base €/m²+IVA, extra, coefficienti Pro, forfait arredo); il coefficiente impresa esiste solo nella variante esplicitamente richiesta, marcata nel nome, aperta sul foglio AVVISO e tracciata in `export_log`.**

## Performance

- **Duration:** ~45 min
- **Completed:** 2026-09-22
- **Tasks:** 3/3 completati
- **Files modified:** 4 (2 creati, 2 modificati)

## Accomplishments
- `build_workbook_parametri()` produce cinque fogli dati (`moltiplicatori`, `listino_categoria`, `extra`, `coefficienti_pro`, `forfait_arredo`) più `ISTRUZIONI`; `coefficiente_impresa` si aggiunge alla colonna `listino_categoria` SOLO quando `con_margine=True`, mai filtrato a valle
- `GET /admin/coefficienti/export.xlsx?margine=true` dietro `require_admin`, nome file marcato (`_con-margine_`), foglio `AVVISO` in prima posizione, `Cache-Control: no-store`
- 5 test che aprono davvero il workbook con `openpyxl` (non solo status code): assenza della colonna/foglio AVVISO nel default, presenza nella variante marcata, 403 al consulente su entrambe le varianti senza scrivere log, `export_log` distingue le due varianti, conteggio righe `forfait_arredo` coincide col DB (chiude il punto aperto "nessun CRUD admin su forfait_arredo" — i 18 forfait ora escono in un file curabile)
- Split-button "Scarica parametri" su `/admin/coefficienti`: click diretto per il default, `AlertDialog` ambra con focus su "Annulla" per la variante con margine — Invio non conferma mai il download del segreto

## Task Commits

Ogni task committato atomicamente:

1. **Task 1: workbook dei parametri a cinque fogli, margine opt-in, endpoint** - `39e63a7` (feat)
2. **Task 2: il test anti-leak che apre davvero il workbook** - `a9a3396` (test)
3. **Task 3: split-button di download e conferma della variante con margine** - `c37ad65` (feat)

**Plan metadata:** committed separately by orchestrator (worktree mode — STATE.md/ROADMAP.md non toccati da questo agente)

## Files Created/Modified
- `backend/app/services/export_excel/parametri.py` - `build_workbook_parametri(db, con_margine) -> (bytes, int)`, cinque fogli, colonna margine solo nel ramo opt-in
- `backend/app/routers/admin/coefficienti.py` - `GET /export.xlsx` con query param `margine`, `require_admin`, riga `ExportLog(risorsa="parametri", include_margine=margine)`, `Cache-Control: no-store`
- `backend/tests/test_export_margine.py` - 5 test che leggono il workbook con `openpyxl`: anti-leak default, presenza colonna+AVVISO+nome nella variante marcata, 403 consulente su entrambe le varianti, distinzione delle due varianti in `export_log`, conteggio righe `forfait_arredo`
- `frontend/src/pages/admin/CoefficientiPage.tsx` - `DropdownMenu` split-button "Scarica parametri" (Scarica / Scarica con margine riservato) + `AlertDialog` ambra di conferma con `autoFocus` su Annulla; sesta tab Anteprima (08-02) invariata

## Decisions Made
Vedi `key-decisions` in frontmatter:
- `variant="outline"` esplicito su `AlertDialogAction` della variante margine, per evitare conflitto di specificità CSS tra `bg-primary` del variant default e `bg-amber-bg` passato via className (deviazione visiva minima, stesso risultato ambra richiesto dallo UI-SPEC)
- Consulente di test creato via `User.role` diretto su DB invece che via `PATCH /admin/utenti`, comportamento equivalente

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `variant="outline"` esplicito su `AlertDialogAction` della variante margine**
- **Found during:** Task 3 (split-button e AlertDialog)
- **Issue:** Il testo del piano specifica solo `className="border border-amber-border bg-amber-bg text-amber-fg hover:bg-amber-border/40"` senza `variant`, ma `AlertDialogAction` di default usa `variant="default"` (bottone `Button` con `asChild`, che applica `bg-primary` tramite `buttonVariants`). Radix `Slot` concatena le classi del `Button` e quelle passate a `AlertDialogPrimitive.Action` senza fare merge stile tailwind-merge: `bg-primary` e `bg-amber-bg` finiscono entrambe nell'attributo `class`, col rischio che l'ordine di generazione del CSS di Tailwind faccia vincere `bg-primary` invece del tono ambra richiesto dallo UI-SPEC (§B: "non va in rosso... ma in tono ambra").
- **Fix:** Aggiunto `variant="outline"` esplicito su `AlertDialogAction`, che rimuove `bg-primary` dalla classe base prima di sovrapporre le classi ambra — nessun conflitto di specificità, tono ambra garantito indipendentemente dall'ordine del CSS generato.
- **Files modified:** `frontend/src/pages/admin/CoefficientiPage.tsx`
- **Verification:** `npx tsc -b --pretty false` pulito, `npm run build` pulita; nessun acceptance criterion del piano richiede `variant` assente, tutti i grep letterali (className amber, assenza destructive) restano soddisfatti
- **Committed in:** `c37ad65` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 bug di specificità CSS)
**Impact on plan:** Nessuno scope creep — correzione di correttezza visiva minima, coerente con l'intento esplicito dello UI-SPEC (tono ambra, mai primary/rosso).

## Issues Encountered
- La base del worktree era indietro rispetto alla head attesa (`e44a471`) al momento dello startup: `git reset --hard` eseguito come da protocollo, prima di qualunque lettura/scrittura, nessun impatto sul lavoro (nessun commit locale preesistente perso).
- Nessun `backend/.venv`/`frontend/node_modules` propri nel worktree (gitignored, mai creati per questo agente isolato): creati due symlink locali (`ln -s`) al venv/node_modules del repo principale, entrambi gitignored e non tracciati — stessa soluzione già usata dal piano 08-01, nessun impatto sul contenuto dei commit.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `build_workbook_parametri()` è pronto per essere riletto dal piano 08-06 (re-import dei parametri): le colonne di contesto in sola lettura (`listino_nome`, `voce_descrizione`, `opzione_etichetta`) sono già marcate come tali per non essere reinterpretate come editabili
- Pattern "export multi-tabella con margine opt-in" riusabile identico se un futuro export dovesse esporre un altro segreto equivalente
- Nessun blocco noto per gli altri piani della Fase 08 — questo piano non condivide file con 08-03/08-05 (wave 2, esecuzione parallela)

---
*Phase: 08-export-import-excel*
*Completed: 2026-09-22*

## Self-Check: PASSED

Tutti i file dichiarati creati/modificati esistono su disco (`backend/app/services/export_excel/parametri.py`, `backend/tests/test_export_margine.py`, `backend/app/routers/admin/coefficienti.py`, `frontend/src/pages/admin/CoefficientiPage.tsx`); tutti e tre i commit (`39e63a7`, `a9a3396`, `c37ad65`) presenti in `git log --oneline`.
