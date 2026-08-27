---
phase: 03-pro-dettaglio-sottocategorie
plan: 03
subsystem: backend
tags: [fastapi, sqlalchemy, pydantic, decimal, paywall, bottom-up]

requires:
  - phase: 03-pro-dettaglio-sottocategorie
    provides: "require_pro / Subscription tessera (03-01)"
  - phase: 03-pro-dettaglio-sottocategorie
    provides: "Sottocategoria/Voce/CoefficienteQuantitaVoce + seed RE + StimaSalvata.risposte_pro_json (03-02)"
provides:
  - "DettaglioProService.compute() — motore Pro bottom-up Decimal-puro, indipendente dal Free (D-01)"
  - "GET /me/stime/{id}/dettaglio-pro + POST /me/stime/{id}/dettaglio-pro/risposte dietro require_pro"
  - "DTO chiusi anti-leak (schemas/dettaglio_pro.py)"
  - "Persistenza risposte domande mirate in risposte_pro_json, base condivisa per il futuro PDF Pro (03-04)"
affects: ["03-04 (PDF Pro dettagliato)", "03-06 (frontend dettaglio Pro)"]

tech-stack:
  added: []
  patterns:
    - "DettaglioProService come sibling di EstimationService: stesso incipit Decimal-puro/_eur()/dataclass frozen, aggregazione diversa (per-voce, raggruppata per sottocategoria/categoria)"
    - "Range per-voce riusando TipoRistrutturazione.range_pct (Assunzione A1), applicato a quantita_stimata*prezzo_unitario_cliente"
    - "GET e POST .../dettaglio-pro chiamano la STESSA DettaglioProService.compute() — nessuna doppia logica che possa divergere (RESEARCH Pitfall 2)"

key-files:
  created:
    - backend/app/services/dettaglio_pro.py
    - backend/app/schemas/dettaglio_pro.py
    - backend/app/routers/dettaglio_pro.py
    - backend/tests/test_dettaglio_pro.py
    - backend/tests/test_dettaglio_pro_paywall.py
  modified:
    - backend/app/main.py

key-decisions:
  - "Docstring di schemas/dettaglio_pro.py riformulata per non contenere letteralmente 'base_eur_mq' (stesso precedente 02/03 per rispettare in senso stretto il criterio grep meccanico)"
  - "Strategia quantita estesa oltre il testo letterale del piano: righe con default_conteggio ma senza domanda_mirata_key (150/300 nel seed, voci a conteggio non mirate tipo ac/forfait) usano direttamente default_conteggio, senza lookup in risposte — necessario perche' il seed 03-02 popola sempre una delle due strategie, mai nessuna"

requirements-completed: [PRO-01, PRO-02]

duration: 35min
completed: 2026-08-27
---

# Phase 3 Plan 03: Motore Pro bottom-up + endpoint dettaglio dietro paywall Summary

**`DettaglioProService.compute()` ricostruisce bottom-up il dettaglio per sottocategoria (voci + quantità stimate a range) dal seed reale RE, esposto da `GET/POST /me/stime/{id}/dettaglio-pro` dietro `require_pro`, con anti-IDOR 404 e persistenza delle risposte alle domande mirate condivisa tra schermata e futuro PDF.**

## Performance

- **Duration:** 35 min
- **Started:** 2026-08-27T07:05:00Z
- **Completed:** 2026-08-27T07:40:00Z
- **Tasks:** 2 completati
- **Files modified:** 6 (5 creati, 1 modificato)

## Accomplishments

- Motore `DettaglioProService.compute(session, listino, mq, tipo, risposte)` Decimal-puro: itera Categoria→Sottocategoria→Voce, applica coefficiente-per-mq oppure conteggio da domanda mirata/default, range per-voce da `TipoRistrutturazione.range_pct` (A1); nessuna colonna/campo impresa letto o restituito; nessun import del motore Free (D-01, guard statico verificato in test)
- Oracolo per-voce pinnato a mano dal seed reale: `A.1.1.1` (coefficiente-per-mq, mq=85/tipo=totale → quantita=51.00, range [1836, 2754]) e `A.0.3` (domanda mirata "bagni", default vs risposta esplicita)
- `GET /me/stime/{id}/dettaglio-pro` e `POST .../dettaglio-pro/risposte` dietro `Depends(require_pro)`: 401 anonimo, 403 Free, 200 Pro; ownership `id+user_id` → 404 anti-IDOR (mai 403) su entrambe le rotte
- Risposte alle domande mirate persistite in `stima.risposte_pro_json`; il GET le rilegge sempre, quindi un POST seguito da un GET restituisce quantità coerenti (verificato end-to-end)
- DTO chiusi anti-leak (`VoceOut`/`SottocategoriaOut`/`CategoriaDettagliataOut`/`DettaglioProOut`) + `RisposteDomandeRequest` bounded (`ge=0, le=cap` su bagni/porte/condizionatori, ASVS V5); check anti-leak ricorsivo verde su risposta e testo grezzo
- Suite backend completa 101/101 passed + 2 skip invariati (GTK3)

## Task Commits

1. **Task 1: DettaglioProService.compute() bottom-up + oracolo unit** - `b6c4943` (feat)
2. **Task 2: DTO chiusi + router dettaglio-pro (GET+POST risposte) dietro require_pro + wiring** - `a97d4ae` (feat)

## Files Created/Modified

- `backend/app/services/dettaglio_pro.py` - `DettaglioProService.compute()`, dataclass frozen `VoceEstimata`/`SottocategoriaEstimata`/`CategoriaDettagliata`/`DettaglioProResult`, helper `_eur()`/`_qta()`
- `backend/app/schemas/dettaglio_pro.py` - DTO chiusi + `RisposteDomandeRequest`/`RisposteDomandeOut`
- `backend/app/routers/dettaglio_pro.py` - `router` con `GET /stime/{id}/dettaglio-pro` + `POST /stime/{id}/dettaglio-pro/risposte`, entrambi dietro `require_pro`, ownership 404
- `backend/app/main.py` - router `dettaglio_pro` registrato con `prefix="/api/v1"`
- `backend/tests/test_dettaglio_pro.py` - oracolo per-voce, domanda mirata (default/esplicita), guard anti-`EstimationService`, anti-leak, integrazione HTTP POST-risposte→GET
- `backend/tests/test_dettaglio_pro_paywall.py` - matrice 401/403/200, anti-IDOR 404 su GET e POST, anti-leak ricorsivo

## Decisions Made

- Vedi `key-decisions` in frontmatter. La più rilevante: la strategia di calcolo quantità è stata estesa oltre il testo letterale del blocco `<behavior>` del piano (che descrive solo coefficiente-per-mq e domanda-mirata) per coprire anche le righe seedate in 03-02 con `default_conteggio` valorizzato ma `domanda_mirata_key` assente (voci a conteggio non mirate, es. forfait/allestimento) — altrimenti 150 delle 300 righe di coefficiente per tipo sarebbero rimaste a quantità zero, un bug di correttezza rispetto ai dati reali del seed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Docstring di `schemas/dettaglio_pro.py` conteneva letteralmente `base_eur_mq`**
- **Found during:** Task 2, verifica finale dei grep di accettazione
- **Issue:** La prima stesura del docstring di modulo dichiarava l'assenza di `base_eur_mq`/`moltiplicatore` nominandoli per esteso, facendo fallire il criterio meccanico `grep -v '^#' ... | grep -c -E '...' == 0` del piano (il testo non è un commento `#`, è dentro una docstring)
- **Fix:** Riformulato il docstring per non contenere le stringhe letterali, mantenendo lo stesso significato
- **Files modified:** `backend/app/schemas/dettaglio_pro.py`
- **Verification:** `grep -v '^#' backend/app/schemas/dettaglio_pro.py | grep -c -E 'coefficiente_impresa|prezzo_impresa|base_eur_mq'` == 0
- **Committed in:** `a97d4ae` (Task 2 commit — corretto prima del commit, mai committato rotto)

**2. [Rule 1/2 - Correttezza dati] Strategia quantità estesa per il caso `default_conteggio` senza `domanda_mirata_key`**
- **Found during:** Task 1, ispezione del seed reale (`docs/seed-dettaglio-pro.json`) prima di scrivere `compute()`
- **Issue:** Il testo letterale del piano descrive solo due strategie (coefficiente-per-mq vs domanda-mirata-con-default), ma metà delle righe di coefficiente seedate in 03-02 (150/300) hanno `default_conteggio` valorizzato senza `domanda_mirata_key` — un terzo caso non descritto esplicitamente
- **Fix:** Aggiunto un terzo ramo in `DettaglioProService._quantita()`: se manca sia il coefficiente-per-mq sia la domanda mirata ma c'è un `default_conteggio`, usarlo direttamente
- **Files modified:** `backend/app/services/dettaglio_pro.py`
- **Verification:** test su A-EDILE conferma tutte le sottocategorie/voci compaiono con quantità coerenti (non zero) anche per queste righe
- **Committed in:** `b6c4943` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 bug di conformità al criterio meccanico, 1 estensione di correttezza dati non ambigua rispetto al seed reale)
**Impact on plan:** Nessuno scope creep — entrambe le correzioni erano necessarie per rispettare rispettivamente i criteri di accettazione letterali del piano e la correttezza bottom-up rispetto ai dati reali prodotti da 03-02.

## Issues Encountered

None oltre alle deviazioni sopra documentate.

## Known Stubs

Nessuno stub bloccante. Il dettaglio Pro è calcolato sui dati reali del seed 03-02 (prezzi RE dal `.xlsx`, coefficienti quantità-per-m²/domanda-mirata bozza per esplicita concessione D-04/D-05, tarabili da admin in Fase 4 — non un placeholder di sviluppo).

## User Setup Required

None — nessuna configurazione di servizio esterno richiesta.

## Threat Flags

Nessuna superficie non prevista dal `<threat_model>` del piano: le due rotte nuove (GET/POST dettaglio-pro) erano già in T-03-05/T-03-06/T-03-07, mitigate come pianificato.

## Next Phase Readiness

- `DettaglioProService.compute()` pronto per essere riusato tal quale dal PDF Pro (03-04): stessa chiamata, stesso `risposte_pro_json`, nessun rischio di divergenza schermata/PDF (RESEARCH Pitfall 2 chiuso per costruzione — un solo punto di calcolo).
- `GET/POST .../dettaglio-pro` pronti per essere consumati dal frontend (03-06): DTO chiusi già nella forma attesa (accordion per sottocategoria).
- Nessun blocco noto.

---
*Phase: 03-pro-dettaglio-sottocategorie*
*Completed: 2026-08-27*
