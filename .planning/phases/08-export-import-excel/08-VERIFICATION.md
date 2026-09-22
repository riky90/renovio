---
phase: 08-export-import-excel
verified: 2026-09-22T00:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 08: Export/import Excel dal pannello admin — Verification Report

**Phase Goal:** La curatela dei dati esce dal `dev.db` e diventa un file che l'admin scarica, modifica e ricarica senza perdere nulla — prerequisito di ogni taratura seria.
**Verified:** 2026-09-22
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Success Criteria dalla ROADMAP)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Round-trip: il file esportato si ricarica senza riformattarlo | ✓ VERIFIED | `test_export_import_roundtrip.py::test_roundtrip_a_vuoto_non_produce_modifiche` (listino, via `parse_flat_listino`/`compute_diff` reali); `test_import_parametri.py::test_roundtrip_parametri_a_vuoto`; `test_import_lead.py::test_roundtrip_lead_a_vuoto`. Tutti costruiscono il file con le stesse funzioni dell'export reale (`build_workbook_listino`/`build_workbook_parametri`/`build_workbook_lead`) e verificano zero righe nuove/modificate. 47 test eseguiti, tutti PASS |
| 2 | Colonna assente = campo non toccato (regola `voce.livello`) | ✓ VERIFIED | `test_dettaglio_pro_livelli.py::TestUploadExcelNonAzzeraLivello::test_upload_excel_non_azzera_livello` — PASS (rieseguito isolatamente). Generalizzato in `test_export_import_roundtrip.py::test_colonna_assente_non_azzera_il_campo` (multi-campo) e in `services/import_excel/*` via `campi_presenti`/`CAMPI_MODIFICABILI` |
| 3 | Export con coefficiente impresa riservato ad `admin`, nome marcato, foglio avviso | ✓ VERIFIED | `backend/app/services/export_excel/parametri.py`: colonna `coefficiente_impresa` aggiunta ALLA lista solo nel ramo `con_margine=True` (mai filtrata a valle). `routers/admin/coefficienti.py:91-112`: `Depends(require_admin)` su entrambe le varianti. `test_export_margine.py`: file default non contiene la colonna né il foglio AVVISO né alcun valore di margine del seed; variante `margine=true` ha `AVVISO` come primo foglio e nome file con `con-margine`; consulente riceve 403 su entrambe le varianti, zero righe di log scritte |
| 4 | Export dei lead traccia chi scarica e quando | ✓ VERIFIED | `backend/app/routers/admin/lead.py:52` scrive `ExportLog` nella stessa richiesta; `routers/admin/export_log.py` (`GET /admin/export-log`, `require_staff`) risolve `user_label` via join; `LeadDashboardPage.tsx` mostra sezione "Download registrati". `test_export_lead_traccia.py` — 9 test PASS (403 per user, header 17 colonne, righe coincidono col DB, ordine decrescente/limite 50, user_label non è id nudo) |
| 5 | Anteprima admin mostra breakdown e quali effetti hanno sparato | ✓ VERIFIED | `AnteprimaTab.tsx` sesta tab di `/admin/coefficienti`, consuma `POST /admin/domande/anteprima` (`require_admin`, preesistente). Tabella con TUTTI gli effetti del catalogo con badge Applicato/Non applicato, breakdown per categoria con base/totale/delta. Verificato codice del backend (`domande.py:496-581`): calcola `base` (risposte=None) vs `corretta` (risposte reali), espone `effetti` con `applicato` per ognuno |

**Score:** 5/5 truths verified

### Required Artifacts (estratti dai must_haves di tutti gli 8 piani)

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/models/export_log.py` | Modello ExportLog | ✓ VERIFIED | esiste, migrato (0018), tabella presente in dev.db |
| `backend/alembic/versions/0018_export_log.py` | Migrazione additiva | ✓ VERIFIED | `create_table`, solo additiva |
| `backend/app/services/export_excel/workbook.py` | Shell condivisa | ✓ VERIFIED | `TOKEN_CANCELLA`, `nuovo_workbook`, `scrivi_foglio_dati`, `build_filename`, `serializza` tutti presenti e usati da listino/parametri/lead |
| `backend/app/services/export_excel/listino.py` | Export listino | ✓ VERIFIED | `build_workbook_listino` |
| `backend/app/services/export_excel/parametri.py` | Export 5 fogli parametri | ✓ VERIFIED | margine opt-in strutturale, letto e testato |
| `backend/app/services/export_excel/lead.py` | Export lead | ✓ VERIFIED | usato da `routers/admin/lead.py` |
| `backend/app/services/import_excel/flat.py` | Lettore formato piatto | ✓ VERIFIED | `e_formato_piatto`, `leggi_foglio_piatto`, `leggi_timestamp_export`, `RigaPiatta` |
| `backend/app/services/import_excel/registry.py` | Registro handler + gate ruolo | ✓ VERIFIED | `HANDLER`, `risolvi_handler`, `ruolo_richiesto` letto SEMPRE dall'handler risolto, mai dal client |
| `backend/app/services/import_excel/parametri.py` | Handler parametri | ✓ VERIFIED | scrittura margine isolata in 2 funzioni `is_admin`-gated |
| `backend/app/services/import_excel/lead.py` | Handler lead | ✓ VERIFIED | `CAMPI_MODIFICABILI={stato,nota,referente_id}`, ogni altro campo divergente → scarto, nessuna creazione da riga senza id |
| `backend/app/routers/admin/import_excel.py` | Router generico import | ✓ VERIFIED | `_verifica_permesso` legge `ruolo_richiesto` dall'handler risolto |
| `backend/app/routers/admin/export_log.py` | Log ultimi 50 download | ✓ VERIFIED | `require_staff`, join su User |
| `backend/alembic/versions/0019_updated_at_curatela.py` | Colonna `updated_at` su 9 tabelle | ✓ VERIFIED | solo `add_column`, coerente coi modelli ORM |
| `frontend/src/components/admin/AnteprimaTab.tsx` | Tab anteprima | ✓ VERIFIED | wired come sesta tab di `CoefficientiPage.tsx` |
| `frontend/src/components/admin/FlatImportDialog.tsx` / `DiffPreviewTable.tsx` | Dialog import + preview diff | ✓ VERIFIED | riusati da `CoefficientiPage.tsx` e `LeadDashboardPage.tsx`, badge "Cambiata dopo l'export" presente |
| `backend/tests/test_export_import_roundtrip.py` | Test round-trip listino | ✓ VERIFIED | 8 test, PASS |
| `backend/tests/test_export_margine.py` | Test anti-leak margine | ✓ VERIFIED | 5 test, PASS |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `ListiniPage.tsx` | `GET /admin/listini/{id}/export.xlsx` | `scaricaExcel()` | ✓ WIRED | client generico riusato |
| `routers/admin/listini.py` | `export_log` | riga di audit pre-return | ✓ WIRED | verificato in `test_export_excel_listino.py` |
| `AnteprimaTab.tsx` | `POST /admin/domande/anteprima` | `calcolaAnteprima()` | ✓ WIRED | endpoint preesistente, non toccato (per contratto del piano) |
| `CoefficientiPage.tsx` | `AnteprimaTab` | sesta `TabsTrigger value="anteprima"` | ✓ WIRED | confermato nel file |
| `upload_listino.py` | `listino_upload_service.parse_flat_listino` | dispatch su formato | ✓ WIRED | `test_export_import_roundtrip.py::test_computo_originale_ancora_accettato` conferma anche il path legacy |
| `CoefficientiPage.tsx` | `GET /admin/coefficienti/export.xlsx?margine=true` | split-button + AlertDialog | ✓ WIRED | confermato in codice e in `test_export_margine.py` |
| `routers/admin/coefficienti.py` | `export_log.include_margine` | riga di audit | ✓ WIRED | `test_export_log_distingue_le_due_varianti` PASS |
| `routers/admin/lead.py` | `ExportLog` | audit stessa richiesta | ✓ WIRED | route `/export.xlsx` registrata PRIMA di `/{lead_id}` — verificato nel file |
| `LeadDashboardPage.tsx` | `GET /admin/export-log` | `useQuery` | ✓ WIRED | sezione "Download registrati" presente |
| `CoefficientiPage.tsx`/`LeadDashboardPage.tsx` | `POST /import-excel/{risorsa}/preview` | `FlatImportDialog` con `risorsa` | ✓ WIRED | confermato nei due file |
| `import_excel.py` | `handler.ruolo_richiesto` | gate per risorsa | ✓ WIRED | `_verifica_permesso` legge dall'handler risolto, MAI dal client — `test_import_lead.py::test_consulente_non_puo_importare_parametri` PASS |
| `DiffPreviewTable.tsx` | `riga_modificata_dopo_export` | badge ambra + banner | ✓ WIRED | grep conferma presenza sia lato backend (scritto solo nel ramo diff) che frontend |

### Anti-Leak (regola di dominio #1, verifica esplicita richiesta)

- `coefficiente_impresa` esce dal file SOLO nel ramo opt-in `con_margine=True`, aggiunto alla lista colonne (non filtrato a valle) — struttura verificata a codice in `export_excel/parametri.py`.
- Nessun valore di margine del seed compare in nessuna cella del file default — verificato cella-per-cella da `test_export_default_non_contiene_coefficiente_impresa`.
- Scrittura di `coefficiente_impresa` in import isolata in due sole funzioni `is_admin`-gated (`_forse_aggiungi_margine`/`_forse_aggiornare_margine`); un consulente non raggiunge nemmeno quel path perché `ruolo_richiesto="admin"` sulla risorsa `parametri` blocca prima.
- Nessun import può azzerare silenziosamente il margine: `#CANCELLA#` non è nell'insieme delle colonne nullable per il margine (colonna NOT NULL a schema), e una riga senza la colonna margine nel file non tocca il campo esistente (`test_file_senza_margine_non_azzera_il_coefficiente` PASS).
- `test_no_leak.py`/`test_no_leak_admin.py` preesistenti continuano a passare (eseguiti nella suite completa, 517 passed).

### Requirements Coverage

| Requirement | Source Plan(s) | Descrizione | Status | Evidence |
|---|---|---|---|---|
| CUR-01 | 08-01, 08-03, 08-06, 08-07, 08-08 | Export/import in round-trip | ✓ SATISFIED (per le risorse listino/parametri/lead — catalogo domande esplicitamente scorporato in Phase 08.1 dalla ROADMAP stessa) | test round-trip a zero su 3 risorse |
| CUR-02 | 08-03, 08-06, 08-07 | Colonna assente = campo non toccato | ✓ SATISFIED | `campi_presenti`/`CAMPI_MODIFICABILI`, test dedicati PASS |
| CUR-03 | 08-04, 08-06 | Export margine solo admin | ✓ SATISFIED | vedi sezione anti-leak sopra |
| CUR-04 | 08-01, 08-05, 08-07 | Traccia download lead | ✓ SATISFIED | `export_log` + `GET /admin/export-log` |
| PAR-04 | 08-02 | Anteprima admin breakdown+effetti | ✓ SATISFIED | `AnteprimaTab.tsx` + endpoint preesistente |

Nessun requisito orfano: tutti i 5 ID dichiarati nella ROADMAP per la Fase 08 compaiono nel frontmatter di almeno un piano, e tutti hanno evidenza di implementazione verificata a codice.

**Nota bookkeeping (non bloccante):** le checkbox di CUR-01..04 e PAR-04 in `.planning/REQUIREMENTS.md` risultano ancora `[ ]`. Per CUR-01/CUR-02 questo è coerente con lo split esplicito verso la Phase 08.1 (catalogo domande, stesso ID, non ancora pianificata) documentato nella ROADMAP stessa. Per CUR-03, CUR-04 e PAR-04 — pienamente soddisfatti da questa fase senza alcuna parte scorporata — le checkbox sembrano semplicemente non aggiornate; segnalo per l'aggiornamento di bookkeeping, non è un gap funzionale.

### Anti-Patterns Found

Nessun blocker. Un solo hit di pattern-matching su `_PLACEHOLDER_TESTO`/`_PLACEHOLDER_PREZZO` in `listino_upload_service.py` (righe 95-96, 236-266) — non è uno stub: sono valori fittizi usati SOLO per soddisfare la validazione Pydantic quando un campo è assente dal formato piatto, e sono esplicitamente esclusi dalla scrittura a database tramite `campi_presenti` (comportamento documentato nel piano 08-03 e verificato dai test di round-trip). Nessun `TBD`/`FIXME`/`XXX`/`TODO`/`HACK` trovato nei file toccati dalla fase.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Round-trip listino/parametri/lead a zero diff | `pytest test_export_import_roundtrip.py test_import_parametri.py test_import_lead.py -q` | tutti PASS | ✓ PASS |
| Anti-leak margine (colonna+valori+ruolo) | `pytest test_export_margine.py -q` | 5 passed | ✓ PASS |
| Staleness/updated_at (D-11) | `pytest test_import_stale.py -q` | 4 passed | ✓ PASS |
| Traccia export lead + log | `pytest test_export_lead_traccia.py test_export_excel_listino.py -q` | 14 passed | ✓ PASS |
| Regressione: `voce.livello` protetto | `pytest test_dettaglio_pro_livelli.py -k azzera_livello -q` | 1 passed | ✓ PASS |
| Migrazione 0019 applicabile e coerente coi modelli ORM | `alembic upgrade head --sql` (dry-run) + grep `updated_at` nei modelli | ALTER TABLE coerenti, colonne dichiarate nei modelli | ✓ PASS |

Totale: 48 test dedicati alla fase, tutti PASS (rieseguiti isolatamente, non solo dichiarati dal SUMMARY).

### Probe Execution

N/A — nessuno script `probe-*.sh` dichiarato o presente per questa fase (fase applicativa web, non migrazione/CLI). Skipped.

### Human Verification Required

Nessuno. Tutte le verità osservabili sono state confermate a livello di codice/test/grep con evidenza diretta (endpoint, gate di ruolo, colonne del workbook, contenuto delle celle). Nessun comportamento visivo/real-time/servizio-esterno rimane da verificare manualmente per raggiungere il goal della fase.

### Gaps Summary

Nessun gap. Le cinque success criteria della ROADMAP e i cinque requisiti (CUR-01..04, PAR-04) sono tutti verificati con evidenza diretta nel codice e nei test (48 test eseguiti, tutti PASS). La regola di dominio non negoziabile (margine mai al client non-admin, mai azzerabile silenziosamente da import) è verificata sia strutturalmente (colonna aggiunta solo nel ramo opt-in, scrittura isolata in 2 funzioni is_admin-gated) sia dai test che apre il workbook e ne legge davvero il contenuto cella per cella.

Unico punto di attenzione non bloccante: bookkeeping delle checkbox in REQUIREMENTS.md (vedi sopra) e il fatto che il `dev.db` locale non ha ancora applicato la migrazione 0019 (irrilevante: file gitignored, basta `alembic upgrade head` prima di lanciare il backend in locale).

---

_Verified: 2026-09-22_
_Verifier: Claude (gsd-verifier)_
