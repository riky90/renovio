---
phase: 04-lead-pannello-admin
plan: 07
subsystem: frontend-admin-shell
tags: [admin, react-router, shadcn, guard, crud-shell]
dependency-graph:
  requires: ["04-04"]
  provides:
    - "AdminLayout (shell /admin con guard client-side)"
    - "AdminTable/AdminCrudDialog/AdminDeleteConfirm (componenti CRUD condivisi)"
    - "api/admin/client.ts (apiPatch/apiDelete)"
    - "5 rotte /admin/* registrate in App.tsx con pagine stub"
  affects:
    - "frontend/src/App.tsx"
tech-stack:
  added:
    - "shadcn: table, tabs, switch, alert-dialog (official registry)"
  patterns:
    - "Guard client-side PRIMA di ogni fetch in AdminLayout (nessun flash dati non-admin)"
    - "Componenti CRUD condivisi generici (nessun campo hardcoded)"
key-files:
  created:
    - frontend/src/components/ui/table.tsx
    - frontend/src/components/ui/tabs.tsx
    - frontend/src/components/ui/switch.tsx
    - frontend/src/components/ui/alert-dialog.tsx
    - frontend/src/api/admin/client.ts
    - frontend/src/pages/admin/AdminLayout.tsx
    - frontend/src/components/admin/AdminTable.tsx
    - frontend/src/components/admin/AdminCrudDialog.tsx
    - frontend/src/components/admin/AdminDeleteConfirm.tsx
    - frontend/src/pages/admin/LeadDashboardPage.tsx
    - frontend/src/pages/admin/ReferentiPage.tsx
    - frontend/src/pages/admin/ListiniPage.tsx
    - frontend/src/pages/admin/CoefficientiPage.tsx
    - frontend/src/pages/admin/CittaTestiPage.tsx
  modified:
    - frontend/src/App.tsx
decisions:
  - "Lead detail: dialog (default UI-SPEC Open Question #1) — non applicabile a questo piano (fondazione), ma coerente per 04-11"
  - "Sidebar attiva: confronto esatto location.pathname === item.path (nessun matching per prefisso, le 5 rotte sono foglie senza sotto-rotte)"
metrics:
  duration: "~35 min"
  completed: "2026-08-28"
---

# Phase 04 Plan 07: Fondazione area /admin — shell, guard, componenti CRUD condivisi, rotte stub Summary

Shell dell'area `/admin` con guard client-side role="admin", sidebar desktop/tabs mobile sulle 5 sezioni, componenti CRUD generici riusabili (AdminTable/AdminCrudDialog/AdminDeleteConfirm), client `apiPatch/apiDelete`, e le 5 rotte registrate in App.tsx con pagine stub — nessun contenuto reale, solo fondazione (D-21, ADM-04).

## What Was Built

- **shadcn primitives** (`table`, `tabs`, `switch`, `alert-dialog`) installati dal registry ufficiale via `npx shadcn add`.
- **`frontend/src/api/admin/client.ts`**: `apiPatch<T>`/`apiDelete` con lo stesso pattern di `api/client.ts` (stesso `API_BASE` guard, `ApiError`, `credentials: "include"`, short-circuit 204); riesporta `apiGet`/`apiPost`/`ApiError`.
- **`frontend/src/pages/admin/AdminLayout.tsx`**: guard client-side — se `!isLoading && (!user || user.role !== "admin")` mostra blocco "Accesso negato" (heading + body + CTA verso "/"), **senza mai fare fetch di dati admin prima del guard** (mitigazione T-04-27). Sidebar `w-64` desktop (≥768px) con 5 voci + icone lucide (Inbox/Tags/SlidersHorizontal/MapPin/Users), voce attiva con accent left-border + testo; tabs orizzontali su mobile (<768px). Header condiviso con `AccountMenu` + badge neutro "Admin".
- **Componenti condivisi generici** (T-04-28 — nessun campo dati hardcoded):
  - `AdminTable.tsx`: contenitore `table` + skeleton rows (row-height 40px) durante il caricamento + empty-state testuale.
  - `AdminCrudDialog.tsx`: shell dialog con form iniettato dalla pagina, singola primary CTA "Salva {entità}" + secondaria "Annulla modifica".
  - `AdminDeleteConfirm.tsx`: `alert-dialog` con "Elimina {entità}" (destructive) / "Annulla" (bare, 1:1-paired).
- **5 pagine stub** (`LeadDashboardPage`, `ReferentiPage`, `ListiniPage`, `CoefficientiPage`, `CittaTestiPage`): renderizzano solo il proprio heading dentro `AdminLayout` — contenuto reale demandato a 04-08 (Listini/Coefficienti+Upload), 04-09 (Città/Testi), 04-11 (Lead+Referenti).
- **`App.tsx`**: registrate `/admin/lead`, `/admin/listini`, `/admin/coefficienti`, `/admin/citta-testi`, `/admin/referenti` + redirect `/admin` → `/admin/lead`.

## Verification

- `npx tsc -b` (frontend, dopo `npm install` — `node_modules` non era presente nel worktree) pulito, nessun errore.
- `npx vite build` completata con successo (build artifact rimosso dal worktree dopo la verifica, non committato).
- `grep -n "/admin" frontend/src/App.tsx` conferma le 5 rotte + redirect registrate.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `node_modules` assente nel worktree**
- **Trovato durante:** verifica `npx tsc --noEmit` (Task 1)
- **Problema:** il worktree non aveva `node_modules/` installato, `npx tsc` scaricava un pacchetto placeholder sbagliato (`tsc@2.0.4` da npm, non il TypeScript del progetto).
- **Fix:** eseguito `npm install` in `frontend/` (431 pacchetti, 0 vulnerabilità), poi `npx tsc -b` e `npx vite build` sono passati puliti.
- **File modificati:** nessuno (solo `node_modules`, non tracciato in git).
- **Commit:** n/a (nessun file sorgente coinvolto).

Nessun'altra deviazione: il resto del piano è stato eseguito come scritto.

## Open Checkpoint

**Task 2 (checkpoint:human-verify, gate="blocking") — NON eseguito, richiede verifica visiva umana.**

La verifica richiede login reale con un account admin (email = `ADMIN_EMAIL`) e ispezione visiva in browser di:
1. Redirect `/admin` → `/admin/lead` e sidebar con 5 sezioni + badge "Admin" per un admin loggato.
2. Blocco "Accesso negato" (nessun dato admin, nessun flash) per un utente non-admin/anonimo su `/admin`.
3. Evidenziazione (accent) della voce sidebar attiva sulla sezione corrente.

Ho verificato **programmaticamente** ciò che è verificabile senza browser/sessione reale:
- Build (`tsc -b` + `vite build`) pulita.
- Le 5 rotte sono registrate e puntano a `AdminLayout`/pagine stub corrette.
- Il guard in `AdminLayout.tsx` controlla `user.role !== "admin"` **prima** di ogni render di contenuto admin e non effettua alcuna fetch di dati admin nel ramo "Accesso negato" (ispezione statica del codice — nessuna query `useQuery`/`apiGet` è presente prima del return del blocco guard).

La verifica visiva/funzionale in browser con account reale resta **aperta** e va eseguita da un umano (o da un agente con accesso a backend+DB seed) prima di considerare il checkpoint "approvato". Non ho bloccato l'esecuzione in attesa: ho committato tutto il lavoro del Task 1 e restituito questo SUMMARY, come da istruzione del piano padre.

## Known Stubs

Le 5 pagine `LeadDashboardPage`/`ReferentiPage`/`ListiniPage`/`CoefficientiPage`/`CittaTestiPage` sono stub intenzionali (solo heading di sezione, nessun dato/fetch) — da riempire in 04-08 (Listini/Coefficienti), 04-09 (Città/Testi), 04-11 (Lead/Referenti), come esplicitamente previsto dal piano.

## Self-Check: PASSED

- FOUND: frontend/src/components/ui/table.tsx
- FOUND: frontend/src/components/ui/tabs.tsx
- FOUND: frontend/src/components/ui/switch.tsx
- FOUND: frontend/src/components/ui/alert-dialog.tsx
- FOUND: frontend/src/api/admin/client.ts
- FOUND: frontend/src/pages/admin/AdminLayout.tsx
- FOUND: frontend/src/components/admin/AdminTable.tsx
- FOUND: frontend/src/components/admin/AdminCrudDialog.tsx
- FOUND: frontend/src/components/admin/AdminDeleteConfirm.tsx
- FOUND: frontend/src/pages/admin/LeadDashboardPage.tsx
- FOUND: frontend/src/pages/admin/ReferentiPage.tsx
- FOUND: frontend/src/pages/admin/ListiniPage.tsx
- FOUND: frontend/src/pages/admin/CoefficientiPage.tsx
- FOUND: frontend/src/pages/admin/CittaTestiPage.tsx
- FOUND commit e790028 (chore: shadcn primitives)
- FOUND commit f63d39b (feat: fondazione area /admin)
