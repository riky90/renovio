---
phase: 10-risultato-leggibile
plan: 17
subsystem: backend-stime-salvate
tags: [gap-closure, G9, arredo, snapshot]
requires: [10-14]
provides:
  - "StimaSalvataCreate e StimaSalvataOut con arredo: ArredoOut | None = None"
  - "GET /me/stime/{id} restituisce arredo dallo snapshot (null se assente)"
  - "Il dettaglio Pro usa l'arredo dello snapshot come base del Bonus Mobili, senza inserimenti manuali"
affects: [10-18]
key-files:
  modified:
    - backend/app/schemas/stima_salvata.py
    - backend/app/routers/stime_salvate.py
    - backend/tests/test_stime_salvate.py
    - backend/tests/test_dettaglio_pro_bonus.py
decisions:
  - "Nessuna migrazione Alembic: risultato_json e' JSON, arredo e' chiave opzionale letta con .get(). Ultima revisione resta 0024, la 0025 resta libera"
  - "SCHEMA_VERSION resta 2 (chiave opzionale, come confronto_finiture di 10-04)"
metrics:
  tasks: 2
  files: 4
completed: 2026-09-30
---

# Phase 10 Plan 17: G9, l'arredo entra nello snapshot delle stime salvate Summary

Le stime salvate conservano l'arredo: `StimaSalvataCreate` non aveva il campo, quindi pydantic scartava in silenzio l'arredo che il client gia' mandava. Correzione solo backend.

## Commits
- 5a15514 (RED): `TestArredoNelloSnapshot` in `test_stime_salvate.py` (POST con arredo -> `risultato_json["arredo"]`, GET lo restituisce con livello/ambienti/totali, POST senza arredo -> null, snapshot vecchio senza chiave -> 200 con null, anti-leak). `test_arredo_dello_snapshot_non_riduce_il_netto` riscritto: l'arredo arriva via POST `/me/stime`, con asserzione che la base `MOBILI` sia uguale al totale arredo inviato. 5 test rossi.
- a7fe342 (GREEN): `arredo: ArredoOut | None = None` in `StimaSalvataCreate` e `StimaSalvataOut`; `dettaglio_stima` legge `snapshot.get("arredo")`; commento su `SCHEMA_VERSION` aggiornato. `salva_stima` invariato (il `model_dump` porta dentro l'arredo da solo).

## Verifiche
- Batteria collegata (`test_stime_salvate`, `test_dettaglio_pro_bonus`, `test_no_leak`, `test_arredo`, `test_dettaglio_pro`, `test_bonus_stima`): 68 passed.
- Grep di accettazione: `arredo: ArredoOut | None = None` = 2, `snapshot.get("arredo")` = 1, nessun file `0025*` in `alembic/versions`.
- Suite completa non lanciata (spetta a 10-18).

## Deviazioni dal piano
Nessuna. Il frontend non e' stato toccato.

## Note
- Gli `state.*` handler del gsd-sdk sono inaffidabili su questo progetto: STATE.md aggiornato con `state.advance-plan` e a mano per il resto.
- Le stime salvate prima di G9 restano senza arredo (nessun backfill): ArredoCard e Bonus Mobili funzionano solo per quelle salvate da ora in poi.

## Self-Check: PASSED
Commit 5a15514 e a7fe342 presenti; file modificati presenti.
