---
phase: 04-lead-pannello-admin
plan: 09
subsystem: frontend-admin-citta-testi
tags: [admin, crud, citta, testi, disclaimer, react-query]
dependency-graph:
  requires: ["04-07", "04-03"]
  provides:
    - "api/admin/citta.ts (client CRUD ComuneListino + list/patch TipoRistrutturazione)"
    - "api/admin/testi.ts (client GET/PATCH testi key/value)"
    - "CittaTestiPage.tsx reale (mappature città, tipi, testi)"
  affects:
    - "frontend/src/pages/admin/CittaTestiPage.tsx"
tech-stack:
  added: []
  patterns:
    - "listListiniOptions() locale in api/admin/citta.ts (non in api/admin/listini.ts, che è di competenza 04-08 in parallelo) per popolare il select listino senza toccare file fuori dal perimetro files_modified"
    - "toNumber locale per normalizzare Decimal->stringa (range_pct) dal wire, stesso pattern di api/stima.ts"
key-files:
  created:
    - frontend/src/api/admin/citta.ts
    - frontend/src/api/admin/testi.ts
  modified:
    - frontend/src/pages/admin/CittaTestiPage.tsx
decisions:
  - "Sezioni Mappature/Tipi/Testi come 3 <section> impilate verticalmente (non tabs), coerente con §D generico; nessuna nuova primitiva richiesta"
  - "Tipi di ristrutturazione: solo edit (nessun add/delete) — il backend 04-03 espone solo list/patch per TipoRistrutturazione, coerente col piano"
  - "Testi: solo edit (nessun add/delete) — chiavi seedate da scripts/seed.py, il backend espone solo GET lista + PATCH valore"
metrics:
  duration: "~30 min"
  completed: "2026-08-28"
---

# Phase 04 Plan 09: Città e testi — CRUD mappature/tipi + disclaimer key/value Summary

Pagina `/admin/citta-testi` reale sopra il backend 04-03: CRUD mappatura città→listino (upsert/patch/delete `ComuneListino`), edit tipi di ristrutturazione (`TipoRistrutturazione`), edit testi/disclaimer key/value (`Testo`) — riusando il pattern CRUD condiviso `AdminTable`/`AdminCrudDialog`/`AdminDeleteConfirm` di 04-07.

## What Was Built

- **`frontend/src/api/admin/citta.ts`**: `listComuni`/`createComune`/`updateComune`/`deleteComune` (mai `comune_slug` nel body — ricalcolato server-side, T-04-12); `listTipi`/`updateTipo` con `range_pct` normalizzato via `toNumber` (Decimal→stringa sul wire, stesso pattern di `api/stima.ts`); `listListiniOptions()` — GET minimale su `/admin/listini` per popolare il select "listino mappato" nel dialog mappatura, tenuto qui (non in un `api/admin/listini.ts` condiviso) per restare nel perimetro `files_modified` del piano mentre 04-08 costruisce in parallelo il client listini/voci completo.
- **`frontend/src/api/admin/testi.ts`**: `listTesti`/`updateTesto` (solo `valore` è editabile, nessuna create/delete — le chiavi sono seedate).
- **`frontend/src/pages/admin/CittaTestiPage.tsx`**: tre sotto-sezioni impilate dentro `AdminLayout`:
  1. **Mappature città→listino** — `AdminTable` (comune · listino mappato · codice ISTAT · azioni), "Aggiungi mappatura" → `AdminCrudDialog` (comune_nome, select listino, codice_istat opzionale, "Salva mappatura"), elimina → `AdminDeleteConfirm` con copy "Eliminare questa mappatura città→listino? Le stime già salvate non saranno modificate." (D-11).
  2. **Tipi di ristrutturazione** — `AdminTable` (nome · ordine · range %) + edit dialog "Salva tipo" (solo modifica, nessun add/delete lato backend).
  3. **Testi e disclaimer** — `AdminTable` (chiave · valore) + edit dialog con `Textarea` "Salva testo".
  Ogni save mostra toast "Modifica salvata" (sonner); ogni icon-button (Modifica/Elimina) ha `title` + `aria-label`; ogni dialog ha una sola primary CTA "Salva {entità}".

## Verification

- `npx tsc --noEmit` (frontend) pulito — nessun errore. `node_modules` era assente nel worktree (git-worktree, gitignored): creata una junction temporanea `New-Item -ItemType Junction` verso `frontend/node_modules` del repo principale per eseguire tsc/vite senza reinstallare le dipendenze, poi rimossa (nessun file tracciato toccato, `git status` confermato pulito prima del commit).
- `npx vite build` completata con successo (`dist/` rimosso dal worktree dopo la verifica, non committato — è gitignored).
- `grep -n "updateTesto" frontend/src/pages/admin/CittaTestiPage.tsx` conferma il collegamento richiesto dal piano.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `node_modules` assente nel worktree**
- **Trovato durante:** verifica `npx tsc --noEmit` (Task 1)
- **Problema:** stesso scenario documentato in 04-07-SUMMARY.md — il worktree non ha `node_modules/` installato (gitignored, non incluso nel checkout del branch).
- **Fix:** junction PowerShell temporanea verso il `node_modules` del repo principale (più veloce di un `npm install` completo per la sola verifica di build), rimossa subito dopo `tsc`/`vite build`.
- **File modificati:** nessuno (solo `node_modules`, non tracciato in git; repo principale verificato intatto dopo la rimozione).
- **Commit:** n/a.

Nessun'altra deviazione: il resto del piano è stato eseguito come scritto.

## Open Checkpoint

**Task 2 (checkpoint:human-verify, gate="blocking") — NON eseguito, richiede verifica visiva/funzionale umana con backend+DB reali.**

Il piano richiede, dopo login admin reale:
1. Aggiungere una mappatura città→listino e verificare che una stima Free per quella città smetta di andare in fallback.
2. Eliminare una mappatura e confermare che l'`alert-dialog` chiarisca che le stime salvate non cambiano.
3. Modificare il testo `disclaimer_fallback_citta` e verificare che il disclaimer mostrato per una città senza listino rifletta il nuovo valore.
4. Modificare un tipo di ristrutturazione e verificare la persistenza.

Questi passi richiedono un server backend in esecuzione con DB seedato e una sessione admin autenticata — non eseguibili in questo contesto worktree-only (nessun server avviato, nessuna sessione browser). Ho verificato **programmaticamente** ciò che è verificabile senza browser/sessione reale:
- Build (`tsc --noEmit` + `vite build`) pulita, nessun errore di tipo.
- `api/admin/citta.ts` non invia mai `comune_slug` nel body di `createComune`/`updateComune` (ispezione statica — il campo non è nemmeno presente in `ComuneListinoBody`).
- `range_pct`/i numerici del body inviato dal form (`Number(form.range_pct)`, `Number(form.listino_id)`, `Number(form.ordine)`) sono normalizzati prima dell'invio; i valori ricevuti (`range_pct`) sono normalizzati con `toNumber` alla ricezione.
- L'elimina mappatura passa sempre da `AdminDeleteConfirm` con la copy esatta del contratto UI-SPEC ("Eliminare questa mappatura città→listino? Le stime già salvate non saranno modificate.").
- Ogni icon-button ha `aria-label="Modifica"`/`aria-label="Elimina"`; ogni `AdminCrudDialog` ha una sola primary CTA "Salva {entità}" (shell condivisa, invariata da 04-07).

La verifica visiva/funzionale in browser con account admin reale e DB seedato resta **aperta** e va eseguita da un umano (o da un agente con accesso a backend+DB) prima di considerare il checkpoint "approvato". Non ho bloccato l'esecuzione in attesa: ho committato tutto il lavoro del Task 1 e restituito questo SUMMARY, come da istruzione del piano padre.

## Known Stubs

Nessuno stub introdotto da questo piano: le tre sotto-sezioni sono completamente cablate contro API reali (`listComuni`/`listTipi`/`listTesti` via `useQuery`, mutazioni via `useMutation` con invalidazione della query cache al successo).

## Threat Flags

Nessuna nuova superficie non prevista dal `threat_model` del piano (T-04-34/35/36/37 già coprono guard client-side, tampering mappatura/comune_slug, information disclosure testi, tampering placeholder testo).

## Self-Check: PASSED

- FOUND: frontend/src/api/admin/citta.ts
- FOUND: frontend/src/api/admin/testi.ts
- FOUND: frontend/src/pages/admin/CittaTestiPage.tsx
- FOUND commit 49ef1ac (feat(04-09): CRUD città/mappature/tipi + testi disclaimer in admin)
