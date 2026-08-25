# Phase 2: Account & PDF - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-25
**Phase:** 2-Account & PDF
**Areas discussed:** Strategia auth & sessione, Salvataggio stima anonima → account, Storico stime & snapshot, PDF Free (gate + contenuto), Verifica email & reset password, Collisione Google↔password, Campi registrazione, Contenuto & file PDF

---

## Strategia auth (backend)

| Option | Description | Selected |
|--------|-------------|----------|
| Self-hosted FastAPI | users nel Postgres, bcrypt/argon2, Google via Authlib, controllo totale, nessun lock-in | ✓ |
| Supabase (managed) | auth gestita, ma user fuori dal DB da sincronizzare | |
| Auth0 / Clerk (managed) | velocissimo ma lock-in/costo, id esterni da mappare | |

**User's choice:** Self-hosted FastAPI
**Notes:** Coerente col resto del dominio (tutti i dati in un solo Postgres); era già segnata come decisione di build aperta in STATE.

## Sessione

| Option | Description | Selected |
|--------|-------------|----------|
| Cookie httpOnly | JWT/session id in cookie httpOnly+SameSite, immune a XSS, logout pulito | ✓ |
| Token JWT in localStorage | header Authorization, esposto a XSS, refresh a mano | |

**User's choice:** Cookie httpOnly

## Ruolo admin (bootstrap)

| Option | Description | Selected |
|--------|-------------|----------|
| Seed/env da variabile | role user/admin, primo admin via seed o ADMIN_EMAIL; ruolo+guard in Fase 2, UI in Fase 4 | ✓ |
| Promozione manuale in DB | ci si registra e ci si promuove via query | |

**User's choice:** Seed/env da variabile

---

## Salvataggio stima anonima → account

| Option | Description | Selected |
|--------|-------------|----------|
| Salva-al-signup della stima corrente | la stima nel browser viene salvata alla registrazione; poi auto-save da loggato | ✓ |
| Persisti-poi-reclama | ogni stima salvata anonima con token, reclamata al signup; più complesso | |
| Salva solo da loggato | nessun collegamento retroattivo; perde la stima che ha spinto a registrarsi | |

**User's choice:** Salva-al-signup della stima corrente

---

## Storico stime

| Option | Description | Selected |
|--------|-------------|----------|
| Storico "Le mie stime" | lista consultabile di tutte le stime salvate; Fase 3 ci si appoggia | ✓ |
| Solo l'ultima stima | un'unica stima sovrascritta | |

**User's choice:** Storico "Le mie stime"

## Snapshot vs ricalcolo

| Option | Description | Selected |
|--------|-------------|----------|
| Snapshot: numeri congelati | input+risultato congelati, immutabili, coerenti col PDF | ✓ |
| Ricalcolo dagli input | solo input, ricalcolo a ogni vista; il PDF già scaricato non combacia più | |

**User's choice:** Snapshot: numeri congelati (si tengono anche gli input per il ricalcolo Pro esplicito)

---

## PDF Free — gate

| Option | Description | Selected |
|--------|-------------|----------|
| Solo utente loggato | dietro account, coerente con soft-wall, rafforza il funnel | ✓ |
| Anche anonimo | più aperto ma toglie una leva di registrazione | |

**User's choice:** Solo utente loggato

## PDF Free — generazione

| Option | Description | Selected |
|--------|-------------|----------|
| Server-side, contenuto = schermata risultato | FastAPI dallo snapshot, anti-leak garantito, riusabile per Pro | ✓ |
| Client-side (dal browser) | jsPDF/html2canvas, meno controllo su branding/anti-leak | |

**User's choice:** Server-side dallo snapshot

---

## Verifica email & reset password

| Option | Description | Selected |
|--------|-------------|----------|
| No verifica + reset via link | nessun gate di verifica; reset via email (serve email transazionale ora) | ✓ |
| Verifica email + reset (completo) | account da confermare + reset; più attrito e lavoro | |
| Nessuno dei due in v1 | zero dipendenza email; password dimenticata = account morto | |

**User's choice:** No verifica + reset via link

## Collisione Google ↔ password (stessa email)

| Option | Description | Selected |
|--------|-------------|----------|
| Un solo account per email, collega auto | email = chiave; Google (verificata) confluisce nello stesso account | ✓ |
| Blocca / account separati | blocca con messaggio; più rigido, più frizione | |

**User's choice:** Un solo account per email, collega auto

---

## Campi registrazione

| Option | Description | Selected |
|--------|-------------|----------|
| Email + password + nome | nome per PDF e lead; evita migrazione dopo | ✓ |
| Solo email + password | minimo; nome chiesto dopo | |

**User's choice:** Email + password + nome

## Contenuto & formato PDF

| Option | Description | Selected |
|--------|-------------|----------|
| 1 pagina, riepilogo completo | branding+nome, input, 4 card range, totale IVA incl, disclaimer, data | ✓ |
| Minimale (solo totali) | input + totale + disclaimer, senza dettaglio card | |

**User's choice:** 1 pagina, riepilogo completo

---

## Claude's Discretion

- Libreria auth/OAuth (Authlib vs alt.), libreria PDF (WeasyPrint/reportlab/HTML→PDF), provider email transazionale.
- Struttura precisa dello snapshot (colonne vs JSON) e schema di `user`/`stima`.
- Asset branding PDF (base palette Slate/blue-600 da 01-UI-SPEC; placeholder logo ok).
- Meccanica UI del gate soft-wall → registrazione → download (modale vs pagina).

## Deferred Ideas

- Sottocategorie Pro + paywall + PDF dettagliato → Fase 3.
- Lead / contatto professionista + pannello admin CRUD → Fase 4 (qui solo ruolo admin + utility email).
- Verifica email obbligatoria → hardening post-v1.
- Pagamenti / prezzo Pro → Fase 3 / post-v1.
- Moltiplicatori prezzo per zona → post-v1.
