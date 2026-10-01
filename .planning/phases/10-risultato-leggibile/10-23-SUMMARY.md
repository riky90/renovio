---
phase: 10-risultato-leggibile
plan: 23
subsystem: stime-salvate-modifica
tags: [G14, G12, put, modifica]
requires: ["10-22"]
provides:
  - "PUT /api/v1/me/stime/{stima_id}: aggiorna la propria stima (snapshot, colonne scalari, budget)"
  - "Home: Modifica + ricalcolo aggiorna la stima salvata (stesso id), mai un POST"
affects: ["10-24"]
key-files:
  modified:
    - backend/app/routers/stime_salvate.py
    - backend/tests/test_stime_salvate.py
    - backend/tests/test_stima_tier.py
    - frontend/src/api/client.ts
    - frontend/src/api/stima.ts
    - frontend/src/lib/richiestaStima.ts
    - frontend/src/pages/EstimatePage.tsx
    - frontend/scripts/check-richiesta-stima.ts
key-decisions:
  - "Il PUT non legge ne' scrive tier, user_id, created_at; preferenze_pro assenti = colonne Pro invariate"
  - "Dopo Modifica il ricalcolo fa sempre PUT sull'id esistente (identico o no), mai POST; errore del PUT = messaggio, nessun ripiego su POST"
  - "stimaInModifica e ultimoSalvataggio sono legati a user.id (derivati, senza effetto): un PUT non puo' puntare alla stima di un altro utente"
requirements-completed: [RIS-04]
completed: 2026-10-01
---

# Phase 10 Plan 23: PUT /me/stime/{id} e Modifica che aggiorna la stima (G14) Summary

Modifica dalla home aggiorna la stima gia' salvata (stesso id, snapshot e budget nuovi) tramite un endpoint PUT protetto da proprieta' che non cambia mai il tier.

## Commit

- `8d6b854` test(10-23): test rossi: PUT, proprieta', tier, snapshot, no-leak (`TestAggiornaStima`, `TestTierAlAggiornamento`)
- `2e9f817` feat(10-23): PUT /me/stime/{id}, helper `_snapshot` e `_colonne_preferenze` condivisi col POST
- `ae7d607` feat(10-23): flusso Modifica nella home, `apiPut`, `putAggiornaStima`, `azioneSalvataggio`

## Cosa e' stato fatto

**Backend.** `aggiorna_stima` usa la stessa select di GET/PATCH (`id` + `user_id == current_user.id`, 404 se nulla). Riscrive `risultato_json` con `_snapshot(payload)` (stessa forma del POST, senza `preferenze_pro` ne' `budget_eur`, `schema_version` corrente) e le colonne scalari `citta`, `mq`, `tipo`, `totale_min/max`, `fallback`, `budget_eur`. Le preferenze Pro, se presenti, sono validate con `_colonne_preferenze` prima di toccare la riga (400 senza modifiche); se assenti le colonne restano. Il POST e' stato rifattorizzato sugli stessi due helper senza cambiare comportamento.

**Frontend.**
- `apiPut` (come `apiPatch`) e `putAggiornaStima(id, payload)` (non manda `preferenze_pro`).
- `azioneSalvataggio({ stimaInModifica, idEsistente, postInVolo })` in `lib/richiestaStima.ts` decide `post` / `put` / `attendi`; i casi sono nello script node di 10-22.
- `EstimatePage`: `modificaDiUtente` (impostato da `handleModifica` se esiste una stima salvata o in volo), `ultimoSalvataggio` con `userId` (ignorato se `user.id` cambia), ref `ultimoResultInviato` (l'effetto agisce una volta per risultato), contatore `postConclusi` perche' chi attendeva l'id ripieghi sul POST se il primo POST fallisce. `updateMutation` con `onSuccess` a livello di useMutation che aggiorna `ultimoSalvataggio` e invalida `["stima-dettaglio", id]`, `["dettaglio-pro", id]`, `["storico-stime"]`. `handleModifica` resetta anche `updateMutation`. Errore del PUT: alert, nessun POST di ripiego.

## Verifica

- `pytest tests/test_stime_salvate.py tests/test_stima_tier.py tests/test_budget_stima.py tests/test_no_leak.py tests/test_dettaglio_pro_livelli.py tests/test_wizard_pro_scelte.py`: 92 passed, 1 skipped (la suite completa e' di 10-24). Prima dell'implementazione 12 test nuovi su 15 erano rossi (405).
- Corpo di `aggiorna_stima`: nessun `row.tier/user_id/created_at =` ne' `subscription_is_active` (grep = 0).
- `node scripts/check-richiesta-stima.ts` OK, `npm run build` OK, `npm run lint` senza warning su client.ts, stima.ts, richiestaStima.ts, EstimatePage.tsx.

## Deviazioni

- [Rule 2] Alert per l'errore del PUT: nel codice non esisteva un "errore di salvataggio" da riusare, ne' ho aggiunto uno minimo (la regola "nessun ripiego su POST" richiede che l'utente veda il fallimento).
- `stessaRichiesta` non e' piu' importata da `EstimatePage` (la regola "ricalcolo identico riusa l'id" e' sostituita dal PUT sempre); resta in `lib` ed e' coperta dallo script.
- Nessun test automatico dell'effetto React (non c'e' un runner frontend): il flusso dal vivo e' nella checklist 10-24.

## Per la checklist 10-24

- Free e Pro: risultato, Modifica con input cambiati, ricalcolo: in "Le mie stime" resta UNA stima, stessa posizione (`created_at` invariato, da confermare che vada bene), valori nuovi; il dettaglio Pro mostra i valori nuovi.
- Modifica senza cambiare nulla: nessun record in piu' (G12).
- Premere Modifica subito dopo il risultato (POST ancora in volo): nessun doppione.
- Stima nuova da pagina aperta da zero: crea un record nuovo.
- Free che attiva Pro e poi Modifica: la stima resta Free.
- Modifica ripetuta piu' volte: sempre la stessa stima.
- Budget: cambiato prima/dopo Modifica, allineato alla stima salvata.
