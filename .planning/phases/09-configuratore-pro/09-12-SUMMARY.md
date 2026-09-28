---
phase: 09-configuratore-pro
plan: 12
subsystem: ui
tags: [react, react-router, wizard, configuratore-pro]

requires:
  - phase: 09-configuratore-pro
    provides: "wizard Pro con pavimento nello step 4, risposteDiPartenza/stepIniziale (09-11)"
provides:
  - "CtaDettaglioPro (home) trasporta citta'/mq/tipo/risposte/destinazione a /nuova-stima, mai piu' un modulo vergine"
  - "NuovaStimaProPage legge history.state con datiDaStato() (validato, T-09-51) e apre il wizard su 'Le finiture' quando ha gia' le risposte"
  - "'Rifai in versione Pro' (Le mie stime) punta a /nuova-stima invece che alla home"
  - "DettaglioProView: pavimento (e ogni domanda a scelta) sempre visibile, ricalcolo immediato al cambio, nessun invio concorrente"
affects: [09-13, 09-14]

tech-stack:
  added: []
  patterns:
    - "datiDaStato(): stesso principio di inizialiDaQuery() ma su history.state invece che query string — qualunque valore fuori forma scarta l'intero campo, mai una riparazione parziale"

key-files:
  created: []
  modified:
    - frontend/src/pages/EstimatePage.tsx
    - frontend/src/pages/NuovaStimaProPage.tsx
    - frontend/src/routes/LeMieStimePage.tsx
    - frontend/src/components/DettaglioProView.tsx

key-decisions:
  - "Guardia anti-invio-concorrente in handleSceltaChange (no-op se risposteMutation.isPending) invece di disabilitare i singoli OptionCard: DomandaField non espone una prop disabled, e il guard a monte copre lo stesso rischio (T-09-52) senza toccare un componente condiviso con il wizard"

patterns-established: []

requirements-completed: [WIZ-04, CFG-01]

duration: 45min
completed: 2026-09-28
---

# Phase 09 Plan 12: Percorso Pro senza modulo vergine (gap G3, parte percorso e dettaglio) Summary

**"Vai alla stima Pro" e "Rifai in versione Pro" ora trasportano i dati della stima appena calcolata invece di riportare a un form vuoto, e nel dettaglio Pro il pavimento si vede e si cambia senza mai premere "Modifica".**

## Performance

- **Duration:** ~45 min
- **Tasks:** 2/2 completati
- **Files modified:** 4

## Accomplishments
- `CtaDettaglioPro` (home) naviga a `/nuova-stima?citta=...&mq=...&tipo=...` portando risposte e destinazione in `history.state`; `NuovaStimaProPage` li legge con `datiDaStato()` (validazione di forma, T-09-51: qualunque valore inatteso scarta l'intero campo) e apre il wizard direttamente sullo step "Le finiture" (`stepIniziale=4`) quando le risposte sono presenti.
- "Rifai in versione Pro" da Le mie stime punta ora a `/nuova-stima` (prima portava alla home, che ignorava i parametri).
- Nel dettaglio Pro le domande a scelta (pavimento incluso) sono uscite dal ramo `domandeCollassate ? ... : ...`: si vedono sempre nel pannello "Qualche dettaglio in piu'", e un cambio ricalcola subito (`risposteMutation.mutate`), con spinner "Ricalcolo in corso…" e nessun invio concorrente.
- Il riepilogo collassato e il comportamento di "Calcola il dettaglio"/"Salta" restano invariati.

## Task Commits

1. **Task 1: I dati della stima viaggiano verso il wizard Pro (home e Le mie stime)** - `2e15842` (feat)
2. **Task 2: Pavimento sempre visibile nel dettaglio Pro, con ricalcolo al cambio** - `c4484bf` (feat)

**Plan metadata:** committed separately by the orchestrator after this SUMMARY.

## Files Created/Modified
- `frontend/src/pages/EstimatePage.tsx` - `CtaDettaglioPro` riceve `input: StimaRequest`, naviga a `/nuova-stima?citta=...&mq=...&tipo=...` con `state: { risposte, destinazione, daStima: true }`
- `frontend/src/pages/NuovaStimaProPage.tsx` - `valoreRispostaValido()`/`datiDaStato()` (validazione di `history.state`, non fidato), `risposteDiPartenza`/`stepIniziale` passati al wizard, testo "Abbiamo ripreso i dati..." quando lo stato e' presente
- `frontend/src/routes/LeMieStimePage.tsx` - link "Rifai in versione Pro" da `/?citta=...` a `/nuova-stima?citta=...`
- `frontend/src/components/DettaglioProView.tsx` - blocco `domandeScelta` spostato fuori da `domandeCollassate ? ... : ...`, `handleSceltaChange()` (ricalcolo immediato + guardia anti-concorrenza), spinner "Ricalcolo in corso…" ed errore inline sulla mutation

## Decisions Made
- `datiDaStato()` scarta l'intero campo (`risposte` o `destinazione`) alla prima deviazione di forma, mai una riparazione parziale: stesso principio difensivo di `inizialiDaQuery()` sui query param, applicato a `history.state`.
- Guardia anti-doppio-invio in `handleSceltaChange` (no-op se `risposteMutation.isPending`) invece di propagare un prop `disabled` in `DomandaField`/`OptionCard`, per non toccare un componente condiviso col wizard Pro.

## Deviations from Plan

None - plan eseguito esattamente come scritto.

## Issues Encountered

None.

## User Setup Required

None - nessuna configurazione di servizi esterni richiesta.

## Next Phase Readiness

- Gap G3 (WIZ-04 parte percorso/dettaglio) chiuso lato codice: build e lint frontend verdi (`npm run build`, `npm run lint`, entrambi via junction NTFS temporanea a `node_modules` del checkout principale, rimossa a fine verifica).
- Resta da ri-collaudare dal vivo (09-HUMAN-UAT.md / 09-14): il percorso "stima non salvata -> Vai alla stima Pro -> step Le finiture gia' compilato" e "dettaglio Pro -> pavimento visibile senza Modifica -> cambio ricalcola" non sono stati provati in browser in questa sessione (nessuno strumento browser disponibile).
- I gap G1 (pavimenti sommati in B-FINITURE) e G2 (A.6 lavorazioni duplicate) restano fuori da questo piano — coperti dai piani paralleli 09-09/09-10 della stessa wave di gap closure.

## Self-Check: PASSED

Tutti e 4 i file citati trovati sul disco; entrambi i commit (`2e15842`, `c4484bf`) presenti in `git log`.

---
*Phase: 09-configuratore-pro*
*Completed: 2026-09-28*
