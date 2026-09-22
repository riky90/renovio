# Phase 08: Export/import Excel dal pannello admin - Context

**Gathered:** 2026-09-21
**Status:** Ready for planning

<domain>
## Phase Boundary

La curatela dei dati esce dal `dev.db` e diventa un file che l'admin scarica, modifica e
ricarica senza perdere nulla. Non e' una capability nuova per l'utente finale: e' la
precondizione di ogni taratura seria — i 52 coefficienti, `voce.livello` curato su 21 voci
su 191, i 18 forfait di arredo, le 30 attese.

**In scope:** export e re-import Excel di quattro risorse (voci/listino, catalogo domande,
parametri del motore + arredo, lead); la regola "colonna assente = campo non toccato"
estesa a tutte; la protezione del file che contiene il coefficiente impresa; la traccia di
chi scarica; l'anteprima admin della stima (solo frontend — il backend esiste gia'); e la
pagina CRUD del catalogo domande.

**Non include:** la pagina CRUD per `attesa_immobile` e `derivazione_risposta` (curabili da
Excel); l'eliminazione di righe da Excel; la taratura vera dei coefficienti, che richiede
preventivi reali o il giudizio dell'esperto di dominio e non e' lavoro di codice.

</domain>

<decisions>
## Implementation Decisions

### Formato dell'export e del round-trip
- **D-01:** Export **piatto, una riga per record**, con colonne esplicite. L'import impara a
  riconoscere questo formato dall'header; `parse_computo` resta intatto per i file del
  computo originale, che continuano a funzionare come oggi. Il formato annidato del computo
  e' proprio quello che rende la curatela impraticabile, ed e' il motivo per cui questa fase
  esiste.
- **D-02:** **Un file per risorsa**, quattro export distinti: voci/listino, catalogo domande,
  parametri del motore + arredo, lead. Ogni export ha il proprio endpoint, quindi il proprio
  permesso e la propria traccia: CUR-03 e CUR-04 restano regole su endpoint separati invece
  che permessi per-foglio dentro un workbook unico.
- **D-03:** Prima colonna **`id` tecnica, sola lettura**, usata come chiave del re-import
  quando c'e', con fallback sulla chiave naturale esistente quando manca. Serve perche' la
  chiave naturale delle voci ricade su `descrizione` (`listino_upload_service.py:82`): senza
  colonna id, correggere una descrizione in Excel produrrebbe una riga nuova e lascerebbe la
  vecchia. `effetto_opzione` non ha nessuna chiave naturale, quindi per quel foglio la
  colonna id e' l'unica identita' possibile.
- **D-04:** Una riga **senza `id` e' un record nuovo**: upsert pieno, la voce viene creata.
  L'Excel serve anche ad aggiungere, non solo a correggere — coerente con l'import attuale,
  che gia' crea sottocategorie e voci.
- **D-05:** Il catalogo domande e' gerarchico su cinque tabelle e si esporta con **un foglio
  per tabella** nello stesso file: `domande`, `opzioni`, `effetti`, `attese`, `derivazioni`.
  Nessuna denormalizzazione: un foglio unico con testo domanda ed etichetta opzione ripetuti
  renderebbe ambiguo il re-import alla prima divergenza fra righe.
- **D-06:** `derivazione_risposta` ha il suo foglio **anche se oggi non ha endpoint API**.
  E' la tabella che deduce una risposta da un'altra (la classe energetica dall'anno) e
  influenza il calcolo: oggi si cura solo dal seed, quindi l'Excel diventa l'unico modo per
  toccarla, che e' meglio di nessun modo.
- **D-07:** Le **attese** (`attesa_immobile`) stanno nel file del **catalogo domande**, non
  in quello dei parametri: `attesa_immobile.attributo_code` si lega a
  `domanda.attributo_code`, e sono i valori che precompilano le risposte.
- **D-08:** Parametri del motore + arredo, **un foglio per tabella**: `moltiplicatori`
  (tipo x categoria), `listino_categoria` (base EUR/m2 e IVA — piu' il coefficiente impresa
  solo nella variante opt-in di D-13), `extra`, `coefficienti_pro` (quantita'-per-m2),
  `forfait_arredo`. Quest'ultimo chiude il punto aperto "nessun CRUD admin su
  `forfait_arredo`", che oggi si cura solo dal seed.

### Cancellazione e protezione della curatela
- **D-09:** **Cella vuota = campo non toccato.** Per togliere un valore gia' presente serve
  un **token esplicito** nella cella. E' l'estensione naturale di CUR-02 e del guardrail
  D-24 della Fase 4: un export ricaricato dopo che Excel ha "pulito" una colonna non deve
  poter azzerare in silenzio la curatela di 191 righe. Il token va documentato nel foglio di
  istruzioni dell'export.
- **D-10:** **Le righe non si eliminano da Excel.** L'import resta additivo e aggiornante;
  l'eliminazione passa solo dal CRUD web. Lettura piu' stretta di D-24: nessun file, per
  quanto sbagliato, puo' cancellare dati.
- **D-11:** L'export porta il **timestamp di generazione**. Al re-import la preview dichiara
  riga per riga cio' che e' cambiato nel database dopo quel momento, poi l'admin decide.
  Nessun blocco duro: la preview (D-18 Fase 4) esiste apposta per far vedere cosa si sta per
  rompere.
- **D-12:** Criterio d'uscita di CUR-01/CUR-02: un **test di round-trip a vuoto** — esporta,
  ricarica il file identico, verifica che il diff sia **zero righe modificate** — in aggiunta
  a `test_upload_excel_non_azzera_livello` (`backend/tests/test_dettaglio_pro_livelli.py:261`).
  Un test che conta, non un'ispezione a occhio: il test attuale copre un campo solo e non
  direbbe niente se il round-trip perdesse `um`, `ordine` o il prezzo.

### Export sensibile e tracciamento
- **D-13:** Il `coefficiente_impresa` e' **opt-in**. Di default l'export dei parametri esce
  **senza** le colonne di margine e quindi non e' sensibile; una richiesta esplicita genera
  la variante marcata, `require_admin`, col nome file marcato e il foglio di avviso in testa
  (CUR-03). Cosi' il file che circola normalmente non contiene il segreto, e la regola #1 di
  `CLAUDE.md` non dipende da chi apre l'allegato.
- **D-14:** Il ruolo **`consulente` puo' scaricare l'export dei lead**, e il download viene
  tracciato. Ha gia' accesso alla dashboard lead dal gate staff in `dependencies/auth.py`:
  negargli il file sarebbe incoerente con cio' che gia' vede a schermo. CUR-04 esiste proprio
  per questo — il dato personale esce, quindi si sa chi lo ha preso.
- **D-15:** Tabella nuova **`export_log`**: chi, quale risorsa, quando, quante righe, e se il
  file includeva il margine. Copre **tutti e quattro** gli export, non solo i lead. Oggi
  nessuna tabella di audit esiste, quindi e' una migrazione nuova; coprire quattro costa
  quanto coprirne uno e risponde anche a "chi si e' portato via il coefficiente impresa".
  Non basta il log applicativo: su Render ruota e la domanda resterebbe senza risposta.
- **D-16:** La traccia **si vede**: lista in fondo alla dashboard lead. Chi guarda i lead
  vede anche chi se li e' portati via.

### Anteprima admin della stima (PAR-04)
- **D-17:** **Il backend esiste gia' e non va toccato.**
  `POST /admin/domande/anteprima` (`routers/admin/domande.py:496`, migrazione 0014, ENG-02)
  restituisce gia' tutto cio' che PAR-04 chiede: breakdown per categoria con `base_min/max`,
  `totale_min/max` e `delta_min/max`; la lista `effetti` con `applicato`, `contributo` e
  `nota` per ognuno; `avvisi`; `attese`; ed e' `require_admin`. La base di confronto e'
  deliberatamente `risposte=None` (layer spento), non `risposte={}`. **PAR-04 e' solo lavoro
  di frontend.**
- **D-18:** L'anteprima e' la **sesta tab di `/admin/coefficienti`**, accanto ai numeri che
  serve a verificare: mettere lo strumento di taratura vicino ai dati da tarare accorcia il
  ciclo modifica-verifica.
- **D-19:** Gira su **input sintetici compilati a mano** — esattamente la forma di
  `AnteprimaIn`: citta', mq, tipo, risposte. E' uno strumento di esplorazione: per tarare
  serve poter provare il caso limite, non solo quelli gia' capitati.
- **D-20:** La tabella effetti mostra **tutti** gli effetti, con `applicato` si'/no.
  L'effetto che **non** ha sparato e' l'informazione piu' preziosa: e' li' che si vede una
  condizione scritta male. Nasconderlo lo rende invisibile esattamente quando serve.

### Pagina CRUD del catalogo domande
- **D-21:** La pagina **entra nella Fase 08**. Decisione esplicita di Riccardo, presa dopo
  che la raccomandazione di tenerla fuori e' stata posta e discussa. **Rischio registrato:**
  e' la quinta capability di una fase che ne ha gia' quattro di export piu' l'anteprima, ed
  e' il candidato naturale a uno split. Se il plan-checker segnala che la fase eccede il
  budget di contesto, questa e' la parte da scorporare — non gli export, che sono il cuore
  del goal di fase. Chiude il chip `task_9da38ee9` e la violazione della regola #3 di
  `CLAUDE.md` (niente dato curato fuori dal pannello).
- **D-22:** Copre **domande + opzioni + effetti**: le tre entita' che si curano in un gesto
  solo. `attese` e `derivazioni` restano curabili solo da Excel (D-05, D-06) — sono tabelle
  di taratura, non di authoring.
- **D-23:** Riusa **`AdminTable` + `AdminCrudDialog` + `AdminDeleteConfirm`**, il pattern
  delle altre otto pagine admin. Nessun componente nuovo, coerenza con D-21 della Fase 4.
- **D-24:** Navigazione **master-detail annidata**: lista domande -> dettaglio della domanda
  con le sue opzioni -> effetti dentro l'opzione. Rispecchia come si ragiona ("cosa succede
  se scelgo questa risposta") e rende strutturalmente impossibile creare un effetto orfano,
  visto che `effetto_opzione` si identifica solo con un id surrogato.
- **D-25:** **Nessun delete fisico**: si disattiva con `attiva = false` (la colonna esiste
  gia' su `domanda` e su `effetto_opzione`). Le stime gia' salvate che citano quella domanda
  restano leggibili — stesso principio dello snapshot immutabile (D-09 Fase 2, D-11 Fase 4).
  Verificare chi referenzia cosa guardando dentro gli snapshot darebbe falsi negativi.

### Collocazione nel pannello
- **D-26:** I bottoni **Scarica** e **Carica** stanno in testa a **ogni pagina admin
  esistente** — `/admin/listini`, `/admin/domande`, `/admin/coefficienti`, `/admin/lead` —
  non in una sezione `/admin/dati` separata. Il file sta dove stanno i dati che contiene,
  quindi il permesso della pagina e' gia' il permesso giusto, e l'export dei lead resta
  accanto alla traccia dei download di D-16.

### Claude's Discretion
- Schema esatto di `export_log` (colonne, indici, relazione con `user`) purche' registri chi,
  cosa, quando, quante righe e se includeva il margine (D-15).
- Nomi esatti delle colonne nei fogli, forma del token di cancellazione (D-09), forma e
  collocazione del timestamp di export (D-11), testo del foglio di istruzioni e del foglio di
  avviso (D-13).
- Come l'import distingue il formato piatto nuovo dal formato del computo originale (D-01):
  header, nome foglio, o marcatore dedicato.
- Se l'upload listino esistente (`/admin/upload-listino/preview` + `/confirm`) resta dov'e'
  o viene assorbito dal nuovo percorso, purche' i file del computo originale continuino a
  funzionare.
- Layout preciso dei form della pagina domande e della tab anteprima, coerente con lo stile
  admin esistente.
- Se conviene spezzare la fase in piu' piani e in che ordine; vedi il rischio annotato in
  D-21.


### Modifiche dopo la pianificazione (2026-09-22)

- **Split: D-05, D-06, D-07 e D-21..D-25 escono da questa fase** e diventano la **Fase 08.1
  "Catalogo domande: pagina CRUD e file Excel"**. Il rischio era registrato in D-21 e si e'
  avverato: il planner ha giudicato che cinque capability non stanno in una fase a fedelta'
  piena (11-12 piani contro i 7 totali delle tre fasi precedenti). L'argomento decisivo non
  era visibile in discussione ed e' venuto dal codice: **`/admin/domande` non esiste** — ne'
  in `NAV_ITEMS` (`frontend/src/pages/admin/AdminLayout.tsx:35`) ne' fra le route
  (`frontend/src/App.tsx:37`). I bottoni Scarica/Carica del catalogo domande non hanno una
  pagina dove stare finche' la CRUD non c'e', quindi pagina e file sono accoppiati: separarli
  avrebbe prodotto un export orfano, non due fasi. Gli otto piani della Fase 08 non dipendono
  dal catalogo domande, quindi lo split e' costato zero rimaneggiamenti. D-26 resta in Fase 08
  per le tre pagine che esistono (`/admin/listini`, `/admin/coefficienti`, `/admin/lead`) e
  passa a 08.1 per `/admin/domande`.

- **Deroga a D-04 sui soli lead.** D-04 dice "riga senza `id` = record nuovo". Sul file dei
  lead non e' applicabile: `Lead.user_id` e' FK non nullable e dal file non si ricava niente
  da cui dedurla, quindi creare un lead da Excel vorrebbe dire attribuire un contatto a un
  utente arbitrario. Il planner ha pianificato **scarto descritto** — la riga senza `id`
  viene rifiutata con motivo visibile nella preview, invece di creare. Confermato da Riccardo
  il 2026-09-22: **nessun lead si crea da Excel.** D-04 resta valida sulle altre tre risorse.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Dominio e decisioni di progetto
- `CLAUDE.md` — regole di dominio non negoziabili. Le due che mordono qui: **#1** il prezzo
  e il coefficiente impresa non escono mai verso un non-admin (D-13), **#3** prezzi e
  coefficienti stanno in database e devono essere modificabili dal pannello (e' il goal
  stesso della fase).
- `.planning/ROADMAP.md` — Phase 08: goal e i cinque criteri di successo.
- `.planning/REQUIREMENTS.md` — CUR-01 (round-trip), CUR-02 (colonna assente = non toccato),
  CUR-03 (export col margine riservato ad admin), CUR-04 (export lead tracciato),
  PAR-04 (anteprima admin con gli effetti che hanno sparato).
- `.planning/PROJECT.md` — Key Decisions: utente vede solo il prezzo cliente; prezzi e
  coefficienti gestiti da pannello admin, non nel codice.
- `.planning/phases/04-lead-pannello-admin/04-CONTEXT.md` — **la piu' importante**. D-18
  (preview del diff prima di applicare), D-19 (import parziale, scarti elencati), D-20
  (solo .xlsx, require_admin, ~10MB), D-10 (l'admin e' proprietario del margine), D-21
  (struttura dell'area /admin), D-22 (anti-leak assoluto verso i non-admin), D-24 (ogni edit
  idempotente, mai distruttivo). Tutte portate avanti senza ri-discuterle.

### Codice da leggere prima di implementare
- `backend/app/services/listino_upload_service.py` — l'import esistente. `parse_computo`
  (riga 92) legge il formato del computo originale: foglio `A-EDILE` piu' i fogli catalogo
  B/C/D. `_voce_key` (riga 82) e `_sotto_key` (riga 74) definiscono la chiave naturale che
  D-03 estende con la colonna id. `apply_diff_idempotent` (riga 295) e' il punto di aggancio
  dell'upsert.
- `backend/app/routers/admin/upload_listino.py` — `POST /preview` (riga 41) e `POST /confirm`
  (riga 75): il flusso a due passi di D-18 Fase 4, da estendere invece che duplicare.
- `backend/app/routers/admin/domande.py` — `POST /anteprima` (riga 496) e' **gia' completo**
  per PAR-04; leggere il docstring, spiega perche' la base di confronto e' `risposte=None`.
  Il CRUD delle domande sotto questo router e' l'API che la pagina di D-21 deve consumare.
- `backend/app/schemas/admin_domande.py` — `AnteprimaIn`, `AnteprimaOut`,
  `AnteprimaCategoriaOut`, `EffettoTracciaOut` (righe 151-200): il contratto esatto che la
  tab anteprima deve rendere.
- `backend/app/models/domanda.py` — le cinque tabelle del catalogo: `Domanda` (PK = `code`,
  chiave naturale stringa), `OpzioneDomanda` (naturale: domanda_code + code),
  `EffettoOpzione` (**solo id surrogato**), `AttesaImmobile`, `DerivazioneRisposta`.
- `backend/app/models/listino.py` — `coefficiente_impresa` su `ListinoCategoria` (riga 38),
  `Numeric(4,3)`. E' l'unica colonna che rende un export sensibile (D-13).
- `backend/app/models/dettaglio_pro.py` — `Voce.livello` nullable (riga 28): il campo curato
  su 21 righe su 191 che tutta la regola CUR-02 esiste per proteggere.
- `backend/app/models/arredo.py` — `ForfaitArredo`, i 18 forfait oggi curabili solo dal seed.
- `backend/app/dependencies/auth.py` — `require_admin` (riga 66) e il gate staff che ammette
  anche il `consulente`; `ROLE_ADMIN` e i tre valori di `User.role`. Il gate resta
  server-side: il ruolo del client non e' mai fidato.
- `backend/app/services/effetti.py` — i sette tipi di effetto, insieme chiuso;
  `EffettoApplicato` e la distinzione fra effetti per-unita' e no. Serve per rendere la
  tabella di D-20 e per i form di D-22.
- `backend/tests/test_dettaglio_pro_livelli.py:261` — `test_upload_excel_non_azzera_livello`,
  il test che gia' copre la regola CUR-02 su un campo; D-12 lo affianca.
- `frontend/src/components/admin/AdminTable.tsx`, `AdminCrudDialog.tsx`,
  `AdminDeleteConfirm.tsx` — il pattern da riusare (D-23).
- `frontend/src/pages/admin/CoefficientiPage.tsx` — le cinque tab esistenti; l'anteprima ne
  diventa la sesta (D-18).

### Fonte dati
- `docs/computo-struttura-dettaglio.md` — struttura dei fogli del computo originale, il
  formato che `parse_computo` continua ad accettare.
- `docs/computo-base-reggio-emilia.xlsx` — il file sorgente reale.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`openpyxl`** e' gia' in `backend/pyproject.toml` e legge **e scrive**: nessuna dipendenza
  nuova per la parte export.
- **Flusso preview + confirm** gia' costruito in Fase 4 e coperto da test: l'import del
  formato piatto ci si innesta invece di aprire una seconda strada.
- **Chiave naturale e upsert idempotente** (`_voce_key`, `_sotto_key`,
  `apply_diff_idempotent`) gia' allineati a `scripts/seed.py`: D-03 aggiunge la colonna id
  sopra questa meccanica, non al posto suo.
- **`POST /admin/domande/anteprima`** completo, con lo schema di risposta gia' progettato per
  la taratura: PAR-04 e' frontend puro.
- **`AdminTable` / `AdminCrudDialog` / `AdminDeleteConfirm`** su otto pagine admin: la pagina
  domande non introduce pattern nuovi.
- **`User.role` a tre valori + `require_admin` + gate staff**: i permessi di CUR-03 e CUR-04
  si esprimono con quello che c'e' gia'.

### Established Patterns
- **Anti-leak a campi chiusi verso i non-admin** — gli schemi Pydantic non espongono
  `coefficiente_impresa` ne' `base_eur_mq`. D-13 lo porta nel mondo dei file: il default e'
  senza margine, la variante marcata e' un'eccezione esplicita e tracciata.
- **Idempotenza e non distruttivita'** (D-24 Fase 4) — vincolo bloccante su ogni percorso di
  scrittura. D-09 e D-10 sono la sua traduzione nel formato Excel.
- **Snapshot immutabile** — un edit admin non tocca le stime gia' salvate. E' la ragione di
  D-25: si disattiva, non si cancella.
- **Il test che conta invece dell'ispezione a occhio** — disciplina gia' scelta come criterio
  d'uscita della Fase 09 e applicata qui in D-12.

### Integration Points
- Nuovi endpoint `GET .../export.xlsx` su quattro router admin, piu' l'estensione del
  percorso di import al formato piatto.
- Migrazione Alembic nuova per `export_log` (D-15). Deve preservare il seed, come ogni
  migrazione di questo progetto.
- Frontend: bottoni Scarica/Carica su quattro pagine admin (D-26), la sesta tab in
  `CoefficientiPage` (D-18), la pagina domande net-new (D-21).

</code_context>

<specifics>
## Specific Ideas

- "Il file sta dove stanno i dati che contiene" — e' il criterio con cui sono state decise
  sia la separazione in quattro file (D-02) sia la collocazione dei bottoni (D-26).
- L'export di default **non** e' sensibile: il margine e' un'eccezione che si chiede, non la
  norma che si subisce (D-13).
- Un effetto che non spara vale piu' di uno che spara: la tabella dell'anteprima non filtra
  (D-20).

</specifics>

<deferred>
## Deferred Ideas

- **Pagina CRUD per `attesa_immobile` e `derivazione_risposta`** — restano curabili solo da
  Excel (D-05, D-06, D-22). Candidate a una fase futura se la curatela via file si rivela
  scomoda.
- **Eliminazione di righe da Excel** — valutata e scartata in D-10; l'eliminazione resta nel
  CRUD web.
- **Anteprima precompilata da una stima salvata** — opzione scartata in D-19 a favore dei soli
  input sintetici. Utile quando ci saranno abbastanza casi reali da riprodurre.
- **Blocco duro sul re-import di un file stale** — scartato in D-11 a favore dell'avviso in
  preview. Da riconsiderare se gli admin diventano piu' di uno.
- **Export dei lead filtrato per citta' del consulente** — non esiste oggi un legame fra
  `User.role = 'consulente'` e una citta'; sarebbe una capability nuova.

</deferred>

---

*Phase: 08-export-import-excel*
*Context gathered: 2026-09-21*
