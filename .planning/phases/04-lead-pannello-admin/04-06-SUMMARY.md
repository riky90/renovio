---
phase: 04-lead-pannello-admin
plan: 06
subsystem: ui
tags: [react, tanstack-query, shadcn, sonner, radix, lead-form]

# Dependency graph
requires:
  - phase: 04-lead-pannello-admin
    provides: "04-01 backend POST /api/v1/lead (login required), resolve_referente, invio email"
provides:
  - "LeadContactDialog: form contatto in dialog, prefill da account, snapshot a range read-only"
  - "api/lead.ts: postLead verso POST /lead"
  - "SoftWallCta.tsx: pulsante Contatta un professionista reale (anonimo→redirect intent-preserving, loggato→dialog)"
  - "shadcn select + sonner (Toaster montato in main.tsx)"
affects: [04-07, 04-08, 04-09, admin-lead-dashboard]

# Tech tracking
tech-stack:
  added: ["next-themes (dipendenza indiretta di shadcn sonner)", "sonner (toast)"]
  patterns:
    - "Dialog controllato open/onOpenChange con useMutation(postLead), reset dei campi alla chiusura"
    - "Guardia dominio D-22: payload/snapshot costruiti solo dai campi a range gia' su schermo (StimaResponse.input + StimaResponse.totale)"

key-files:
  created:
    - frontend/src/api/lead.ts
    - frontend/src/components/LeadContactDialog.tsx
    - frontend/src/components/ui/select.tsx
    - frontend/src/components/ui/sonner.tsx
  modified:
    - frontend/src/main.tsx
    - frontend/src/components/SoftWallCta.tsx
    - frontend/package.json
    - frontend/package-lock.json

key-decisions:
  - "Fascia oraria: select con opzioni mattina/pomeriggio/sera (UI-SPEC §A Open Question 3, discrezione planner)"
  - "Rimosso lo stato feedback soft-wall (mai piu' settato dopo il wiring reale) invece di lasciarlo come dead code"

patterns-established:
  - "LeadContactDialog come primo consumer di useMutation + toast sonner per un flusso form-in-dialog: riusabile per i futuri form admin CRUD (04-07+)"

requirements-completed: [LEAD-01]

# Metrics
duration: ~35min
completed: 2026-08-28
---

# Phase 4 Plan 06: Flusso contatto lead (LeadContactDialog) Summary

**Pulsante "Contatta un professionista" ora cablato end-to-end: dialog shadcn con form (nome/email precompilati da useAuth, telefono, preferenza radio-group, fascia oraria select, messaggio textarea) che invia POST /lead con snapshot a range, conferma inline + toast sonner; utente anonimo reindirizzato a /registrati?intent=contatta preservando la stima.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-08-28T10:05:00Z (stima)
- **Completed:** 2026-08-28T10:40:05Z
- **Tasks:** 2/2 auto eseguiti, 1 checkpoint human-verify aperto (vedi sotto)
- **Files modified:** 8

## Accomplishments
- `api/lead.ts` + `LeadContactDialog.tsx`: form contatto completo in dialog, snapshot read-only a range, stati submitting/success/error come da UI-SPEC §A
- shadcn `select` e `sonner` installati dal registry ufficiale, `<Toaster />` montato in `main.tsx`
- `SoftWallCta.tsx`: comportamento reale per anonimo (redirect intent-preserving) e loggato (apertura dialog), nessuna regressione sul ramo Pro/Free
- Guardia dominio D-22 verificata via grep anti-leak: nessun riferimento a `coefficiente_impresa`/`base_eur_mq`/`prezzo_impresa` nel client

## Task Commits

Each task was committed atomically:

1. **Task 1: shadcn select+sonner, api/lead.ts, LeadContactDialog** - `e6d273d` (feat)
2. **Task 2: Wiring SoftWallCta (anonimo redirect / loggato dialog)** - `970ab50` (feat)
3. **Fix: guardia ridondante che rompeva `tsc -b`** - `9bc3dd3` (fix, scoperto durante la build finale, Rule 1)

**Plan metadata:** (questo commit, in coda)

## Files Created/Modified
- `frontend/src/api/lead.ts` - `postLead(payload): Promise<{id:number}>` verso `POST /lead`, tipi `LeadCreateInput`/`PreferenzaContatto`/`FasciaOraria`
- `frontend/src/components/LeadContactDialog.tsx` - dialog controllato con form completo, `useMutation(postLead)`, snapshot a range, stati submitting/success/error, toast sonner
- `frontend/src/components/ui/select.tsx` - primitive shadcn ufficiale (registry, nessun gate)
- `frontend/src/components/ui/sonner.tsx` - primitive shadcn ufficiale (Toaster)
- `frontend/src/main.tsx` - montaggio `<Toaster />` a livello root
- `frontend/src/components/SoftWallCta.tsx` - `handleContattaClick` sostituisce lo stub `handleSoftWallClick`; ramo anonimo (`navigate` con `intent=contatta`) e ramo loggato (`LeadContactDialog`); rimosso lo stato `feedback` ora morto
- `frontend/package.json` / `package-lock.json` - dipendenze `sonner` + `next-themes` (indiretta, richiesta dal componente sonner shadcn)

## Decisions Made
- Fascia oraria implementata come `select` con 3 opzioni fisse (mattina/pomeriggio/sera), come da default UI-SPEC (Open Question #3, non bloccante)
- `LeadContactDialog` usa `useAuth().user` internamente per il prefill invece di ricevere `user` come prop, per coerenza con il pattern gia' usato da `RegistratiPage`/`AccediPage`
- Il redirect anonimo riusa il meccanismo generico di `RegistratiPage`/`AccediPage` (`intent` + `pendingStima`), gia' esistente e non specifico a "contatta": nessuna modifica necessaria a quelle pagine

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Guardia ridondante causava errore TS2367 solo in `tsc -b` (non in `tsc --noEmit`)**
- **Found during:** verifica finale con `npm run build` (dopo i task 1-2, il comando di verify del plan usa `npx tsc --noEmit` che non lo intercetta)
- **Issue:** `if (!formValid || preferenza === "") return;` — TypeScript, tramite control-flow analysis su condizioni aliasate (formValid dipende da `preferenzaValid = preferenza !== ""`), narrowava gia' `preferenza` a `PreferenzaContatto` dopo `!formValid`, rendendo `preferenza === ""` un confronto senza overlap → build fallita
- **Fix:** rimossa la clausola ridondante, `if (!formValid) return;` e' sufficiente e lascia a TS il narrowing corretto
- **Files modified:** `frontend/src/components/LeadContactDialog.tsx`
- **Verification:** `npm run build` (tsc -b + vite build) pulito
- **Committed in:** `9bc3dd3`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Fix necessario per la build di produzione, nessuno scope creep.

## Issues Encountered
- Il comando di `<verify>` del plan (`npx tsc --noEmit`) non usa la modalita' project-reference (`tsc -b`) usata da `npm run build`, quindi non ha intercettato l'errore di narrowing sopra. Risolto eseguendo comunque una build completa come controllo aggiuntivo prima di dichiarare il plan pronto per il checkpoint.

## OPEN CHECKPOINT — Task 3 (checkpoint:human-verify, gate="blocking")

**Non eseguito interattivamente da questo agente** (richiede avviare backend+frontend live, registrare/loggare un account reale, ispezionare i log email di sviluppo del backend — verifica visiva/funzionale che l'executor non puo' automatizzare in questo contesto). Registrato qui invece di bloccare l'esecuzione, come da istruzioni.

**Cosa verificare (dal PLAN):**
1. Avvia backend (`cd backend && uv run uvicorn app.main:app --reload`) e frontend (`cd frontend && npm run dev`).
2. Da anonimo, calcola una stima, clicca "Contatta un professionista" → deve portare a `/registrati?intent=contatta` mantenendo la stima.
3. Registrati/accedi, torna alla stima, clicca di nuovo → si apre il dialog con nome/email precompilati.
4. Compila telefono + preferenza, invia → compare "Richiesta inviata..." + toast; controlla nei log backend che l'email al referente e la conferma utente siano state loggate (dev-fallback SMTP).
5. Conferma che lo snapshot mostra solo città/mq/tipo/range (nessun prezzo impresa).

**Stato verificato automaticamente (proxy):**
- `npx tsc --noEmit` pulito, `npm run build` (tsc -b + vite build) pulito
- Backend `POST /api/v1/lead` gia' presente (router `app/routers/lead.py`, dipendenza 04-01)
- Grep anti-leak su `api/lead.ts`/`LeadContactDialog.tsx` = nessun match (D-22)
- `SoftWallCta.tsx` apre `LeadContactDialog` per loggato e naviga a `/registrati?intent=contatta` con `state.pendingStima` per anonimo (verificato via lettura codice + grep)

**Resume-signal atteso dall'orchestratore:** un umano deve eseguire i passi 1-5 sopra e scrivere "approvato" oppure descrivere i problemi riscontrati.

## User Setup Required

None - nessuna configurazione di servizio esterno richiesta (il backend usa dev-fallback SMTP gia' esistente da 04-01).

## Next Phase Readiness
- Flusso contatto lead pronto lato codice, in attesa di verifica umana interattiva (checkpoint aperto sopra)
- `LeadContactDialog` stabilisce il pattern dialog+useMutation+toast riusabile dai prossimi plan admin CRUD (04-07+)
- Nessun blocco per procedere ad altri plan della wave 2 che non dipendono da questo checkpoint

---
*Phase: 04-lead-pannello-admin*
*Completed: 2026-08-28*

## Self-Check: PASSED

All created files found on disk, all task commit hashes found in git log.
