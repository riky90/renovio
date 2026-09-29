---
phase: 10-risultato-leggibile
plan: 04
subsystem: stima-api-and-budget-alert
tags: [risultato, confronto-finiture, budget, api]
requires: [10-02, 10-03]
provides:
  - ConfrontoFinitureOut, StimaResponse.confronto_finiture, StimaResponse.finiture_al_minimo
  - livello_inferiore / livello_corrente (services/risultato.py)
  - DOMANDA_LIVELLO_FINITURE (services/effetti.py)
  - normalizeConfronto, deltaConfronto, righe Ora / Con finiture nel BudgetAlert
affects: [10-05, 10-08]
key-files:
  created:
    - backend/tests/test_confronto_finiture.py
  modified:
    - backend/app/services/effetti.py
    - backend/app/services/risultato.py
    - backend/app/schemas/stima.py
    - backend/app/routers/stima.py
    - backend/tests/test_risultato.py
    - backend/tests/test_no_leak.py
    - frontend/src/api/stima.ts
    - frontend/src/lib/risultato.ts
    - frontend/src/components/BudgetAlert.tsx
    - frontend/src/pages/EstimatePage.tsx
key-decisions:
  - "Il confronto e' un secondo EstimationService.compute con livello_finiture un gradino sotto: ricalcolo vero, nessuna proporzione lato client (D-09)"
  - "L'ordine dei livelli viene da opzione_domanda.ordine (solo opzioni attive); nessuna lista base/medio/alto nel codice"
  - "Confronto None se risposte assenti, nessun livello inferiore, codice sconosciuto o ricalcolo che non abbassa il massimo; finiture_al_minimo true solo con finiture scelte/di default gia' al livello piu' basso"
  - "Il confronto guarda solo il totale lavori: l'arredo resta fuori (D-08); EstimationService non toccato, oracolo 47.985-70.575 intatto"
duration: n/a
completed: 2026-09-29
---

# Phase 10 Plan 04: Confronto a finiture inferiori Summary

POST /stima restituisce `confronto_finiture` (ricalcolo Free un livello sotto) e `finiture_al_minimo`; il BudgetAlert "fuori budget" mostra Ora / Con finiture e il delta a range, oppure i testi "finiture economiche" / "meno lavori" quando il confronto non c'e'.

## Tasks

| Task | Commit | Note |
|------|--------|------|
| 1 confronto_finiture in POST /stima | 9bdf34f | test scritti insieme all'implementazione (un solo commit, niente RED separato) |
| 2 client e BudgetAlert | 170f612 | build ok, lint senza errori (solo warning preesistenti) |

## Verifica

- pytest test_confronto_finiture, test_risultato, test_no_leak: 36 passed; test_stima_api, test_estimation: 22 passed.
- `npm run build` ok; `npm run lint` solo warning preesistenti.
- Nessuna occorrenza di "moltiplicatore" nelle righe aggiunte; `estimation.py` non modificato.

## Deviations from Plan

- Il ciclo RED/GREEN non e' stato committato separatamente: test e implementazione stanno nel commit 9bdf34f. I test sono stati eseguiti solo dopo l'implementazione.
- Il caso "ricalcolo non abbassa il massimo" (Pitfall 3) non ha un test dedicato: il seed non permette di costruirlo via API e non e' stato aggiunto un test della funzione di mappatura. Il ramo e' coperto solo dalla lettura del codice.

## Known Stubs

Nessuno. `budget_eur` in `StimaResponse` (client) e' un campo opzionale voluto, popolato dal piano 10-05.

## Threat Flags

Nessuno: DTO chiuso a 4 campi, verificato da test_no_leak.

## Self-Check: PASSED (file e commit 9bdf34f, 170f612 presenti)
