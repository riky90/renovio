---
phase: 08-export-import-excel
plan: 05
subsystem: api
tags: [fastapi, sqlalchemy, openpyxl, react-query, audit-log]

# Dependency graph
requires:
  - phase: 08-export-import-excel
    provides: "08-01: tabella export_log migrata (0018), shell workbook.py, ExportLogOut, scaricaExcel(path) blob generico"
provides:
  - "GET /api/v1/admin/lead/export.xlsx — export piatto dei lead, require_staff (admin+consulente), Cache-Control: no-store, riga export_log per ogni download"
  - "GET /api/v1/admin/export-log — ultimi 50 download di tutte e quattro le risorse, user_label risolto server-side"
  - "Toolbar Scarica lead + sezione Download registrati su LeadDashboardPage.tsx"
affects: [08-06, 08-07, 08-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "build_workbook_lead(db) segue lo stesso schema di build_workbook_listino: nuovo_workbook -> scrivi_foglio_dati -> serializza, con una riga ISTRUZIONI aggiuntiva scritta a mano su wb['ISTRUZIONI']['A5'] per il testo specifico della risorsa"
    - "GET /export.xlsx registrato PRIMA di GET /{lead_id} in routers/admin/lead.py: un path parameter non tipizzato a livello di route intercetta qualsiasi segmento, l'ordine di registrazione decide quale route matcha"
    - "export_log.py risolve user_label con una sola query (join ExportLog+User), mai una query per riga"

key-files:
  created:
    - backend/app/services/export_excel/lead.py
    - backend/app/routers/admin/export_log.py
    - backend/tests/test_export_lead_traccia.py
    - frontend/src/api/admin/exportLog.ts
  modified:
    - backend/app/routers/admin/lead.py
    - backend/app/routers/admin/__init__.py
    - frontend/src/pages/admin/LeadDashboardPage.tsx

key-decisions:
  - "Route GET /export.xlsx inserita fisicamente prima di GET /{lead_id} in lead.py: senza questo ordine il path 'export.xlsx' verrebbe catturato dal parametro lead_id (poi 422 sul cast a int) invece che dalla nuova route"
  - "Nel router lead.py evitata ogni occorrenza letterale della stringa 'require_admin' (anche nei commenti): l'acceptance criteria del piano verifica con un grep cieco che quella stringa non compaia nel file, quindi la spiegazione del perche' si usa require_staff e non require_admin e' stata riformulata senza nominarlo"
  - "user_label = nome se valorizzato altrimenti email: dato che User.nome e' NOT NULL a schema, in pratica e' sempre il nome; il fallback resta comunque nel codice per coerenza col contratto dichiarato in admin_export.py"

requirements-completed: [CUR-04]

# Metrics
duration: ~35min
completed: 2026-09-22
---

# Phase 08 Plan 05: Export lead tracciato + log dei download Summary

**`GET /admin/lead/export.xlsx` dietro `require_staff` (admin e consulente, D-14) con audit obbligatorio in `export_log`, `GET /admin/export-log` che espone gli ultimi 50 download di tutte e quattro le risorse, e sezione "Download registrati" in coda a `LeadDashboardPage.tsx`.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-09-22
- **Tasks:** 3/3 completati
- **Files modified:** 7 (4 creati, 3 modificati)

## Accomplishments
- `build_workbook_lead(db)` — foglio unico `lead` a 17 colonne (nessuna colonna di margine, `totale_min`/`totale_max` sono gia' prezzi cliente pubblici), ordinato per `created_at` decrescente come la dashboard; nota sui campi ricurabili dal futuro re-import scritta nel foglio `ISTRUZIONI`
- `GET /admin/lead/export.xlsx` — stesso gate `require_staff` delle altre route di `lead.py` (il consulente scarica cio' che gia' vede a schermo, D-14), `Cache-Control: no-store`, riga `export_log` scritta nella stessa richiesta prima del return, mai in un blocco che possa inghiottirla
- `GET /admin/export-log` — ultimi 50 download di tutte e quattro le risorse, join singola su `User` per `user_label`, nessun filtro per ruolo sulle righe (D-16, trasparenza reciproca)
- Dashboard lead: bottone "Scarica lead" nella toolbar header (stesso pattern di `ListiniPage.tsx`), sezione "Download registrati" con badge ambra solo quando `include_margine` e' vero

## Task Commits

Ogni task committato atomicamente:

1. **Task 1: export dei lead dietro require_staff, tracciato** - `fddef3e` (feat)
2. **Task 2: endpoint di lettura della traccia** - `16e687b` (feat)
3. **Task 3: toolbar Scarica lead e sezione Download registrati** - `a79558e` (feat)

**Plan metadata:** committed separately by orchestrator (worktree mode — STATE.md/ROADMAP.md non toccati da questo agente)

## Files Created/Modified
- `backend/app/services/export_excel/lead.py` - `build_workbook_lead(db) -> (bytes, int)`, 17 colonne, nessun campo derivato dal coefficiente impresa
- `backend/app/routers/admin/lead.py` - `GET /export.xlsx` registrata prima di `GET /{lead_id}`, `require_staff`, `no-store`, scrittura `ExportLog`
- `backend/app/routers/admin/export_log.py` - `GET /export-log`, `.limit(50)`, join `ExportLog`+`User` per `user_label`
- `backend/app/routers/admin/__init__.py` - import e `include_router(export_log.router)`, edit minimo e additivo (piano 08-04 tocca lo stesso file in parallelo)
- `backend/tests/test_export_lead_traccia.py` - 200 admin/consulente, 403 user senza riga di log, header 17 colonne, righe coincidenti col DB, `no-store`, export-log 403/ordine/limite 50/`user_label`
- `frontend/src/api/admin/exportLog.ts` - `ExportLogRow`, `getExportLog()` su `apiGet("/admin/export-log")`
- `frontend/src/pages/admin/LeadDashboardPage.tsx` - toolbar "Scarica lead", sezione "Download registrati" (colonne Data/Utente/Risorsa/Righe/Margine), `RISORSA_LABELS`, `EXPORT_ERROR`

## Decisions Made
Vedi `key-decisions` in frontmatter. Nessuna decisione architetturale (Rule 4): il piano copriva gia' interamente lo scope.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Rimossa la stringa letterale "require_admin" dalla docstring di `esporta_lead`**
- **Found during:** Task 1, dopo la prima verifica con grep
- **Issue:** La docstring iniziale spiegava la scelta di `require_staff` scrivendo per esteso "NON `require_admin`" — l'acceptance criteria del piano verifica con `grep -n "require_admin" backend/app/routers/admin/lead.py` che quella stringa non compaia affatto nel file, quindi la prosa esplicativa violava il proprio stesso contratto di verifica
- **Fix:** Riformulata la docstring senza nominare `require_admin`, mantenendo lo stesso significato ("stesso gate staff delle altre route di questo file, aperto anche al consulente")
- **Files modified:** `backend/app/routers/admin/lead.py`
- **Verification:** `grep -n "require_admin" backend/app/routers/admin/lead.py` torna vuoto; suite di test rieseguita (20 passed)
- **Committed in:** `fddef3e` (Task 1 commit, corretto prima del commit)

---

**Total deviations:** 1 auto-fixed (bug di formulazione, nessun impatto funzionale)
**Impact on plan:** Nessuno scope creep — correzione testuale interna a un commento, individuata e risolta prima del commit stesso.

## Issues Encountered

**Worktree partito da una base vecchia (`f011ed4`, commit di deploy Vercel non correlato) invece della head attesa (`e44a4715`):** `git reset --hard` eseguito come da protocollo prima di qualunque lettura/scrittura (nessun commit locale preesistente perso, working tree era pulito).

**`backend/.venv` e `frontend/node_modules` assenti in questo worktree** (gitignored, mai creati per questo agente isolato, stesso problema documentato nel piano 08-01): risolto con due symlink locali (non tracciati da git, verificato con `git status --short --ignored`) verso le cartelle del repo principale.

## User Setup Required

None - nessuna configurazione di servizio esterno richiesta.

## Next Phase Readiness
- `services/export_excel/lead.py` e `export_log.py` pronti per essere riusati/estesi dai piani 08-06/08-07/08-08 (export domande/parametri, import) senza modifiche a questo codice
- `frontend/src/api/admin/exportLog.ts` gia' pronto per essere riusato da altre pagine admin se in futuro la sezione "Download registrati" venisse duplicata altrove (oggi resta unica, in coda a `LeadDashboardPage.tsx`, per contratto UI-SPEC §D)
- Verifica manuale a schermo (bottone Scarica lead, riga di download visibile dopo ricarica) non eseguita in questo agente isolato: nessun ambiente backend con dati reali disponibile nel worktree, coerente con la limitazione gia' documentata nel piano 08-02. Verificato invece con la suite pytest completa (31 test, `test_export_lead_traccia.py`+`test_admin_lead.py`+`test_lead.py`) e `npm run build` puliti.
- Nessun blocco noto per i piani successivi della Fase 08

---
*Phase: 08-export-import-excel*
*Completed: 2026-09-22*

## Self-Check: PASSED

Tutti gli 8 file dichiarati (7 di codice + questo SUMMARY) trovati sul filesystem. Tutti e tre
i commit (`fddef3e`, `16e687b`, `a79558e`) trovati in `git log --oneline --all`.
