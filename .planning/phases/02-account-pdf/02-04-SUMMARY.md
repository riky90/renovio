---
phase: 02-account-pdf
plan: 04
subsystem: auth-frontend
tags: [react-router, react-query, shadcn, cookie-session]

# Dependency graph
requires:
  - phase: 02-account-pdf
    plan: 03
    provides: "Router HTTP auth completo (POST /auth/registrati|login|logout, GET /auth/me) con cookie httpOnly reale"
provides:
  - "client.ts/auth.ts con credentials:'include' su tutte le fetch autenticate (Pitfall 4)"
  - "hooks/useAuth.ts: useQuery(['me']) + mutazioni login/registrazione/logout"
  - "Router client-side (react-router) con /, /registrati, /accedi"
  - "RegistratiPage/AccediPage (card 400px, validazione on-blur, CTA accent, bottone Google outline)"
  - "AccountMenu (avatar iniziali + dropdown Le mie stime/Esci)"
  - "EstimatePage: header con stato sessione (AccountMenu / bottone Accedi / skeleton)"
affects: [02-05, 02-06, 02-08, 02-09]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "apiPost<T> in client.ts gestisce esplicitamente 204 No Content (logout) restituendo undefined, per non far crashare response.json() su corpo vuoto"
    - "getMe() tratta 401 come stato 'non autenticato' (ritorna null), non come errore rumoroso — coerente con lo state anonimo dell'app"
    - "useAuth() centralizza query+mutazioni; ogni mutazione fa setQueryData(['me']) ottimistico + invalidateQueries per riflettere subito lo stato nell'header"
    - "Bottoni Google (Continua con Google / Accedi con Google) sono anchor <a> verso ${VITE_API_BASE}/auth/google/login, non fetch — il flusso OAuth richiede una navigazione reale del browser"

key-files:
  created:
    - frontend/src/api/auth.ts
    - frontend/src/hooks/useAuth.ts
    - frontend/src/routes/RegistratiPage.tsx
    - frontend/src/routes/AccediPage.tsx
    - frontend/src/components/AccountMenu.tsx
    - frontend/src/components/ui/avatar.tsx
    - frontend/src/components/ui/dropdown-menu.tsx
  modified:
    - frontend/src/api/client.ts
    - frontend/src/App.tsx
    - frontend/src/pages/EstimatePage.tsx

key-decisions:
  - "main.tsx non modificato: QueryClientProvider già avvolge App, e App ora monta RouterProvider al suo interno — soddisfa il requisito 'QueryClientProvider avvolge il router' senza toccare il file"
  - "/password-dimenticata linkato da AccediPage ma non ancora registrato come rotta (arriva nel Plan 06, come da testo del piano) — nessun blocco, coerente con la sequenza dei piani"

requirements-completed: [AUTH-01, AUTH-03]

# Metrics
duration: 20min
completed: 2026-08-25
---

# Phase 2 Plan 4: Frontend autenticazione (router, pagine, sessione) Summary

**Router react-router con /registrati e /accedi, hook useAuth (sessione + mutazioni), AccountMenu con logout, e client.ts/auth.ts aggiornati con `credentials: "include"` per il cookie httpOnly cross-origin in dev — Task 1 e Task 2 completati e committati; Task 3 (checkpoint umano di verifica browser) resta aperto su richiesta esplicita dell'utente, che lo eseguirà manualmente.**

## Performance

- **Duration:** ~20 min (Task 1 + Task 2)
- **Tasks:** 2/3 completati (Task 3 è un checkpoint umano, non eseguibile dall'agente)
- **Files modified:** 10 (7 creati, 3 modificati)

## Accomplishments

- `frontend/src/api/client.ts`: `apiGet`/`apiPost` con `credentials: "include"`; `apiPost` gestisce il 204 No Content (logout) senza tentare il parsing JSON su corpo vuoto.
- `frontend/src/api/auth.ts`: `postRegistrazione`, `postLogin`, `postLogout`, `getMe` verso `/auth/*`; `getMe` tratta 401 come utente anonimo (ritorna `null`), non come errore.
- `frontend/src/hooks/useAuth.ts`: `useAuth()` espone `user`/`isLoading` (da `useQuery(['me'])`) e le mutazioni `login`/`registrazione`/`logout`, ciascuna con aggiornamento ottimistico + invalidazione della query di sessione.
- shadcn `avatar` e `dropdown-menu` installati dal registry ufficiale (nessuna nuova dipendenza npm: entrambi coperti dal pacchetto `radix-ui` già presente).
- `frontend/src/App.tsx`: `createBrowserRouter` con le rotte `/` (EstimatePage), `/registrati` (RegistratiPage), `/accedi` (AccediPage).
- `frontend/src/routes/RegistratiPage.tsx` e `AccediPage.tsx`: card centrata 400px, campi con validazione on-blur (copy da UI-SPEC), CTA accent full-width 44px, divisore "oppure", bottone outline "Continua con Google"/"Accedi con Google" verso `/auth/google/login`, footer di navigazione incrociata, alert destructive su errore (email già registrata / credenziali non valide, campi preservati).
- `frontend/src/components/AccountMenu.tsx`: avatar con iniziali da Nome, dropdown con nome+email non interattivi, "Le mie stime", "Esci" (logout mutation + redirect a `/`).
- `frontend/src/pages/EstimatePage.tsx`: header con titolo a sinistra e, a destra, `AccountMenu` (loggato) / bottone outline "Accedi" (anonimo) / skeleton circolare durante il session-check — nessun blocco del resto della pagina durante il check.

## Task Commits

1. **Task 1: client credentials + api/auth.ts + useAuth hook** - `59abe8d` (feat)
2. **Task 2: Router react-router + pagine registrati/accedi + AccountMenu + header** - `b315a67` (feat)
3. **Task 3: Verifica manuale flusso login/logout** - checkpoint `human-verify` (`gate="blocking"`), **non eseguito dall'agente**: il codice è pronto, la verifica in browser resta in carico all'utente per sua scelta esplicita.

**Plan metadata:** (commit successivo con SUMMARY.md/STATE.md/ROADMAP.md)

## Files Created/Modified

- `frontend/src/api/client.ts` - `apiGet`/`apiPost` con `credentials:"include"`, gestione 204
- `frontend/src/api/auth.ts` - client API auth (registrati/login/logout/me)
- `frontend/src/hooks/useAuth.ts` - hook sessione + mutazioni
- `frontend/src/App.tsx` - router react-router
- `frontend/src/routes/RegistratiPage.tsx` - schermata registrazione
- `frontend/src/routes/AccediPage.tsx` - schermata login
- `frontend/src/components/AccountMenu.tsx` - menu account (avatar + dropdown)
- `frontend/src/components/ui/avatar.tsx` - primitivo shadcn (net-new)
- `frontend/src/components/ui/dropdown-menu.tsx` - primitivo shadcn (net-new)
- `frontend/src/pages/EstimatePage.tsx` - header con stato sessione

## Decisions Made

- `apiPost<T>` restituisce `undefined as T` su risposta 204 — necessario per `postLogout()` che altrimenti farebbe crashare `response.json()` su un corpo vuoto (bug non esplicitato dal piano, corretto inline durante Task 1 — Rule 1).
- `main.tsx` lasciato invariato: il piano lo elencava tra i `files_modified` ma la struttura esistente (QueryClientProvider avvolge App) già soddisfa il vincolo "QueryClientProvider avvolge il router" una volta che App monta il RouterProvider al suo interno — nessuna modifica necessaria, nessuna deviazione di comportamento.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `apiPost` non gestiva il 204 No Content di `/auth/logout`**
- **Found during:** Task 1, scrittura di `api/auth.ts` (`postLogout`)
- **Issue:** l'implementazione iniziale di `apiPost<T>` chiamava sempre `response.json()`; su una risposta 204 (nessun corpo) `response.json()` lancia un errore di parsing, rompendo il logout.
- **Fix:** aggiunto un controllo esplicito `if (response.status === 204) return undefined as T;` prima del parsing JSON.
- **Files modified:** `frontend/src/api/client.ts`
- **Verification:** `npx tsc --noEmit` verde; revisione logica del flusso (204 -> undefined, altri status -> json).
- **Committed in:** `59abe8d` (parte del commit Task 1)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug)
**Impact on plan:** Nessuno scope creep: il fix era necessario perché il piano stesso richiede `postLogout()` verso un endpoint che risponde 204 (confermato da 02-03-SUMMARY.md).

## Issues Encountered

Nessuno oltre alla deviazione sopra documentata.

## User Setup Required

Nessuna azione di configurazione esterna richiesta per Task 1/2. **Task 3 richiede un'azione manuale dell'utente**: avviare backend (`http://localhost:8000`) e frontend (`http://localhost:5173`) e verificare a mano il flusso registrazione → cookie HttpOnly → logout → re-login → credenziali errate, come descritto nel piano (`02-04-PLAN.md`, Task 3). Non è un'installazione di pacchetti, è la verifica browser che l'utente ha scelto di eseguire personalmente.

## Next Phase Readiness

- Codice del Plan 04 completo e verificato via typecheck (`npx tsc --noEmit` verde su entrambi i task).
- **Gate aperto:** il checkpoint `human-verify` (Task 3) non è stato approvato — resta da eseguire manualmente dall'utente prima di considerare il Plan 04 chiuso end-to-end. Nessun blocco per iniziare Plan 05/06/altro lavoro indipendente, ma il flusso login/logout reale in browser non è stato ancora confermato in questa sessione.
- Nessun impatto sui piani successivi: le interfacce (`useAuth`, `api/auth.ts`, `AccountMenu`) sono stabili e pronte per essere consumate da `LeMieStimePage` (Plan 09) e dal flusso soft-wall (Plan 08/09, D-07).

---
*Phase: 02-account-pdf*
*Completed: 2026-08-25 (Task 1-2; Task 3 in attesa di verifica manuale dell'utente)*

## Self-Check: PASSED
Tutti i file dichiarati (10) e i commit dichiarati (`59abe8d`, `b315a67`, `a8d9a15`) verificati presenti su disco / in git log. Task 3 resta come checkpoint umano aperto (non un fallimento del self-check: è per design il gate che l'utente ha scelto di eseguire manualmente).
