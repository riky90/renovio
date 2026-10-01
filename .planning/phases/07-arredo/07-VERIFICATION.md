---
phase: 07-arredo
verified: 2026-10-01T00:00:00Z
status: passed
score: 5/5 success criteria verified
retroactive: true
---

# Phase 07: Arredo — Verification Report

**Phase Goal:** L'utente dice quali ambienti vuole arredare e riceve un forfait arredo a range,
esposto accanto al totale lavori e mai dentro — e da lì il Bonus Mobili diventa accendibile.
**Verified:** 2026-10-01, in modo retroattivo durante l'audit della milestone v2.0
**Status:** passed

> **Verifica retroattiva.** La ROADMAP registra una verifica dal vivo al momento della
> consegna ("totale lavori invariato, arredo accanto e non dentro", commit `6158eef`), ma non
> esisteva un VERIFICATION.md. Questa verifica è fatta sul codice di oggi; `test_arredo.py` è
> verde nella corsa del 2026-10-01 (223 passed sui file delle fasi 05-07).

## Success Criteria

| # | Criterio (ROADMAP) | Stato | Evidenza |
|---|---|---|---|
| 1 | `E-ARREDO` esiste e `categoria.nel_totale_lavori` la esclude dal totale come dato | ✓ VERIFIED | `alembic/versions/0015_arredo.py`; filtro in `services/estimation.py:98`; `test_e_arredo_esiste_ed_e_esclusa_dal_totale`, `test_riportare_arredo_nel_totale_lo_cambia` (la riga è un dato, non una costante) |
| 2 | Il forfait Free viene da `(ambiente, livello) → eur_min, eur_max`, guidato dalla multiselect | ✓ VERIFIED | `test_somma_esatta_dei_forfait`, `test_livello_alto_costa_piu_del_base`, `test_forfait_disattivato_non_conta`, `test_il_servizio_non_conosce_il_codice_della_domanda` |
| 3 | `StimaResponse.arredo` è fratello di `totale`, `None` quando non richiesto, con il disclaimer dentro il payload | ✓ VERIFIED | `test_senza_ambienti_la_chiave_e_none`, `test_con_ambienti_compare_accanto_al_totale`, `test_nessuna_chiave_di_margine_nel_payload_arredo`; snapshot (`routers/stime_salvate.py`) e PDF Free; **PDF Pro dal 2026-10-01** (audit M1, `1f43856`) |
| 4 | L'oracolo non si muove e Σ categorie + extra = totale resta esatta | ✓ VERIFIED | `test_oracolo_primario_invariato`, `test_riconciliazione_esatta`, `test_arredo_non_compare_fra_le_categorie` |
| 5 | Il Bonus Mobili si può accendere dal pannello admin senza deploy | ✓ VERIFIED | `routers/admin/bonus.py` (campo `attivo`); `test_seminato_ma_spento`, `test_acceso_calcola_sulla_base_arredo`, `test_tetto_di_spesa_cappa_la_base` |

**Score:** 5/5

## Requirements

| Requirement | Status | Evidence |
|---|---|---|
| ARR-01 | ✓ SATISFIED | Criterio 1 |
| ARR-02 | ✓ SATISFIED | Criterio 2 |
| ARR-03 | ✓ SATISFIED | Criterio 3. Fino all'audit v2.0 il PDF Pro non mostrava l'arredo (M1); corretto in `1f43856` con il partial comune `_pdf_bonus_arredo.html` e `test_pdf_pro.py::TestPdfProBonusEArredo` |
| ARR-04 | ✓ SATISFIED | Criterio 5 |

## Gaps

Nessuno aperto. Il rendering WeasyPrint dei PDF resta da collaudare al go-live su Render
(stessa riserva della Fase 10).
