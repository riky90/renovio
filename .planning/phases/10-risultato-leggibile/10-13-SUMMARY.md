---
phase: 10-risultato-leggibile
plan: 13
subsystem: bonus-panel
tags: [gap-closure, G5, bonus, detrazioni, range-bar]
requires: [10-10, 10-11, 10-12]
provides:
  - "bonus_out_per_stima: unico helper server per BonusOut (dettaglio, detrazione sui lavori, netto), riusabile dal Pro (10-14)"
  - "BonusOut.detrazione_lavori_min/max e netto_min/max opzionali (default None, snapshot vecchi validi)"
  - "RangeBar prop evidenza; BonusPanel con barra del costo totale e segmento Dopo le detrazioni"
affects: [10-14, 10-15]
key-files:
  created:
    - backend/app/services/bonus_stima.py
    - backend/tests/test_bonus_stima.py
  modified:
    - backend/app/routers/stima.py
    - backend/app/schemas/stima.py
    - backend/tests/test_no_leak.py
    - frontend/src/api/stima.ts
    - frontend/src/lib/risultato.ts
    - frontend/src/components/RangeBar.tsx
    - frontend/src/components/BonusPanel.tsx
    - frontend/src/components/SavedEstimateDetail.tsx
    - frontend/src/pages/EstimatePage.tsx
    - frontend/src/pages/DettaglioProPage.tsx
decisions:
  - "Netto = Totale IVA inclusa - detrazione sui lavori (senza E-ARREDO), a coppie, mai sotto 0; tutto server-side"
  - "Il client mappa soltanto: nessuna sottrazione fra totale e detrazione in BonusPanel"
metrics:
  tasks: 2
  files: 12
completed: 2026-09-29
---

# Phase 10 Plan 13: Gap G5, pannello Bonus con costo totale e netto Summary

Il pannello Bonus mostra la barra del Totale IVA inclusa con evidenziato il costo al netto delle detrazioni, calcolato dal server con un helper condiviso.

## Commits
- 52d4f0e: helper server `bonus_out_per_stima`, DTO esteso, router che passa dall'helper, test
- c7488df: RangeBar `evidenza`, BonusPanel nuovo, `normalizeBonus` con i 4 campi opzionali, chiamanti aggiornati

## Verifiche
- pytest (test_bonus_stima, test_bonus, test_no_leak, test_stima_api, test_estimation, test_stime_salvate, test_arredo): 102 passed
- `npm run build` ok; `npm run lint` exit 0 (solo warning preesistenti)

## Deviations from Plan
- [Rule 2] Aggiunto test_arredo.py alla batteria pytest, perche' usa la stessa fixture e il router modificato. Nessun altro scostamento.
- `grep "min={bonus.detrazione_min}"` trova una riga in BonusPanel: e' la riga di legenda di fallback (snapshot senza `detrazione_lavori_*`), non la RangeBar.

## Known Stubs
None.

## Threat Flags
None. BonusOut a campi chiusi, test_no_leak aggiornato (T-10-G5-01); disclaimer dal payload e nota arredo (T-10-G5-03).

## Self-Check: PASSED
