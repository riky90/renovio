# Project State — ristruttura-stima

## Current Position
- **Milestone:** v1 (MVP)
- **Phase:** 1 — Stima Free end-to-end (non ancora pianificata)
- **Status:** Progetto inizializzato. Roadmap a 4 fasi approvata.

## Last Session
- **2026-08-24** — Inizializzazione progetto: analizzato il file computo Excel, raccolte le decisioni fondanti (brief in `BRIEF-DISCUSSIONE.md`), creati PROJECT.md, config.json, REQUIREMENTS.md, ROADMAP.md.
- Nota ambiente: il set di agenti GSD non è installato (`agents_installed: false`) e lo shim `gsd-sdk` sul PATH è rotto. I documenti sono stati generati inline. Per usare i workflow automatici plan/execute installare gli agenti: `npx get-shit-done-cc@latest --global`.

## Next Step
- `/gsd-plan-phase 1` (richiede gli agenti GSD installati) oppure pianificazione manuale della Fase 1.

## Open Questions / To Decide
- Prezzo abbonamento Pro.
- Provider auth definitivo (Supabase / Firebase / Auth0) — scelta di build.
- Stack tecnico (candidato dai progetti dell'utente: FastAPI + React, deploy Railway).
- Quali voci esatte sono le "voci-chiave" del motore Pro.
- Meccanica esatta referenti per città (mail vs visualizzazione all'utente).

## Decision Log Pointer
Vedi PROJECT.md → Key Decisions e `BRIEF-DISCUSSIONE.md`.
