---
phase: 04-lead-pannello-admin
plan: 11
subsystem: frontend-admin
tags: [lead, referenti, admin, crud, react-query]
dependency-graph:
  requires: ["04-04 (backend lead+referenti CRUD)", "04-07 (AdminLayout/AdminTable/AdminCrudDialog/AdminDeleteConfirm, stub pages)"]
  provides: ["frontend/src/pages/admin/LeadDashboardPage.tsx (reale)", "frontend/src/pages/admin/ReferentiPage.tsx (reale)", "frontend/src/api/admin/lead.ts", "frontend/src/api/admin/referenti.ts"]
  affects: ["/admin/lead", "/admin/referenti"]
tech-stack:
  added: []
  patterns: ["useQuery list+detail toggle (analog LeMieStimePage)", "AdminTable/AdminCrudDialog/AdminDeleteConfirm riuso da 04-07", "toNumber Decimal-as-string normalize (analog stima.ts)"]
key-files:
  created:
    - frontend/src/api/admin/lead.ts
    - frontend/src/api/admin/referenti.ts
  modified:
    - frontend/src/pages/admin/LeadDashboardPage.tsx
    - frontend/src/pages/admin/ReferentiPage.tsx
decisions:
  - "Città filtro lead + select città/listino referenti popolati da GET /admin/listini (listListiniForSelect in referenti.ts, riusato da entrambe le pagine) invece di derivare le città dai soli lead in lista — coerente con la regola di dominio 'città = selettore del listino'."
  - "Riga lead cliccabile implementata avvolgendo il contenuto di ogni cella in un div con onClick (AdminTable è fuori scope per questo piano, nessuna modifica al componente condiviso)."
  - "Switch 'attivo' nella tabella referenti è un toggle rapido (PATCH immediato) oltre al campo switch nel dialog di modifica — nessun conflitto, entrambi scrivono sullo stesso campo."
  - "Toast di successo per delete referente riusa la copy generica 'Modifica salvata' (UI-SPEC non specifica una copy dedicata per il toast di delete, solo per l'alert-dialog di conferma)."
metrics:
  duration: "~1h"
  completed: "2026-08-28"
---

# Phase 04 Plan 11: Dashboard lead + CRUD referenti (UI reale) Summary

Riempite le pagine stub `LeadDashboardPage`/`ReferentiPage` (create in 04-07) sopra i backend admin di 04-04: dashboard lead con filtri città/stato, dettaglio a range con aggiornamento stato/nota, e CRUD referenti con switch attivo/priorità e conferma distruttiva.

## What was built

- **`frontend/src/api/admin/lead.ts`** — `getAdminLeads(filters)`, `getAdminLead(id)`, `updateAdminLead(id, {stato, nota})`. Normalizza `totale_min`/`totale_max` (wire Decimal-as-string) con `toNumber`, stesso pattern di `api/stima.ts`. `LeadOut` non ha nessun campo margine impresa (struttura ereditata 1:1 dal backend `LeadOut`).
- **`frontend/src/pages/admin/LeadDashboardPage.tsx`** — lista in `AdminTable` (colonne Data/Città/Nome/Contatti/Totale stima/Stato), filtri città (popolati da `GET /admin/listini`) e stato (`Nuovo`/`Gestito`), link "Rimuovi filtri", empty-state vero vs filtrato distinti. Riga cliccabile apre il dettaglio in `AdminCrudDialog` (entityLabel="nota e stato" → CTA "Salva nota e stato" automatica) con sezioni Dati di contatto / Stima allegata (range, tabular-nums) / Nota interna (select stato + textarea nota). Salvataggio → `updateAdminLead` → toast "Lead aggiornato" + invalidate `["admin-leads"]`/`["admin-lead-detail"]`.
- **`frontend/src/api/admin/referenti.ts`** — `listReferenti/createReferente/updateReferente/deleteReferente` + `listListiniForSelect` (GET /admin/listini, riusato anche da LeadDashboardPage per il filtro città).
- **`frontend/src/pages/admin/ReferentiPage.tsx`** — `AdminTable` (nome/email/telefono/città-listino/attivo-switch/priorità/azioni), header "Aggiungi referente" → `AdminCrudDialog` (select città/listino, nome, email, telefono, switch attivo, input numerico priorità), Modifica/Elimina per riga con `aria-label`, `AdminDeleteConfirm` con copy "Eliminare {nome}? Non riceverà più i lead di questa città." Switch attivo in tabella funge anche da toggle rapido (PATCH immediato).

## Deviations from Plan

### Auto-fixed Issues

Nessuna — nessun bug o blocco incontrato durante l'esecuzione.

### Notes (non-deviation, executor judgment within Open Questions)

1. **Riga lead cliccabile senza modificare `AdminTable.tsx`** — il componente condiviso (fuori scope per questo piano, riusato da altre pagine 04-08/04-09/04-10) non espone un `onRowClick`. Implementato avvolgendo ogni cella in un `<div onClick=...>` così l'intera area di testo della riga è cliccabile (leggera differenza dal "riga intera edge-to-edge" descritto in UI-SPEC §C, ma stesso comportamento funzionale — apre il dettaglio).
2. **Dialog dettaglio lead a `max-width` default (~448px, `sm:max-w-md`)** anziché i 560px indicati in UI-SPEC §C — `AdminCrudDialog` (riusato, fuori scope) non espone un prop di larghezza. Il contenuto rimane leggibile; nessun overflow riscontrato nella verifica del build.
3. **Città filtro/select popolate da `GET /admin/listini`** invece che dai soli lead esistenti in lista, per coerenza con la regola di dominio "città = selettore del listino" e per avere sempre tutte le città disponibili anche con lista lead vuota/filtrata.

## Known Stubs

Nessuno — entrambe le pagine sono cablate end-to-end sui backend 04-04 (nessun dato hardcoded, nessun placeholder "coming soon").

## Threat Flags

Nessuna nuova superficie: entrambe le pagine consumano solo le rotte `admin/lead` e `admin/referenti` già coperte dal threat register del piano (`require_admin` server-side, T-04-43/44/45), nessun nuovo endpoint/pattern di accesso introdotto lato frontend.

## Verification

- `npx tsc -b --noEmit` (via `frontend/node_modules/.bin/tsc` del checkout principale, junction `node_modules` nel worktree) → **pulito**, nessun errore.
- Grep anti-leak — `coefficiente_impresa|base_eur_mq` su tutti e 4 i file assegnati → **nessun match** (il commento iniziale di `lead.ts` è stato riformulato per non contenere le stringhe letterali, mantenendo lo stesso significato).

## CHECKPOINT: OPEN (Task 3 — checkpoint:human-verify)

**Tipo:** human-verify (gate="blocking")
**Stato:** non eseguibile in questo contesto (nessun ambiente backend/DB seedato disponibile in questo worktree di esecuzione automatica) — registrato come **checkpoint aperto**, non bloccante per il commit del codice.

**Cosa verificare manualmente (dall'orchestratore o da un run successivo):**
1. Login come admin; `/admin/referenti`: creare un referente attivo su una città (switch attivo, priorità), poi modificarlo ed eliminarlo (conferma distruttiva "Eliminare {nome}? Non riceverà più i lead di questa città.").
2. Generare un lead (flusso 04-06), poi `/admin/lead`: filtrare per città/stato, aprire il dettaglio (snapshot a range, nessun prezzo impresa visibile), impostare "gestito" + nota, salvare → verificare il toast "Lead aggiornato".
3. Verificare gli empty-state (vero vs filtrato) rimuovendo/aggiungendo filtri.

**Resume-signal atteso:** "approvato" oppure descrizione dei problemi riscontrati.

## Self-Check

- `frontend/src/api/admin/lead.ts` — FOUND
- `frontend/src/api/admin/referenti.ts` — FOUND
- `frontend/src/pages/admin/LeadDashboardPage.tsx` — FOUND (modificato, non più stub)
- `frontend/src/pages/admin/ReferentiPage.tsx` — FOUND (modificato, non più stub)
- Commit `2f80d83` (feat: dashboard lead) — FOUND in `git log`
- Commit `223ffba` (feat: CRUD referenti) — FOUND in `git log`

## Self-Check: PASSED
