---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
last_updated: "2026-08-24T11:48:54.307Z"
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 4
  completed_plans: 2
  percent: 0
---

# Project State — ristruttura-stima

## Current Position

Phase: 01 (stima-free-end-to-end) — EXECUTING
Plan: 3 of 4

- **Milestone:** v1 (MVP)
- **Phase:** 1 — Stima Free end-to-end (**in esecuzione**, Plan 02/04 completato)
- **Status:** Ready to execute
- **Regola range (locked):** ±% solo sui lavori (4 categorie); extra fissi (€2.806 lordo); totale = Σ card + extra. Oracolo primario: 85 mq · totale = €47.985–€70.575.
- **Stack (da RESEARCH):** FastAPI + SQLAlchemy 2.0 + Pydantic v2 + Postgres/Alembic · React 19 + Vite + TS 5.9 + react-query + Tailwind/shadcn · autocomplete comuni ISTAT bundlato offline.

## Last Session

- **2026-08-24** — Eseguito Plan 01-02 (Seed + EstimationService): seed idempotente di `docs/seed-coefficienti-base.json` (1 listino RE default, 4 categorie, 3 tipi, 12 moltiplicatori, 2 extra, 2 alias comune_listino); `EstimationService.compute()` in Decimal puro, IVA per categoria, range ±% solo sui 4 subtotali di categoria, extra fissi mai scalati; `resolve_listino()` con fallback su RE. Oracolo primario 85mq·totale pinnato esatto (47985–70575); riconciliazione card+extra=totale verificata esatta; nessun leak di coefficiente_impresa nel risultato. TDD RED→GREEN, 12/12 test passanti. Vedi `01-02-SUMMARY.md`. Prima:
  - Eseguito Plan 01-01 (Walking Skeleton): backend FastAPI/SQLAlchemy 2.0/Alembic + frontend React/Vite/TS scaffoldati; schema Fase 1 completo (8 tabelle) migrato; loop end-to-end `GET /api/v1/health/db` provato (Browser → API → DB → Browser). Vedi `01-01-SUMMARY.md`.
  - Init progetto (analisi computo Excel, decisioni fondanti, PROJECT/config/REQUIREMENTS/ROADMAP).
  - **Ambiente GSD riparato**: agenti installati (profilo full, `agents_installed: true`); shim `gsd-sdk` ripuntato al SDK reale `~/.claude/gsd-source/bin/gsd-sdk.js` (backup `.bak`); ledger migrazioni riparato azzerando i checksum (backup in `~/.claude/gsd-install-state.json.bak-*`). Nota: SDK sul PATH è 1.50-canary, workflow 1.42.3 — `query` compatibile.
  - **Discussione Fase 1 completata** → `01-CONTEXT.md`: motore €/m² base × moltiplicatore per tipo; range ±% per tipo (admin); città a campo libero + fallback RE con disclaimer; risultato = 4 card + totale; soft wall (stima anonima, account per salvare/PDF/contatto → Fase 2). Roadmap invariata.

## Next Step

- Eseguire Plan 01-03 della Fase 1 (endpoint POST /api/v1/stima + contratto API/frontend).

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

## Decisions

- [Phase 01-stima-free-end-to-end]: typescript pinnato a 5.9.3 stabile (non 6.x/7.x preview) per requisito RESEARCH/plan
- [Phase 01-stima-free-end-to-end]: uv add --native-tls necessario per bypassare il proxy aziendale con cert self-signed
- [Phase 01-stima-free-end-to-end]: httpx2 aggiunto come dev dep backend (richiesto da starlette 1.6 TestClient, non previsto in RESEARCH)
- [Phase 01-stima-free-end-to-end]: [Phase 01-stima-free-end-to-end P02]: comune_listino seeded con 2 righe alias RE (Reggio Emilia, Reggio nell'Emilia) anziche 1, per risolvere entrambi gli alias senza fallback
- [Phase 01-stima-free-end-to-end]: [Phase 01-stima-free-end-to-end P02]: sys.path bootstrap in scripts/seed.py per supportare l'esecuzione diretta 'python scripts/seed.py' richiesta dal piano
