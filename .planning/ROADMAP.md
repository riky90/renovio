# Roadmap — ristruttura-stima

**Milestone attiva:** v2.0 — *domande e motore parametrico* · **Granularity:** coarse · 6 fasi (05–10) · 27 requisiti v2 mappati (100%)

La v1 risponde a `(città, mq, tipo)`. La v2 risponde a *com'è fatta questa casa e cosa vuoi
farci* — e lo fa senza che aggiungere una domanda costi un deploy: il catalogo di domande, le
opzioni e i loro effetti sono dati amministrabili, non codice.

**Regola di numerazione GSD:** le fasi non ripartono da 01 a ogni milestone. La v1 ha usato
01–04, la v2 usa **05–10**.

<details>
<summary><strong>✅ Milestone v1.0 — MVP (fasi 01–04, 30 piani) — SHIPPED 2026-09-09</strong></summary>

Dal computo Excel di Reggio Emilia a una stima self-service a range: quattro categorie, IVA
differenziata, extra, account con Google, PDF brandizzato Free e Pro, lead al professionista,
pannello admin completo. In produzione dal 2026-09-09 (backend su Render, frontend su Vercel).

| Fase | Nome | Piani | Requisiti |
|------|------|-------|-----------|
| 01 | Stima Free end-to-end | 4/4 | EST-01..06, ENG-01..03 |
| 02 | Account & PDF | 9/9 | AUTH-01..04, PDF-01 |
| 03 | Pro & dettaglio sottocategorie | 6/6 | PRO-01..03, PDF-02 |
| 04 | Lead & pannello admin | 11/11 | LEAD-01..03, ADM-01..04 |

Dettaglio completo, decisioni chiave e debito tecnico ereditato:
[`.planning/milestones/v1.0-ROADMAP.md`](milestones/v1.0-ROADMAP.md).
Requisiti archiviati: [`.planning/milestones/v1.0-REQUIREMENTS.md`](milestones/v1.0-REQUIREMENTS.md).

</details>

---

### Phase 05: Catalogo domande + motore Free parametrico

**Status:** ✅ Complete (2026-09-21) — commit `5ea305b`. Eseguita **fuori dal ciclo GSD**, ricostruita qui in retrospettiva: vedi `05-RETRO-SUMMARY.md`.
**Goal:** Un solo catalogo di domande in database alimenta il motore Free, che applica moltiplicatori, €/m² additivi e correzioni per scostamento — restando bit-identico alla v1 quando nessuno risponde.
**Mode:** mvp
**UI hint:** no
**Requirements:** QST-01, QST-02, QST-03, QST-04, PAR-01, PAR-02, PAR-03, PAR-05
**Success Criteria:**

1. Le tabelle `domanda` / `opzione_domanda` / `effetto_opzione` / `attesa_immobile` esistono e sono seminate (migrazione `0014`)
2. `tipo_effetto` è un insieme chiuso di sette valori, risolti da `services/effetti.py` — nessun `if` di business nel motore
3. Senza risposte, o con risposte pari agli attesi, l'oracolo primario non si muove: 85 m² · totale · RE → 47.985–70.575 €
4. Una correzione per scostamento sposta **solo** la categoria bersagliata e solo della differenza dall'atteso
5. Nessun coefficiente impresa entra nel nuovo layer

**Plans:** eseguita fuori GSD, in un solo blocco.

- [x] 05-RETRO — Catalogo domande in database e motore Free parametrico (`5ea305b`)

### Phase 06: Wizard unico, domande servite dal DB

**Status:** ✅ Complete (2026-09-21) — commit `1f2a8b8`. Eseguita **fuori dal ciclo GSD**, ricostruita qui in retrospettiva: vedi `06-RETRO-SUMMARY.md`.
**Goal:** Un solo wizard a 4 step per Free e Pro, con le domande e i default serviti dal database: aggiungere una domanda torna a essere lavoro da pannello admin.
**Mode:** mvp
**UI hint:** yes
**Requirements:** WIZ-01, WIZ-02, WIZ-03
**Success Criteria:**

1. `GET /api/v1/domande?tier=&mq=` serve catalogo, opzioni e default già risolti per la fascia di m²
2. Il payload **non** contiene gli effetti, verificato sul JSON serializzato
3. `EstimateForm` ed `EstimateFormPro` collassano in `EstimateWizard` (1 · Dove — 2 · L'immobile — 3 · La ristrutturazione — 4 · Le finiture)
4. `NumberStepper` sostituisce gli input numerici grezzi
5. I default derivano dai m², mai zero, e lo step 2 è saltabile

**Plans:** eseguita fuori GSD, in un solo blocco.

- [x] 06-RETRO — Domande servite dal DB e wizard unico Free/Pro (`1f2a8b8`)

### Phase 07: Arredo

**Status:** ✅ Complete (2026-09-21) — 1/1 piano, `07-01-SUMMARY.md`. Verificata dal vivo: totale lavori invariato, arredo accanto e non dentro. **Non ancora committata.**
**Goal:** L'utente dice quali ambienti vuole arredare e riceve un forfait arredo a range, esposto **accanto** al totale lavori e mai dentro — e da lì il Bonus Mobili diventa accendibile.
**Mode:** mvp
**UI hint:** yes
**Requirements:** ARR-01, ARR-02, ARR-03, ARR-04
**Success Criteria:**

1. Esiste la categoria `E-ARREDO` e la colonna `categoria.nel_totale_lavori` la esclude dal totale lavori come **dato**, non come costante nel codice
2. Il forfait Free viene da una tabella `(ambiente, livello) → eur_min, eur_max`, guidata dalla multiselect "ambienti da arredare"
3. `StimaResponse.arredo` è fratello di `totale`: `None` quando non richiesto (mai zeri), con disclaimer *dentro* il payload, così finisce nello snapshot e nel PDF
4. **L'oracolo non si muove**: `totale` resta il totale lavori, la riconciliazione Σ categorie + extra = totale resta esatta
5. `bonus_fiscale.mobili` si può accendere dal pannello admin senza deploy

### Phase 08: Export/import Excel dal pannello admin

**Status:** ⏳ NEXT
**Goal:** La curatela dei dati esce dal `dev.db` e diventa un file che l'admin scarica, modifica e ricarica senza perdere nulla — prerequisito di ogni taratura seria.
**Mode:** mvp
**UI hint:** yes
**Requirements:** CUR-01, CUR-02, CUR-03, CUR-04, PAR-04
**Success Criteria:**

1. **Round-trip**: il file uscito da `GET /admin/{risorsa}/export.xlsx` si ricarica da `POST /admin/upload-listino/preview` senza riformattarlo
2. Colonna assente nel file = campo non toccato (la regola che protegge `voce.livello`, già coperta da `test_upload_excel_non_azzera_livello`)
3. L'export che contiene il coefficiente impresa è scaricabile solo dal ruolo `admin`, con nome file marcato e foglio di avviso in testa
4. L'export dei lead traccia chi scarica e quando
5. L'anteprima admin della stima mostra il breakdown e **quali effetti hanno sparato**

**Plans:** 8/8 plans complete

Plans:
**Wave 1**

- [x] 08-01-PLAN.md — Fondazione export + "Scarica listino" tracciato (tabella `export_log`, shell del workbook, client blob)
- [x] 08-02-PLAN.md — Tab Anteprima della stima, sesta tab di /admin/coefficienti (PAR-04, solo frontend)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 08-03-PLAN.md — Ricarica listino: formato piatto, chiave per id, round-trip a zero
- [x] 08-04-PLAN.md — Scarica parametri del motore, con il margine come variante opt-in (CUR-03)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 08-05-PLAN.md — Export lead tracciato + log dei download in fondo alla dashboard (CUR-04)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 08-06-PLAN.md — Ricarica parametri: endpoint di import generico per risorsa

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 08-07-PLAN.md — Ricarica lead, limitata ai campi di lavorazione

**Wave 6** *(blocked on Wave 5 completion)*

- [x] 08-08-PLAN.md — `updated_at` sulla curatela e avviso "cambiata dopo l'export" (D-11)

**Non pianificato in questa fase — in attesa di decisione:** il gruppo *catalogo domande*
(pagina CRUD D-21..D-25 + export/import dei cinque fogli D-05/D-06/D-07). Vedi la
raccomandazione di split in `.planning/phases/08-export-import-excel/08-CONTEXT.md` D-21.

### Phase 08.1: Catalogo domande: pagina CRUD e file Excel

**Status:** pending
**Goal:** Il catalogo delle domande smette di essere curabile solo dal seed: prende una pagina nel pannello e un file Excel, così che chi tara le domande non debba passare da un deploy.
**Mode:** mvp
**UI hint:** yes
**Requirements:** CUR-01, CUR-02
**Depends on:** Phase 08
**Split from:** Phase 08, il 2026-09-22. Il rischio era già registrato in `08-CONTEXT.md` D-21; il planner ha confermato che cinque capability non stanno in una fase a fedeltà piena. L'argomento decisivo è emerso dal codice e non dalla discussione: **`/admin/domande` non esiste** — né in `NAV_ITEMS` (`frontend/src/pages/admin/AdminLayout.tsx:35`) né fra le route (`frontend/src/App.tsx:37`). I bottoni Scarica/Carica di D-26 per il catalogo non hanno una pagina dove stare finché la CRUD non c'è, quindi pagina e file sono accoppiati e formano una sotto-fase coerente invece di una pagina scorporata e un export orfano.
**Success Criteria:**

1. `/admin/domande` esiste come route e voce di `NAV_ITEMS`, e cura **domande + opzioni + effetti** in navigazione master-detail annidata (D-21..D-24)
2. Nessun delete fisico: si disattiva con `attiva = false`, e le stime già salvate che citano la domanda restano leggibili (D-25)
3. Il file del catalogo esporta **cinque fogli** — `domande`, `opzioni`, `effetti`, `attese`, `derivazioni` — e si ricarica in round-trip a diff zero, stesso criterio di D-12 (D-05, D-06, D-07)
4. `derivazione_risposta` diventa curabile senza toccare il seed: è la tabella che deduce la classe energetica dall'anno e oggi non ha né endpoint né pagina (D-06)
5. La toolbar Scarica/Carica di D-26 è in testa alla pagina nuova, come sulle altre quattro

**Nota:** il backend CRUD di domande/opzioni/effetti **esiste già per intero** (`backend/app/routers/admin/domande.py:144-413`). La fase è in gran parte frontend più una voce nel registro export/import costruito in Fase 08. Chiude il chip `task_9da38ee9` e la violazione della regola #3 di `CLAUDE.md`.

**Plans:** 2/6 plans executed

Plans:
**Wave 1**

- [x] 08.1-01-PLAN.md — Disattivare invece di cancellare: migrazione 0020 (`attiva` su opzioni e attese, `updated_at` sul catalogo), niente DELETE, guardia D-28, opzione implicita degli stepper, filtri nel motore, seed che non riscrive piu' la curatela
- [x] 08.1-02-PLAN.md — Pagina /admin/domande, livello domande: nav, route, form a tre sezioni, toggle Attiva, `detail` del backend propagato al client

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 08.1-03-PLAN.md — Scarica catalogo domande: file a cinque fogli tracciato in `export_log`, bersaglio leggibile degli effetti
- [ ] 08.1-04-PLAN.md — Livello opzioni: tabella, form con immagine, toggle con il rifiuto D-28 nel toast

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 08.1-05-PLAN.md — Carica catalogo domande: handler `domande` nel registro di import, round-trip a zero che conta, D-28 anche da file
- [ ] 08.1-06-PLAN.md — Livello effetti: otto tipi, bersaglio a cascata, stepper senza livello opzioni

### Phase 09: Configuratore Pro e chiusura del bug dei cataloghi

**Status:** pending
**Goal:** Il motore Pro smette di sommare voci alternative: gli assi di scelta diventano dati, e i coefficienti quantità vengono tarati nella stessa fase in cui si aggiunge risoluzione.
**Mode:** mvp
**UI hint:** yes
**Requirements:** QST-05, CFG-01, CFG-02, CFG-03, CFG-04, WIZ-04
**Success Criteria:**

1. `DettaglioProService.compute()` risolve `includi` / `escludi` / `fattore_quantita` / `quantita_per_unita` dallo stesso catalogo del Free
2. **Nessuna sottocategoria di tipo `catalogo` contiene più di una famiglia di alternative**, verificato da un test che *conta* le voci incluse per sottocategoria — non da un'ispezione a occhio
3. Migrazione senza perdita: `voce.livello` → asse `finitura`; le tre `domanda_mirata_key` → domande `stepper` con `quantita_per_unita`
4. `computo_parsing.py` non assegna più lo stesso `0,6 × TIPO_FACTOR` a tutte le voci a m²
5. Il percorso Pro del wizard è esercitato dal vivo end-to-end con un account Pro reale

**Rischio dichiarato:** fino alla chiusura di questa fase il dettaglio Pro resta **gonfiato al
rialzo** su A-EDILE, B-FINITURE (tranne il gres), C-SERRAMENTI e D-PRODOTTI. È una scelta
consapevole, non una dimenticanza.

### Phase 10: Risultato leggibile e tetto di budget

**Status:** pending
**Goal:** Il numero smette di essere un numero: si legge da dove viene, quanto pesa ogni categoria, quanto è davvero incerto — e cosa fare se supera il budget dichiarato.
**Mode:** mvp
**UI hint:** yes
**Requirements:** RIS-01, RIS-02, RIS-03, RIS-04
**Success Criteria:**

1. `RangeBar` è proporzionale ai valori reali (oggi i pallini sono fissi a 12% e 88%)
2. Ogni `CategoryCard` mostra l'incidenza €/m² e il peso relativo della categoria
3. Il riepilogo espone imponibile, IVA ed extra
4. Superato il budget dichiarato, compare un avviso con il confronto ricalcolato a finiture inferiori
5. Il budget **non** muove il prezzo: due assi distinti, *finiture* sì e *budget* no

---

## Dopo la v2

Invariate dal piano precedente e non ancora schedulate: progetti come contenitore di più
stime · indirizzo e geocoding · AI come **parser** del testo libero, mai come stimatore ·
igiene (test runner frontend, `tsc -b` ufficiale).

**Storage avatar — chiuso fuori piano (2026-09-21).** Le cinque `R2_*` non sono mai state
configurate e l'upload avatar rispondeva 503 in produzione dal deploy. Aprire un bucket R2
richiede una carta di credito anche sul piano gratuito, quindi `services/storage_service.py`
ha ora **due backend**: R2 se le cinque variabili ci sono, la tabella `avatar_blob`
(migrazione `0016`) altrimenti, servita da `GET /api/v1/media/{key}`. Il router non è
cambiato; quale backend sia attivo si legge da `GET /health/db` → `"storage"`. In produzione
va impostata **una** variabile, `BACKEND_PUBLIC_URL`.

---

## Traceability

| Requisito | Fase |
|-----------|------|
| QST-01..04 | 05 |
| PAR-01..03, PAR-05 | 05 |
| WIZ-01..03 | 06 |
| ARR-01..04 | 07 |
| CUR-01..04, PAR-04 | 08 |
| CUR-01..02 (catalogo domande) | 08.1 |
| QST-05, CFG-01..04, WIZ-04 | 09 |
| RIS-01..04 | 10 |

Tutti i 27 requisiti v2 sono mappati a esattamente una fase.
