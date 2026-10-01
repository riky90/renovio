---
phase: 06-wizard-unico
verified: 2026-10-01T00:00:00Z
status: passed
score: 5/5 success criteria verified
retroactive: true
---

# Phase 06: Wizard unico, domande servite dal DB — Verification Report

**Phase Goal:** Un solo wizard a 4 step per Free e Pro, con le domande e i default serviti dal
database: aggiungere una domanda torna a essere lavoro da pannello admin.
**Verified:** 2026-10-01, in modo retroattivo durante l'audit della milestone v2.0
**Status:** passed

> **Verifica retroattiva.** La fase è stata eseguita fuori dal ciclo GSD (vedi
> `06-RETRO-SUMMARY.md`). La verifica è fatta sul codice di oggi. Il wizard è stato usato dal
> vivo da Riccardo nei collaudi delle fasi 08.1, 09 e 10 (`*-HUMAN-UAT.md`): è la prova d'uso
> della UI. Il percorso Pro end-to-end resta WIZ-04, assegnato alla Fase 09.

## Success Criteria

| # | Criterio (ROADMAP) | Stato | Evidenza |
|---|---|---|---|
| 1 | `GET /api/v1/domande?tier=&mq=` serve catalogo, opzioni e default già risolti per la fascia di m² | ✓ VERIFIED | `test_domande_api.py`: `test_catalogo_free_non_vuoto_e_ordinato`, `test_default_degli_stepper_vengono_dalla_fascia_di_mq`, `test_fasce_diverse_danno_default_diversi`, `test_tier_pro_include_le_domande_free` |
| 2 | Il payload non contiene gli effetti, verificato sul JSON serializzato | ✓ VERIFIED | `test_il_catalogo_non_pubblica_gli_effetti` |
| 3 | `EstimateForm` ed `EstimateFormPro` collassano in `EstimateWizard` (1 · Dove — 2 · L'immobile — 3 · La ristrutturazione — 4 · Le finiture) | ✓ VERIFIED | `frontend/src/components/EstimateWizard.tsx:387-393` definisce i quattro step (il quarto solo in tier Pro). Nessun `EstimateForm`/`EstimateFormPro` rimasto in `src/` (resta `EstimateFormFields.tsx`, i campi comuni dello step 1) |
| 4 | `NumberStepper` sostituisce gli input numerici grezzi | ✓ VERIFIED | `components/ui/number-stepper.tsx` (`h-11`, cioè 44px, commento alla riga 85); usato da `DomandaField.tsx` per i controlli numerici |
| 5 | I default derivano dai m², mai zero, e lo step 2 è saltabile | ✓ VERIFIED | `test_senza_mq_i_default_numerici_sono_null_mai_zero`; `ValoriStandardHint` "Vai avanti con i valori standard" (`EstimateWizard.tsx:272`) |

**Score:** 5/5

## Requirements

| Requirement | Status | Evidence |
|---|---|---|
| WIZ-01 | ✓ SATISFIED | Criteri 1 e 3; `test_configuratore_pro_non_entra_nel_wizard` |
| WIZ-02 | ✓ SATISFIED | Criterio 4 |
| WIZ-03 | ✓ SATISFIED | Criterio 5 |

## Note

- Non esiste un test runner frontend: i criteri 3-5 sono verificati leggendo il codice e con
  l'uso dal vivo nei collaudi successivi, non da test automatici.
- Audit v2.0, M2: lo step 4 ora parte dal livello scelto allo step 3 (`livello_finiture`),
  invece che dal default di tabella (`4d44e3c`).
