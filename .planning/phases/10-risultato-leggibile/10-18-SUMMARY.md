---
phase: 10-risultato-leggibile
plan: 18
subsystem: collaudo
tags: [gap-closure, ri-collaudo, G7-G9]
requires: [10-16, 10-17]
provides:
  - "Checklist di ri-collaudo G7-G9 (.planning/checklists/2026-09-30-ricollaudo-10-g7-g9.md)"
  - "Esito registrato: non approvato, nuovi gap G10-G13"
affects: [10-19]
key-files:
  created:
    - .planning/checklists/2026-09-30-ricollaudo-10-g7-g9.md
  modified:
    - .planning/phases/10-risultato-leggibile/10-HUMAN-UAT.md
decisions:
  - "G10: il Bonus Mobili va dentro la card Arredo; il pannello Bonus mostra solo la detrazione sui lavori"
  - "G13: nei PDF le cifre min/max vanno ai bordi come sul web"
  - "Confermato: il server continua a calcolare il netto, il pannello non lo mostra"
metrics:
  tasks: 2
  files: 2
completed: 2026-09-30
---

# Phase 10 Plan 18: ri-collaudo G7-G9 Summary

Ri-collaudo del 2026-09-30 pomeriggio: G7 e G8 passano sul web, G9 passa con account Free.
Riccardo ha trovato quattro gap nuovi (G10-G13), registrati in 10-HUMAN-UAT.md.

## Commits
- 011c942: checklist di ri-collaudo G7-G9 e fix/retest in 10-HUMAN-UAT
- ef0f604: esito del ri-collaudo, gap G10-G13

## Controlli automatici (Task 1)

| Controllo | Esito |
|---|---|
| Suite backend completa | 965 passed, 5 skipped (WeasyPrint), 0 failed, 41m31s |
| `npm run build` | ok |
| `npm run lint` | exit 0, solo warning preesistenti (2 only-export-components, 5 set-state-in-effect) |

## Esito del checkpoint (Task 2)
Non approvato.
- G10: Bonus Mobili dentro la card Arredo, fuori dal pannello Bonus.
- G11: con account Pro, "Le mie stime" non mostra card Arredo e Bonus Mobili (da /dettaglio-pro si').
- G12: Modifica + ricalcolo identico crea una seconda stima (regressione di G4c).
- G13: cifre ai bordi anche nei PDF.

## Deviazioni
- Il checkpoint si e' chiuso con "non approvato": il ciclo di gap continua con nuovi piani.
