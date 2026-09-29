---
phase: 10-risultato-leggibile
plan: 03
subsystem: frontend-budget
tags: [risultato, budget, wizard, rangebar, alert]
requires: [10-01]
provides:
  - lib/risultato.ts (parseImporto, formatImporto, statoBudget, TESTI_AVVISO)
  - ImportoField (campo importo euro)
  - BudgetAlert (avviso a tre stati con modifica/rimozione)
  - tacca budget su RangeBar
affects: [10-04, 10-05, 10-08, 10-09]
tech-stack:
  added: []
  patterns: [budget solo in stato pagina, mai in POST /stima ne' in risposte]
key-files:
  created:
    - frontend/src/components/ImportoField.tsx
    - frontend/src/components/BudgetAlert.tsx
  modified:
    - frontend/src/lib/risultato.ts
    - frontend/src/components/EstimateWizard.tsx
    - frontend/src/components/RangeBar.tsx
    - frontend/src/components/TotalCard.tsx
    - frontend/src/pages/EstimatePage.tsx
key-decisions:
  - "Budget = stringa fissa allo step 3, non Domanda di catalogo (A1): non passa dal layer effetti"
  - "statoBudget: budget < min fuori, min <= budget <= max limite, oltre dentro; nullo o <= 0 -> nessuno stato"
  - "Le stringhe dell'avviso vivono in TESTI_AVVISO per la parita' col PDF (10-08)"
  - "Alert con role=status e aria-live=polite; mai variante destructive"
requirements-completed: [RIS-04, RIS-01]
duration: ~20min
completed: 2026-09-29
---

# Phase 10 Plan 03: Budget nel wizard, tacca e BudgetAlert Summary

Il wizard chiede il budget (facoltativo) allo step 3, la RangeBar mostra la tacca "Il tuo budget" e sotto la TotalCard compare l'avviso a tre stati (fuori/limite/dentro) modificabile o rimovibile, senza toccare il prezzo.

## Commits
- 79d0241: domanda budget allo step 3, ImportoField, funzioni e testi in lib/risultato
- b73b102: tacca su RangeBar, BudgetAlert, wiring in EstimatePage

## Verification
`npm run build` OK; `npm run lint` senza errori (solo warning preesistenti `set-state-in-effect`, nessuno nei file nuovi). Acceptance grep: `budget` in `api/domande.ts` = 0; `mutation.mutate` non contiene budget; `avantiDisabilitato` invariato. Comportamento dei tre stati rinviato alla checklist 10-09.

## Deviations from Plan
None - plan executed as written.

## Known Stubs
`onSalva` in EstimatePage aggiorna solo lo stato locale: la persistenza sulla stima salvata e' prevista dal piano 10-05 (intenzionale, dichiarato nel piano).

## Threat Flags
None.

## Self-Check: PASSED
