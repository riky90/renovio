---
phase: 08-export-import-excel
reviewed: 2026-09-23T14:00:00Z
depth: standard
iteration: 2
files_reviewed: 52
files_reviewed_list:
  - backend/alembic/versions/0018_export_log.py
  - backend/alembic/versions/0019_updated_at_curatela.py
  - backend/app/models/__init__.py
  - backend/app/models/arredo.py
  - backend/app/models/catalogo.py
  - backend/app/models/dettaglio_pro.py
  - backend/app/models/export_log.py
  - backend/app/models/lead.py
  - backend/app/models/listino.py
  - backend/app/routers/admin/__init__.py
  - backend/app/routers/admin/coefficienti.py
  - backend/app/routers/admin/export_log.py
  - backend/app/routers/admin/import_excel.py
  - backend/app/routers/admin/lead.py
  - backend/app/routers/admin/listini.py
  - backend/app/routers/admin/upload_listino.py
  - backend/app/schemas/admin_export.py
  - backend/app/schemas/admin_import.py
  - backend/app/schemas/admin_upload.py
  - backend/app/services/export_excel/__init__.py
  - backend/app/services/export_excel/lead.py
  - backend/app/services/export_excel/listino.py
  - backend/app/services/export_excel/parametri.py
  - backend/app/services/export_excel/workbook.py
  - backend/app/services/import_excel/__init__.py
  - backend/app/services/import_excel/flat.py
  - backend/app/services/import_excel/lead.py
  - backend/app/services/import_excel/parametri.py
  - backend/app/services/import_excel/registry.py
  - backend/app/services/listino_upload_service.py
  - backend/tests/test_export_excel_listino.py
  - backend/tests/test_export_import_roundtrip.py
  - backend/tests/test_export_lead_traccia.py
  - backend/tests/test_export_margine.py
  - backend/tests/test_import_lead.py
  - backend/tests/test_import_parametri.py
  - backend/tests/test_import_stale.py
  - backend/tests/test_migrazioni_sqlite.py
  - frontend/src/api/admin/anteprima.ts
  - frontend/src/api/admin/exportExcel.ts
  - frontend/src/api/admin/exportLog.ts
  - frontend/src/api/admin/importExcel.ts
  - frontend/src/api/admin/uploadListino.ts
  - frontend/src/components/admin/AnteprimaTab.tsx
  - frontend/src/components/admin/DiffPreviewTable.tsx
  - frontend/src/components/admin/ExcelUploadDialog.tsx
  - frontend/src/components/admin/FlatImportDialog.tsx
  - frontend/src/lib/adminCopy.ts
  - frontend/src/lib/tipoRistrutturazione.ts
  - frontend/src/pages/admin/CoefficientiPage.tsx
  - frontend/src/pages/admin/LeadDashboardPage.tsx
  - frontend/src/pages/admin/ListiniPage.tsx
findings:
  critical: 2
  warning: 5
  info: 2
  total: 9
status: issues_found
---

# Fase 08: Report di Code Review (iterazione 2)

**Reviewed:** 2026-09-23
**Depth:** standard
**Files Reviewed:** 52 (backend + frontend)
**Status:** issues_found

## Sommario

Passaggio di verifica sui sei fix dell'iterazione 1 (commit `4665022`, `9b352e4`,
`aa3d6fb`, `3d64583`, `54db0ee`, `d9ca2ad`), più caccia a regressioni introdotte
da quei fix.

**Le sei findings in scope sono tutte genuinamente chiuse** — verificate leggendo
il codice come sta ora, non fidandosi del report di fix. Il dettaglio per finding
è nella sezione "Verifica delle findings chiuse" qui sotto. I fix sono fatti bene:
rispettano la disciplina del modulo che toccano, i commenti spiegano il *perché* e
non il *cosa*, e nessuno dei tre che toccano semantica di scrittura
(upsert, validazione import, migrazione) introduce una regressione rilevabile.

Le nuove findings non vengono dai fix: vengono da zone adiacenti che l'iterazione 1
non aveva scavato abbastanza a fondo. Due sono BLOCKER, entrambe riprodotte
eseguendo il codice:

1. `import_excel/parametri.py` converte a `int` valori presi dal file senza
   proteggere la conversione: un guard sbagliato (`lstrip("-").isdigit()`) lascia
   passare `--5`, e `int("--5")` solleva `ValueError` non gestito → 500. Quattro
   punti nel file. Contraddice la regola dichiarata nella docstring del modulo
   ("uno scarto descritto, mai un 500").
2. Due righe con la stessa chiave naturale e senza `id` nello stesso payload
   producono due INSERT e un `IntegrityError` al `db.commit()` del router → 500 e
   l'intero import perduto. È invisibile alla suite perché **le fixture di test
   costruiscono la sessione con `autoflush=True` mentre la produzione usa
   `autoflush=False`** (`app/db.py:16`) — divergenza che maschera un'intera
   classe di bug (WR-04).

Sul fronte anti-leak (regola di dominio #1) non ci sono regressioni: `coefficiente_impresa`
resta scritto solo nei due punti `_forse_aggiungi_margine`/`_forse_aggiorna_margine`,
entrambi dietro `is_admin`, e il nuovo scarto di WR-02 non legge né scrive quella
colonna fuori dai punti preesistenti.

---

## Verifica delle findings chiuse

Ogni voce è stata verificata sul codice corrente, non sul report di fix.

### CR-01 — CHIUSA

`backend/app/services/listino_upload_service.py:454-465` introduce `_campo_presente`,
e `_upsert_sottocategoria` (`:468-511`) / `_upsert_voce` (`:514-557`) la usano sia sul
ramo "riga nuova" (campo assente → default del modello) sia sul ramo "riga esistente"
(campo assente → attributo non toccato). Ho verificato i due presupposti impliciti del
fix, che il report non dimostra:

- **I default del modello esistono davvero.** `Sottocategoria.ordine` e `Voce.ordine`
  sono `nullable=False, default=0, server_default="0"`
  (`app/models/dettaglio_pro.py:45` e `:70`), quindi ometterli dal costruttore non
  produce un INSERT con NULL su colonna NOT NULL.
- **I campi ancora scritti incondizionatamente sul ramo "nuova" sono garantiti presenti.**
  `nome`, `famiglia`, `descrizione`, `um`, `prezzo_unitario_cliente` e `categoria_code`
  stanno tutti in `_CAMPI_RICHIESTI_RIGA_NUOVA` (`:83-91`), e `parse_flat_listino`
  scarta la riga senza id che non li porta (`:224-232`). Per `parse_computo`
  (`campi_presenti is None`) sono presenti per costruzione.

I nomi-campo usati da `_campo_presente` (`sottocategoria_ordine`, `ordine`,
`prezzo_unitario_cliente`…) coincidono con le chiavi di `campi_presenti`, che è
`set(valori.keys())` dei nomi-colonna del foglio piatto (`:270`): nessun disallineamento
silenzioso fra i due vocabolari.

L'esclusione deliberata di `voce.livello` dal giro di `_upsert_voce` è corretta e ora
documentata con la ragione giusta — ma genera l'asimmetria descritta in **WR-02**.

### CR-02 — CHIUSA

Chiusa su tutti e tre i fronti dichiarati, e li ho verificati separatamente:

- `frontend/src/components/admin/FlatImportDialog.tsx:82-93`: `toRigaPiattaIn` ora
  partiziona `valori_nuovi` in `valori` (non-null) e `campi_da_cancellare` (null).
  L'iterazione sulle chiavi di `valori_nuovi` invece che su `campi_modificati` è
  equivalente: per le righe `modificate` i due insiemi coincidono per costruzione
  (`parametri.py:619-624`, `lead.py:288-296`), per le `nuove` `valori_nuovi` è il
  `valori_creazione` completo, che è esattamente ciò che `/confirm` deve ricevere.
- `backend/app/services/import_excel/registry.py:55-73`: `campi_nulli_in_valori` è
  applicata in `diff` **e** in `apply` di entrambi gli handler
  (`lead.py:246-262` e `:317`, `parametri.py:543-559` e `:667`). Un `None` dentro
  `valori` non può più raggiungere `str(...)`.
- `_risolvi` di `lead.py:178-179` e `_risolvi_coeff_pro` di `parametri.py:354-358`
  restano gli stessi, ma ora sono irraggiungibili con un `None`: il guard è a monte
  in entrambi i percorsi (diff e apply), non solo in uno.

Ho controllato che il guard non possa scattare su un payload legittimo:
`parse()` di entrambi gli handler sposta sempre i `None` su `campi_da_cancellare`
(`lead.py:215-220`, `parametri.py:485-491`), quindi `valori` non contiene mai `None`
per costruzione.

### CR-03 — CHIUSA

`backend/alembic/versions/0019_updated_at_curatela.py:69-83` applica i tre passi
(add nullable → backfill esplicito → `batch_alter_table` per NOT NULL + `server_default`).
Verificata indipendentemente eseguendo la regressione:

```
$ backend/.venv/Scripts/python.exe -m pytest tests/test_migrazioni_sqlite.py -q
8 passed in 9.24s
```

Ho verificato i due rischi che la ricostruzione batch su SQLite porta con sé e che il
report di fix asserisce senza dimostrare:

- **Nessun `CheckConstraint` nei modelli** (`grep -rn "CheckConstraint" backend/app/models/`
  è vuoto): la riflessione SQLite di SQLAlchemy non li recupererebbe, e sarebbero persi
  silenziosamente nella ricostruzione. Non ce ne sono, quindi il rischio non si materializza.
- **Nessun `PRAGMA foreign_keys=ON`** nell'applicazione o in `alembic/env.py`: il
  `DROP TABLE` interno al batch non incontra l'enforcement delle FK. Se un domani quel
  pragma venisse attivato (è una scelta ragionevole), questa migrazione andrebbe
  rivisitata — vale la pena di un commento nel file.

Il backfill scrive `datetime.now(timezone.utc).replace(tzinfo=None)`, coerente col
confronto naive→aware di `registry.riga_modificata_dopo_export:78-86`: la guardia di
staleness non marca tutto come superato al primo re-import.

### WR-01 — CHIUSA

`valore_booleano` (`backend/app/services/import_excel/flat.py:62-93`) copre bool nativo,
0/1 numerici, e testi veri/falsi in italiano e inglese; `None` per l'indecidibile.
Usata in tutti e tre i punti citati dalla review: `parametri.py:311-316` (`extra.attivo`),
`parametri.py:427-432` (`forfait_arredo.attivo`), `lead.py:105-113` (`email_inviata`).

Ho verificato che non restino altre colonne booleane importabili scoperte: fra
`COLONNE_MOLTIPLICATORI`, `COLONNE_LISTINO_CATEGORIA`, `COLONNE_EXTRA`,
`COLONNE_COEFF_PRO`, `COLONNE_FORFAIT` e `COLONNE_LEAD` le sole colonne booleane sono
le tre già coperte. `Listino.is_default`/`attivo` e `Categoria.livello_selezionabile`/
`nel_totale_lavori` non sono importabili da nessun foglio.

Il ramo `isinstance(valore, (int, float))` è corretto malgrado `bool` sia sottoclasse
di `int`: il controllo `isinstance(valore, bool)` viene prima.

### WR-02 — CHIUSA

`_risolvi_listino_categoria` (`backend/app/services/import_excel/parametri.py:238-262`)
ora scarta la riga nuova non creabile con due motivi distinti — colonna margine assente,
e margine fuori da `(0, 1]` — e lo fa in `diff()`, quindi l'admin la vede in anteprima
prima di confermare. Il conteggio di `/confirm` torna coerente con l'anteprima.

Il `continue` superstite in `apply()` (`:684-694`) è ora correttamente descritto come
difesa in profondità per il solo caso `is_admin=False`, irraggiungibile su questa
risorsa (`ruolo_richiesto = "admin"`, verificato in `_ParametriHandler` e nel gate di
`routers/admin/import_excel.py:58-68`).

**Nessuna regressione anti-leak.** I due nuovi messaggi di scarto nominano la colonna e
rimandano indietro il valore che l'admin ha caricato lui stesso (`r.valori[CAMPO_MARGINE]`),
mai un valore letto dal database. La scrittura resta confinata a
`_forse_aggiungi_margine`/`_forse_aggiorna_margine`, entrambe dietro `is_admin`.

### WR-03 — CHIUSA per i nomi dei campi, INCOMPLETA per i tipi

`frontend/src/api/admin/uploadListino.ts:45-59` dichiara ora `id`, `livello` e
`campi_presenti`, e il test cross-linguaggio
`TestContrattoVoceRigaTypeScript::test_voce_riga_ts_elenca_gli_stessi_campi_di_voce_riga_in`
li presidia. La finding come formulata è chiusa.

Ma il test confronta **solo i nomi**, non i tipi, e nel farlo lascia in piedi un tipo
sbagliato su un campo che il commento appena aggiunto dichiara allineato al "contratto
sul filo" — vedi **WR-03 (nuova)**, che ha anche una conseguenza visibile a schermo.

---

## Critical Issues

### CR-01: `int()` non protetto su valori presi dal file: un `--5` in una cella fa 500

**File:** `backend/app/services/import_excel/parametri.py:224` (`listino_id`), `:387`
(`voce_id`), `:449` (`opzione_id`), più `:151`, `:211`, `:375`, `:433` (`int(r.id)`)

**Issue:**
Tre resolver validano un id numerico preso dal file così:

```python
listino_id = int(listino_id_raw) if str(listino_id_raw).strip().lstrip("-").isdigit() else None
```

`lstrip("-")` rimuove **tutti** i meno iniziali, non uno. Per `"--5"` il guard produce
`"5".isdigit() == True`, e poi `int("--5")` solleva `ValueError`. L'eccezione non è
catturata: né dal resolver, né da `diff()`, né dal router
(`routers/admin/import_excel.py:93` non ha try/except attorno a `handler.diff`), né da
un exception handler globale (`app/main.py` registra solo `RateLimitExceeded`). Risultato:
HTTP 500 sulla `/preview`, con l'utente che vede il toast generico "Import non riuscito".

I quattro `int(r.id)` hanno lo stesso problema per via diversa: `RigaPiattaIn.id` è
`str | None` e in `/confirm` arriva dal client senza alcuna validazione numerica
(`schemas/admin_import.py:39`), quindi un `id` non numerico basta a far 500.
`lead.py:145-148` fa la cosa giusta e lo avvolge in try/except — è il precedente da
seguire, non da ignorare.

Riprodotto eseguendo `diff()` su un database seminato:

```
listino_categoria -> ECCEZIONE NON GESTITA: ValueError invalid literal for int() with base 10: '--5'
coefficienti_pro  -> ECCEZIONE NON GESTITA: ValueError invalid literal for int() with base 10: '--7'
forfait_arredo    -> ECCEZIONE NON GESTITA: ValueError invalid literal for int() with base 10: '--3'
moltiplicatori    -> ECCEZIONE NON GESTITA: ValueError invalid literal for int() with base 10: 'abc'  (via int(r.id))
```

`"--5"` in una cella non richiede malizia: è un refuso di battitura o un residuo di
copia-incolla in un foglio Excel. Il caso contraddice direttamente la regola che la
docstring del modulo si dà ("un valore fuori bound è uno scarto, non un update") e la
disciplina "mai un 500" ripetuta in `flat.py`, `listino_upload_service.py` e
`routers/admin/import_excel.py`.

**Fix:** Una sola funzione di conversione che non può sollevare, usata in tutti e sette
i punti:

```python
def _intero(valore: object) -> int | None:
    """Conversione a intero che non solleva MAI: `None` = non convertibile,
    e chi chiama lo traduce in uno scarto descritto. `int(str(...))` diretto
    su una cella di file e' sempre un 500 in attesa (vedi `--5`, che passa
    qualunque guard basato su `lstrip("-").isdigit()`)."""
    try:
        return int(str(valore).strip())
    except (TypeError, ValueError):
        return None
```

```python
listino_id = _intero(listino_id_raw)
if listino_id is None:
    return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo="listino_categoria: listino_id non numerico"))
```

e per gli `int(r.id)`:

```python
riga_id = _intero(r.id)
if riga_id is None:
    return _Risoluzione(scarto=ScartoRowOut(riga=0, motivo=f"{r.foglio}: id non numerico ({r.id!r})"))
riga_db = db.get(Moltiplicatore, riga_id)
```

Come rete di sicurezza indipendente dal singolo resolver, vale la pena avvolgere
`handler.diff(...)` e `handler.apply(...)` nel router in un `except Exception` che
risponda 400 con messaggio descritto invece di 500 — il contratto dichiarato del modulo
è che nessuna riga malformata possa far cadere l'intero import.

### CR-02: due righe con la stessa chiave naturale nello stesso file fanno fallire l'intero import con un 500

**File:** `backend/app/services/import_excel/parametri.py:707` (`db.add` senza flush),
`backend/app/routers/admin/import_excel.py:131` (`db.commit()` non protetto),
`backend/app/db.py:16` (`autoflush=False`)

**Issue:**
`apply()` risolve ogni riga con una query (`db.query(...).filter_by(...).one_or_none()`)
e, se non trova nulla, fa `db.add(...)` **senza flush**. La sessione di produzione è
costruita con `autoflush=False`:

```python
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

quindi l'oggetto aggiunto per la prima riga **non** viene scritto prima della query della
seconda riga. Due righe con la stessa chiave naturale e senza `id` risolvono entrambe a
"non esiste", vengono entrambe aggiunte, e il vincolo unico scatta al `db.commit()` del
router — che non è protetto da alcun try/except. Risultato: `IntegrityError` non gestito
→ HTTP 500, nessuna riga importata (nemmeno le altre 300 valide del file), e l'admin
non ha modo di sapere quale riga fosse il problema.

Riguarda tutti i fogli con chiave naturale vincolata:
`uq_moltiplicatore_tipo_categoria`, `uq_listino_categoria`,
`uq_coefficiente_qta_voce_tipo`, `uq_forfait_arredo_opzione_livello`, più la PK
testuale di `Extra`.

Riprodotto con la configurazione di sessione di produzione:

```
nuove: 2 modificate: 0 scarti: []
righe_applicate: 2
COMMIT FALLITO -> IntegrityError (sqlite3.IntegrityError) UNIQUE constraint failed:
  moltiplicatore.tipo_code, moltiplicatore.categoria_code
```

Lo stesso script con `sessionmaker(bind=engine)` (cioè `autoflush=True`, la forma usata
da **tutte** le fixture di test — vedi WR-04) stampa `COMMIT OK`. È per questo che i
555 test passano: la suite non esercita mai la semantica di flush della produzione.

Duplicare una riga è l'errore di foglio di calcolo più comune che esista. Nota che
`listino_upload_service.apply_diff_idempotent` non ha il problema perché
`_upsert_sottocategoria`/`_upsert_voce` fanno `db.flush()` subito dopo `db.add()`
(`:502-503`, `:548-549`): è lo stesso modulo a mostrare il pattern corretto.

**Fix:** Due interventi, indipendenti, entrambi utili.

1. Flush esplicito dopo ogni creazione, come fa già `listino_upload_service`:

```python
if ris.esistente is None:
    ...
    db.add(_MODEL[r.foglio](**valori_creazione))
    # Flush esplicito: `SessionLocal` e' `autoflush=False`, quindi senza
    # questo la riga successiva con la stessa chiave naturale non la
    # vedrebbe e l'INSERT duplicato esploderebbe al commit del router.
    db.flush()
```

2. Rilevare il duplicato *dentro il payload* in `diff()`, così l'admin lo vede in
anteprima invece di scoprirlo a conferma fatta — tenendo un set delle chiavi naturali
già emesse fra le `nuove` e producendo uno `ScartoRowOut` alla seconda occorrenza.

In più, il `db.commit()` del router andrebbe protetto: un `IntegrityError` al commit
deve tradursi in un 400 descritto con rollback, mai in un 500.

---

## Warnings

### WR-01: sul percorso per chiave naturale l'anteprima non mostra i campi di sottocategoria che la conferma poi scrive

**File:** `backend/app/services/listino_upload_service.py:416-436` (`compute_diff`),
in relazione a `:646-650` (`apply_diff_idempotent`)

**Issue:**
In `compute_diff`, la variabile `sotto` viene valorizzata **solo** sul ramo per id:

```python
if riga.id is not None:
    match = per_id.get(riga.id)
    ...
    voce, sotto = match
else:
    voce = per_chiave.get(_voce_key(riga))   # `sotto` resta None
...
if sotto is not None:
    for campo_riga, campo_sotto in _CAMPI_DIFF_SOTTOCATEGORIA.items():
        ...
```

Per una riga senza `id` risolta per chiave naturale, il confronto su
`_CAMPI_DIFF_SOTTOCATEGORIA` (`categoria_code`, `sottocategoria_codice`,
`sottocategoria_nome`, `sottocategoria_famiglia`, `sottocategoria_ordine`) **non viene
mai eseguito**. Due conseguenze, entrambe sbagliate:

- se nessun campo di *voce* è cambiato, la riga non compare affatto nel diff e la
  modifica alla sottocategoria è persa in silenzio (nessuno scarto, nessun avviso);
- se almeno un campo di voce è cambiato, la riga finisce in `modificate` e
  `apply_diff_idempotent` chiama `_upsert_sottocategoria`, che — dopo il fix CR-01 —
  scrive correttamente i campi presenti… **che l'anteprima non ha mai mostrato**.
  L'admin conferma una scrittura che non gli è stata proposta.

Il secondo caso è quello che conta: l'intero valore di questa fase è "guardi il diff,
poi confermi". Un diff che sotto-dichiara ciò che verrà scritto rompe quella promessa.
Il fix CR-01 ha allineato `_upsert_*` alla disciplina di `_applica_*` ma ha lasciato
`compute_diff` disallineato dall'altra parte.

**Fix:** risolvere anche la sottocategoria sul ramo per chiave naturale, riusando la
mappa che `compute_diff` già costruisce:

```python
per_chiave: dict[tuple, tuple[Voce, Sottocategoria]] = {}
...
    per_chiave[key] = (voce, sotto)
...
else:
    match = per_chiave.get(_voce_key(riga))
    if match is not None:
        voce, sotto = match
```

Con `sotto` valorizzato in entrambi i rami il `if sotto is not None` diventa superfluo e
il diff torna a descrivere esattamente ciò che `apply` scriverà.

### WR-02: l'anteprima annuncia una modifica a `livello` che la conferma non applica mai (righe senza id)

**File:** `backend/app/services/listino_upload_service.py:347-353`
(`_CAMPI_DIFF_VOCE` include `livello`), `:552-554` (`_upsert_voce` lo esclude)

**Issue:**
`livello` è fra i campi diffati (`_CAMPI_DIFF_VOCE`), quindi `compute_diff` lo segnala
come modificato se il file lo porta e differisce dal database. Ma `_upsert_voce` lo
esclude deliberatamente dal ciclo di scrittura
(`for campo in ("descrizione", "um", "prezzo_unitario_cliente", "ordine")`), per la
ragione — corretta — che le righe di `parse_computo` si dichiarano complete e
scriverebbero `None` su ogni voce.

Il risultato sul percorso per chiave naturale è l'immagine speculare di WR-01:
l'anteprima dice "livello cambia", la conferma non lo cambia, `righe_importate` conta
comunque la riga come importata. L'admin che cura i livelli a mano dal file piatto vede
il diff giusto, conferma, e non trova la modifica applicata — senza nessun messaggio.

Il percorso per id non ha il problema (`_applica_voce:578-580` include `livello`), quindi
la divergenza è esattamente quella fra i due percorsi che CR-01 ha appena armonizzato
per gli altri campi.

**Fix:** distinguere l'origine invece del percorso. Le righe di `parse_flat_listino`
portano sempre `campi_presenti` valorizzato, quelle di `parse_computo` hanno
`campi_presenti is None`: la condizione da usare non è "ramo per id" ma "il file
dichiara esplicitamente il campo".

```python
for campo in ("descrizione", "um", "prezzo_unitario_cliente", "ordine"):
    if _campo_presente(riga, campo):
        setattr(voce, campo, getattr(riga, campo))
# `livello` SOLO se dichiarato esplicitamente: `campi_presenti is None`
# (parse_computo) non vale come dichiarazione, il computo non ha quella
# colonna e scriverebbe None azzerando la curatela.
if riga.campi_presenti is not None and "livello" in riga.campi_presenti:
    voce.livello = riga.livello
```

In alternativa, se si preferisce lasciare `_upsert_voce` com'è, togliere `livello` da
`_CAMPI_DIFF_VOCE` **solo** per le righe senza id, così l'anteprima smette di promettere
una scrittura che non avverrà. La prima strada è preferibile: il campo è curato a mano e
il file piatto è l'unico modo di curarlo in blocco.

### WR-03: `prezzo_unitario_cliente` è dichiarato `number` in TypeScript ma sul filo è una stringa — e si vede a schermo

**File:** `frontend/src/api/admin/uploadListino.ts:55`,
`frontend/src/components/admin/ExcelUploadDialog.tsx:60`

**Issue:**
`VoceRigaIn.prezzo_unitario_cliente` è un `Decimal` pydantic, che in JSON viene
serializzato come **stringa** (convenzione Decimal-as-string del progetto, dichiarata in
`import_excel/parametri.py:584-588`). Verificato:

```
{"riga":{"id":1,...,"prezzo_unitario_cliente":"12.50",...},"valore_precedente":"3.00",...}
```

L'interfaccia TS — appena ritoccata dal commit `d9ca2ad` con un commento che dichiara di
rispecchiare `VoceRigaIn` "campo per campo" — la dichiara `number`. `normalizeDiffRow`
(`:96-102`) normalizza `valore_precedente` con `toNumberOrNull` ma passa `raw.riga`
inalterato, quindi a runtime il campo resta una stringa.

Non è solo un tipo sbagliato: produce un difetto visibile. In `toDiffPreviewRows`:

```ts
valorePrecedente: row.valore_precedente.toLocaleString("it-IT", { style: "currency", currency: "EUR" }),
valoreNuovo:      row.riga.prezzo_unitario_cliente.toLocaleString("it-IT", { style: "currency", currency: "EUR" }),
```

la prima chiama `Number.prototype.toLocaleString` e produce `12,50 €`; la seconda chiama
`String.prototype.toLocaleString`, che **ignora gli argomenti** e restituisce la stringa
grezza `"12.50"`. Nella tabella di anteprima dell'upload listino la colonna "precedente"
è formattata in euro e la colonna "nuovo" no — con il separatore decimale sbagliato per
la locale italiana.

Il test cross-linguaggio aggiunto da WR-03 non lo intercetta perché confronta solo i
**nomi** dei campi (`re.findall(r"^\s{2}(\w+)\??:", ...)`), mai i tipi, e dà quindi una
sicurezza che non ha.

**Fix:** dichiarare il tipo vero e normalizzare nel punto in cui si normalizza già
`valore_precedente`:

```ts
// Decimal-as-string al confine API: pydantic serializza Decimal come
// stringa JSON, non come number.
prezzo_unitario_cliente: string;
```

```ts
function normalizeDiffRow(raw: RawDiffRow): DiffRow {
  return {
    riga: raw.riga,
    prezzoNuovo: toNumberOrNull(raw.riga.prezzo_unitario_cliente),
    valore_precedente: toNumberOrNull(raw.valore_precedente),
    riga_modificata_dopo_export: raw.riga_modificata_dopo_export,
  };
}
```

e usare `prezzoNuovo` in `toDiffPreviewRows`. Nota che `VoceRiga` viene rispedito
verbatim a `/confirm`, quindi il campo grezzo deve restare stringa nell'oggetto `riga`:
il numero normalizzato va accanto, non al suo posto. Conviene inoltre estendere il test
di contratto a confrontare anche i tipi (almeno stringa-vs-numero), altrimenti il
prossimo campo `Decimal` ripeterà l'errore.

### WR-04: le fixture di test costruiscono la sessione con `autoflush=True`, la produzione con `autoflush=False`

**File:** `backend/tests/test_import_parametri.py:53`, `backend/tests/test_import_lead.py`,
`backend/tests/test_export_import_roundtrip.py`, `backend/tests/test_import_stale.py`
(e altri ~30 file di test), contro `backend/app/db.py:16`

**Issue:**
La produzione usa `sessionmaker(autocommit=False, autoflush=False, bind=engine)`; ogni
fixture usa `sessionmaker(bind=engine)`, che lascia il default `autoflush=True`. La
differenza non è cosmetica: cambia se una query vede gli oggetti pendenti aggiunti
poco prima. È esattamente la divergenza che rende **CR-02** invisibile a 555 test —
lo stesso script produce `COMMIT OK` con la configurazione di test e `IntegrityError`
con quella di produzione.

La divergenza è preesistente e più ampia della fase 08, ma i file di test di questa fase
sono proprio quelli che devono presidiare la semantica di scrittura dell'import, e su
quella semantica stanno mentendo.

**Fix:** far costruire la sessione di test dalla stessa fabbrica della produzione, così
che la configurazione non possa più divergere:

```python
from app.db import SessionLocal as _ProdSessionLocal

testing_session_local = sessionmaker(
    bind=engine, **{k: _ProdSessionLocal.kw[k] for k in ("autocommit", "autoflush")}
)
```

oppure, più semplicemente e in un solo punto, una `conftest.py` che esponga una factory
condivisa con `autoflush=False` esplicito. Va fatto in un passaggio dedicato: cambiare
la semantica di flush sotto a 555 test può far emergere altri difetti mascherati — il
che, del resto, è il punto.

### WR-05: `alembic revision --autogenerate` emetterebbe `drop_table("lead")` e `drop_table("testo")`

**File:** `backend/app/models/__init__.py:6-29` (import mancanti),
`backend/alembic/env.py:15` e `:28`

**Issue:**
`alembic/env.py` costruisce `target_metadata = Base.metadata` affidandosi al solo
`from app import models` per registrare le entità. Ma `app/models/__init__.py` non
importa `app.models.lead` né `app.models.testo`, quindi quelle due tabelle non finiscono
in `Base.metadata`. Verificato:

```
$ python -c "from app.db import Base; from app import models; print('lead' in Base.metadata.tables, 'testo' in Base.metadata.tables)"
False False
```

Conseguenza diretta: il prossimo `alembic revision --autogenerate` genera una migrazione
che **elimina le tabelle `lead` e `testo`** — cioè i contatti commerciali, il dato di
maggior valore dell'applicazione. Basta che chi la genera non rilegga riga per riga il
file prodotto, che è la ragione stessa per cui si usa autogenerate.

La fase 08 rende la cosa più pressante, non meno: la migrazione `0019` aggiunge
`updated_at` proprio a `lead`, e i test nuovi importano i due moduli a mano con un
commento che spiega l'aggiramento — il sintomo è stato notato e lasciato lì.

**Fix:** due righe in `app/models/__init__.py`, più le due voci in `__all__`:

```python
from app.models.lead import Lead
from app.models.testo import Testo
```

A quel punto l'import esplicito nei test diventa superfluo e il commento che lo
giustifica va rimosso. Vale anche un test che asserisca che ogni modulo sotto
`app/models/` risulti registrato in `Base.metadata`, così la prossima entità aggiunta e
dimenticata si fa sentire subito.

---

## Info

### IN-01: `apply()` conta come "applicate" anche le righe no-op

*(riportata dall'iterazione 1, deliberatamente fuori scope del passaggio di fix — invariata)*

**File:** `backend/app/services/import_excel/parametri.py:661-703`,
`backend/app/services/import_excel/lead.py:312-329`

**Issue:** Quando una riga risolta ha un `id` ma il file non porta campi che differiscano
davvero dal database (`campi_aggiornati`/`validati` vuoto), `apply()` incrementa comunque
`applicate`/`righe_applicate`. Il numero riportato all'admin ("N righe applicate") non è
quindi "N righe cambiate", il che è lievemente fuorviante per una conferma di round-trip
a vuoto.

**Fix:** contare la riga solo se almeno un campo è stato effettivamente scritto, oppure
cambiare la copy della UI perché non implichi "cambiate".

### IN-02: `ConfirmPiattoIn.risorsa` è dichiarata obbligatoria e non viene mai usata

**File:** `backend/app/schemas/admin_import.py:72`,
`backend/app/routers/admin/import_excel.py:110-131`

**Issue:** `confirm_import` risolve l'handler dal path param `risorsa` e non guarda mai
`payload.risorsa`, che resta un campo obbligatorio (`min_length=1, max_length=32`) del
body. Un client che mandi `POST /import-excel/parametri/confirm` con
`{"risorsa": "lead", ...}` ottiene l'handler `parametri` senza alcun segnale. Non è
sfruttabile (il gate di ruolo segue l'handler risolto, cioè il path), ma è un campo che
sembra avere un significato e non ne ha.

**Fix:** o validare la coerenza (`if payload.risorsa != risorsa: raise HTTPException(400, ...)`),
o togliere il campo dallo schema. La prima opzione costa una riga e trasforma un
disallineamento silenzioso del client in un errore leggibile.

---

_Reviewed: 2026-09-23_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard — iterazione 2_
