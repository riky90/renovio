# Project State — ristruttura-stima

## Current Position
- **Milestone:** v1 (MVP)
- **Phase:** 1 — Stima Free end-to-end (**contesto raccolto**, pronta per il planning)
- **Status:** Progetto inizializzato, roadmap 4 fasi, CONTEXT Fase 1 scritto e committato.

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
