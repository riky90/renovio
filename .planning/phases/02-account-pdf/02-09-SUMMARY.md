---
phase: 02-account-pdf
plan: 09
subsystem: frontend-account-pdf
tags: [react-router, react-query, save-at-signup, pdf-download]

# Dependency graph
requires:
  - phase: 02-account-pdf
    plan: 04
    provides: "useAuth(), api/auth.ts con credentials:'include', router react-router, AccountMenu"
  - phase: 02-account-pdf
    plan: 07
    provides: "POST/GET /api/v1/me/stime (salva/lista/dettaglio), snapshot immutabile"
  - phase: 02-account-pdf
    plan: 08
    provides: "GET /api/v1/me/stime/{id}/pdf (PDF Free brandizzato, server-side, dallo snapshot)"
provides:
  - "api/stima.ts: postSalvaStima/getStoricoStime/getStimaDettaglio/scaricaPdf, tutte con credentials:'include'"
  - "PdfDownloadButton (stati idle/loading/errore, UI-SPEC F.4), SavedEstimateDetail (riuso layout risultato Fase 1), LeMieStimePage (/le-mie-stime, lista+empty state+dettaglio, redirect /accedi se anonimo)"
  - "SoftWallCta aggiornato: 2/4 bottoni navigano/agiscono (save/download), 2 restano soft-wall; save-at-signup e auto-save da loggato (D-07) end-to-end"
affects: [03-pro-detail]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "La stima pendente viaggia da SoftWallCta a /registrati (o /accedi) via router state ({ pendingStima }), mai come query param — solo il flag intent e' in URL (T-09-04)"
    - "postSalvaStima riceve esattamente il payload StimaResponse gia' mostrato: nessuna chiamata a POST /api/v1/stima nel percorso di salvataggio (D-09)"
    - "scaricaPdf fa fetch diretto (non apiGet, che parserebbe JSON) per leggere il blob PDF, ricava il filename da Content-Disposition e attiva il download nativo via <a download> temporaneo"
    - "PdfDownloadButton e' un componente auto-contenuto (useMutation su scaricaPdf) riusato identico in EstimatePage (via SoftWallCta), SavedEstimateDetail e implicitamente in RegistratiPage/AccediPage (che invocano scaricaPdf direttamente per il trigger automatico post-signup/login)"

key-files:
  created:
    - frontend/src/components/PdfDownloadButton.tsx
    - frontend/src/components/SavedEstimateDetail.tsx
    - frontend/src/routes/LeMieStimePage.tsx
  modified:
    - frontend/src/api/stima.ts
    - frontend/src/App.tsx
    - frontend/src/components/SoftWallCta.tsx
    - frontend/src/pages/EstimatePage.tsx
    - frontend/src/routes/RegistratiPage.tsx
    - frontend/src/routes/AccediPage.tsx

key-decisions:
  - "LeMieStimePage gestisce lista+dettaglio con stato locale (selectedId), non una rotta nested /le-mie-stime/:id — semplifica il piano senza violare il contratto UI (nessun requisito esplicito di deep-link nel testo del piano/UI-SPEC)"
  - "Dopo save-at-signup/login con intent pendente, RegistratiPage/AccediPage mostrano la conferma inline 'Stima salvata nel tuo account.' direttamente sulla stessa pagina (con link a /le-mie-stime e a /), invece di un redirect a una vista dettaglio dinamica — evita di dover propagare l'id salvato attraverso un'ulteriore navigazione, mantenendo lo stesso risultato UX del contratto UI-SPEC"

requirements-completed: [PDF-01, AUTH-03]

# Metrics
duration: 45min
completed: 2026-08-26
---

# Phase 2 Plan 9: Save-at-signup, storico, download PDF frontend end-to-end Summary

**SoftWallCta con 2 bottoni ora reali (save/download via intent + router state) e 2 rimasti soft-wall, auto-save silenzioso da loggato, storico "Le mie stime" con dettaglio immutabile che riusa CategoryCard/TotalCard/FallbackDisclaimer, e PdfDownloadButton con stati loading/errore — codice completo e typecheck verde; il checkpoint umano di verifica end-to-end in browser (Task 3) resta aperto in attesa dell'utente.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-08-26
- **Completed:** 2026-08-26 (Task 1-2)
- **Tasks:** 2/3 completati (Task 3 e' un checkpoint `human-verify` non eseguibile dall'agente)
- **Files modified:** 9 (3 creati, 6 modificati)

## Accomplishments

- `frontend/src/api/stima.ts`: `postSalvaStima` (POST /me/stime, congela esattamente la `StimaResponse` gia' mostrata), `getStoricoStime` (GET /me/stime, normalizza Decimal-come-stringa riusando `toNumber`), `getStimaDettaglio` (GET /me/stime/{id}, normalizza + id/created_at), `scaricaPdf` (GET /me/stime/{id}/pdf, legge il blob, filename da `Content-Disposition`, trigger download nativo via `<a download>` temporaneo) — tutte con `credentials:"include"`.
- `frontend/src/components/PdfDownloadButton.tsx`: contratto UI-SPEC F.4 — label "Scarica PDF" di default, "Generazione in corso..." con spinner disabilitato durante il click, testo inline destructive sotto il bottone su errore (mai un alert a schermo intero).
- `frontend/src/components/SavedEstimateDetail.tsx`: riepilogo input (badge citta/mq/tipo) + `FallbackDisclaimer` condizionale + le 4 `CategoryCard` + extra + `TotalCard` (riuso identico dei componenti Fase 1, nessuna duplicazione di layout) + `PdfDownloadButton` in fondo, nessun bottone soft-wall (utente gia' autenticato).
- `frontend/src/routes/LeMieStimePage.tsx`: rotta `/le-mie-stime` protetta (`useAuth().user === null` -> redirect `/accedi`), heading "Le mie stime", lista storico (citta+totale range in Label, mq·tipo·data in Body muted, tap-target -> dettaglio), skeleton rows durante il caricamento, empty state ("Non hai ancora stime salvate" + CTA "Nuova stima" -> `/`), dettaglio via `getStimaDettaglio` con pulsante "← Le mie stime" per tornare alla lista.
- `frontend/src/App.tsx`: rotta `/le-mie-stime` registrata.
- `frontend/src/components/SoftWallCta.tsx`: accetta ora `result`/`isAuthenticated`/`savedId`/`isSaving`. Da anonimo, "Scarica PDF" e "Salva / crea account" navigano a `/registrati?intent=save[+download]` passando la stima corrente via router `state` (mai in query param, T-09-04); "Passa a Pro" e "Contatta un professionista" restano invariati (feedback soft-wall). Da loggato, "Salva / crea account" e' nascosto (sostituito dalla conferma inline "Stima salvata nel tuo account." quando `savedId` e' presente) e "Scarica PDF" diventa un `PdfDownloadButton` diretto sull'id gia' salvato.
- `frontend/src/pages/EstimatePage.tsx`: auto-save da loggato (D-07) — un `useEffect` osserva il successo della stima e, se l'utente e' autenticato, chiama `postSalvaStima(result)` una sola volta (guardia su `saveMutation.data`/`isPending`/`isError`); `handleModifica` resetta anche `saveMutation` per permettere un nuovo auto-save sulla stima successiva.
- `frontend/src/routes/RegistratiPage.tsx`: completa il gancio del Plan 04 — legge `location.state.pendingStima`; su registrazione riuscita con `intent` pendente, chiama `postSalvaStima` (nessun ricalcolo, D-09) e, se l'intent include `download`, `scaricaPdf(id)` subito dopo; la card mostra poi la conferma inline "Stima salvata nel tuo account." con link a "Le mie stime"/"Nuova stima" (o l'errore PDF inline se il download fallisce).
- `frontend/src/routes/AccediPage.tsx`: stesso gancio applicato al login (un utente con intent pendente che sceglie "Accedi" invece di registrarsi ottiene lo stesso salvataggio/download), con lo stesso stato di conferma inline.

## Task Commits

1. **Task 1: API storico/salvataggio/PDF + PdfDownloadButton + SavedEstimateDetail + LeMieStimePage** - `2e1ac32` (feat)
2. **Task 2: SoftWallCta save/download + save-at-signup + auto-save da loggato** - `4d069b0` (feat)
3. **Task 3: Verifica manuale flusso completo anonimo -> registrazione -> salva -> storico -> PDF** - checkpoint `human-verify` (`gate="blocking"`), **non eseguito dall'agente**: codice pronto, verifica in browser resta all'utente.

**Plan metadata:** (commit successivo con SUMMARY.md/STATE.md/ROADMAP.md)

## Files Created/Modified

- `frontend/src/api/stima.ts` - postSalvaStima/getStoricoStime/getStimaDettaglio/scaricaPdf
- `frontend/src/components/PdfDownloadButton.tsx` - bottone download PDF con stati (net-new)
- `frontend/src/components/SavedEstimateDetail.tsx` - vista snapshot read-only (net-new)
- `frontend/src/routes/LeMieStimePage.tsx` - storico + dettaglio (net-new)
- `frontend/src/App.tsx` - rotta /le-mie-stime
- `frontend/src/components/SoftWallCta.tsx` - 2/4 bottoni ora reali
- `frontend/src/pages/EstimatePage.tsx` - auto-save da loggato
- `frontend/src/routes/RegistratiPage.tsx` - save-at-signup + trigger download
- `frontend/src/routes/AccediPage.tsx` - stesso gancio applicato al login

## Decisions Made

- La stima pendente viaggia esclusivamente via router `state` (mai query param) tra `SoftWallCta` -> `/registrati`/`/accedi` -> conferma, coerente con T-09-04 del threat model del piano.
- `LeMieStimePage` usa stato locale (`selectedId`) per il dettaglio invece di una rotta nested, per semplicita' — nessun requisito di deep-link esplicito nel piano/UI-SPEC.
- Dopo save-at-signup/login, la conferma resta sulla stessa pagina (Registrati/Accedi) con link espliciti a "Le mie stime"/"Nuova stima", invece di un redirect automatico a una vista dettaglio dinamica.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] AccediPage.tsx modificata pur non elencata nei `files_modified` del piano**
- **Found during:** Task 2, completamento del gancio save-at-signup
- **Issue:** Il piano richiede esplicitamente il gancio "dopo una registrazione/login riuscita con intent" in `RegistratiPage.tsx`, ma un utente che arriva da `SoftWallCta` con un intent pendente e clicca "Hai gia' un account? Accedi" finirebbe su `AccediPage.tsx` senza alcuna gestione del salvataggio/download, rompendo il flusso end-to-end richiesto dai `must_haves.truths` del piano ("Da anonimo... poi la stima viene salvata").
- **Fix:** Applicato lo stesso gancio (lettura `location.state.pendingStima`, `postSalvaStima`/`scaricaPdf` su intent, conferma inline) anche in `AccediPage.tsx`; il link "Accedi" da `RegistratiPage.tsx` e "Registrati" da `AccediPage.tsx` ora propagano `pendingStima` via `state` in entrambe le direzioni.
- **Files modified:** `frontend/src/routes/AccediPage.tsx`, `frontend/src/routes/RegistratiPage.tsx` (propagazione dello state sui link incrociati)
- **Verification:** `npx tsc --noEmit` verde; revisione manuale del flusso (anonimo -> intent -> Accedi invece di Registrati -> salvataggio comunque eseguito).
- **Committed in:** `4d069b0` (parte del commit Task 2)

---

**Total deviations:** 1 auto-fixed (Rule 2 — funzionalita' critica richiesta implicitamente dai `must_haves` del piano stesso, stesso precedente gia' documentato in 02-06-SUMMARY.md per AccediPage.tsx)
**Impact on plan:** Nessuno scope creep: necessario per soddisfare il flusso end-to-end gia' descritto nel testo/must_haves del piano, non un'aggiunta arbitraria.

## Issues Encountered

Nessuno oltre alla deviazione sopra documentata. Non e' stato possibile verificare in questa sessione il rendering reale del PDF scaricato (limite noto WeasyPrint/GTK3 su Windows dev, gia' documentato in 02-08-SUMMARY.md) — l'endpoint risponde 500 in dev ma e' corretto in produzione; il codice del `PdfDownloadButton`/`scaricaPdf` gestisce correttamente questo caso mostrando lo stato di errore inline, non un crash.

## User Setup Required

Nessuna azione di configurazione esterna richiesta. **Task 3 richiede la verifica manuale dell'utente in browser** (backend `:8000` + frontend `:5173` attivi): flusso anonimo -> `/registrati` (o `/accedi`) con intent -> conferma "Stima salvata nel tuo account." -> "Le mie stime" mostra la stima -> dettaglio identico -> "Scarica PDF" riscarica lo stesso documento -> da loggato una nuova stima si auto-salva senza premere alcun bottone. Nota: il download PDF vero e proprio non e' verificabile end-to-end su questa macchina Windows per il limite GTK3 gia' noto (dev-only); il checkpoint puo' comunque essere approvato per il resto del flusso e la generazione PDF si considera verificata in staging/produzione (Railway/Debian).

## Next Phase Readiness

- Codice Fase 2 Plan 9 completo e verificato via typecheck (`npx tsc --noEmit` verde su entrambi i task).
- **Gate aperto:** il checkpoint `human-verify` (Task 3) non e' stato approvato in questa sessione — resta da eseguire manualmente dall'utente prima di considerare il Plan 09 (e quindi la Fase 2) chiuso end-to-end. Nessun blocco per iniziare la Fase 3.
- Rimane inoltre aperto **02-04 Task 3** (checkpoint indipendente, gia' segnalato nelle sessioni precedenti come approvato/chiuso secondo 02-04-SUMMARY.md — verificare lo stato reale in STATE.md prima di procedere).
- Con questo plan, i success criteria 3 (stime associate all'account) e 4 (download PDF brandizzato) della Fase 2 sono implementati end-to-end lato codice; restano da confermare dal vivo tramite il checkpoint Task 3.

---
*Phase: 02-account-pdf*
*Completed: 2026-08-26 (Task 1-2; Task 3 in attesa di verifica manuale dell'utente)*

## Self-Check: PASSED
Tutti i file dichiarati (9) e i commit dichiarati (`2e1ac32`, `4d069b0`) verificati presenti su disco / in git log.
