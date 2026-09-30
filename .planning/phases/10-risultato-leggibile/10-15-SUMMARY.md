---
phase: 10-risultato-leggibile
plan: 15
subsystem: collaudo
tags: [gap-closure, ri-collaudo, G1-G6]
requires: [10-10, 10-11, 10-12, 10-13, 10-14]
provides:
  - "Checklist di ri-collaudo G1-G6 (.planning/checklists/2026-09-29-ricollaudo-10.md)"
  - "Esito del ri-collaudo registrato: non approvato, tre gap nuovi G7-G9"
affects: [10-16, 10-17, 10-18]
key-files:
  created:
    - .planning/checklists/2026-09-29-ricollaudo-10.md
  modified:
    - .planning/phases/10-risultato-leggibile/10-HUMAN-UAT.md
decisions:
  - "G7: il pannello Bonus mostra una sola barra, il valore della detrazione (via totale e netto)"
  - "G8: le cifre min/max della RangeBar tornano ai bordi del box"
  - "G9: l'arredo va salvato negli snapshot adesso, dentro la Fase 10"
  - "Confermate le scelte su auto-save (10-12), netto senza Bonus Mobili (10-13), peso % sull'imponibile (G2), causa radice di G3"
metrics:
  tasks: 2
  files: 2
completed: 2026-09-30
---

# Phase 10 Plan 15: ri-collaudo G1-G6 Summary

Ri-collaudo dei gap G1-G6 percorso da Riccardo il 2026-09-30: G2, G3, G4 e G6 passano; G1 e G5
sono superati da richieste nuove (G7, G8) e il difetto differito dell'arredo diventa G9.

## Commits
- 19a568f: checklist di ri-collaudo (32 voci) e fix/retest dei gap in 10-HUMAN-UAT

## Verifiche
- Controlli automatici (suite backend completa, `npm run build`, `npm run lint`): verdi a fine
  esecuzione dei piani 10-10..10-14 il 2026-09-29, secondo il journal di quel giorno. La tabella con
  i numeri non e' stata scritta in questo SUMMARY e non e' stata rimisurata: la rimisura la fa 10-18.
- Checkpoint umano (Task 2): **non approvato**. Esito e note in
  `.planning/checklists/2026-09-29-ricollaudo-10.md`, sezione "Esito del ri-collaudo (2026-09-30)".

## Esito
- G2, G3, G4, G6: `resolved` in 10-HUMAN-UAT.md.
- G1, G5: `superseded` da G8 e G7.
- G7, G8, G9: `failed`, pianificati in 10-16 (G7, G8), 10-17 (G9) e 10-18 (nuovo ri-collaudo).

## Deviazioni
- Il checkpoint si e' chiuso con "non approvato" invece che con "approvato": il ciclo di gap continua
  con i piani 10-16..10-18 invece di passare alla verifica di fase.
