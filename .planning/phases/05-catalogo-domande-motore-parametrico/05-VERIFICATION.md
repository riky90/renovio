---
phase: 05-catalogo-domande-motore-parametrico
verified: 2026-10-01T00:00:00Z
status: passed
score: 5/5 success criteria verified
retroactive: true
---

# Phase 05: Catalogo domande + motore Free parametrico — Verification Report

**Phase Goal:** Un solo catalogo di domande in database alimenta il motore Free, che applica
moltiplicatori, €/m² additivi e correzioni per scostamento — restando bit-identico alla v1
quando nessuno risponde.
**Verified:** 2026-10-01, in modo retroattivo durante l'audit della milestone v2.0
**Status:** passed

> **Verifica retroattiva.** La fase è stata eseguita fuori dal ciclo GSD (vedi
> `05-RETRO-SUMMARY.md`) e non aveva un VERIFICATION.md. Questa verifica è stata fatta sul
> codice di oggi (`master` a valle di `1f43856`), non sullo stato del commit `5ea305b`:
> attesta che i criteri reggono **ora**, dopo le fasi 06-10 che ci hanno costruito sopra.
> Test eseguiti il 2026-10-01: `test_domande_free.py`, `test_domande_api.py`,
> `test_admin_domande.py`, `test_estimation.py`, `test_migrazioni_sqlite.py`,
> `test_no_leak.py` e altri, **223 passed**.

## Success Criteria

| # | Criterio (ROADMAP) | Stato | Evidenza |
|---|---|---|---|
| 1 | Le tabelle `domanda` / `opzione_domanda` / `effetto_opzione` / `attesa_immobile` esistono e sono seminate (migrazione `0014`) | ✓ VERIFIED | `alembic/versions/0014_catalogo_domande.py`; seed in `seed_data/seed-domande.json`; `test_seed_idempotente_non_duplica`, `test_seed_crea_ancora_domande_e_opzioni_mancanti`; catena migrazioni in `test_migrazioni_sqlite.py` |
| 2 | `tipo_effetto` è un insieme chiuso risolto da `services/effetti.py`, senza `if` di business nel motore | ✓ VERIFIED (con deviazione) | `effetti.py:103-123` definisce le costanti e `TIPI_EFFETTO`; `valida_effetto` rifiuta i tipi fuori insieme (`test_valida_effetto_rifiuta_le_righe_incoerenti`). In `services/estimation.py` nessun codice di domanda. **Deviazione:** i tipi oggi sono **otto**, non sette: `eur_fisso_categoria` è stato aggiunto dopo. L'insieme resta chiuso, che è la sostanza di QST-02 |
| 3 | Senza risposte, o con risposte pari agli attesi, l'oracolo non si muove: 85 m² · totale · RE → 47.985–70.575 € | ✓ VERIFIED | `test_layer_spento_produce_loracolo_primario`, `test_risposte_vuote_sono_identiche_a_layer_spento`, `test_risposte_pari_agli_attesi_non_muovono_nulla`, `test_nessuna_opzione_di_default_porta_effetti` |
| 4 | Una correzione per scostamento sposta solo la categoria bersagliata, e solo della differenza dall'atteso | ✓ VERIFIED | `test_scostamento_sui_bagni_muove_solo_le_categorie_bersaglio`, `test_scostamento_negativo_riduce`, `test_moltiplicatori_prima_degli_additivi` (ordine PAR-01) |
| 5 | Nessun coefficiente impresa entra nel nuovo layer | ✓ VERIFIED | `test_nessuna_tabella_del_catalogo_espone_il_coefficiente_impresa`; `test_no_leak.py::test_response_never_leaks_impresa_secret` |

**Score:** 5/5

## Requirements

| Requirement | Status | Evidence |
|---|---|---|
| QST-01 | ✓ SATISFIED | Catalogo in DB, CRUD admin (`test_admin_domande.py`), import/export Excel (08.1) |
| QST-02 | ✓ SATISFIED | Insieme chiuso, ora di otto tipi (vedi criterio 2) |
| QST-03 | ✓ SATISFIED | `attese_per_mq()` è la sorgente sia dei default del wizard (`test_default_degli_stepper_vengono_dalla_fascia_di_mq`) sia della baseline (`test_attesa_disattivata_non_fa_piu_da_baseline`) |
| QST-04 | ✓ SATISFIED | `test_domande_api.py::test_il_catalogo_non_pubblica_gli_effetti`, verificato sul JSON serializzato |
| PAR-01 | ✓ SATISFIED | `test_moltiplicatori_prima_degli_additivi`, `test_moltiplicatore_zero_azzera_e_salta_la_coda` |
| PAR-02 | ✓ SATISFIED | Criterio 3 |
| PAR-03 | ✓ SATISFIED | Criterio 4 |
| PAR-05 | ✓ SATISFIED | Criterio 5 |

## Gaps

Nessuno. L'unico scarto rispetto al testo dei criteri (otto tipi invece di sette) non tocca il
requisito.
