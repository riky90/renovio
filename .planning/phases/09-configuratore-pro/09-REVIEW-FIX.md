---
phase: 09-configuratore-pro
fixed_at: 2026-09-29T07:35:15Z
review_path: .planning/phases/09-configuratore-pro/09-REVIEW.md
iteration: 1
findings_in_scope: 8
fixed: 8
skipped: 0
status: all_fixed
---

# Phase 09: Code Review Fix Report

**Fixed at:** 2026-09-29T07:35:15Z
**Source review:** .planning/phases/09-configuratore-pro/09-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 8 (CR-01, WR-01..WR-07; gli Info IN-01..IN-05 sono fuori scope)
- Fixed: 8
- Skipped: 0

Verifica: test mirati dopo ogni fix, `npx tsc -b` e `npm run build` sul frontend,
suite backend completa a fine lavoro (esito in fondo).

## Fixed Issues

### CR-01: "Modifica listino" può impedire l'avvio della produzione

**Files modified:** `backend/app/routers/admin/listini.py`, `backend/app/services/listino_upload_service.py`, `backend/scripts/seed.py`, `backend/tests/test_admin_listini.py`, `backend/tests/test_seed.py`, `frontend/src/pages/admin/ListiniPage.tsx`
**Commit:** 5a4df2e
**Applied fix:**
- `PATCH /admin/listini/{id}` con `is_default=true` toglie il flag agli altri listini nella stessa transazione. `is_default=false` sull'unico predefinito risponde 409. Lo stesso invariante vale per `POST /admin/listini` e per l'upload "nuova città" (`apply_diff_idempotent`), che prima potevano creare un secondo predefinito.
- Il seed ritrova il listino RE per `citta_riferimento` (sola lettura nel pannello) invece che per `nome`, e lo marca predefinito solo se nessun altro listino lo è.
- Nel dialog lo switch "Predefinito" è disabilitato sul listino predefinito, con una spiegazione. Sugli altri listini, quando è attivo, un aiuto avverte che il listino diventerà il fallback.
- Non ho aggiunto l'indice parziale `UNIQUE (is_default) WHERE is_default`, che la review indicava come opzionale: servirebbe una migrazione 0024 nuova. L'invariante oggi è applicato solo dal codice.

### WR-01: Il seed annulla a ogni boot "Predefinito"/"Attivo"

**Files modified:** `backend/scripts/seed.py`, `backend/tests/test_seed.py`
**Commit:** 7747248
**Applied fix:** il seed non riscrive più `listino.attivo`: il campo prende il default solo alla creazione. `is_default` è già gestito da CR-01, che lo imposta solo se manca un predefinito. Il pannello non può più togliere il flag all'unico predefinito, quindi il seed non lo ribalta.

### WR-02: Il downgrade della 0021 resta asimmetrico sugli effetti

**Files modified:** `backend/alembic/versions/0021_assi_pro_da_livello_e_chiavi_mirate.py`, `backend/tests/test_migrazioni_sqlite.py`
**Commit:** 153a712
**Status:** fixed: requires human verification
**Applied fix:** `downgrade()` è ora un no-op documentato, come chiedevi (downgrade non distruttivo, upgrade invariato). Non si possono distinguere le righe scritte dall'upgrade da quelle identiche create dal seed o a mano. Per questo non si cancellano più né gli `includi` di `finitura` né i `quantita_per_unita` sulle chiavi mirate, e il downgrade non dipende più da `voce.livello`. Anche la sezione (B) aveva la stessa asimmetria verso il seed, quindi l'ho resa no-op insieme alla (A). Ho aggiornato i due test esistenti e aggiunto il caso chiesto dalla review: `includi` preesistente su una voce livellata più un `quantita_per_unita` preesistente, entrambi conservati.
**Da verificare:** dopo un `downgrade 0020` restano in `effetto_opzione` le righe della 0021. Lo schema 0020 e 0021 è identico e un nuovo upgrade non le duplica.

### WR-03: 0021/0022/0023 risolvono la sottocategoria senza filtro sul listino e senza ORDER BY

**Files modified:** `backend/alembic/versions/0022_taratura_pro_approvata.py`, `backend/alembic/versions/0023_pavimenti_alternativi.py`, `backend/scripts/applica_taratura.py`, `backend/tests/test_migrazioni_sqlite.py`
**Commit:** 58b7daa
**Status:** fixed: requires human verification
**Applied fix:** `_risolvi_voce_id` filtra sul listino predefinito (`_listino_default_id`, `is_default IS true ORDER BY id LIMIT 1`), come fa `seed_domande`, e ordina per id sottocategorie e voci. Il template di `applica_taratura.py` eredita lo stesso filtro. Aggiunto un test con due listini con gli stessi codici: il listino non predefinito ha id più basso e resta intatto.
**Scostamento dalla review:** se manca un listino predefinito non faccio un no-op esplicito. Le chiavi risultano non risolte e decide la guardia che c'è già: la 0023 fa no-op senza la domanda `tipo_pavimento`; il template fa no-op se `_catalogo_presente` è falso e solleva `RuntimeError` se è vero. Con il no-op esplicito il test esistente `test_catalogo_presente_e_chiave_non_risolta_solleva_runtime_error`, che non ha listini, non avrebbe più sollevato l'errore. Ho preferito tenere il fail-loud.
**Nota:** la 0021 non risolve per sottocategoria (legge `voce.livello` e `domanda_mirata_key` per id), quindi non l'ho toccata. Su `dev.db`, già a 0023, la modifica non ha effetto. In produzione (0013) la 0023 è comunque un no-op, perché manca il catalogo domande.

### WR-04: Il downgrade della 0023 cancella effetti che l'upgrade non ha scritto

**Files modified:** `backend/alembic/versions/0023_pavimenti_alternativi.py`, `backend/tests/test_migrazioni_sqlite.py`
**Commit:** 6a0842c
**Status:** fixed: requires human verification
**Applied fix:** il downgrade cancella solo le righe identiche alle costanti: stessa chiave naturale, `valore` uguale (con `_vicino`) e `attivo` vero. Un effetto ritarato o disattivato dall'admin resta. Ho corretto la docstring del modulo e quella di `downgrade()` per dichiarare il limite residuo: le righe identiche create dal seed non si distinguono da quelle dell'upgrade e tornano comunque allo stato 0022. Il `updated_at` sentinella non era applicabile, perché l'upgrade già eseguito ha scritto timestamp reali. Nuovo test "seed già passato → upgrade → taratura a mano → downgrade".

### WR-05: Il template disattiva la guardia fail-loud sulle migrazioni di soli coefficienti

**Files modified:** `backend/scripts/applica_taratura.py`, `backend/tests/test_applica_taratura.py`
**Commit:** 43d78f7
**Applied fix:** `_catalogo_presente(bind, opzione, voce)` restituisce True se la migrazione tocca `_COEFFICIENTI` e la tabella `voce` ha righe; il controllo sulle domande citate è rimasto com'era. Nuovo test: una migrazione di soli coefficienti con una voce bersaglio alterata solleva `RuntimeError`.

### WR-06: `--aggiorna-assi` perde in silenzio le decisioni `finitura` se `voce.livello` è vuoto

**Files modified:** `backend/scripts/genera_excel_taratura.py`, `backend/tests/test_taratura_pro.py`
**Commit:** 00741be
**Applied fix:** se il foglio vecchio ha righe `finitura` con `livello_attuale` e la nuova proposta non ne ha, `aggiorna_foglio_assi` solleva `ValueError` ("voce.livello è vuoto nel DB: ripopolalo prima di --aggiorna-assi") prima di toccare il workbook. Ho usato `ValueError` invece di `SystemExit` per coerenza con gli altri errori del modulo. Le altre righe vecchie che spariscono con decisione OK o vuota ora vengono segnalate con un avviso. Non ho implementato il suggerimento "meglio ancora" della review, cioè derivare l'asse finitura dagli effetti del seed: è un cambio di algoritmo, non un fix.

### WR-07: Il cambio pavimento invia modifiche non confermate e mostra una scelta non applicata

**Files modified:** `frontend/src/components/DettaglioProView.tsx`
**Commit:** 0e16902
**Status:** fixed: requires human verification
**Applied fix:** la mutation riceve `{risposte, livelli}`. `handleSceltaChange` invia le risposte e i livelli del dettaglio salvato (`dettaglio.domande[].valore`, `dettaglio.livelli`) più la sola scelta cambiata. In `onError` riporta la card all'opzione precedente. Il pannello non viene più ricollassato dal cambio pavimento: il collasso resta solo su "Calcola il dettaglio" e "Salta", così le modifiche in corso nel pannello espanso restano visibili e non applicate. Non esiste un test runner frontend: va provato a mano nel ri-collaudo.

## Suite completa

Ho eseguito `backend/.venv/Scripts/python.exe -m pytest` nel worktree isolato, con tutti gli 8 commit: **858 passed, 2 failed, 5 skipped** in 33 minuti.

I due fallimenti sono ambientali e non dipendono dai fix. Il worktree non ha `backend/dev.db`, che è in gitignore:
- `tests/test_health.py::test_health_db_returns_live_count` apre la `SessionLocal` su `dev.db`, e l'engine crea un file vuoto ("no such table: voce");
- `tests/test_seed_dettaglio.py::test_seed_json_coerente_con_le_decisioni_del_file_di_taratura` fa skip solo se `dev.db` manca, ma lo trova vuoto per colpa del test precedente.

Ho rilanciato gli stessi due file nel worktree con una copia del `dev.db` reale: **8 passed**. Frontend: `npx tsc -b` e `npm run build` ok.

---

_Fixed: 2026-09-29T07:35:15Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
