---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: verifying
last_updated: "2026-08-24T13:04:33.427Z"
progress:
  total_phases: 4
  completed_phases: 1
  total_plans: 4
  completed_plans: 4
  percent: 25
---

# Project State — ristruttura-stima

## Current Position

Phase: 01 (stima-free-end-to-end) — COMPLETE
Plan: 4 of 4 (tutti completati)

- **Milestone:** v1 (MVP)
- **Phase:** 1 — Stima Free end-to-end (**completa**, Plan 01/02/03/04 tutti completati)
- **Status:** Phase complete — ready for verification
- **Regola range (locked):** ±% solo sui lavori (4 categorie); extra fissi (€2.806 lordo); totale = Σ card + extra. Oracolo primario: 85 mq · totale = €47.985–€70.575.
- **Stack (da RESEARCH):** FastAPI + SQLAlchemy 2.0 + Pydantic v2 + Postgres/Alembic · React 19 + Vite + TS 5.9 + react-query + Tailwind/shadcn · autocomplete comuni ISTAT bundlato offline.

## Last Session

- **2026-08-24** — Eseguito Plan 01-04 (Frontend Free end-to-end): shadcn (base radix, preset vega) inizializzato su Tailwind v4 con token Slate/blue-600 riscritti a mano da UI-SPEC (il CLI shadcn installato, v4.19.0, non ha più il preset "New York"); comuni.json ISTAT (7904 comuni) bundlato per l'autocomplete città 100% client-side; `EstimateForm` (città+mq+tipo, validazione italiana, CTA gated) + `CityAutocomplete` (selezionabile mouse/tastiera) + `EstimatePage` (form → `useMutation(postStima)` → riepilogo input + disclaimer condizionale + 4 card categoria + extra fissi + `TotalCard` accent + `SoftWallCta`), stati skeleton/error. `api/stima.ts` normalizza i campi Decimal-come-stringa di Pydantic v2 a number al confine API. Verificato dal vivo contro il backend reale: 85mq/totale/Reggio Emilia → 47.985–70.575 € (riconciliazione esatta), Modena → fallback con disclaimer; grep conferma nessun leak di coefficiente/impresa nel frontend. Checkpoint human-verify: approvato dall'utente dopo 2 fix richiesti in sessione (autocomplete non selezionabile — bug classico onBlur-vs-click di cmdk risolto; poi highlight riga attiva rinforzato a blue-600 pieno su richiesta). Vedi `01-04-SUMMARY.md`. **Fase 1 completa.** Prima:
  - Eseguito Plan 01-03 (Endpoint POST /api/v1/stima): `app/schemas/stima.py` (StimaRequest limitato + StimaResponse/CategoriaOut/ExtraOut/TotaleOut a campi chiusi, anti-leak); `app/routers/stima.py` risolve città + calcola via EstimationService + costruisce la risposta esplicitamente (mai model_validate su entità ORM); split imponibile/IVA per categoria recuperato algebricamente in modo esatto; `app/limiter.py` (nuovo modulo condiviso) applica rate limit 20/minute. Oracolo 85mq/totale confermato end-to-end su HTTP (47985–70575, fallback=False); Modena → fallback=True con disclaimer; 422 su mq/tipo/città fuori range. `test_no_leak.py` prova ricorsivamente (chiavi a ogni profondità + substring) che coefficiente_impresa/base_eur_mq/moltiplicatore/prezzo_impresa non appaiono mai nella risposta seriale, su RE + Modena × 3 tipi. TDD RED→GREEN, 26/26 test passanti. Vedi `01-03-SUMMARY.md`. Prima:
  - Eseguito Plan 01-02 (Seed + EstimationService): seed idempotente di `docs/seed-coefficienti-base.json` (1 listino RE default, 4 categorie, 3 tipi, 12 moltiplicatori, 2 extra, 2 alias comune_listino); `EstimationService.compute()` in Decimal puro, IVA per categoria, range ±% solo sui 4 subtotali di categoria, extra fissi mai scalati; `resolve_listino()` con fallback su RE. Oracolo primario 85mq·totale pinnato esatto (47985–70575); riconciliazione card+extra=totale verificata esatta; nessun leak di coefficiente_impresa nel risultato. TDD RED→GREEN, 12/12 test passanti. Vedi `01-02-SUMMARY.md`. Prima:
  - Eseguito Plan 01-01 (Walking Skeleton): backend FastAPI/SQLAlchemy 2.0/Alembic + frontend React/Vite/TS scaffoldati; schema Fase 1 completo (8 tabelle) migrato; loop end-to-end `GET /api/v1/health/db` provato (Browser → API → DB → Browser). Vedi `01-01-SUMMARY.md`.
  - Init progetto (analisi computo Excel, decisioni fondanti, PROJECT/config/REQUIREMENTS/ROADMAP).
  - **Ambiente GSD riparato**: agenti installati (profilo full, `agents_installed: true`); shim `gsd-sdk` ripuntato al SDK reale `~/.claude/gsd-source/bin/gsd-sdk.js` (backup `.bak`); ledger migrazioni riparato azzerando i checksum (backup in `~/.claude/gsd-install-state.json.bak-*`). Nota: SDK sul PATH è 1.50-canary, workflow 1.42.3 — `query` compatibile.
  - **Discussione Fase 1 completata** → `01-CONTEXT.md`: motore €/m² base × moltiplicatore per tipo; range ±% per tipo (admin); città a campo libero + fallback RE con disclaimer; risultato = 4 card + totale; soft wall (stima anonima, account per salvare/PDF/contatto → Fase 2). Roadmap invariata.

## Next Step

- Fase 1 (stima-free-end-to-end) completa — tutti i 4 piani eseguiti e human-verificati. Procedere con la verifica di fase / transizione alla Fase 2 (autenticazione + salvataggio stima).

## Open Questions / To Decide

- Prezzo abbonamento Pro.
- Provider auth definitivo (Supabase / Firebase / Auth0) — scelta di build.
- Stack tecnico (candidato dai progetti dell'utente: FastAPI + React, deploy Railway).
- Quali voci esatte sono le "voci-chiave" del motore Pro.
- Meccanica esatta referenti per città (mail vs visualizzazione all'utente).

## Decision Log Pointer

Vedi PROJECT.md → Key Decisions e `BRIEF-DISCUSSIONE.md`.

## Performance Metrics

| Phase | Plan | Duration | Notes |
|-------|------|----------|-------|
| Phase 01-stima-free-end-to-end P01 | 25min | 3 tasks | 48 files |
| Phase 01-stima-free-end-to-end P02 | 20min | 1 tasks | 7 files |
| Phase 01-stima-free-end-to-end P03 | 20min | 2 tasks | 6 files |
| Phase 01-stima-free-end-to-end P04 | 58min | 2 tasks | 35 files |

## Decisions

- [Phase 01-stima-free-end-to-end]: typescript pinnato a 5.9.3 stabile (non 6.x/7.x preview) per requisito RESEARCH/plan
- [Phase 01-stima-free-end-to-end]: uv add --native-tls necessario per bypassare il proxy aziendale con cert self-signed
- [Phase 01-stima-free-end-to-end]: httpx2 aggiunto come dev dep backend (richiesto da starlette 1.6 TestClient, non previsto in RESEARCH)
- [Phase 01-stima-free-end-to-end]: [Phase 01-stima-free-end-to-end P02]: comune_listino seeded con 2 righe alias RE (Reggio Emilia, Reggio nell'Emilia) anziche 1, per risolvere entrambi gli alias senza fallback
- [Phase 01-stima-free-end-to-end]: [Phase 01-stima-free-end-to-end P02]: sys.path bootstrap in scripts/seed.py per supportare l'esecuzione diretta 'python scripts/seed.py' richiesta dal piano
- [Phase 01-stima-free-end-to-end]: app/limiter.py estratto come modulo condiviso per evitare import circolare tra main.py e routers/stima.py nel decorare l'endpoint con il rate limit
- [Phase 01-stima-free-end-to-end]: imponibile_min/max e iva_min/max per categoria recuperati algebricamente (totale/(1+iva_pct)) nel router, senza modificare EstimationService gia' bloccato dal Piano 02
- [Phase 01-stima-free-end-to-end]: shadcn CLI ha cambiato generazione (v4.19.0): niente preset 'New York'; usato --base radix + preset vega, token Slate/blue-600 riscritti a mano da UI-SPEC
- [Phase 01-stima-free-end-to-end]: Decimal backend serializzati come stringhe JSON (Pydantic v2): normalizzati a number in api/stima.ts al confine API
- [Phase 01-stima-free-end-to-end]: CityAutocomplete: rimosso onBlur di chiusura popover (bug classico, in gara con onSelect click-based di cmdk); chiusura via onSelect/Escape/outside-pointerdown
- [Phase 01-stima-free-end-to-end]: Highlight riga attiva autocomplete rafforzato a bg-primary/text-primary-foreground (blue-600 pieno) su richiesta utente al checkpoint
