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

---
---

# Phase 08: Code Review Fix Report — Iterazione 2

**Fixed at:** 2026-09-23
**Source review:** `.planning/phases/08-export-import-excel/08-REVIEW.md`
(re-review di iterazione 2, `iteration: 2` nel suo frontmatter)
**Iteration:** 2

> Questa sezione è stata **aggiunta in coda** al report di iterazione 1, che
> resta integro qui sopra. Il frontmatter in testa al file descrive
> l'iterazione 1 e non è stato toccato: i numeri dell'iterazione 2 sono
> quelli del riepilogo qui sotto.

## Avvertenza: gli identificativi sono riusati, le findings no

La re-review di iterazione 2 **riusa gli identificativi** `CR-01`, `CR-02` e
`WR-01`…`WR-05`, ma denotano findings **diverse** da quelle omonime
dell'iterazione 1. Non sono riaperture e non sono regressioni: le sei
findings dell'iterazione 1 sono state verificate chiuse dalla re-review
stessa (sezione "Verifica delle findings chiuse" in `08-REVIEW.md`). Citare
un id tipo "CR-01" senza dire di quale iterazione è ambiguo.

Tabella di disambiguazione, da usare ogni volta che si nomina un id di
questa fase:

| id | iterazione 1 (fix `4665022`…`d9ca2ad`) | iterazione 2 (fix `7233e15`…`826cf4a`) |
|---|---|---|
| CR-01 | l'upsert per chiave naturale ignorava `campi_presenti` | `int()` non protetto su valori presi dal file: un `--5` in una cella fa 500 |
| CR-02 | `#CANCELLA#` scriveva la stringa `"None"` invece di NULL | due righe con la stessa chiave naturale nello stesso file fanno 500 e perdono l'intero import |
| CR-03 | la migrazione `0019` non si applicava su SQLite | — (nessuna CR-03 in iterazione 2) |
| WR-01 | `bool()` su celle booleane scritte a mano | il diff per chiave naturale non mostra i campi di sottocategoria che la conferma poi scrive |
| WR-02 | riga `listino_categoria` nuova saltata in silenzio | l'anteprima annuncia una modifica a `livello` che la conferma non applica |
| WR-03 | `VoceRiga` (TypeScript) taceva `id` e `campi_presenti` | `prezzo_unitario_cliente` è dichiarato `number` ma sul filo è una stringa |
| WR-04 | — | le fixture di test usano `autoflush=True`, la produzione `autoflush=False` |
| WR-05 | — | `alembic revision --autogenerate` emetterebbe `drop_table("lead")` e `drop_table("testo")` |
| IN-01 | `apply()` conta come "applicate" anche le righe no-op | la stessa, riportata invariata |
| IN-02 | — | `ConfirmPiattoIn.risorsa` è obbligatoria e non viene mai usata |

Dove il testo qui sotto dice semplicemente "CR-01", "WR-03" e simili, si
riferisce **sempre alla colonna di destra** — le findings dell'iterazione 2.

**Riepilogo:**

- Findings in scope: 7 (CR-01, CR-02, WR-01, WR-02, WR-03, WR-04, WR-05)
- Fixed: 7
- Skipped: 0
- Fuori scope per scelta: IN-01 e IN-02 (Info)

Commit, nell'ordine in cui sono stati fatti:

| commit | finding |
|---|---|
| `7233e15` | WR-05 — `app/models/__init__.py` riesporta `Lead` e `Testo` |
| `954050e` | CR-01 — nessun `int()` non protetto sui valori presi dal file |
| `b5c87ef` | CR-02 — due righe con la stessa chiave naturale non fanno più 500 |
| `378a55b` | WR-01 — il diff per chiave naturale mostra anche la sottocategoria |
| `096a3fe` | WR-02 — il `livello` annunciato nel diff viene davvero scritto |
| `0c6baf3` | WR-03 — `prezzo_unitario_cliente` è una stringa sul filo, non un `number` |
| `826cf4a` | WR-04 — le fixture dei test usano la configurazione di produzione |
| `2eb18ae` | merge `--no-ff` dei sette fix su `master` |
| `e131c20` | test sul token di reset manomesso (non è una finding — vedi sotto) |

---

## Fixed Issues

### WR-05: `alembic revision --autogenerate` avrebbe proposto `drop_table("lead")`

**Stato:** fixed
**Commit:** `7233e15`
**File modificati:** `backend/app/models/__init__.py`,
`backend/tests/test_migrazioni_sqlite.py`,
`backend/tests/test_modelli_registrati.py` (nuovo)

**Cosa è cambiato.** I due import mancanti (`from app.models.lead import
Lead`, `from app.models.testo import Testo`) più le due voci in `__all__`.
`alembic/env.py` costruisce `target_metadata = Base.metadata` fidandosi del
solo `from app import models`: senza quei due import le tabelle `lead` e
`testo` non entravano nel metadata, e il prossimo autogenerate avrebbe
emesso la loro cancellazione — cioè i contatti commerciali.

È la stessa cosa che l'iterazione 1 aveva annotato in coda al proprio report
come "una cosa notata ma non corretta"; qui diventa una finding e viene
chiusa. L'import esplicito con cui `test_migrazioni_sqlite.py` aggirava il
buco sparisce, insieme al commento che lo giustificava.

**Regressione aggiunta:** `backend/tests/test_modelli_registrati.py` — per
ogni modulo sotto `app/models/` verifica che le entità lì definite risultino
in `Base.metadata` dopo il solo `from app import models`. Gira **in un
sottoprocesso pulito**, e non è un dettaglio: nella stessa sessione pytest
altri file importano `app.models.lead` a mano, quindi il metadata sarebbe
già popolato e in-process il test passerebbe anche col difetto in piedi.

### CR-01: `int()` non protetto su valori presi dal file

**Stato:** fixed
**Commit:** `954050e`
**File modificati:** `backend/app/services/import_excel/parametri.py`,
`backend/app/routers/admin/import_excel.py`,
`backend/tests/test_import_parametri.py`

**Cosa è cambiato.** Il guard delle tre chiavi naturali numeriche era
`str(x).strip().lstrip("-").isdigit()`, e `lstrip("-")` toglie **tutti** i
meno iniziali: `"--5"` lo superava e il successivo `int("--5")` sollevava
`ValueError`, non catturata da nessuno — non il resolver, non `diff()`, non
il router, non un exception handler globale. Un refuso di battitura in una
cella bastava per un 500 e per la perdita dell'intero file.

Al suo posto `_intero()`, che non solleva mai: `None` significa "non
convertibile" e chi chiama lo traduce in uno scarto descritto. Usata in
tutti e sette i punti — i tre guard di chiave naturale (`listino_id`,
`voce_id`, `opzione_id`) e i quattro `int(r.id)`, che avevano lo stesso
problema per un'altra via, perché `RigaPiattaIn.id` è una stringa libera e
in `/confirm` arriva dal client senza validazione numerica.

In più una rete di sicurezza nel router, indipendente dai resolver:
`parse`/`diff` in preview e `apply`/`commit` in confirm avvolti in un
`except Exception` che risponde 400 con messaggio leggibile (e in confirm fa
`rollback()`). **Il messaggio non riporta `str(exc)`**: il testo di
un'eccezione può contenere un frammento di riga, e su questa risorsa una
riga porta `coefficiente_impresa`, che non esce mai verso il client (regola
di dominio #1). Il dettaglio completo finisce nel log con traceback.

**Regressione aggiunta:** `TestIdNonNumericoNonFa500`, sei test — `_intero`
sui casi limite, i tre `--N` in preview che devono essere scarti descritti,
`/confirm` con quattro id non numerici che deve tornare 200 con zero righe
applicate, e l'eccezione imprevista in `diff` che deve diventare 400 senza
nominare il margine.

### CR-02: due righe con la stessa chiave naturale facevano 500

**Stato:** fixed
**Commit:** `b5c87ef`
**File modificati:** `backend/app/services/import_excel/parametri.py`,
`backend/app/routers/admin/import_excel.py`,
`backend/tests/session_factory.py` (nuovo),
`backend/tests/test_import_parametri.py`

**Cosa è cambiato, su tre fronti indipendenti.**

1. `db.flush()` esplicito dopo ogni creazione in `apply()`, come fa già
   `listino_upload_service._upsert_voce`. Con il flush la seconda riga trova
   la prima e diventa un aggiornamento, invece di un secondo INSERT che
   esplode al commit.
2. Rilevazione del duplicato **dentro il payload** in `diff()`: un set delle
   chiavi naturali già promesse come creazione, e uno `ScartoRowOut` alla
   seconda occorrenza. L'admin lo vede in anteprima, prima di confermare.
3. `IntegrityError` al commit tradotto in 400 con rollback. Anche qui il
   messaggio non riporta `str(exc)`: un `IntegrityError` stampa query e
   parametri, e fra quei parametri può esserci `coefficiente_impresa`.

Qui arriva anche `backend/tests/session_factory.py`, e non è un extra: il
difetto era invisibile a 555 test proprio perché le fixture costruivano la
sessione con `sessionmaker(bind=engine)`, cioè `autoflush=True`, mentre la
produzione è `autoflush=False`. Con `autoflush=True` la query della seconda
riga innescherebbe da sola il flush della prima e la regressione passerebbe
**anche sul codice rotto**. La fabbrica legge i kwargs da `SessionLocal.kw`
invece di ricopiarli, così la configurazione non può divergere una seconda
volta; l'allineamento di tutti gli altri file di test è WR-04.

**Regressione aggiunta:** `TestChiaveNaturaleDuplicataNelFile`, cinque test
— la guardia sulla configurazione della sessione, `apply()` nudo con due
righe identiche che deve committare creando UNA riga, il duplicato visibile
in anteprima, il round-trip `/confirm` con il duplicato forzato nel payload,
e il vincolo violato che deve dare 400 senza nominare il margine.

### WR-01: il diff per chiave naturale non mostrava i campi di sottocategoria

**Stato:** fixed
**Commit:** `378a55b`
**File modificati:** `backend/app/services/listino_upload_service.py`,
`backend/tests/test_export_import_roundtrip.py`

**Cosa è cambiato.** In `compute_diff` la variabile `sotto` veniva
valorizzata solo sul ramo per id; sul ramo per chiave naturale restava
`None` e il confronto sui cinque campi di `_CAMPI_DIFF_SOTTOCATEGORIA` non
veniva mai eseguito — mentre `apply_diff_idempotent` quei campi li scrive.
Se nessun campo di voce era cambiato la riga spariva dal diff e la modifica
alla sottocategoria era persa in silenzio; se almeno uno era cambiato, la
conferma scriveva anche campi che l'anteprima non aveva mostrato.

`per_chiave` porta ora la coppia `(Voce, Sottocategoria)`, come `per_id`.
Con `sotto` valorizzato su entrambi i rami la guardia `if sotto is not None`
diventa codice morto e sparisce: non proteggeva da niente, nascondeva il
buco.

**Regressione aggiunta:** `TestDiffDichiaraICampiDiSottocategoria`, due test
— la modifica di sola sottocategoria che non deve sparire dal diff, e la
modifica mista dove l'insieme dei campi annunciati deve coincidere
esattamente con quello dei campi poi scritti.

### WR-02: il `livello` annunciato nel diff non veniva scritto

**Stato:** fixed
**Commit:** `096a3fe`
**File modificati:** `backend/app/services/listino_upload_service.py`,
`backend/tests/test_export_import_roundtrip.py`

**Cosa è cambiato.** `livello` era fra i campi diffati (`_CAMPI_DIFF_VOCE`)
ma `_upsert_voce` lo escludeva dal ciclo di scrittura: sul percorso per
chiave naturale l'anteprima diceva "livello cambia", la conferma non lo
cambiava, e `righe_importate` contava comunque la riga come importata.

L'esclusione aveva una ragione corretta — le righe di `parse_computo` si
dichiarano complete, ma il computo la colonna livello non ce l'ha e
scriverebbe `None` su ogni voce azzerando la curatela — e una condizione
sbagliata: "ramo per id sì, per chiave naturale no". La condizione giusta è
"il file dichiara **esplicitamente** il campo", cioè `campi_presenti is not
None and "livello" in campi_presenti`: solo `parse_flat_listino` valorizza
`campi_presenti`, e il file piatto è l'unico modo di curare i livelli in
blocco. La nuova `_livello_dichiarato()` isola quella condizione e spiega
perché `_campo_presente` non basta. Stesso trattamento sul ramo "voce
nuova", dove il livello dichiarato nel file si perdeva fra la riga letta e
la riga creata.

**Regressione aggiunta:** `TestLivelloSulPercorsoPerChiaveNaturale`, quattro
test — il livello annunciato che deve essere scritto, la contro-prova che il
computo continua a non azzerarlo, la voce nuova che conserva il livello
dichiarato, e `#CANCELLA#` che resta una dichiarazione esplicita e azzera
davvero.

### WR-03: `prezzo_unitario_cliente` è una stringa sul filo, non un `number`

**Stato:** fixed
**Commit:** `0c6baf3`
**File modificati:** `frontend/src/api/admin/uploadListino.ts`,
`frontend/src/components/admin/ExcelUploadDialog.tsx`,
`backend/tests/test_export_import_roundtrip.py`

**Cosa è cambiato.** `VoceRigaIn.prezzo_unitario_cliente` è un `Decimal`
pydantic, che in JSON viene serializzato come **stringa** (convenzione
Decimal-as-string del progetto). L'interfaccia TS lo dichiarava `number` e
`normalizeDiffRow` passava `raw.riga` inalterato, quindi a runtime il campo
restava una stringa. Non era solo un tipo sbagliato: in `toDiffPreviewRows`
la colonna "precedente" chiamava `Number.prototype.toLocaleString` e
produceva `12,50 €`, la colonna "nuovo" chiamava
`String.prototype.toLocaleString`, che **ignora gli argomenti** e
restituiva `12.50` — separatore decimale sbagliato per la locale italiana e
nessun simbolo di valuta, a schermo.

`prezzo_unitario_cliente` è ora dichiarato `string`, e il numero
normalizzato arriva **accanto** al campo grezzo (`DiffRow.prezzoNuovo`), non
al suo posto: l'oggetto `riga` viene rispedito verbatim a `/confirm` e deve
restare quello che il server ha mandato.

**Regressione estesa.** Il test cross-linguaggio introdotto dalla WR-03
*dell'iterazione 1* non intercettava niente di tutto questo perché
confrontava solo i **nomi** dei campi. Ora confronta anche la forma JSON di
ogni tipo (string/number/boolean/array), con la riduzione che tratta
`Decimal` come `string`. A fianco, `TestContrattoDiffRowSulFilo` verifica
sul filo vero che `prezzo_unitario_cliente` e `valore_precedente` arrivino
come stringhe JSON.

### WR-04: le fixture dei test usano la configurazione di sessione di produzione

**Stato:** fixed
**Commit:** `826cf4a`
**File modificati:** 42 in tutto — 41 file di test che passano da
`sessionmaker(bind=engine)` alla fabbrica condivisa
`tests.session_factory.sessione_di_test`, più
`backend/tests/test_configurazione_sessione.py` (nuovo)

**Cosa è cambiato.** Ogni fixture costruiva `sessionmaker(bind=engine)`, che
lascia `autoflush=True`, mentre `app/db.py` usa `autoflush=False`. La
differenza decide se una query vede gli oggetti pendenti aggiunti poco
prima, cioè esattamente la semantica di scrittura che la suite dell'import
deve presidiare: è il motivo per cui 555 test non vedevano la CR-02.

Due test nuovi chiudono il buco da entrambi i lati: uno confronta l'intero
dizionario di kwargs con quello di `app.db.SessionLocal`, l'altro analizza
l'**AST** di ogni file di test per impedire che un file nuovo si
ricostruisca la sessione per conto suo.

La review avvertiva che l'intervento andava fatto in un passaggio dedicato
perché "cambiare la semantica di flush sotto a 555 test può far emergere
altri difetti mascherati". Non ne è emerso nessuno: la suite completa dopo
il cambio è verde (numeri in fondo).

---

## Skipped Issues

Nessuna. Tutte e sette le findings in scope sono state corrette.

**Fuori scope per scelta, non dimenticate:**

- **IN-01** (`apply()` conta come "applicate" anche le righe no-op) — Info,
  riportata invariata dall'iterazione 1 e lasciata aperta anche qui, come
  richiesto. Resta descritta in `08-REVIEW.md`.
- **IN-02** (`ConfirmPiattoIn.risorsa` è obbligatoria e non viene mai usata)
  — Info, nuova dell'iterazione 2. Non è sfruttabile, perché il gate di
  ruolo segue l'handler risolto dal path e non il body, ed è stata
  deliberatamente esclusa dallo scope di questo passaggio. Resta aperta.

---

## Fuori dalle findings: il test sul token di reset (`e131c20`)

**Non è una finding della review.** È emersa come fallimento nella suite
completa lanciata dopo il merge:

```
FAILED tests/test_password_reset.py::TestResetTokenUnit::test_token_manomesso_ritorna_none
AssertionError: assert 42 is None
```

**Non è un difetto di sicurezza.** `read_reset_token` rifiuta correttamente
ogni manomissione reale; era il test a non poter fallire in modo
affidabile.

**Il meccanismo, per esteso.** La firma del token di reset è un HMAC-SHA1 di
20 byte. In base64url occupa 27 caratteri da 6 bit, cioè 162 bit per 160 bit
di firma: i 2 bit finali sono riempimento e valgono sempre zero. L'ultimo
carattere ha perciò solo 16 valori possibili (`048AEIMQUYcgkosw`). Il
vecchio test sostituiva proprio quell'ultimo carattere con `a`, indice 26,
che cade nello stesso gruppo di quattro di `Y` (indici 24–27 = `Y`, `Z`,
`a`, `b`): quando la firma finiva in `Y` la manomissione lasciava i 20 byte
decodificati **identici**, il token restava legittimamente valido, e
l'asserzione falliva.

Misurato su 4000 firme distinte: il vecchio test falliva su 263 di esse, il
6,6%, esattamente il tasso di 1 su 16 previsto dal calcolo.

**Il fix** manomette il **primo** carattere, che porta solo bit
significativi, e copre tutti e tre i segmenti del token (payload, timestamp,
firma) invece del solo carattere finale: zero mancati rilevamenti su 12000
manomissioni.

È della stessa famiglia dell'acceptance criterion del piano `08-05` che era
soddisfacibile modificando un commento (il `grep -n "require_admin"` che la
docstring del router violava con la propria prosa esplicativa): una verifica
scritta in modo tale da poter essere vera per ragioni diverse da quella che
le si attribuisce. Vale la pena tenerla come categoria di difetto a sé,
perché non la intercetta nessun test — è il test a essere il difetto.

---

## Note operative

**Il fixer è stato interrotto da un limite di sessione, sul confine
`Write` → `commit`.** Stava lavorando in un worktree git a
`C:/Users/RINALDIR/AppData/Local/Temp/sv-08-reviewfix-Q7r6vD`, sul branch
`gsd-reviewfix/08-241`, e aveva lasciato il file marcatore
`.review-fix-recovery-pending.json` nella cartella di fase. Sei commit erano
già sul branch; il lavoro di WR-04 — i 41 file di test riallineati e i file
di test nuovi che li presidiano — era **scritto sul disco del worktree ma
non committato**.

Recupero fatto a mano: il lavoro su disco è stato committato come `826cf4a`,
e il branch è stato portato su `master` con un merge `--no-ff` (`2eb18ae`).
Worktree e branch temporaneo sono stati poi rimossi, e il file marcatore
cancellato.

**Da ricordare:** un `git worktree remove --force` per riflesso, in quel
momento, avrebbe distrutto il lavoro di WR-04 — 42 file, nessuno dei quali
recuperabile da git perché non ancora committato. Il marcatore
`.review-fix-recovery-pending.json` va letto come "lì dentro c'è del lavoro
non committato", non come "c'è un worktree da ripulire". L'ordine giusto è
sempre: ispezionare `git status` **dentro** il worktree, committare o
salvare ciò che c'è, e solo allora rimuovere.

**Verifica finale.** Suite backend completa su `master`, dopo tutti i commit
qui sopra, lanciata con `backend/.venv/Scripts/python.exe -m pytest` da
`backend/`:

```
579 passed, 5 skipped, 2 warnings in 744.25s (0:12:24)
```

Frontend:

```
$ npx tsc -b --force        # esce 0
$ npx oxlint                # esce 0
```

I 5 warning `react(set-state-in-effect)` di `oxlint` sono preesistenti e non
toccati da questo lavoro.

Database locale alla revisione alembic `0019 (head)`.

---

_Fixed: 2026-09-23_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 2_
