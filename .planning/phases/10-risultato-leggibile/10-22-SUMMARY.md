---
phase: 10-risultato-leggibile
plan: 22
subsystem: frontend-salvataggio-stima
tags: [G12, auto-save, tanstack-query]
requires: ["10-21"]
provides:
  - "Funzioni pure in frontend/src/lib (richiestaStima, domande) provate da uno script node"
  - "ultimoSalvataggio affidabile anche con Modifica premuto a salvataggio in volo"
affects: ["10-23", "10-24"]
key-files:
  created:
    - frontend/src/lib/richiestaStima.ts
    - frontend/src/lib/domande.ts
    - frontend/scripts/check-richiesta-stima.ts
    - frontend/scripts/fixtures/catalogo-free-85.json
  modified:
    - frontend/src/api/domande.ts
    - frontend/src/components/EstimateWizard.tsx
    - frontend/src/pages/EstimatePage.tsx
key-decisions:
  - "Il prefill del wizard non e' la causa di G12: nessuna correzione al wizard"
  - "La correzione del percorso di salvataggio e' l'onSuccess a livello di useMutation; la chiusura definitiva dei doppioni sul percorso Modifica e' il flusso G14 di 10-23"
requirements-completed: [RIS-04]
completed: 2026-10-01
---

# Phase 10 Plan 22: diagnosi G12 e irrobustimento di ultimoSalvataggio Summary

Il confronto delle richieste e il ricalcolo dei default del wizard sono funzioni pure provate da `node scripts/check-richiesta-stima.ts`; `ultimoSalvataggio` si imposta ora nell'`onSuccess` di `useMutation`.

## Commit

- `9e1f9e4` refactor(10-22): funzioni pure del wizard in lib/ (richiestaStima, domande)
- `64dd971` test(10-22): script node per G12, giro Modifica col catalogo reale e race di reset()
- `1efa5c5` fix(10-22): ultimoSalvataggio nell'onSuccess di useMutation, guardia sulla richiesta in volo

## Causa radice G12

**Ipotesi confermata (meccanismo): 1, race su `reset()`.** `handleModifica` chiama `saveMutation.reset()`. In TanStack Query v5 i callback passati a `mutate(vars, { onSuccess })` appartengono all'observer; `reset()` lo stacca dalla mutation in volo e quei callback non partono piu'. Se il primo auto-save (POST /me/stime) e' ancora in corso quando si preme Modifica, `setUltimoSalvataggio` (che stava nel callback per-call) non viene mai chiamato; `ultimoSalvataggio` resta `null`, `richiestaIdentica` e' falso e il ricalcolo identico salva una seconda volta.

Prova: sezione (c) di `frontend/scripts/check-richiesta-stima.ts`, con `MutationObserver` reale di `@tanstack/query-core`. Senza `reset()` il callback per-call parte (controllo); con `observer.reset()` mentre la mutation e' in volo il callback per-call NON parte (`perCall` resta 1), mentre quello nelle opzioni parte (`opzioni` = 2). Lo script esce con codice 0.

**Esclusa: 2, risposte diverse dopo il giro Modifica.** Lo script fa il giro Modifica col catalogo Free reale (fixture `catalogo-free-85.json`, 85 m²): scelte con ambienti da arredare, stepper cambiato, scelta multipla svuotata (`[]`), solo default; dopo il rimontaggio con `risposteDopoPrimoCatalogo` e `soloVisibili`, `stessaRichiesta(r1, r2)` e' vera in tutti i casi. Le richieste sono identiche, il prefill non e' il difetto.

**Non provate in node: 3 (CityAutocomplete / mqRaw al remount) e 4 (percorso Pro / `pendingStima`).** Dipendono da componenti React e dal browser, che lo script non esegue. Non e' stata trovata evidenza a loro favore ne' sono dimostrate false.

**Limite dichiarato:** il meccanismo della race e' dimostrato, ma che sia esattamente cio' che Riccardo ha visto dal vivo non e' osservato; e' la causa piu' probabile (Modifica premuto presto dopo il risultato, POST ancora in volo). La conferma dal vivo e' nella checklist 10-24.

## Correzione

- Prefill del wizard: nessuna modifica, non e' la causa.
- `EstimatePage.tsx`: `ultimoSalvataggio` impostato nell'`onSuccess` di `useMutation` (variabili `{ payload, richiesta }`), non piu' nel callback per-call; il `reset()` non lo perde.
- Ref `richiestaInSalvataggio`: l'effetto di auto-save non lancia un secondo POST per la richiesta identica a quella in volo, anche dopo `reset()`; azzerato in `onSettled`.
- `stessaRichiesta` importata da `@/lib/richiestaStima` (copie locali rimosse); il confronto resta stretto.
- Passa a 10-23 (G14): dopo Modifica il ricalcolo fa PUT sull'id esistente, mai POST, quindi i doppioni sul percorso Modifica sono impossibili per costruzione.

## Verifica

- `node scripts/check-richiesta-stima.ts`: OK (exit 0)
- `npm run build`: OK; `npm run lint`: nessun warning su EstimatePage.tsx ed EstimateWizard.tsx (restano warning preesistenti in altri file)
- Fixture senza chiavi vietate (coefficiente, prezzo_impresa, moltiplicatore)
- Verifica dal vivo rimandata alla checklist 10-24: account Free e Pro, con ambienti da arredare, premendo Modifica subito dopo il risultato.

## Deviazioni

Nessuna: piano eseguito come scritto. Il Task 2 era stato lasciato non committato da una sessione interrotta; il diff coincideva col piano e l'ho tenuto.
