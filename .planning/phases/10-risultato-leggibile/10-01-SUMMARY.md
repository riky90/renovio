---
phase: 10-risultato-leggibile
plan: 01
subsystem: frontend
tags: [risultato, rangebar, iva, presentazione]
requires: []
provides:
  - lib/risultato.ts (scalaBarra, incidenzaEurMq, sommaMediCategorie, pesoCategoria, riepilogoIva)
  - formatRangeEurMq
affects: [10-02]
tech-stack:
  added: []
  patterns: [funzioni pure di presentazione derivate dallo snapshot]
key-files:
  created: [frontend/src/lib/risultato.ts]
  modified:
    - frontend/src/lib/currency.ts
    - frontend/src/components/RangeBar.tsx
    - frontend/src/components/CategoryCard.tsx
    - frontend/src/components/TotalCard.tsx
    - frontend/src/components/BonusPanel.tsx
    - frontend/src/pages/EstimatePage.tsx
    - frontend/src/components/SavedEstimateDetail.tsx
key-decisions:
  - "Peso categoria calcolato solo sulle categorie, senza extra né arredo"
  - "Riga IVA con aliquota più alta assorbe l'arrotondamento per sommare a totale.iva"
requirements-completed: [RIS-01, RIS-02, RIS-03]
duration: ~15min
completed: 2026-09-29
---

# Phase 10 Plan 01: Risultato Free leggibile Summary

Barra del totale proporzionale (asse 0 -> tetto 1,2 x max), incidenza €/m² e peso per categoria, riepilogo imponibile/IVA per aliquota/extra dentro la TotalCard, tutto derivato dallo snapshot (vale anche per stime salvate pre-fase).

## Commits
- 5ed4a5c: lib/risultato.ts, formatRangeEurMq, RangeBar proporzionale
- 2d68228: CategoryCard e TotalCard
- b4dcccf: riordino EstimatePage / SavedEstimateDetail, lista extra rimossa

## Deviations from Plan

**1. [Rule 3 - Blocking] BonusPanel secondo chiamante della RangeBar**
- Il piano indicava TotalCard come unico chiamante; BonusPanel usa RangeBar e rompeva il build. Passati `min/max` = detrazione_min/max.
- Files: frontend/src/components/BonusPanel.tsx (commit 5ed4a5c)

**2. Task 2 e 3 non verdi separatamente**: i chiamanti sono stati aggiornati insieme (props obbligatorie), poi il commit è stato diviso per file; solo l'HEAD finale è verificato con build+lint.

## Verification
`npm run build` e `npm run lint` verdi (solo warning preesistenti nelle pagine admin). Grep di accettazione tutti soddisfatti. Nessun test automatico frontend; controllo visivo rinviato al piano 10-09.

## Known Stubs
None.

## Self-Check: PASSED
