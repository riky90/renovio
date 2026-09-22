---
phase: 08-export-import-excel
plan: 07
subsystem: api
tags: [fastapi, sqlalchemy, openpyxl, react-query, import-excel]

# Dependency graph
requires:
  - phase: 08-export-import-excel (08-05)
    provides: "export_excel/lead.py::build_workbook_lead — header esatto del foglio lead"
  - phase: 08-export-import-excel (08-06)
    provides: "registry.py (HANDLER/registra/risolvi_handler), admin_import.py (RigaPiattaIn/DiffRigaOut/DiffPiattoOut/ConfirmPiattoIn), FlatImportDialog.tsx, router generico /import-excel/{risorsa}"
provides:
  - "Import lead (services/import_excel/lead.py): risoluzione solo per id (deroga a D-04), CAMPI_MODIFICABILI={stato,nota,referente_id}, ogni altro campo divergente dal DB blocca la riga"
  - "Permesso per risorsa (ImportHandler.ruolo_richiesto): admin sui parametri, staff sui lead, controllato dal router generico dopo aver risolto la risorsa"
  - "Toolbar lead: Scarica lead · Carica file"
affects: [08-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ImportHandler.ruolo_richiesto (\"admin\"|\"staff\") come nuovo campo del Protocol: router generico legge il ruolo dall'handler RISOLTO (mai dal client), gate spostato da require_admin fisso a get_current_user + controllo dinamico"
    - "confirm_import passa is_admin=(user.role==ROLE_ADMIN) reale invece di True fisso: necessario ora che una risorsa (lead) accetta anche il consulente, non solo l'admin"
    - "Resolver a singolo foglio senza ramo 'nuova' (diff/apply ritornano sempre [] come prima lista): la deroga a D-04 si applica a livello di struttura, non di if sparso nel codice"
    - "Confronto per-campo tipizzato (_valori_uguali) per rilevare un tentativo di riscrittura su colonne non modificabili: Decimal per i totali, int per mq, bool per email_inviata, isoformat per created_at (mai str(datetime), formato diverso da isoformat), stringa per il resto"

key-files:
  created:
    - backend/app/services/import_excel/lead.py
    - backend/tests/test_import_lead.py
  modified:
    - backend/app/services/import_excel/registry.py
    - backend/app/services/import_excel/parametri.py
    - backend/app/routers/admin/import_excel.py
    - frontend/src/pages/admin/LeadDashboardPage.tsx

key-decisions:
  - "CAMPI_MODIFICABILI limitato a stato/nota/referente_id (senza email_inviata): il piano lo lasciava 'eventualmente', nessun test lo richiede, e la PATCH esistente non lo tocca — includerlo avrebbe aperto una superficie di scrittura non richiesta da nessun must_have"
  - "COLONNE_LEAD include 'id' esplicitamente (a differenza di quanto sembrerebbe leggendo solo l'header del foglio): leggi_foglio_piatto scarta silenziosamente ogni colonna non in colonne_ammesse, quindi omettere 'id' avrebbe fatto risultare OGNI riga 'senza id' — scoperto dal primo run dei test (3 falliti su 8)"
  - "_valori_uguali confronta created_at via isoformat() su entrambi i lati, non str(datetime): str(datetime) usa lo spazio come separatore data/ora, isoformat() usa 'T' — lo stesso valore sarebbe risultato sempre 'diverso' nel round-trip a vuoto"

requirements-completed: [CUR-01, CUR-02, CUR-04]

duration: ~50min
completed: 2026-09-22
---

# Phase 08 Plan 07: Import Excel dei lead Summary

**Handler `lead` che chiude il quarto round-trip (`stato`/`nota`/`referente_id` curabili in blocco da Excel, tutto il resto dei dati di contatto/totali bloccato riga-per-riga se diverge dal database) e permesso per risorsa sul router generico di import (admin sui parametri, staff sui lead), con bottone "Carica file" sulla dashboard lead.**

## Performance

- **Duration:** ~50 min (dalla lettura del piano al commit finale)
- **Completed:** 2026-09-22
- **Tasks:** 2/2 completati
- **Files modified:** 6 (2 creati, 4 modificati)

## Accomplishments

- `services/import_excel/registry.py`: `ImportHandler.ruolo_richiesto: str` aggiunto al Protocol — `"admin"` o `"staff"`, dichiarato da ogni handler, mai un valore fidato dal client
- `services/import_excel/lead.py`: risoluzione **solo per `id`** (i lead non hanno chiave naturale), riga senza `id` sempre uno scarto descritto (deroga dichiarata a D-04, mai un lead nuovo — `diff()`/`apply()` non hanno un ramo "nuova"), `CAMPI_MODIFICABILI = {"stato", "nota", "referente_id"}`, qualunque altra colonna del foglio presente con un valore diverso dal database blocca l'INTERA riga (`_valori_uguali`, confronto tipizzato per campo), `stato` limitato a `{"nuovo", "gestito"}` (stesso dominio della UI esistente), `#CANCELLA#` ammesso solo su `nota`/`referente_id`, zero `db.delete`
- `routers/admin/import_excel.py`: gate da `require_admin` fisso a `get_current_user` + `_verifica_permesso(handler, user)` che legge `ruolo_richiesto` dall'handler risolto — controllato DOPO la risoluzione della risorsa e PRIMA di leggere il file; `confirm_import` passa `is_admin=(user.role == ROLE_ADMIN)` reale invece di `True` fisso (necessario ora che il consulente puo' raggiungere `/confirm` per la risorsa lead)
- `services/import_excel/parametri.py`: `ruolo_richiesto = "admin"` aggiunto all'handler esistente, nessun altro cambio — la suite di 08-06 resta verde a dimostrazione che il gate non si e' allentato
- 8 test in `test_import_lead.py`: round-trip a vuoto, `stato`/`nota` aggiornabili in blocco, email non modificabile da file (scarto + valore DB invariato), riga senza id non crea un lead (conteggio invariato), consulente 200 sui lead, utente 403 su preview e confirm, lo stesso consulente 403 sui parametri (permesso per risorsa, non globale), nessuna eliminazione su import parziale
- Frontend: bottone "Carica file" (`variant="outline"`, icona `UploadCloud`) dopo "Scarica lead" in `LeadDashboardPage.tsx`, riusa `FlatImportDialog` esistente con `risorsa="lead"`, invalida le query `admin-leads` e `admin-export-log` a import riuscito, nessun gate client-side sul ruolo

## Task Commits

Ogni task committato atomicamente:

1. **Task 1: handler dei lead e permesso per risorsa sul router generico** - `982a494` (feat)
2. **Task 2: bottone Carica file sulla dashboard lead** - `6ac5cbe` (feat)

**Plan metadata:** committed separately by orchestrator (worktree mode — STATE.md/ROADMAP.md non toccati da questo agente)

## Files Created/Modified

- `backend/app/services/import_excel/lead.py` - Handler lead: `parse`/`diff`/`apply`, `CAMPI_MODIFICABILI`, `_risolvi`, `_valori_uguali`, `ruolo_richiesto = "staff"`
- `backend/app/services/import_excel/registry.py` - `ImportHandler.ruolo_richiesto: str` aggiunto al Protocol
- `backend/app/services/import_excel/parametri.py` - `_ParametriHandler.ruolo_richiesto = "admin"`
- `backend/app/routers/admin/import_excel.py` - Gate per risorsa (`_verifica_permesso`), `is_admin` reale in `confirm_import`, import del modulo `lead` per side-effect di registrazione
- `backend/tests/test_import_lead.py` - 8 test (dettagliati sopra)
- `frontend/src/pages/admin/LeadDashboardPage.tsx` - Bottone "Carica file", `FlatImportDialog` montato, invalidazione query

## Decisions Made

Vedi `key-decisions` in frontmatter — sintesi:
- `email_inviata` lasciato fuori da `CAMPI_MODIFICABILI` (il piano lo definiva "eventuale", nessun test lo richiede)
- `COLONNE_LEAD` deve includere `"id"` esplicitamente — omissione scoperta dal primo run dei test
- Confronto `created_at` via `isoformat()`, non `str(datetime)`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `COLONNE_LEAD` non includeva `"id"`, facendo risultare ogni riga "senza id"**
- **Found during:** Task 1, primo run di `test_import_lead.py` (3/8 falliti)
- **Issue:** `leggi_foglio_piatto` scarta silenziosamente ogni colonna dell'header non presente in `colonne_ammesse`. Avendo definito `COLONNE_LEAD` senza `"id"` (per analogia con `COLONNE_LEAD` di `export_excel/lead.py`, che invece la include come prima colonna dell'header), la colonna `id` non veniva mai letta: ogni riga del foglio risultava "senza id", quindi scartata dalla deroga a D-04 anche quando l'id era presente e valido.
- **Fix:** Aggiunto `"id"` a `COLONNE_LEAD` (stesso pattern di `COLONNE_MOLTIPLICATORI`/`COLONNE_LISTINO_CATEGORIA` in `parametri.py`, che lo includono correttamente).
- **Files modified:** `backend/app/services/import_excel/lead.py`
- **Verification:** `test_roundtrip_lead_a_vuoto`, `test_stato_e_nota_aggiornabili`, `test_email_non_modificabile_da_file` passano dopo il fix
- **Committed in:** `982a494` (Task 1, corretto prima del commit)

**2. [Rule 1 - Bug] Confronto `created_at` tramite `str(datetime)` invece di `isoformat()`**
- **Found during:** Task 1, secondo run dei test (2/8 falliti dopo il fix precedente)
- **Issue:** `_valori_uguali` normalizzava `created_at` con lo stesso ramo generico `str(valore).strip()` usato per i campi stringa. `str(datetime)` produce `"2026-09-22 20:54:01.123456"` (spazio), mentre il file esportato porta `lead.created_at.isoformat()` = `"2026-09-22T20:54:01.123456"` ('T') — un round-trip a vuoto risultava sempre "diverso" su questo campo, con la riga scartata come tentativo di riscrittura di un campo non modificabile.
- **Fix:** Ramo dedicato per `created_at`: `valore_db.isoformat()` se e' un'istanza `datetime`, confrontato con la stringa del file.
- **Files modified:** `backend/app/services/import_excel/lead.py`
- **Verification:** `test_roundtrip_lead_a_vuoto`/`test_stato_e_nota_aggiornabili` passano; suite completa (import lead + import parametri + export lead + admin lead) 36/36 verde
- **Committed in:** `982a494` (Task 1, corretto prima del commit)

---

**Total deviations:** 2 auto-fixed (entrambi bug, scoperti dai test del piano stesso prima del commit)
**Impact on plan:** Nessuno scope creep — entrambi i fix sono interni al file dichiarato dal piano (`lead.py`), necessari per la correttezza dichiarata dal piano stesso (round-trip a vuoto = zero righe modificate).

## Known Limitations

- `email_inviata` non e' in `CAMPI_MODIFICABILI`: se in futuro serve segnare a mano un invio via file (il piano lo lasciava "eventuale"), va aggiunto esplicitamente all'insieme e coperto da un test dedicato — oggi resta un campo di sola lettura/confronto come nome/email/telefono.
- Il messaggio di scarto per un campo non modificabile divergente non elenca il valore proposto (solo il nome del campo), per non ripetere nel testo un dato di contatto potenzialmente sensibile in un log/risposta HTTP — coerente con la disciplina generale del progetto, ma non esplicitamente richiesto dal piano.

## Issues Encountered

Worktree partito da una base indietro rispetto alla head attesa (`f011ed4` invece di `28cc510`): `git reset --hard 28cc510...` eseguito come da protocollo prima di qualunque lettura/scrittura (working tree pulito, nessun commit locale perso).

`backend/.venv`/`frontend/node_modules` assenti in questo worktree (gitignored): risolto con due symlink locali verso le cartelle del repo principale, stessa soluzione dei piani precedenti della fase, nessun impatto sul contenuto dei commit (verificato con `git status --short`).

## User Setup Required

None - nessuna configurazione di servizio esterno richiesta.

## Next Phase Readiness

- Il registro `HANDLER` e il gate per risorsa sono pronti per il piano 08-08 (guardia stale su `updated_at`): la sua estensione a `DiffRigaOut` (badge "Cambiata dopo l'export") si applica a `DiffPreviewTable.tsx`, un punto solo, indipendente dagli handler di questa fase
- Verifica manuale a schermo (bottone Carica file, dialog di import, aggiornamento tabella dopo conferma) non eseguita in questo agente isolato: nessun ambiente backend con dati reali disponibile nel worktree, coerente con la limitazione gia' documentata nei piani precedenti della fase. Verificato invece con la suite pytest completa (36 test: import lead + import parametri + export lead + admin lead) e `npx tsc -b` pulito.
- Nessun blocco noto per il piano 08-08.

---
*Phase: 08-export-import-excel*
*Completed: 2026-09-22*
