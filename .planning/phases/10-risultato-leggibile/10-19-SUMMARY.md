---
phase: 10-risultato-leggibile
plan: 19
subsystem: backend-bonus
tags: [bonus, arredo, G10, tdd, anti-leak]
requires: ["10-17"]
provides:
  - "BonusDettaglioOut.su_arredo (decisa dal server)"
  - "BonusOut.rata_annua_lavori_min/max"
affects: ["10-21 (client: filtra per su_arredo)"]
tech-stack:
  added: []
  patterns: ["marcatura per differenza fra calcolo completo e calcolo sui lavori"]
key-files:
  modified:
    - backend/app/schemas/stima.py
    - backend/app/services/bonus_stima.py
    - backend/tests/test_bonus_stima.py
    - backend/tests/test_no_leak.py
    - backend/tests/test_dettaglio_pro_bonus.py
    - backend/tests/test_stime_salvate.py
key-decisions:
  - "Una voce e' su_arredo se compare in `completo` e non in `lavori`; nessun codice bonus cablato"
  - "Nessun backfill: gli snapshot precedenti a G10 hanno su_arredo=false e rata_annua_lavori_*=null"
requirements-completed: [RIS-03]
duration: ~25min
completed: 2026-09-30
---

# Phase 10 Plan 19: su_arredo e rata annua sui lavori Summary

Il server marca ogni voce di bonus che vive solo sulla base arredo (`su_arredo`) ed espone la rata annua dei soli lavori (`rata_annua_lavori_min/max`), per Free, Pro e snapshot, senza toccare i router.

## Commit

- `3157c7d` test(10-19): RED, 14 test falliti per campo assente o chiave inattesa
- `6023ba2` feat(10-19): GREEN, DTO esteso e `bonus_out_per_stima` aggiornato

## Cosa e' stato fatto

- `BonusDettaglioOut.su_arredo: bool = False`, `BonusOut.rata_annua_lavori_min/max: Decimal | None = None`.
- `bonus_out_per_stima`: con arredo, `su_arredo = codice non presente fra le voci di lavori`; rata sui lavori = rata del calcolo `lavori` (0 se `None`). Senza arredo, nessuna voce marcata e rata lavori = rata totale. Regola documentata nei docstring, incluso il caso limite di un bonus su lavori e arredo insieme.
- `grep -c MOBILI` su `bonus_stima.py` = 0. Il commit feat non tocca `backend/app/routers`.

## Verifica

Batteria mirata (test_bonus_stima, test_bonus, test_no_leak, test_dettaglio_pro_bonus, test_dettaglio_pro, test_stime_salvate, test_arredo, test_stima_api): 118 passed al primo giro GREEN, 1 failed (vedi deviazione); poi `test_dettaglio_pro_bonus.py` 6 passed. Totale atteso 119 passed, 0 failed.

## Deviazioni dal piano

**1. [Rule 1 - Bug] Insieme chiuso `CHIAVI_BONUS` in test_dettaglio_pro_bonus.py**
- **Trovato durante:** Task 2, batteria GREEN
- **Problema:** `test_bonus_presente_e_coerente_col_totale_ivato` confronta le chiavi del blocco bonus con un insieme chiuso non elencato nel piano; le due chiavi nuove lo facevano fallire.
- **Fix:** aggiunte `rata_annua_lavori_min/max` a `CHIAVI_BONUS`.
- **Commit:** `6023ba2`

## Known Stubs

Nessuno.

## Threat Flags

Nessuno: solo le tre chiavi dichiarate, nessun coefficiente ne' prezzo impresa; insiemi chiusi Free e Pro aggiornati in test_no_leak.

## Nota per la checklist di collaudo (10-24)

Le stime salvate con arredo prima di G10 (dal 2026-09-30, dopo 10-17) mostrano ancora il Bonus Mobili nel pannello Bonus: nessun backfill.

## Self-Check: PASSED

Commit `3157c7d` e `6023ba2` presenti; file modificati presenti.
