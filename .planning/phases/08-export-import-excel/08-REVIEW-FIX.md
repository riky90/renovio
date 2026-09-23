---
phase: 08-export-import-excel
fixed_at: 2026-09-23T10:05:00Z
review_path: .planning/phases/08-export-import-excel/08-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 08: Code Review Fix Report

**Fixed at:** 2026-09-23
**Source review:** `.planning/phases/08-export-import-excel/08-REVIEW.md`
**Iteration:** 1

**Riepilogo:**

- Findings in scope: 6 (CR-01, CR-02, CR-03, WR-01, WR-02, WR-03)
- Fixed: 6
- Skipped: 0
- Fuori scope per scelta: IN-01 (Info)

Ogni fix ha una regressione dedicata, e per ognuna è stato verificato che
fallisse sul codice precedente. Le uniche eccezioni sono dichiarate riga per
riga più sotto.

Suite completa alla fine:

```
$ backend/.venv/Scripts/python.exe -m pytest -q
555 passed, 5 skipped, 2 warnings in 905.24s (0:15:05)
```

I due warning sono preesistenti (`PytestCollectionWarning` sulla classe
`Testo`, che pytest prova a raccogliere perché il nome inizia per `Test`).
I 5 skip sono preesistenti tranne uno introdotto qui, dichiarato in WR-03.

Frontend:

```
$ npx tsc -b --force
TSC_EXIT=0
$ npx oxlint
OXLINT_EXIT=0    (0 errori; solo warning preesistenti, nessuno sui file toccati)
```

---

## Fixed Issues

### CR-03: la migrazione `0019` non si applicava su SQLite

**Stato:** fixed
**Commit:** `4665022`
**File modificati:** `backend/alembic/versions/0019_updated_at_curatela.py`,
`backend/tests/test_migrazioni_sqlite.py` (nuovo)

**Cosa è cambiato.** La colonna `updated_at` ora si aggiunge in tre passi
invece che con un singolo `add_column(server_default=func.now(),
nullable=False)`: colonna nullable senza default, backfill esplicito
all'istante della migrazione, poi `batch_alter_table` per stringere a NOT
NULL e installare `server_default=now()`. Su SQLite il batch ricostruisce la
tabella, e dentro un `CREATE TABLE` il default `CURRENT_TIMESTAMP` è legale.
Il `downgrade` passa dallo stesso batch, per simmetria e per non dipendere
dal `DROP COLUMN` nativo.

Il `server_default` del terzo passo non è cosmetico: i modelli ORM
dichiarano `server_default=func.now()` senza un default Python, quindi ogni
INSERT che non valorizza `updated_at` — cioè ogni riga nuova creata
dall'import — si appoggia al default del database.

**Riproduzione, prima del fix** (su una copia di `backend/dev.db`, per non
toccare l'originale):

```
$ DATABASE_URL="sqlite:///.../repro.db" ./.venv/Scripts/python.exe -m alembic upgrade head
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) Cannot add a column with non-constant default
[SQL: ALTER TABLE sottocategoria ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL]
```

**Il database locale è stato davvero migrato.** Backup preso prima
(`backend/dev.db.bak-pre-0019-20260923-083311`), poi:

```
$ ./.venv/Scripts/python.exe -m alembic current      # prima
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
0018

$ ./.venv/Scripts/python.exe -m alembic upgrade head
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0018 -> 0019, updated_at sulle nove tabelle curate: guardia di staleness per il re-import (D-11)

$ ./.venv/Scripts/python.exe -m alembic current      # dopo
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
0019 (head)
```

Integrità del database migrato, riga per riga (backfill completo, nessuna FK
rotta dalla ricostruzione batch):

```
integrity: ('ok',)
fk_check: []
sottocategoria (21, 21)          # (righe, righe con updated_at valorizzato)
voce (191, 191)
categoria (5, 5)
listino_categoria (4, 4)
moltiplicatore (12, 12)
extra (2, 2)
coefficiente_qta_voce (573, 573)
forfait_arredo (18, 18)
lead (0, 0)
```

**Il `downgrade` è coerente.** Verificato il giro completo
`upgrade head -> downgrade 0018 -> upgrade head` su una copia del database
reale: dopo il downgrade le nove colonne spariscono, `PRAGMA
foreign_key_check` resta vuoto, i conteggi righe sono invariati (`voce`:
191), e il re-upgrade le rimette.

**Regressione aggiunta:** `backend/tests/test_migrazioni_sqlite.py`, 8 test.

```
$ ./.venv/Scripts/python.exe -m pytest tests/test_migrazioni_sqlite.py -q
8 passed in 7.64s
```

Sul codice precedente:

```
$ git checkout -- backend/alembic/versions/0019_updated_at_curatela.py
$ ./.venv/Scripts/python.exe -m pytest tests/test_migrazioni_sqlite.py -q
FAILED tests/test_migrazioni_sqlite.py::test_upgrade_all_ultima_revisione_gira_su_un_database_popolato
FAILED tests/test_migrazioni_sqlite.py::test_0019_backfilla_le_righe_preesistenti
2 failed, 6 passed in 7.69s
```

**Un dettaglio che vale la pena conoscere.** Il test ovvio — "esegui
`alembic upgrade head` su un file SQLite usa-e-getta" — NON avrebbe
intercettato questo bug. SQLite rifiuta `ADD COLUMN ... DEFAULT
CURRENT_TIMESTAMP NOT NULL` **solo su una tabella non vuota**:

```
$ python -c "..."
3.50.4
empty table: OK
non-empty table FAIL: Cannot add a column with non-constant default
```

Per questo il test che conta
(`test_upgrade_all_ultima_revisione_gira_su_un_database_popolato`) migra
fino alla penultima revisione, popola **ogni** tabella con una riga fittizia,
e solo allora applica la revisione di testa. È scritto in forma generica
(penultima → popola → testa) proprio per valere anche sulla prossima
migrazione, non solo sulla `0019`. Gli altri sette test coprono: la catena su
database vergine, il confronto colonna per colonna fra schema migrato e
schema da `create_all`, le nove colonne NOT NULL con server default, il
backfill con l'istante giusto, l'INSERT senza `updated_at` su database
migrato, la reversibilità, e la sopravvivenza di FK e vincoli unici alla
ricostruzione batch.

---

### CR-01: l'upsert per chiave naturale ignorava `campi_presenti`

**Stato:** fixed
**Commit:** `9b352e4`
**File modificati:** `backend/app/services/listino_upload_service.py`,
`backend/tests/test_export_import_roundtrip.py`

**Cosa è cambiato.** `_upsert_sottocategoria` e `_upsert_voce` ora scrivono
sulla riga esistente solo i campi presenti in `riga.campi_presenti`, con la
stessa disciplina che `_applica_sottocategoria`/`_applica_voce` già
applicavano sul percorso per id. Sulla riga NUOVA i campi assenti restano ai
default del modello (`ordine=0`), che per una riga che non esisteva è il
valore corretto. `campi_presenti is None` continua a significare "tutti
presenti", che è il caso reale di `parse_computo`.

`voce.livello` resta deliberatamente fuori dal giro, e ora il commento dice
perché in modo esatto: le righe di `parse_computo` si dichiarano complete
(`campi_presenti is None`) ma il file del computo non ha una colonna
livello, quindi includerlo scriverebbe `None` su ogni voce a ogni
ri-caricamento, azzerando la curatela fatta a mano.

**Regressione aggiunta:** `TestRigaSenzaIdNonAzzeraCampiAssenti`, 3 test —
voce nuova sotto una sottocategoria esistente, voce esistente risolta per
chiave naturale con la cella `id` persa, più la contro-prova che i campi
presenti si scrivono ancora.

```
$ ./.venv/Scripts/python.exe -m pytest tests/test_export_import_roundtrip.py -q
11 passed in 24.11s
```

Sul codice precedente:

```
$ git checkout -- backend/app/services/listino_upload_service.py
$ ./.venv/Scripts/python.exe -m pytest tests/test_export_import_roundtrip.py -q
FAILED ...::TestRigaSenzaIdNonAzzeraCampiAssenti::test_voce_nuova_non_riscrive_l_ordine_della_sottocategoria_esistente
FAILED ...::TestRigaSenzaIdNonAzzeraCampiAssenti::test_voce_esistente_risolta_per_chiave_naturale_non_perde_l_ordine
2 failed, 9 passed in 29.36s
```

Suite di contorno (tutto ciò che tocca il servizio di upload):

```
$ ./.venv/Scripts/python.exe -m pytest tests/test_upload_listino.py tests/test_dettaglio_pro_livelli.py \
    tests/test_import_stale.py tests/test_export_excel_listino.py \
    tests/test_export_import_roundtrip.py tests/test_seed.py -q
69 passed, 1 warning in 132.80s (0:02:12)
```

---

### CR-02: `#CANCELLA#` scriveva la stringa `"None"` invece di NULL

**Stato:** fixed
**Commit:** `aa3d6fb`
**File modificati:** `frontend/src/components/admin/FlatImportDialog.tsx`,
`backend/app/services/import_excel/registry.py`,
`backend/app/services/import_excel/lead.py`,
`backend/app/services/import_excel/parametri.py`,
`backend/tests/test_import_lead.py`,
`backend/tests/test_import_parametri.py`

**Cosa è cambiato, su tre fronti.**

1. `toRigaPiattaIn` separa i null: i valori reali restano in `valori`, i
   campi a `null` finiscono in `campi_da_cancellare`, che è il canale su cui
   il backend distingue "cancella" da "scrivi questo valore".
2. Difesa in profondità lato server: nuova `campi_nulli_in_valori()` in
   `import_excel/registry.py`, applicata in `diff` e `apply` di entrambi gli
   handler. Un `None` dentro `valori` non può venire da `parse()` — che i
   `None` li sposta sempre — quindi è sempre un client che sbaglia: diventa
   uno scarto descritto invece di una stringa scritta a database.
3. L'helper `_a_riga_piatta_in` delle due suite replicava lo stesso errore
   del frontend, ed è per questo che nessun test se ne accorgeva. Ora
   ricostruisce il payload come la funzione TypeScript corretta.

**Regressione aggiunta:** `TestCancellazioneRoundTrip` (lead, 3 test) e
`TestCancellazioneRoundTripCoefficientiPro` (parametri, 3 test): il
round-trip completo preview → confirm che deve scrivere NULL, il payload
malformato che deve dare 0 righe applicate senza toccare il database, e lo
scarto visibile in preview.

```
$ ./.venv/Scripts/python.exe -m pytest tests/test_import_lead.py tests/test_import_parametri.py \
    tests/test_import_stale.py tests/test_export_margine.py -q
31 passed in 62.04s (0:01:02)
```

Sul backend precedente (fix frontend/helper già in place):

```
FAILED tests/test_import_lead.py::TestCancellazioneRoundTrip::test_un_null_dentro_valori_e_uno_scarto_non_una_stringa
FAILED tests/test_import_lead.py::TestCancellazioneRoundTrip::test_la_preview_segnala_lo_scarto_su_un_null_dentro_valori
FAILED tests/test_import_parametri.py::TestCancellazioneRoundTripCoefficientiPro::test_un_null_dentro_valori_e_uno_scarto_non_una_stringa
FAILED tests/test_import_parametri.py::TestCancellazioneRoundTripCoefficientiPro::test_la_preview_segnala_lo_scarto_su_un_null_dentro_valori
4 failed, 18 passed in 44.66s
```

La corruzione è visibile nel diff di quel run, testualmente:

```
valori_precedenti={'domanda_mirata_key': 'bagni'}, valori_nuovi={'domanda_mirata_key': 'None'}
```

Con l'helper `_a_riga_piatta_in` riportato alla forma vecchia (cioè
simulando il frontend non corretto), falliscono anche i due test di
round-trip:

```
FAILED tests/test_import_lead.py::TestCancellazioneRoundTrip::test_cancella_nota_scrive_null_non_la_stringa_none
FAILED tests/test_import_parametri.py::TestCancellazioneRoundTripCoefficientiPro::test_cancella_domanda_mirata_key_scrive_null
2 failed in 7.25s
```

**Limite dichiarato.** La funzione TypeScript in sé non ha un test
automatico: il frontend non ha un test runner configurato (nessun vitest,
nessun jest, `package.json` ha solo `dev`/`build`/`lint`/`preview`).
Installarne uno è una decisione che non ho preso da solo. Quello che la
copre oggi: `tsc -b` (verde), e l'helper Python che ne replica la logica —
se le due divergono di nuovo, i due test di round-trip qui sopra falliscono.

---

### WR-01: `bool()` su celle booleane scritte a mano

**Stato:** fixed
**Commit:** `3d64583`
**File modificati:** `backend/app/services/import_excel/flat.py`,
`backend/app/services/import_excel/lead.py`,
`backend/app/services/import_excel/parametri.py`,
`backend/tests/test_import_lead.py`,
`backend/tests/test_import_parametri.py`

**Cosa è cambiato.** Nuova `valore_booleano()` in `import_excel/flat.py`:
riconosce il booleano nativo (il caso del round-trip a vuoto, dove openpyxl
rilegge il tipo scritto dall'export), i numeri 0/1, e i testi veri/falsi in
italiano e inglese; torna `None` quando non è decidibile. `extra.attivo` e
`forfait_arredo.attivo` traducono quel `None` in uno scarto descritto, mai
in un'ipotesi su cosa intendesse l'admin.

Stessa funzione nel confronto di `lead.email_inviata`, dove il difetto aveva
il verso opposto: un `FALSE` testuale su una colonna non modificabile
risultava diverso dal database e scartava l'intera riga, bloccando
l'aggiornamento legittimo di `stato`/`nota` sulla stessa riga.

**Regressione aggiunta:** `TestBooleaniScrittiAMano` (parametri: 5 forme di
falso, 5 di vero, più il caso non interpretabile che deve restare uno
scarto) e `TestEmailInviataScrittaAMano` (lead: 4 forme di falso che non
devono bloccare, più la contro-prova che una divergenza vera scarta ancora).

```
$ ./.venv/Scripts/python.exe -m pytest tests/test_import_lead.py tests/test_import_parametri.py tests/test_import_stale.py -q
42 passed in 72.33s (0:01:12)
```

Sul codice precedente, 10 dei nuovi test falliscono:

```
FAILED tests/test_import_lead.py::TestEmailInviataScrittaAMano::test_false_testuale_non_blocca_l_aggiornamento_di_stato[FALSE]
FAILED tests/test_import_lead.py::TestEmailInviataScrittaAMano::test_false_testuale_non_blocca_l_aggiornamento_di_stato[false]
FAILED tests/test_import_lead.py::TestEmailInviataScrittaAMano::test_false_testuale_non_blocca_l_aggiornamento_di_stato[No]
FAILED tests/test_import_lead.py::TestEmailInviataScrittaAMano::test_false_testuale_non_blocca_l_aggiornamento_di_stato[0]
FAILED tests/test_import_parametri.py::TestBooleaniScrittiAMano::test_falso_scritto_a_mano_disattiva_davvero[FALSE]
FAILED tests/test_import_parametri.py::TestBooleaniScrittiAMano::test_falso_scritto_a_mano_disattiva_davvero[false]
FAILED tests/test_import_parametri.py::TestBooleaniScrittiAMano::test_falso_scritto_a_mano_disattiva_davvero[No]
FAILED tests/test_import_parametri.py::TestBooleaniScrittiAMano::test_falso_scritto_a_mano_disattiva_davvero[0]
FAILED tests/test_import_parametri.py::TestBooleaniScrittiAMano::test_falso_scritto_a_mano_disattiva_davvero[falso]
FAILED tests/test_import_parametri.py::TestBooleaniScrittiAMano::test_booleano_non_interpretabile_e_uno_scarto_descritto
10 failed, 6 passed, 22 deselected in 45.10s
```

---

### WR-02: riga `listino_categoria` nuova saltata in silenzio

**Stato:** fixed
**Commit:** `54db0ee`
**File modificati:** `backend/app/services/import_excel/parametri.py`,
`backend/tests/test_import_parametri.py`

**Cosa è cambiato.** Ho scelto la prima delle due strade proposte dalla
review: rifiutare il caso in `diff()`, dove l'admin lo vede PRIMA di
confermare. `_risolvi_listino_categoria` ora scarta la riga nuova con due
motivi distinti — colonna `coefficiente_impresa` assente ("l'export di
default non porta quella colonna, serve l'export con margine") e valore
fuori da `(0, 1]`. Il conteggio di `/confirm` torna così coerente con quanto
mostrato in anteprima.

Il `continue` in `apply()` resta come difesa in profondità per il solo caso
`is_admin=False`, che su questa risorsa è irraggiungibile
(`ruolo_richiesto = "admin"`); il commento ora lo dice invece di descriverlo
come un limite noto non esercitato dai test.

L'invariante del margine è preservata: nessuna delle due nuove uscite legge
o scrive `coefficiente_impresa` fuori dai punti già esistenti, e
`test_export_margine.py` resta verde.

**Regressione aggiunta:** `TestListinoCategoriaNuovaSenzaMargine`, 3 test —
lo scarto visibile in anteprima con `righe_applicate == 0` e nessuna riga
creata, la contro-prova che con un margine valido la riga si crea davvero
(e il conteggio la include), e il margine fuori bound.

```
$ ./.venv/Scripts/python.exe -m pytest tests/test_import_parametri.py tests/test_export_margine.py -q
30 passed in 152.02s (0:02:32)
```

Sul codice precedente:

```
FAILED tests/test_import_parametri.py::TestListinoCategoriaNuovaSenzaMargine::test_riga_nuova_senza_margine_e_uno_scarto_visibile_in_anteprima
FAILED tests/test_import_parametri.py::TestListinoCategoriaNuovaSenzaMargine::test_riga_nuova_con_margine_fuori_bound_e_uno_scarto_descritto
2 failed, 1 passed, 22 deselected in 21.56s
```

---

### WR-03: `VoceRiga` (TypeScript) taceva `id` e `campi_presenti`

**Stato:** fixed
**Commit:** `d9ca2ad`
**File modificati:** `frontend/src/api/admin/uploadListino.ts`,
`backend/tests/test_export_import_roundtrip.py`

**Cosa è cambiato.** L'interfaccia `VoceRiga` dichiara ora `id: number |
null`, `campi_presenti: string[] | null` e anche `livello: string | null`
(mancava pure quello). Il commento sopra l'interfaccia spiega perché quei
campi non vanno mai persi: senza `id` la riga cade sull'upsert per chiave
naturale, senza `campi_presenti` i placeholder delle colonne assenti
verrebbero scritti a database come dati veri — cioè esattamente CR-01.

**Regressione aggiunta.** Qui il finding è una dichiarazione di tipo, non un
bug a runtime, quindi un test di comportamento non lo coprirebbe. Ho scritto
invece un confronto cross-linguaggio,
`TestContrattoVoceRigaTypeScript::test_voce_riga_ts_elenca_gli_stessi_campi_di_voce_riga_in`:
legge l'interfaccia `VoceRiga` dal sorgente TypeScript e confronta i nomi
dei campi con `VoceRigaIn.model_fields`. Sul codice precedente falliva
elencando esattamente i tre campi mancanti:

```
$ git checkout -- frontend/src/api/admin/uploadListino.ts
$ ./.venv/Scripts/python.exe -m pytest tests/test_export_import_roundtrip.py -q -k ContrattoVoceRigaTypeScript
E       assert {'categoria_c..._codice', ...} == {'campi_prese...livello', ...}
E         Extra items in the right set:
E         'livello'
E         'campi_presenti'
E         'id'
1 failed, 12 deselected in 9.08s
```

Il test fa `pytest.skip` se manca l'INTERA cartella `frontend/` (checkout di
solo backend, es. immagine Docker); se la cartella c'è ma il file no, è un
errore. Questo è lo skip in più rispetto ai 4 preesistenti nel conteggio
finale.

A fianco, `TestContrattoDiffRowSulFilo` presidia l'altra metà del contratto:
ogni riga di `/preview` porta davvero quei campi, con l'esatto set atteso.

```
$ ./.venv/Scripts/python.exe -m pytest tests/test_export_import_roundtrip.py -q
13 passed in 31.62s
```

---

## Skipped Issues

Nessuna. Tutte e sei le findings in scope sono state corrette.

IN-01 (Info, `apply()` conta come "applicate" anche le righe no-op) è fuori
dallo scope di questo passaggio, come richiesto, e resta aperta in REVIEW.md.

---

## Note operative

**Il database locale è stato migrato.** `backend/dev.db` è passato da `0018`
a `0019 (head)`. Il backup pre-migrazione è
`backend/dev.db.bak-pre-0019-20260923-083311` (gitignorato come tutti i
`dev.db.bak-*`). Se serve tornare indietro: `alembic downgrade 0018` è
verificato e coerente, oppure si ripristina il backup.

**Nessun push.** I sei commit sono locali su `master`, come richiesto.
`git rev-list --count origin/main..master` riporta ora 78 commit non
pushati (erano 72 prima di questo passaggio; la nota che circolava a 69 era
già disallineata rispetto al ramo).

**Identità git.** Nessun `git config --global` eseguito; i commit usano
l'identità per-repo già configurata (`Riccardo Rinaldi`).

**Il lavoro è stato fatto in un worktree isolato** (`gsd-reviewfix/08-369`
sotto `%TEMP%`), poi portato su `master` con un fast-forward. Worktree e
branch temporaneo sono stati rimossi; `git worktree list` mostra solo il
repo principale e l'albero di lavoro è pulito.

**Una cosa notata ma non corretta,** perché fuori dallo scope della review e
non fra le findings: `app/models/__init__.py` non riesporta `Lead` e `Testo`.
`alembic/env.py` fa `from app import models` per costruire `target_metadata`,
quindi oggi un `alembic revision --autogenerate` vedrebbe le tabelle `lead` e
`testo` come da eliminare. I test nuovi aggirano la cosa importando
esplicitamente i due moduli, con un commento che spiega perché. Vale la pena
aprirci sopra un item a parte.

---

_Fixed: 2026-09-23_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
