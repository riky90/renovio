# Project State — ristruttura-stima

## Current Position
- **Milestone:** v1 (MVP)
- **Phase:** 1 — Stima Free end-to-end (**pianificata e verificata**, pronta per l'esecuzione)
- **Status:** 4 PLAN + SKELETON scritti; plan-checker PASS; warning W1/W4 chiusi (regola range). Prossimo: `/gsd-execute-phase 1`.
- **Regola range (locked):** ±% solo sui lavori (4 categorie); extra fissi (€2.806 lordo); totale = Σ card + extra. Oracolo primario: 85 mq · totale = €47.985–€70.575.
- **Stack (da RESEARCH):** FastAPI + SQLAlchemy 2.0 + Pydantic v2 + Postgres/Alembic · React 19 + Vite + TS 5.9 + react-query + Tailwind/shadcn · autocomplete comuni ISTAT bundlato offline.

## Last Session
- **2026-08-24** — Init progetto (analisi computo Excel, decisioni fondanti, PROJECT/config/REQUIREMENTS/ROADMAP). Poi:
  - **Ambiente GSD riparato**: agenti installati (profilo full, `agents_installed: true`); shim `gsd-sdk` ripuntato al SDK reale `~/.claude/gsd-source/bin/gsd-sdk.js` (backup `.bak`); ledger migrazioni riparato azzerando i checksum (backup in `~/.claude/gsd-install-state.json.bak-*`). Nota: SDK sul PATH è 1.50-canary, workflow 1.42.3 — `query` compatibile.
  - **Discussione Fase 1 completata** → `01-CONTEXT.md`: motore €/m² base × moltiplicatore per tipo; range ±% per tipo (admin); città a campo libero + fallback RE con disclaimer; risultato = 4 card + totale; soft wall (stima anonima, account per salvare/PDF/contatto → Fase 2). Roadmap invariata.

## Next Step
- `/gsd-plan-phase 1` — pianificazione della Fase 1 (agenti installati, pronti).

## Open Questions / To Decide
- Prezzo abbonamento Pro.
- Provider auth definitivo (Supabase / Firebase / Auth0) — scelta di build.
- Stack tecnico (candidato dai progetti dell'utente: FastAPI + React, deploy Railway).
- Quali voci esatte sono le "voci-chiave" del motore Pro.
- Meccanica esatta referenti per città (mail vs visualizzazione all'utente).

## Decision Log Pointer
Vedi PROJECT.md → Key Decisions e `BRIEF-DISCUSSIONE.md`.
