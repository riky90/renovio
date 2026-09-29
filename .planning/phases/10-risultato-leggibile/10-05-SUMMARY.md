---
phase: 10-risultato-leggibile
plan: 05
subsystem: stime-salvate-budget
tags: [budget, migrazione, patch, snapshot]
requires: [10-04]
provides:
  - colonna stima.budget_eur (migrazione 0024)
  - PATCH /api/v1/me/stime/{id}/budget
  - patchBudgetStima, StimaSalvataOut.budget_eur (client)
affects: [10-08]
key-files:
  created:
    - backend/alembic/versions/0024_budget_eur_su_stima.py
    - backend/tests/test_budget_stima.py
  modified:
    - backend/app/models/stima_salvata.py
    - backend/app/schemas/stima_salvata.py
    - backend/app/routers/stime_salvate.py
    - backend/tests/test_migrazioni_sqlite.py
    - backend/tests/test_no_leak.py
    - frontend/src/api/stima.ts
    - frontend/src/pages/EstimatePage.tsx
    - frontend/src/pages/NuovaStimaProPage.tsx
    - frontend/src/components/SavedEstimateDetail.tsx
key-decisions:
  - "budget_eur in colonna nullable, escluso da risultato_json: parametro modificabile, niente doppia verita' dopo un PATCH"
  - "PATCH (non PUT): aggiorna un solo campo, apiPatch esiste gia' nel client"
  - "confronto_finiture e finiture_al_minimo entrano nello snapshot al salvataggio, letti con .get() (snapshot vecchi -> None/False)"
  - "Auto-save da loggato invia il budget nel payload; se il budget cambia durante il salvataggio, un effect su savedId fa la PATCH"
duration: n/a
completed: 2026-09-29
---

# Phase 10 Plan 05: Budget salvato con la stima Summary

Il budget si salva nella colonna `stima.budget_eur` (migrazione 0024), si aggiorna con PATCH protetto da ownership senza toccare lo snapshot, e ricompare con l'avviso riaprendo la stima da "Le mie stime".

## Tasks

1. **Backend** (a6f9df1): migrazione 0024, modello, schemi (`BudgetIn`/`BudgetOut`, `le=999_999_999`), `salva_stima` con `exclude={"preferenze_pro", "budget_eur"}`, dettaglio con `.get()` e `budget_eur` dalla colonna, endpoint `aggiorna_budget` con `get_current_user` (Free e Pro), 404 anti-IDOR. Test: `test_budget_stima.py` (persistenza, PATCH, null, 422, IDOR, 401, free/pro, invarianza snapshot, snapshot pre-fase), revisione head 0024, no-leak esteso. dev.db a 0024.
2. **Client** (132120d): `patchBudgetStima`, `budget_eur` in `StimaSalvataOut`/`getStimaDettaglio`, `EstimatePage` (auto-save, SoftWallCta/pendingStima, sync PATCH), `NuovaStimaProPage`, `SavedEstimateDetail` con `BudgetAlert` e invalidazione `["stima-dettaglio", id]`.

## Verifica

- pytest test_budget_stima, test_stime_salvate, test_migrazioni_sqlite, test_no_leak: 62 passed.
- `npm run build` e `npm run lint`: exit 0 (solo warning preesistenti).
- `alembic current`: 0024 (head).

## Deviations from Plan

Nessuna di sostanza. Il test sulla PATCH per tier "pro" forza la colonna `tier` direttamente invece di attivare un abbonamento (stesso effetto sul router, che non guarda il tier). L'aggiunta dell'import `apiPatch` in `stima.ts` ha richiesto un secondo giro di build (errore TS subito corretto).

## Known Stubs

Nessuno.

## Threat Flags

Nessuno: T-10-12..T-10-16 mitigate con test; T-10-17 e T-10-26 accettate come da piano.

## Self-Check: PASSED

File creati presenti (0024, test_budget_stima.py), commit a6f9df1 e 132120d in git log.
