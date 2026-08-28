---
phase: 04-lead-pannello-admin
plan: 05
subsystem: api
tags: [openpyxl, python-multipart, fastapi, excel-upload, sqlalchemy]

# Dependency graph
requires:
  - phase: 04-lead-pannello-admin plan 02
    provides: "admin/listini.py CRUD listino+categoria+voce, admin/upload_listino.py stub router, ListinoAdminOut/ComuneListino pattern"
provides:
  - "computo_parsing.py: classificazione riga condivisa (header vs voce, state machine A-EDILE, cataloghi B/C/D) tra script dev e service runtime"
  - "listino_upload_service.py: validate_upload/parse_computo/resolve_destinazione/compute_diff/apply_diff_idempotent, due rami (listino esistente | nuova città)"
  - "POST /api/v1/admin/upload-listino/preview e /confirm: flusso a due passi, stateless round-trip, upsert idempotente non distruttivo"
  - "openpyxl promosso a runtime dependency, python-multipart pinnato esplicitamente"
affects: [04-08 (UI dropzone/diff upload — consuma queste due route)]

# Tech tracking
tech-stack:
  added: [python-multipart>=0.0.21 (runtime, FastAPI UploadFile)]
  patterns:
    - "Classificazione riga Excel estratta in modulo puro condiviso (computo_parsing.py) tra script dev e service runtime, con parametro scarti opzionale per hardening senza regressione sul chiamante dev"
    - "Round-trip stateless preview→confirm: il client re-invia il payload diff completo, nessuna cache/sessione server per il pending upload"
    - "UploadTarget discriminato (kind: esistente|nuova_citta) via Pydantic TypeAdapter + Field(discriminator)"

key-files:
  created:
    - backend/app/services/computo_parsing.py
    - backend/app/services/listino_upload_service.py
    - backend/app/schemas/admin_upload.py
    - backend/tests/test_upload_listino.py
  modified:
    - backend/app/routers/admin/upload_listino.py
    - backend/scripts/extract_dettaglio_pro.py
    - backend/pyproject.toml

key-decisions:
  - "Scope dell'upload limitato a Sottocategoria/Voce (dettaglio Pro): ListinoCategoria (base_eur_mq/coefficiente_impresa, motore Free) resta un ritocco CRUD separato e deliberato (04-02), coerente con D-10 — Voce non ha mai colonne di margine per costruzione, quindi l'upload non può e non deve scriverle"
  - "Validazione prezzo>0 applicata a livello di business rule nel service runtime (VoceRigaIn Field(gt=0)), NON nella classificazione pura condivisa (computo_parsing.py), per non regredire extract_dettaglio_pro.py che nel file reale contiene voci con prezzo 0.0 (verificato: lo script fallirebbe se il vincolo fosse nella funzione condivisa)"
  - "Natural key voce ancorata alla natural key sottocategoria (categoria_code, sotto_codice-o-nome, voce_codice-o-descrizione), non solo all'id, per confrontare righe non ancora applicate (diff) contro lo stato DB reale nello stesso modo dell'upsert finale"

patterns-established:
  - "Modulo di classificazione pura condivisibile tra script one-off e service runtime, con hardening opzionale via parametro (scarti=None preserva comportamento originale)"

requirements-completed: [ADM-01]

# Metrics
duration: 1h35min
completed: 2026-08-28
---

# Phase 04 Plan 05: Upload Excel listino (preview+confirm) Summary

**Flusso Excel a due passi `/admin/upload-listino/preview` + `/confirm` con destinazione discriminata (listino esistente o nuova città), parser hardened condiviso con lo script Fase 3, upsert idempotente mai distruttivo su Sottocategoria/Voce.**

## Performance

- **Duration:** ~1h35min complessive (12 min lettura+checkpoint aperto, poi ripresa dopo approvazione utente: ~1h23min per Task 1-3)
- **Started:** 2026-08-28T10:23:00Z
- **Completed:** 2026-08-28T11:53:00Z
- **Tasks:** 3/3 completati
- **Files modified:** 7 (4 creati, 3 modificati)

## Accomplishments

- Checkpoint `blocking-human` (Task 1) approvato dal coordinatore/utente: `openpyxl` promosso a runtime dependency, `python-multipart>=0.0.21` aggiunto esplicitamente (risolto a 0.0.32 da uv).
- `computo_parsing.py`: classificazione riga (header vs voce, state machine A-EDILE con confine "TOTALE ALLESTIMENTO"/blocco sintetico A.0, cataloghi flat B/C/D) estratta da `extract_dettaglio_pro.py` in un modulo condiviso, con hardening opzionale (parametro `scarti`) che non regredisce lo script dev — verificato bit-a-bit: `docs/seed-dettaglio-pro.json` rigenerato identico al committato.
- `listino_upload_service.py`: `validate_upload` (estensione/dimensione PRIMA del parse) + `parse_computo` (ogni riga malformata → scarto, mai un'eccezione a 500) + `resolve_destinazione`/`compute_diff`/`apply_diff_idempotent` sui due rami (listino esistente, nuova città).
- Router `POST /api/v1/admin/upload-listino/preview` + `POST .../confirm`: flusso stateless (Pattern 4), destinazione discriminata via Pydantic, `require_admin` su entrambe.
- 18 test nuovi tutti verdi: 403/401, smoke multipart reale, validazione file, ramo esistente (nuove/modificate/scarti/idempotenza/D-24/404), ramo nuova città (T-04-42 preview non scrive, D-13 confirm crea Listino+ComuneListino risolvibile senza fallback, idempotenza).

## Task Commits

1. **Task 1: Gate legittimità pacchetti (approvato)** - `20aa1af` (chore) — openpyxl → runtime, python-multipart pinnato
2. **Task 2: computo_parsing.py + listino_upload_service.py** - `45227fd` (feat, GREEN)
3. **Task 3: router /admin/upload-listino preview+confirm** - `99d23f4` (feat, GREEN)

**Checkpoint aperto (poi risolto):** `7b3c1f4` (docs) — documentazione dello stato bloccato, prima dell'approvazione ricevuta dal coordinatore.

_Nota: TDD applicato come service+router-level (RED implicito nei test scritti e verificati contro l'implementazione già presente, poi iterati fino a GREEN — non una sequenza commit-per-commit RED→GREEN separata, dato il volume di codice del Task 2/3 scritto in un'unica sessione dopo l'approvazione)._

## Files Created/Modified

- `backend/app/services/computo_parsing.py` - Classificazione riga condivisa (pura, hardening opzionale via `scarti`)
- `backend/app/services/listino_upload_service.py` - parse/diff/upsert idempotente, 2 rami destinazione
- `backend/app/schemas/admin_upload.py` - UploadTarget discriminato, DiffPreviewOut/DiffConfirmIn/ImportResultOut
- `backend/app/routers/admin/upload_listino.py` - POST /preview + /confirm dietro require_admin
- `backend/scripts/extract_dettaglio_pro.py` - Refactored per importare da computo_parsing (nessuna regressione)
- `backend/pyproject.toml` - openpyxl → runtime, python-multipart aggiunto
- `backend/tests/test_upload_listino.py` - 18 test (403/401, smoke multipart, D-20, ramo esistente, ramo nuova città, D-24, idempotenza)

## Decisions Made

- Scope dell'upload limitato a Sottocategoria/Voce (dettaglio Pro): `ListinoCategoria` (base_eur_mq/coefficiente_impresa) resta un ritocco CRUD separato (04-02) — coerente con D-10, `Voce` non ha mai colonne di margine.
- Validazione `prezzo > 0` spostata dal modulo di classificazione pura (che deve restare invariato per `extract_dettaglio_pro.py`, il cui file reale contiene voci con prezzo 0.0) al service runtime, come regola di business separata.
- Natural key voce ancorata alla natural key sottocategoria (non al solo id), per confrontare correttamente righe non ancora applicate contro lo stato DB durante il diff.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Validazione prezzo>0 inizialmente collocata nel modulo di classificazione condivisa, causava regressione sullo script Fase 3**
- **Found during:** Task 2, verifica no-regression di `extract_dettaglio_pro.py`
- **Issue:** Il file reale (`docs/computo-base-reggio-emilia.xlsx`) contiene almeno una voce con prezzo 0.0; la prima versione di `_validate_voce_input` in `computo_parsing.py` rifiutava prezzo<=0, facendo fallire lo script dev su dati reali (mai accaduto in Fase 3, dove non c'era questo vincolo).
- **Fix:** Rimossa la validazione prezzo>0 dal livello di classificazione pura; spostata come regola di business nel service runtime (`VoceRigaIn` Pydantic `Field(gt=0)`), con conversione a scarto invece di eccezione non gestita in `_sotto_dict_to_righe`.
- **Files modified:** backend/app/services/computo_parsing.py, backend/app/services/listino_upload_service.py
- **Verification:** `uv run python scripts/extract_dettaglio_pro.py` rigenera `docs/seed-dettaglio-pro.json` identico bit-a-bit al file committato (nessuna diff); test `test_riga_malformata_scartata_resto_importato` verde.
- **Committed in:** 45227fd (Task 2 commit)

**2. [Rule 1 - Bug] Riga di confine "TOTALE ALLESTIMENTO DI CANTIERE" nei fixture di test inizialmente costruita con colonne invertite**
- **Found during:** Task 2/3, prima esecuzione dei test
- **Issue:** Il fixture helper `_build_xlsx` nel file di test posizionava il testo del marcatore di confine nella colonna "codice" invece che "descrizione", facendo sì che la riga venisse scartata da `if descrizione is None: continue` prima di raggiungere il controllo del confine — di conseguenza la state machine restava permanentemente in fase "allestimento" e le voci di test finivano sotto la sottocategoria sintetica A.0 invece che sotto le sottocategorie reali (A.1 ecc.), causando collisioni di chiave naturale con i dati di seed reali.
- **Fix:** Corretto l'ordine delle colonne nel fixture (`_TOTALE_ALLESTIMENTO_ROW = (None, "TOTALE ALLESTIMENTO DI CANTIERE", None, None, None)`), auto-anteposto in `_build_xlsx`.
- **Files modified:** backend/tests/test_upload_listino.py
- **Verification:** 18/18 test verdi.
- **Committed in:** 45227fd (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (entrambi Rule 1 — bug scoperti durante la verifica no-regression/test-writing di questo stesso piano, nessuno scope creep).
**Impact on plan:** Nessun impatto negativo — entrambi i fix erano necessari per la correttezza del piano stesso, non modifiche a codice fuori scope.

## Issues Encountered

- **`tests/test_health.py::test_health_db_returns_live_count`** fallisce anche in isolamento (`sqlite3.OperationalError: no such table: listino`) — problema ambientale pre-esistente già documentato in `04-02-SUMMARY.md`/`deferred-items.md` (dev.db locale non migrato in questo worktree), non correlato ai file di questo piano. Non toccato (Scope Boundary). Suite completa: 158 passed, 4 skip (GTK3, invariati), 1 failed (solo questo, pre-esistente).

## User Setup Required

None - nessuna configurazione di servizio esterno richiesta. Il checkpoint `blocking-human` del Task 1 è stato risolto con l'approvazione esplicita ricevuta durante l'esecuzione (vedi commit `20aa1af`).

## Next Phase Readiness

- **ADM-01 (upload bulk Excel)** completo lato server per questo piano: parse hardened, diff senza scritture, upsert idempotente non distruttivo, creazione Listino+ComuneListino per città nuova solo in confirm, validazione dimensione/estensione, protezione admin.
- Il piano 04-08 (UI dropzone/diff) può ora consumare `/api/v1/admin/upload-listino/preview` e `/confirm` così come definite qui (schema `DiffPreviewOut`/`DiffConfirmIn`/`ImportResultOut` in `schemas/admin_upload.py`).
- Nota per 04-08 o un futuro ritocco: per rendere una città caricata via upload immediatamente utilizzabile anche dal motore Free (`/api/v1/stima`), l'admin deve ancora eseguire il passo CRUD separato (`POST /admin/listini/{id}/categorie`, 04-02) per popolare `base_eur_mq`/`coefficiente_impresa` — questo piano copre solo il dettaglio Pro (Sottocategoria/Voce), per costruzione (D-10).

## Self-Check: PASSED

Tutti i 7 file dichiarati (`computo_parsing.py`, `listino_upload_service.py`, `admin_upload.py`, `test_upload_listino.py`, `upload_listino.py`, `extract_dettaglio_pro.py`, `pyproject.toml`) verificati presenti su disco. Tutti i 4 commit dichiarati (`7b3c1f4`, `20aa1af`, `45227fd`, `99d23f4`) verificati presenti in `git log`.

---
*Phase: 04-lead-pannello-admin*
*Completed: 2026-08-28*
