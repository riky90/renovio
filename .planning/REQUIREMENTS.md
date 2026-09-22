# Requirements — ristruttura-stima

**Milestone attiva:** v2.0 — *domande e motore parametrico*
**Milestone precedente:** v1.0 (MVP) — chiusa, archiviata in `.planning/milestones/v1.0-REQUIREMENTS.md`

La v1 risponde a `(città, mq, tipo)`. La v2 risponde a *com'è fatta questa casa e cosa vuoi
farci*, senza che aggiungere una domanda costi un deploy.

---

## v2 Requirements

### Catalogo di domande (QST)

- [x] **QST-01**: Le domande del wizard sono un catalogo in database (`domanda` → `opzione_domanda` → `effetto_opzione`), amministrabile senza deploy di backend o frontend
- [x] **QST-02**: `tipo_effetto` è un insieme **chiuso** di sette valori con aritmetica nota al motore: nessuna espressione o formula libera in tabella
- [x] **QST-03**: `attesa_immobile` (valore atteso per attributo e fascia di m²) alimenta sia i **default** del wizard sia la **baseline** dello scostamento, da una sola fonte
- [x] **QST-04**: Il catalogo servito al client **non pubblica gli effetti**: la taratura resta server-side
- [ ] **QST-05**: Ogni chiave consumata dal motore Pro (`domanda_mirata_key`) ha una domanda corrispondente nel catalogo

### Motore parametrico (PAR)

- [x] **PAR-01**: Il motore Free applica gli effetti nell'ordine documentato — moltiplicatori di categoria, poi €/m² additivi, poi correzioni per scostamento — così un termine additivo non viene scalato da un moltiplicatore che non lo riguarda
- [x] **PAR-02**: **Neutralità a riposo**: senza risposte, o con risposte tutte pari agli attesi, il risultato è identico alla v1. L'oracolo primario (85 m² · totale · Reggio Emilia → 47.985–70.575 €) non si muove
- [x] **PAR-03**: Le correzioni si applicano sullo **scostamento** dall'atteso, mai sul valore assoluto
- [x] **PAR-04**: Anteprima admin (`POST /admin/anteprima-stima`) che mostra il breakdown, quali effetti hanno sparato e il delta rispetto alla stima senza risposte — è lo strumento con cui si tara
- [x] **PAR-05**: Nessun layer parametrico porta il coefficiente impresa: le correzioni sono in euro-cliente

### Wizard (WIZ)

- [x] **WIZ-01**: Un solo wizard per Free e Pro, a 4 step, con le domande servite da `GET /api/v1/domande`
- [x] **WIZ-02**: `NumberStepper` come primitivo dei contatori (−/valore/+, tap ≥44px, `inputMode="numeric"`)
- [x] **WIZ-03**: I default derivano dai m², mai zero, e lo step dell'immobile è saltabile con i valori standard
- [ ] **WIZ-04**: Il percorso Pro del wizard è verificato dal vivo end-to-end, non solo a livello di tipi

### Arredo (ARR)

- [ ] **ARR-01**: Esiste la categoria `E-ARREDO`, esclusa dal totale lavori tramite la colonna dato `categoria.nel_totale_lavori` — nessuna costante di business nel codice
- [ ] **ARR-02**: Free: forfait per `(ambiente, livello)` a range, guidato dalla multiselect "ambienti da arredare"
- [ ] **ARR-03**: L'arredo è esposto come **fratello** di `totale`, mai dentro, con il suo disclaimer nel payload, così finisce nello snapshot e nel PDF
- [ ] **ARR-04**: Con l'input arredo disponibile, il Bonus Mobili si può accendere dal pannello admin senza deploy

### Curatela dei dati (CUR)

- [x] **CUR-01**: Export/import Excel dal pannello admin in **round-trip**: il file esportato si ricarica senza riformattarlo
- [x] **CUR-02**: Colonna assente nel file = campo non toccato (è la regola che protegge la curatela di `voce.livello` dal re-upload)
- [x] **CUR-03**: L'export che contiene il coefficiente impresa è riservato al ruolo `admin`, mai al `consulente`, con nome file marcato e foglio di avviso
- [x] **CUR-04**: L'export dei lead è dato personale: si traccia chi scarica e quando

### Configuratore Pro (CFG)

- [ ] **CFG-01**: Il motore Pro risolve gli effetti `includi` / `escludi` / `fattore_quantita` / `quantita_per_unita` dallo stesso catalogo del Free
- [ ] **CFG-02**: **Nessuna sottocategoria di tipo `catalogo` contiene più di una famiglia di alternative** nello stesso computo, verificato da un test che *conta* le voci incluse per sottocategoria
- [ ] **CFG-03**: Migrazione senza perdita: `voce.livello` diventa l'asse `finitura`, le `domanda_mirata_key` diventano domande `stepper`. Nessuna riga di dato si perde
- [ ] **CFG-04**: I coefficienti quantità sono tarati **nella stessa fase** in cui si aggiungono gli assi, non dopo

### Risultato leggibile (RIS)

- [ ] **RIS-01**: `RangeBar` proporzionale ai valori reali (oggi i pallini sono fissi a 12% e 88%, quindi una stima ±10% e una ±20% appaiono ugualmente incerte)
- [ ] **RIS-02**: Incidenza €/m² per categoria e peso relativo delle categorie
- [ ] **RIS-03**: Riepilogo imponibile / IVA / extra
- [ ] **RIS-04**: Avviso di superamento del budget dichiarato, con il confronto ricalcolato a finiture inferiori

---

## Vincoli permanenti (ereditati dalla v1, non rinegoziabili)

- Mai esporre prezzo o coefficiente impresa — verificato da `test_no_leak.py` e `test_no_leak_admin.py` su ogni nuovo endpoint e schema
- Output sempre a range, mai un numero secco
- Prezzi e coefficienti in database, mai cablati nel codice (ENG-02)
- Città = selettore del listino, con fallback dichiarato
- IVA differenziata per categoria
- **D-01**: Free e Pro non riconciliano, per costruzione

## v3 / Deferred

- **Budget dichiarato**: raccolto e mostrato come tetto, ma **senza effetto sul prezzo** (due assi distinti: *finiture* muove il numero, *budget* no)
- **Parser AI** sul testo libero ("quali muri recuperare") — AI come parser, mai come stimatore
- **Progetti come contenitore** di più stime · **indirizzo e geocoding**
- **Listino da ampliare**: triplo vetro, alluminio, legno-alluminio, resina, microcemento, posa a spina o diagonale, piatto doccia a filo. Non si chiedono finché il listino non li prezza — un campo che non muove il numero promette una precisione che non c'è
- **Massimali ecobonus differenziati per intervento** (cappotto 60k, climatizzazione 30k, riqualificazione globale 100k) — oggi c'è un tetto unico a 60.000 €, corretto finché all'ecobonus arriva solo `C-SERRAMENTI`
- **Tetti di spesa dal 2028** — le righe `valido_dal 2027` sono aperte (`valido_al = NULL`) e resteranno valide anche nel 2028 con il tetto vecchio
- **Test runner lato frontend** e `tsc -b` come comando ufficiale
- **Cinque variabili `R2_*` su Render** — l'upload avatar risponde 503 finché non ci sono

## Out of Scope

- Simulazione finanziamento a rate
- Moltiplicatori prezzo per zona geografica (la città seleziona il listino, non un moltiplicatore)
- Portale completo rete professionisti
- **Matrice di prezzi per combinazione**: con gli assi richiesti sono oltre 130.000 combinazioni × 4 categorie. Il modello a effetti chiede ~50–60 numeri, ed è quello che si cura da pannello

---

## Traceability

| Requisiti | Fase |
|-----------|------|
| QST-01..04, PAR-01..03, PAR-05 | 05 — Catalogo domande + motore Free parametrico ✅ |
| WIZ-01..03 | 06 — Wizard unico ✅ |
| ARR-01..04 | 07 — Arredo |
| CUR-01..04, PAR-04 | 08 — Export/import Excel |
| QST-05, CFG-01..04, WIZ-04 | 09 — Configuratore Pro e chiusura del bug |
| RIS-01..04 | 10 — Risultato leggibile e tetto di budget |

Copertura: 27/27 requisiti v2 mappati a esattamente una fase.
