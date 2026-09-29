---
phase: 10-risultato-leggibile
plan: 14
subsystem: dettaglio-pro-bonus
tags: [gap-closure, G6, bonus, pro]
requires: [10-13]
provides:
  - "DettaglioProOut.bonus calcolato in _compute_dettaglio via bonus_out_per_stima"
  - "BonusPanel dentro DettaglioProView (Le mie stime e /dettaglio-pro), una sola volta"
affects: [10-15]
key-files:
  created:
    - backend/tests/test_dettaglio_pro_bonus.py
  modified:
    - backend/app/routers/dettaglio_pro.py
    - backend/app/schemas/dettaglio_pro.py
    - backend/tests/test_no_leak.py
    - frontend/src/api/stima.ts
    - frontend/src/api/dettaglio-pro.ts
    - frontend/src/components/DettaglioProView.tsx
    - frontend/src/pages/DettaglioProPage.tsx
decisions:
  - "Basi lorde Pro = imponibile + IVA di categoria arrotondata all'euro (come riepilogo_iva_pro); extra lordi; arredo e destinazione dallo snapshot in lettura difensiva"
  - "Il netto usa riepilogo.totale_min/max (Totale IVA inclusa Pro); il client mappa soltanto"
metrics:
  tasks: 2
  files: 8
completed: 2026-09-29
---

# Phase 10 Plan 14: Gap G6, pannello Bonus nella vista Pro Summary

Il dettaglio Pro restituisce i bonus calcolati server-side sui suoi totali IVA inclusa, e la vista Pro li mostra con la barra del totale Pro e il netto evidenziato.

## Commits
- de5400f: `_bonus_pro` in `_compute_dettaglio`, `DettaglioProOut.bonus`, test bonus Pro, test_no_leak esteso
- 9fe3f66: `normalizeBonus`/`RawBonusOut` esportati, tipi Pro, BonusPanel in DettaglioProView, rimosso da DettaglioProPage

## Verifiche
- pytest (test_dettaglio_pro_bonus, test_dettaglio_pro, _budget, _livelli, test_pdf_pro, test_no_leak): 72 passed, 2 skipped (WeasyPrint); il test arredo e' stato poi corretto e rieseguito da solo (6 passed)
- `npm run build` ok; `npm run lint` exit 0 (solo warning preesistenti)

## Deviations from Plan
- [Rule 1] `StimaSalvataCreate` non ha il campo `arredo`: un `arredo` postato dal client viene scartato e lo snapshot non lo contiene mai. Il test lo inserisce direttamente in `risultato_json` (con MOBILI acceso, e' spento nel seed). Il codice Pro legge comunque l'arredo dello snapshot come da piano.
- Acceptance `grep "totaleMin={dettaglio.totale_ivato_min}"` trova 2 righe (BudgetAlert e BonusPanel), non 1: entrambi legittimi.
- test_no_leak: lo scan testuale del dettaglio Pro esclude `bonus` (aliquota 0.5 collide coi coefficienti), come nel Free, e ne verifica le chiavi chiuse.

## Deferred Issues
- `arredo` non viene persistito negli snapshot creati via POST /me/stime (schema senza il campo): ArredoCard e la base MOBILI del Pro non hanno dati reali. Fuori scope di G6; da valutare in 10-15 o a parte.

## Known Stubs
None.

## Threat Flags
None. BonusOut a campi chiusi, gate `require_pro` e ownership invariati.

## Self-Check: PASSED
