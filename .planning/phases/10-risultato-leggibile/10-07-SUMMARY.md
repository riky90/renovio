---
phase: 10-risultato-leggibile
plan: 07
subsystem: dettaglio-pro-frontend
tags: [pro, iva, budget, range-bar, componenti-condivisi]
requires: [10-06]
provides:
  - RiepilogoIvaRighe e LetturaCategoria (componenti condivisi Free/Pro)
  - DettaglioProOut esteso lato client (totale_ivato, riepilogo_iva, lettura_categorie, confronto, budget)
  - Vista Pro con RangeBar, riepilogo IVA, BudgetAlert e lettura per categoria
affects: [10-08, 10-09]
key-files:
  created:
    - frontend/src/components/RiepilogoIvaRighe.tsx
    - frontend/src/components/LetturaCategoria.tsx
  modified:
    - frontend/src/api/stima.ts
    - frontend/src/api/dettaglio-pro.ts
    - frontend/src/components/TotalCard.tsx
    - frontend/src/components/CategoryCard.tsx
    - frontend/src/components/BudgetAlert.tsx
    - frontend/src/components/SottocategoriaAccordion.tsx
    - frontend/src/components/DettaglioProView.tsx
key-decisions:
  - "normalizeConfronto e RawConfrontoFinitureOut esportati da api/stima.ts e riusati in dettaglio-pro.ts"
  - "BudgetAlert: prop mostraTotaleConfrontato mostra la riga 'Ora (IVA inclusa)' in ogni stato; default false, Free invariato"
  - "La lettura per categoria Pro sta sotto la riga 'Totale {categoria}' dell'accordion, via prop opzionale lettura"
  - "Nessun calcolo su IVA, peso o incidenza nel client Pro: solo mappatura dei valori del DTO"
duration: n/a
completed: 2026-09-29
---

# Phase 10 Plan 07: Lettura del risultato nella vista Pro web Summary

La vista Pro web mostra ora barra proporzionale con tacca budget, riepilogo IVA per aliquota, EUR/m2 e peso per categoria e l'avviso budget su base IVA inclusa, con gli stessi componenti del Free e numeri solo dal DTO del piano 10-06.

## Tasks

1. **Tipi Pro e componenti condivisi** (53fb96e): normalizzazione dei campi nuovi in `dettaglio-pro.ts`; `RiepilogoIvaRighe` e `LetturaCategoria` estratti da TotalCard e CategoryCard senza cambi di markup.
2. **Vista Pro** (f915b2b): blocco RangeBar + riepilogo sotto "Totale generale stimato", BudgetAlert con PATCH e invalidazione della query `["dettaglio-pro", stimaId]`, lettura per categoria nell'accordion.

## Verifica

- `npm run build`: verde. `npm run lint`: 0 errori (solo warning preesistenti).
- Grep di acceptance rispettati (nessun `iva_pct`/`coefficiente` nella vista Pro, nessun termine vietato nei componenti nuovi).

## Deviations from Plan

None - plan executed as written.

## Known Stubs

Nessuno.

## Threat Flags

Nessuno. T-10-27/28 mitigate come da piano; T-10-29 accettata.

## Self-Check: PASSED

File creati presenti e commit in git log.
