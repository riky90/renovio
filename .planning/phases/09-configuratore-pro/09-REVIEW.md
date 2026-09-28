---
phase: 09-configuratore-pro
reviewed: 2026-09-28T18:17:57Z
depth: standard
files_reviewed: 24
files_reviewed_list:
  - backend/alembic/versions/0021_assi_pro_da_livello_e_chiavi_mirate.py
  - backend/alembic/versions/0023_pavimenti_alternativi.py
  - backend/app/routers/dettaglio_pro.py
  - backend/app/routers/stime_salvate.py
  - backend/app/schemas/dettaglio_pro.py
  - backend/app/schemas/stima_salvata.py
  - backend/scripts/applica_taratura.py
  - backend/scripts/genera_excel_taratura.py
  - backend/tests/test_alternative_mondo_aperto.py
  - backend/tests/test_migrazioni_sqlite.py
  - backend/tests/test_wizard_pro_scelte.py
  - backend/tests/test_no_leak.py
  - frontend/src/api/stima.ts
  - frontend/src/components/DettaglioProView.tsx
  - frontend/src/components/EstimateWizard.tsx
  - frontend/src/pages/EstimatePage.tsx
  - frontend/src/pages/NuovaStimaProPage.tsx
  - frontend/src/pages/admin/BonusPage.tsx
  - frontend/src/pages/admin/CoefficientiPage.tsx
  - frontend/src/pages/admin/DomandePage.tsx
  - frontend/src/pages/admin/ListiniPage.tsx
  - frontend/src/pages/admin/domande/EffettiSezione.tsx
  - frontend/src/pages/admin/domande/OpzioniSezione.tsx
  - frontend/src/routes/LeMieStimePage.tsx
findings:
  critical: 1
  warning: 7
  info: 5
  total: 13
status: issues_found
---

# Phase 09: Code Review Report (gap closure 09-09..09-14)

**Reviewed:** 2026-09-28T18:17:57Z
**Depth:** standard
**Files Reviewed:** 24
**Status:** issues_found

## Review precedente

La review precedente (2026-09-28T07:52:14Z) copriva i piani 09-01..09-08
(range `b92e06e..9661c1f`, 36 file) e riportava 0 critical, 2 warning e 2 info.
Stato attuale dei suoi finding:
- **WR-01** (0021/0022 mai verificate su Postgres): **ancora aperto**, e ora
  vale anche per la 0023. Nessun test Postgres è stato aggiunto. Nota che la
  produzione è ferma alla 0013 (`origin/main`), quindi al prossimo push Render
  eseguirà di fila 0014..0023 su Postgres senza che la catena sia mai stata
  eseguita su quel motore.
- **WR-02** (il downgrade della 0021 cancella `domanda`/`opzione_domanda` di
  `finitura` preesistenti): **chiuso in parte** dal 09-14 (commit `6971054`).
  Domanda e opzioni non vengono più toccate, ma il downgrade resta asimmetrico
  sugli effetti e adesso dipende dalla colonna vestigiale `voce.livello`
  (vedi WR-02 sotto).
- **IN-01** (`assert` in `computo_parsing.py:334`) e **IN-02** (N+1 in
  `DettaglioProService.compute`): **ancora aperti**. I file non sono stati
  toccati dal 09-09..09-14 e restano fuori dallo scope di questa review.

## Summary

Ho revisionato i file toccati dai piani 09-09..09-14 (diff `30d4379..HEAD`):
- la migrazione nuova 0023 e il downgrade corretto della 0021;
- l'estensione di `/me/opzioni-pro` e di `POST /me/stime` con `scelte`;
- le regole di curatela G1/G2 in `genera_excel_taratura.py` e `applica_taratura.py`;
- il percorso Pro nel wizard e in `NuovaStimaProPage`;
- il pavimento sempre visibile in `DettaglioProView`;
- i dialog admin completati nel 09-13.

Controlli di dominio espliciti:
- **Regola 1, nessun prezzo impresa né coefficiente al client: rispettata.**
  `DomandaProOut` e `OpzioneProOut` restano DTO chiusi, e `_domanda_out()` mappa
  campo per campo. `OpzioniProOut.domande` non espone effetti, `valore` degli
  effetti, `coefficiente_qta_per_mq` né prezzi. `test_no_leak.py` copre il nuovo
  endpoint (`test_opzioni_pro_non_leaka_effetti_ne_coefficienti`). Le pagine
  admin mostrano coefficienti Pro e moltiplicatori, ma sono rotte `require_admin`.
- **La 0023 non dipende da `voce.livello`: confermato.** Nel file la parola
  `livello` non compare (0 occorrenze). Le voci si risolvono per
  codice/descrizione dentro la sottocategoria. La dipendenza da `livello`
  rimane invece nel downgrade della 0021 (WR-02) e nel generatore di taratura
  (WR-05).
- **Postgres:** tutto il DML è `sa.table`/`sa.select` portabile. Non c'è SQL
  grezzo, gli insert non impostano `id` (serial) e i booleani sono Python
  `bool`. Esiste però un problema reale di determinismo: `.first()` è chiamato
  senza `ORDER BY` e senza filtro sul listino (WR-03). Su `origin/main` la
  catena 0014..0023 parte da un DB senza catalogo domande. La 0023 quindi in
  produzione sarà un no-op (manca la domanda `tipo_pavimento`) e il lavoro vero
  lo farà il seed al boot.

Il finding più grave non riguarda le migrazioni. È il dialog "Modifica
listino" introdotto dal 09-13: rende modificabili dal pannello due campi
(`nome`, `is_default`) su cui il backend non applica alcun invariante. Con
l'uso normale del pannello questo può impedire il boot del container su
Render (CR-01).

## Critical Issues

### CR-01: "Modifica listino" può impedire l'avvio della produzione (rinomina del listino RE / doppio predefinito)

**File:** `frontend/src/pages/admin/ListiniPage.tsx:119-131, 403-448`. Backend coinvolto, fuori scope ma chiamato direttamente: `backend/app/routers/admin/listini.py:126-146`, `backend/scripts/seed.py:805-815` e `:597`, `backend/app/services/city_resolver.py:30`, `backend/app/services/lead_service.py:36`.

**Issue:** il nuovo dialog manda `PATCH /admin/listini/{id}` con `{nome, is_default, attivo}`. `modifica_listino` scrive i tre campi così come arrivano, senza nessun invariante. Ci sono due percorsi che rompono il sistema.

1. **Rinomina del listino "Reggio Emilia".** `seed()` cerca il listino con
   `filter_by(nome="Reggio Emilia")`. Se l'admin lo rinomina (per esempio
   "Reggio Emilia 2026"), al boot successivo il seed non lo trova e ne **crea
   un secondo** con `is_default=True`, risemina sotto di esso tutte le
   sottocategorie e le voci, e poi chiama `seed_domande`. `seed_domande` esegue
   `filter_by(is_default=True).one_or_none()` e trova due righe, quindi solleva
   `MultipleResultsFound`. Il `CMD` del `Dockerfile` è
   `alembic upgrade head && python scripts/seed.py && uvicorn ...`, quindi
   uvicorn non parte e **la produzione resta giù** finché qualcuno non corregge
   il DB a mano.
2. **Secondo listino marcato "Predefinito".** Con due listini `is_default=True`,
   `resolve_listino` (`.one()`) e `lead_service` (`.one()`) sollevano
   `MultipleResultsFound`. Ogni `/api/v1/stima` per una città senza listino
   dedicato risponde 500. Se invece l'admin toglie "Predefinito" all'unico
   listino di default, le stesse chiamate sollevano `NoResultFound`. In
   entrambi i casi il boot successivo si blocca come al punto 1: il seed
   rimette `is_default=True` su RE e `seed_domande` ne trova due.

Prima del 09-13 questi campi non erano modificabili da UI. Il dialog trasforma
un invariante che il codice dava per scontato in un'azione da un clic.

**Fix:** servono sia il backend (vincolo reale) sia il frontend (guardia UX).
```python
# backend/app/routers/admin/listini.py::modifica_listino
if payload.is_default is not None:
    if payload.is_default:
        db.execute(update(Listino).where(Listino.id != listino.id).values(is_default=False))
    elif listino.is_default:
        raise HTTPException(409, "Serve sempre un listino predefinito: marca prima un altro listino")
    listino.is_default = payload.is_default
```
Poi il seed va reso stabile rispetto alla rinomina: deve cercare il listino
per una chiave che il pannello non modifica (`citta_riferimento`, che il
dialog mostra già in sola lettura) invece che per `nome`, e non deve
forzare `is_default=True` se esiste già un altro default. In alternativa il
campo Nome si mostra in sola lettura per il listino di seed. Un vincolo
parziale nel DB (`UNIQUE (is_default) WHERE is_default`, indice parziale
Postgres/SQLite) rende l'invariante non aggirabile.

## Warnings

### WR-01: Il seed annulla a ogni boot "Predefinito"/"Attivo" impostati dal nuovo dialog

**File:** `frontend/src/pages/admin/ListiniPage.tsx:432-447`. Causa in `backend/scripts/seed.py:815-816`.

**Issue:** `seed()` esegue ogni volta `listino.is_default = True` e
`listino.attivo = True` sul listino RE. Se l'admin disattiva RE o lo toglie dai
predefiniti dal nuovo dialog, il salvataggio va a buon fine (toast "Modifica
salvata"), ma al deploy successivo il valore torna indietro senza alcun
avviso. È lo stesso difetto che D-41 ha eliminato per `domanda.attiva`/`testo`
("il catalogo è del pannello, non del seed"). Qui il dialog promette una
modifica che il sistema non conserva.

**Fix:** il seed scriva `is_default`/`attivo` solo alla creazione del listino
(create-if-missing, come `domanda`/`opzione_domanda`). In alternativa il
dialog mostri i due switch in sola lettura per il listino di seed, con una
spiegazione.

### WR-02: Il downgrade della 0021 resta asimmetrico sugli effetti e ora dipende da `voce.livello`

**File:** `backend/alembic/versions/0021_assi_pro_da_livello_e_chiavi_mirate.py:394-416`

**Issue:** l'upgrade salta un `includi` che esiste già (`_effetto_esiste`, riga
233), mentre il downgrade cancella *ogni* `includi` di `finitura` la cui voce
ha `voce.livello == opzione.code`, **chiunque l'abbia creato**. È l'asimmetria
di WR-02, spostata da domanda/opzioni agli effetti. Esempio concreto: il
`dev.db` attuale. Dal 09-10 ha `voce.livello` ripopolato a mano su 21 voci
GRES, esattamente le voci su cui il seed ha già creato gli `includi` di
`finitura`. Un `alembic downgrade 0020` cancella questi 21 effetti del seed,
che la 0021 non ha mai scritto. In più la correttezza del downgrade ora
dipende da una colonna che il 09-10 stesso definisce "vestigiale" e che
`scripts/seed.py` non scrive mai. Su un DB fresco il downgrade non fa niente;
su un DB ripopolato a mano cancella curatela. Il test nuovo
(`test_downgrade_0021_preserva_finitura_preesistente_e_effetto_curato_a_mano`)
copre soltanto voci *senza* livello, quindi non esercita questo caso.

**Fix:** l'unica simmetria vera richiede di sapere cosa ha scritto l'upgrade.
Un modo è marcare le righe con un `updated_at` sentinella della migrazione e
cancellare solo quelle. L'altro è dichiarare il downgrade della sezione (A)
"no-op documentato", come fa la 0022 per ciò che non può distinguere. In ogni
caso va aggiunto un test con voce livellata *e* un `includi` preesistente
sulla stessa coppia (opzione, voce).

### WR-03: 0021/0022/0023 risolvono la sottocategoria senza filtro sul listino e senza `ORDER BY`

**File:** `backend/alembic/versions/0023_pavimenti_alternativi.py:126-158` (`_risolvi_voce_id`). Lo stesso schema è in `0022_taratura_pro_approvata.py:88-103` e nel template `backend/scripts/applica_taratura.py::emetti_migrazione`.

**Issue:** `Sottocategoria` è per listino (`listino_id NOT NULL`). Il seed
risolve i bersagli naturali **solo sul listino predefinito**
(`seed.py:597, 548-549`), mentre la migrazione prende
`select(sottocategoria.id).where(categoria_code=..., codice=...).first()` su
tutti i listini. Se esiste un secondo listino con gli stessi codici, cosa
prevista dalla regola 4 e dall'import Excel di `upload_listino`, succede
questo:
- su Postgres `.first()` senza `ORDER BY` restituisce una riga qualsiasi,
  quindi gli effetti possono agganciarsi alle voci del listino sbagliato;
- la guardia fail-loud passa o fallisce in base a quale listino esce per
  primo;
- il downgrade può risolvere un `voce_id` diverso da quello usato
  dall'upgrade e lasciare orfani gli effetti scritti.

SQLite restituisce di fatto l'ordine di rowid, quindi i test su SQLite non
possono vedere il problema.

**Fix:** allineare la risoluzione a quella del seed.
```python
listino = sa.table("listino", sa.column("id"), sa.column("is_default"))
default_id = bind.execute(sa.select(listino.c.id).where(listino.c.is_default.is_(True))).scalar_one_or_none()
# ... .where(sottocategoria.c.listino_id == default_id, ...)
```
Se `default_id` è `None`, fare no-op (catalogo non seminato). Aggiungere lo
stesso filtro nel template di `applica_taratura.py`, così le migrazioni
future lo ereditano.

### WR-04: Il downgrade della 0023 cancella effetti che l'upgrade non ha scritto

**File:** `backend/alembic/versions/0023_pavimenti_alternativi.py:309-331`, e la docstring alle righe 47-50 e 297-302.

**Issue:** la docstring dice che il downgrade "toglie solo ciò che l'upgrade ha
scritto", ma non è così. L'upgrade salta ogni effetto che esiste già
(riga 263); il downgrade cancella per chiave naturale **senza guardare
`valore` né `attivo`**. Nei casi reali questo significa:
- sul `dev.db` di oggi l'upgrade è stato un no-op, perché il catalogo era già
  seminato (lo dice il 09-14 SUMMARY). Un downgrade cancella comunque tutti i
  175 effetti e le 3 opzioni, cioè curatela del seed;
- un `fattore_quantita` ritarato dall'admin (per esempio da 0.12 a 0.15), o un
  effetto disattivato (`attivo=False`), viene cancellato. Al successivo
  upgrade, o al seed, viene ricreato con il valore di seed e `attivo=True`, e
  la taratura dell'admin è persa.

Il test `test_0023_downgrade_toglie_solo_cio_che_upgrade_ha_scritto` rimuove
prima a mano gli effetti (`_rimuovi_effetti_e_opzioni_0023`), quindi prova
solo il caso favorevole in cui l'upgrade li ha davvero scritti.

**Fix:** cancellare solo le righe con `valore` uguale a quello della costante
(con `_vicino`) e con `updated_at` uguale a quello dell'upgrade. In
alternativa correggere la docstring e dichiarare il downgrade distruttivo
verso la curatela successiva. Aggiungere un test "seed già passato → upgrade →
downgrade" che verifichi quali effetti restano.

### WR-05: Il template di migrazione disattiva la guardia fail-loud quando la migrazione tocca solo coefficienti

**File:** `backend/scripts/applica_taratura.py` (template `_TEMPLATE_MIGRAZIONE`, `_domande_citate`/`_catalogo_presente`, circa righe 780-866 del file)

**Issue:** `_catalogo_presente()` restituisce `False` quando `_domande_citate()`
è vuoto, cioè quando `_VALORI_EFFETTO`/`_INCLUDI_SPOSTATI`/`_EFFETTI_RIMOSSI`
sono tutti vuoti. Una migrazione emessa per sole modifiche di
`coefficiente_qta_voce` (`_COEFFICIENTI` non vuoto) diventa quindi **sempre**
silenziosa sulle chiavi non risolte, anche su un DB con catalogo completo. È
proprio il difetto "migrazione inerte in silenzio" (lezione 09-06 / T-09-57)
che il 09-09 voleva chiudere. I coefficienti dipendono dal catalogo voci, non
dal catalogo domande, quindi la presenza del catalogo va verificata sulle
voci.

**Fix:**
```python
def _catalogo_presente(bind, opzione, voce) -> bool:
    if _COEFFICIENTI and bind.execute(sa.select(voce.c.id).limit(1)).first() is not None:
        return True
    ...  # controllo attuale sulle domande citate
```
Aggiungere un test in `test_applica_taratura.py` con una migrazione di soli
coefficienti e una voce bersaglio alterata, che deve produrre `RuntimeError`.

### WR-06: `--aggiorna-assi` perde in silenzio le decisioni `finitura` se `voce.livello` è vuoto

**File:** `backend/scripts/genera_excel_taratura.py:409-464` (ramo 1 di `proponi_assegnazione`), `:940-1033` (`aggiorna_foglio_assi`)

**Issue:** l'asse `finitura` (incluso il gres a pavimento con quota bagno) si
propone solo da `v.livello_attuale`, cioè da `voce.livello`. Su un DB fresco
(`scripts/seed.py` non scrive mai `livello`) il ramo produce zero righe.
`aggiorna_foglio_assi` riaggiunge in coda solo le righe vecchie con decisione
**diversa da "OK"**, e solo nello stato `compilato`. Le decisioni "OK" già
accettate, cioè tutte quelle del workbook `bozza-accettata`, spariscono senza
avviso. Il successivo `applica_taratura --solo-assi` riscrive allora
`seed-domande.json` senza gli `includi` di `finitura`. È successo davvero nel
09-10 (due false partenze, correzione manuale descritta nelle Deviazioni) ed
è rimasto affidato a un passo manuale documentato.

**Fix:** fallire subito quando il foglio vecchio contiene righe
`asse_proposto == "finitura"` e le nuove proposte ne hanno zero, per esempio
con `raise SystemExit("voce.livello vuoto: ripopolalo prima di --aggiorna-assi")`.
Più in generale, riaggiungere o segnalare *ogni* riga sparita, anche quelle
con "OK". Meglio ancora: derivare l'asse finitura dagli effetti `finitura`
già presenti nel seed invece che dalla colonna vestigiale.

### WR-07: Il cambio pavimento nel dettaglio invia modifiche non confermate e, in caso di errore, mostra una scelta non applicata

**File:** `frontend/src/components/DettaglioProView.tsx:108-115`

**Issue:** `handleSceltaChange` invia `{...risposteInput, [code]: valore}`
insieme a `livelliInput`. Se il pannello è espanso e l'utente ha cambiato
bagni/porte o un livello **senza** premere "Calcola il dettaglio", un clic sul
pavimento salva anche quei valori e poi richiude il pannello (`onSuccess →
setDomandeCollassate(true)`). L'utente non ha confermato quel ricalcolo.
Inoltre `setRisposteInput(aggiornate)` avviene prima della mutation. Se la
mutation fallisce, la card del pavimento resta sulla nuova opzione mentre
totali, riepilogo e PDF riflettono ancora la vecchia. Resta solo l'Alert
generico a segnalare la discrepanza.

**Fix:** nel ramo "scelta sempre visibile" inviare le risposte *salvate* (da
`dettaglio.domande[].valore`) più la sola scelta cambiata. In `onError`
riportare `risposteInput[code]` al valore precedente.
```ts
const precedente = risposteInput[code];
risposteMutation.mutate(payload, { onError: () => setRisposteInput((p) => ({ ...p, [code]: precedente })) });
```

## Info

### IN-01: La 0023 duplica ciò che il seed fa già al boot, e aggiunge solo un modo di fallire

**File:** `backend/alembic/versions/0023_pavimenti_alternativi.py:12-17`

**Issue:** `_EFFETTI_RIMOSSI` è vuoto e nessun `valore` cambia. L'ho verificato
con un diff fra `2b6e29b:seed-domande.json` e HEAD sulle domande
`tipo_pavimento`/`finitura`: 175 aggiunte, 0 rimozioni, 0 valori cambiati.
`seed_domande` crea già al boot le opzioni e gli effetti mancanti anche su un
DB esistente (`_crea_effetto_se_manca` gira per ogni opzione, esistente o
nuova). La docstring ("un DB esistente non ripassa mai dal seed") vale per le
righe *da aggiornare*, non per quelle *da creare*. In pratica la 0023 anticipa
ciò che il seed farebbe comunque, e in cambio può bloccare il boot con un
`RuntimeError` se una descrizione di voce è stata modificata dal pannello
(vedi IN-02). Non è un bug, ma il costo e il beneficio vanno riconsiderati.

**Fix:** correggere la docstring. Valutare se la guardia debba solo avvisare
(log) invece di sollevare quando l'unica differenza sono effetti da creare.

### IN-02: Il testo del dialog voce invita a modificare le chiavi naturali di seed e migrazioni

**File:** `frontend/src/pages/admin/ListiniPage.tsx:520-526`

**Issue:** "Codice e descrizione identificano la voce nel computo: si cambiano
da Voci dettaglio Pro". Seed, 0022 e 0023 agganciano gli effetti proprio per
codice o descrizione esatta. Se la descrizione di una voce con codice NULL
cambia:
- il seed salta in silenzio gli effetti che la citano;
- le migrazioni emesse da `applica_taratura` falliscono con `RuntimeError`,
  bloccando il boot.

**Fix:** aggiungere all'aiuto un avviso esplicito (per esempio "cambiare la
descrizione scollega gli effetti che la citano").

### IN-03: Moquette, posa A.6.1 al 100% ma fornitura gres a quota bagno

**File:** `backend/scripts/genera_excel_taratura.py:268-273, 435-451`

**Issue:** per `moquette` la fornitura gres a pavimento riceve
`fattore_quantita 0.12` (il loop gira su tutte le opzioni diverse da gres),
mentre la posa A.6.1 resta a quantità piena perché moquette non è in
`OPZIONI_CON_QUOTA_BAGNO_A6_1`. L'ho verificato nel seed: moquette ha 19
`fattore_quantita`, nessuno su A.6.1. Il computo risultante paga la posa gres
su tutta la casa e la fornitura gres solo per il bagno. È la decisione "da
confermare a Riccardo" del 09-09, ma il 09-14 SUMMARY afferma "quota assente
per moquette", che contraddice il seed. Va chiarita nel ri-collaudo.

### IN-04: "Rifai in versione Pro" non porta risposte e destinazione

**File:** `frontend/src/routes/LeMieStimePage.tsx:96-98`

**Issue:** il link passa solo `citta`/`mq`/`tipo`. A differenza di
`CtaDettaglioPro`, qui non c'è un `state` con risposte e destinazione, quindi
il wizard riparte dallo step 1 e l'utente deve rispondere di nuovo alle
domande Free, benché lo snapshot le contenga. Il gap G3 è chiuso solo per il
percorso dalla home.

### IN-05: `preferenze_pro.scelte` viene accettato e salvato anche per le stime Free

**File:** `backend/app/routers/stime_salvate.py:81-105`

**Issue:** le scelte vengono validate e scritte in `risposte_pro_json` anche
quando `tier == "free"`. Non è un problema di sicurezza, perché il dettaglio
resta dietro `require_pro`, ma un utente Free può salvare dati Pro che una
stima Free non dovrebbe avere.

**Fix:** ignorare `scelte` (o rispondere 400) quando `tier != "pro"`.

---

_Reviewed: 2026-09-28T18:17:57Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
