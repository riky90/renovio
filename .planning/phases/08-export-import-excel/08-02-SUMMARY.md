---
phase: 08-export-import-excel
plan: 02
subsystem: ui
tags: [react, react-query, typescript, admin-panel, shadcn]

# Dependency graph
requires:
  - phase: 05-catalogo-domande-motore-free
    provides: "POST /admin/domande/anteprima gia' completo (backend/app/routers/admin/domande.py:496-581), consumato qui senza modifiche"
provides:
  - "Client tipizzato frontend/src/api/admin/anteprima.ts (calcolaAnteprima) sopra l'endpoint esistente"
  - "Sesta tab Anteprima su /admin/coefficienti: form sintetico + breakdown per categoria + tabella completa degli effetti"
  - "Moduli condivisi frontend/src/lib/tipoRistrutturazione.ts e frontend/src/lib/adminCopy.ts, deduplicati da LeadDashboardPage.tsx/CoefficientiPage.tsx"
affects: [08-export-import-excel]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Client API con normalizzazione Decimal-as-string via toNumber(), stesso pattern di api/admin/listini.ts"
    - "Form con risposteToccate ref/state per non sovrascrivere le risposte utente quando il catalogo si ricarica (stesso pattern di EstimateWizard.tsx)"
    - "Costanti di copy/label condivise estratte in frontend/src/lib/ invece di duplicate per pagina"

key-files:
  created:
    - frontend/src/api/admin/anteprima.ts
    - frontend/src/components/admin/AnteprimaTab.tsx
    - frontend/src/lib/tipoRistrutturazione.ts
    - frontend/src/lib/adminCopy.ts
  modified:
    - frontend/src/pages/admin/CoefficientiPage.tsx
    - frontend/src/pages/admin/LeadDashboardPage.tsx

key-decisions:
  - "TIPO_LABELS estratta da LeadDashboardPage.tsx in frontend/src/lib/tipoRistrutturazione.ts, come richiesto esplicitamente dal testo del piano (Task 2)"
  - "EMPTY_HEADING/EMPTY_BODY estratte da CoefficientiPage.tsx in frontend/src/lib/adminCopy.ts, come richiesto esplicitamente dal testo del piano (Task 3); SAVE_ERROR resta locale, non referenziato da questo piano"
  - "Catalogo domande caricato con tier=pro (non free): l'admin deve poter provare anche le domande riservate al Pro, che sono quelle che muovono il dettaglio (testo esplicito del piano)"
  - "domandeVisibili() applicata alla lista domande, stesso comportamento del wizard pubblico, per non mostrare campi orfani dietro un gate non soddisfatto"
  - "Tipo effetto mappato a etichetta leggibile con una tabella locale delle otto voci chiuse di services/effetti.py::TIPI_EFFETTO (il commento di DomandaField.tsx parla di 'sette tipi', ma effetti.py ne enumera otto: 4 Free + 4 Pro)"

patterns-established:
  - "Estrazione di costanti di copy duplicate in frontend/src/lib/ al primo secondo utilizzo, invece di lasciarle privatizzate per pagina"

requirements-completed: [PAR-04]

duration: 32min
completed: 2026-09-22
---

# Phase 08 Plan 02: Tab Anteprima stima (admin) Summary

**Sesta tab "Anteprima" su `/admin/coefficienti`: form sintetico (città/mq/tipo/domande) contro `POST /admin/domande/anteprima`, con breakdown per categoria e tabella completa di tutti gli effetti del catalogo (applicati e non), riusando i componenti del wizard pubblico senza clonarli.**

## Performance

- **Duration:** 32 min
- **Started:** 2026-09-22T11:48:00Z (stima)
- **Completed:** 2026-09-22T12:20:02Z
- **Tasks:** 3/3
- **Files modified:** 6 (4 creati, 2 modificati)

## Accomplishments
- Client tipizzato `calcolaAnteprima()` sopra l'endpoint gia' esistente, nessun path nuovo, nessuna modifica sotto `backend/`
- Form che riusa `CityAutocomplete`/`NumberStepper`/`DomandaField` del wizard pubblico, senza clonarli e senza campi cablati per nome
- Breakdown a card per categoria (base/totale/delta) con colore neutro, nessuna semantica positivo/negativo introdotta
- Tabella effetti che mostra **tutti** gli elementi restituiti dal server, nell'ordine del catalogo, senza filtri/paginazione/attenuazione visiva — solo il badge di stato cambia

## Task Commits

Each task was committed atomically:

1. **Task 1: client dell'anteprima e tipi** - `74882cc` (feat)
2. **Task 2: form a input sintetici della tab Anteprima** - `49284b0` (feat)
3. **Task 3: breakdown per categoria, tabella di tutti gli effetti e innesto della sesta tab** - `0430673` (feat)

**Plan metadata:** committed separately by orchestrator (worktree mode — STATE.md/ROADMAP.md non toccati da questo agente)

## Files Created/Modified
- `frontend/src/api/admin/anteprima.ts` - Tipi `AnteprimaIn`/`Anteprima`/`AnteprimaCategoria`/`EffettoTraccia` + `calcolaAnteprima()`, normalizzazione Decimal-as-string
- `frontend/src/components/admin/AnteprimaTab.tsx` - Form sintetico, breakdown per categoria, banner avvisi, tabella effetti completa
- `frontend/src/lib/tipoRistrutturazione.ts` - `TIPO_LABELS` condivisa (estratta da `LeadDashboardPage.tsx`)
- `frontend/src/lib/adminCopy.ts` - `EMPTY_HEADING`/`EMPTY_BODY` condivise (estratte da `CoefficientiPage.tsx`)
- `frontend/src/pages/admin/CoefficientiPage.tsx` - Sesta `TabsTrigger`/`TabsContent` "Anteprima", import delle costanti da `lib/adminCopy`
- `frontend/src/pages/admin/LeadDashboardPage.tsx` - Import di `TIPO_LABELS` da `lib/tipoRistrutturazione` invece della costante locale

## Decisions Made
- Vedi `key-decisions` in frontmatter. Nessuna decisione architetturale (Rule 4): tutto il lavoro era gia' interamente circoscritto dal contratto del piano e dello UI-SPEC.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - dedup esplicitamente richiesta dal piano] Estrazione di TIPO_LABELS e EMPTY_HEADING/EMPTY_BODY in moduli condivisi**
- **Found during:** Task 2 e Task 3
- **Issue:** Il testo del piano chiedeva esplicitamente di estrarre `TIPO_LABELS` (gia' privata in `LeadDashboardPage.tsx`) e `EMPTY_HEADING`/`EMPTY_BODY` (gia' private in `CoefficientiPage.tsx`) in un modulo condiviso "senza duplicarle" — questi due file non erano nella lista `files_modified` del piano.
- **Fix:** Creati `frontend/src/lib/tipoRistrutturazione.ts` e `frontend/src/lib/adminCopy.ts`; `LeadDashboardPage.tsx` e `CoefficientiPage.tsx` aggiornati per importare invece di duplicare.
- **Files modified:** `frontend/src/lib/tipoRistrutturazione.ts`, `frontend/src/lib/adminCopy.ts`, `frontend/src/pages/admin/LeadDashboardPage.tsx`, `frontend/src/pages/admin/CoefficientiPage.tsx`
- **Verification:** `npx tsc -b` pulito, `npm run build` pulita
- **Committed in:** `49284b0` (TIPO_LABELS), `0430673` (EMPTY_HEADING/EMPTY_BODY)

---

**Total deviations:** 1 auto-fix (Rule 2, richiesto esplicitamente dal testo del piano)
**Impact on plan:** Nessuno scope creep — l'estrazione era gia' istruzione letterale del piano stesso, solo i due file toccati non erano elencati in `files_modified`.

## Issues Encountered

**Conteggio letterale dell'acceptance criteria del Task 3 non torna esattamente:** il piano indica `grep -c "TabsTrigger" frontend/src/pages/admin/CoefficientiPage.tsx` deve restituire `6` dopo l'aggiunta della sesta tab. Il comando reale restituisce `7`, perche' `grep -c` conta le RIGHE con un match e la riga di `import { ..., TabsTrigger, ... }` e' gia' una riga che matcha, oltre alle sei righe `<TabsTrigger value="...">`. La sostanza dell'acceptance criteria e' comunque verificata: `grep -n "value=\"anteprima\""` restituisce le due righe attese (TabsTrigger + TabsContent) e tutte e cinque le tab preesistenti (`moltiplicatori`/`base`/`iva`/`extra`/`coeff-pro`) restano presenti e invariate. Nessuna azione correttiva necessaria: il codice e' corretto, solo il numero letterale nel testo del piano non teneva conto della riga di import.

**Nessun ambiente backend disponibile in questo worktree** (`backend/.venv` e `backend/dev.db` assenti): la verifica live a schermo richiesta dal blocco `<verification>` del piano (Reggio Emilia, 85 m², moderata, oracolo €47.985–€70.575) non e' stata eseguita in questo agente. Verificato invece con `npx tsc -b` (pulito su tutte e tre le commit) e `npm run build` (pulita, nessun errore, solo il warning pre-esistente su chunk size non correlato a questo piano). La verifica visiva in browser resta da fare dall'utente o dall'orchestratore con un ambiente backend attivo.

## User Setup Required

None - nessuna configurazione di servizio esterno richiesta.

## Next Phase Readiness
- La sesta tab e' pronta e compila; nessuna modifica sotto `backend/` (verificato con `git diff --name-only`).
- Verifica live a schermo (Reggio Emilia/85mq/moderata contro l'oracolo primario) ancora da fare con un ambiente backend attivo — vedi "Issues Encountered".
- Nessun blocco per gli altri piani della Fase 08: questo piano non condivide file con gli altri piani della wave (vedi `depends_on: []` in frontmatter).

---
*Phase: 08-export-import-excel*
*Completed: 2026-09-22*
