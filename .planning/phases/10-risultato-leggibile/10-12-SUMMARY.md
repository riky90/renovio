---
phase: 10-risultato-leggibile
plan: 12
subsystem: risultato
tags: [gap-closure, G4, modifica, wizard, auto-save]
requires: []
provides:
  - "Modifica nella stima Free riapre il wizard precompilato (citta, m2, tipo, destinazione, risposte, budget)"
  - "auto-save che non duplica il record se la richiesta ricalcolata e' identica"
affects: [10-15]
key-files:
  modified:
    - frontend/src/pages/EstimatePage.tsx
decisions:
  - "G4: stessa richiesta = stessa stima (si riusa l'id, al massimo PATCH del budget); input diversi = nuovo record, la precedente resta in 'Le mie stime'"
requirements: [RIS-04]
metrics:
  completed: 2026-09-29
  tasks: 2
---

# Phase 10 Plan 12: chiusura G4 (Modifica precompilata) Summary

Modifica salva la richiesta corrente in `bozza`, rimonta il wizard con `key={wizardKey}` e passa `iniziali`, `risposteDiPartenza` (l'intera `bozza.risposte`; 10-11 filtra i default), `budgetIniziale` e `stepIniziale=1`, poi scrolla in cima. Il budget resta fuori da POST /stima (D-03 invariato).

Auto-save: `stessaRichiesta()` confronta citta (trim), mq, tipo, destinazione e risposte normalizzate (chiavi e array ordinati). `ultimoSalvataggio {id, richiesta}` sopravvive a Modifica. Se la richiesta ricalcolata e' identica non parte un nuovo POST /me/stime e `idSalvato` riusa l'id (sync budget via PATCH esistente, SoftWallCta, handleSalvaBudget). Input diversi creano un nuovo record.

## Commits
- a513120 feat(10-12): Modifica riapre il wizard precompilato
- 7660595 feat(10-12): auto-save senza duplicati

## Verifica
- `npm run build` ok; `npm run lint` senza nuovi warning (solo preesistenti).
- Ri-collaudo dal vivo nella checklist 10-15.

## Deviations from Plan
- Il grep di accettazione `ultimoSalvataggio` >= 4 da 3 righe (la logica e' compatta); funzionalita' completa.
- Nessun test frontend automatico (non c'e' infrastruttura di test componenti).

## Known Stubs
None.

## Self-Check: PASSED
