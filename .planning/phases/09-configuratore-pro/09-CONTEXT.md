# Phase 09: Configuratore Pro e chiusura del bug dei cataloghi - Context

**Gathered:** 2026-09-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Il motore Pro (`DettaglioProService.compute()`) smette di sommare voci alternative: legge gli
effetti Pro (`includi` / `escludi` / `fattore_quantita` / `quantita_per_unita`) dallo stesso
catalogo domande del Free, gli assi di scelta diventano dati curabili dal pannello, e i
coefficienti quantità vengono tarati nella stessa fase. Requisiti: QST-05, CFG-01..04, WIZ-04.

Stato misurato su `backend/dev.db` il 2026-09-25, da cui parte la fase:
- `voce.livello` e' valorizzato solo su 21 voci, tutte in `B-FINITURE / PAVIMENTI E RIVESTIMENTI
  GRES` (7 base, 7 medio, 7 alto). Le altre sette sottocategorie `famiglia='catalogo'`
  (PAVIMENTI, PAVIMENTI PARQUET, BATTISCOPA, MATERIALI DI POSA, RUBINETTERIE, PORTE, PRODOTTI)
  hanno zero voci con livello, quindi il motore le somma tutte.
- In `A.6 PAVIMENTI E RIVESTIMENTI` (A-EDILE, `gerarchica`) le pose alternative A.6.1 (gres),
  A.6.2 (parquet), A.6.5 (maxi lastra), A.6.6 (mosaico) si sommano.
- Nessuna domanda ha `tier_minimo='pro'`; a database esistono solo effetti Free (68 righe).
- `coefficiente_qta_voce.domanda_mirata_key` usa tre chiavi (`bagni` 78 righe, `porte` 33,
  `condizionatori` 33) senza una domanda corrispondente nel catalogo (QST-05).
- `computo_parsing.py` assegna `0.6 × TIPO_FACTOR` a ogni voce a m² e `0.15 × TIPO_FACTOR` a
  ogni voce a ml (TIPO_FACTOR leggera 0.4 / moderata 0.7 / totale 1.0).

</domain>

<decisions>
## Implementation Decisions

### Ereditate (non si ridiscutono)
- Ordine di risoluzione del motore Pro, dal piano sorgente: si parte da tutte le voci → le
  **esclusioni** vincono sempre → per ogni asse a scelta singola restano solo le voci
  dell'opzione scelta o del suo default → le voci non governate da alcun asse restano
  **sempre incluse** (generalizza la regola `livello IS NULL`) → quantità dalla catena
  `CoefficienteQuantitaVoce` esistente → `fattore_quantita` → si scartano le sottocategorie
  rimaste vuote.
- Migrazione senza perdita: `voce.livello` diventa l'asse `finitura` (opzioni base/medio/alto);
  le tre `domanda_mirata_key` diventano tre `Domanda` `stepper` con effetto `quantita_per_unita`.
- La linea Free/Pro non si sposta; output sempre a range; nessun coefficiente impresa nel
  catalogo, nei coefficienti quantità o nell'Excel di taratura; D-41: il seed non riscrive la
  curatela esistente.
- Tipi di effetto: insieme chiuso di otto, validati da `valida_effetto` (Fase 08.1). Nessun
  tipo nuovo in questa fase.

### Perimetro delle domande Pro
- **D-01:** Solo il **nucleo che chiude il bug**: (1) asse **finitura** base/medio/alto su
  B/C/D, (2) asse **tipo di pavimento** (gres / parquet / maxi lastra / mosaico) che governa
  sia le pose di A.6 sia le forniture di B, (3) i tre stepper **bagni / porte /
  condizionatori** dalla migrazione delle chiavi mirate. Il resto dell'elenco del piano
  (formato piastrelle, sanitari, doccia/vasca, miscelatori, rivestimento bagno, cucina, quali
  porte, muri, tapparelle) e' fuori fase.
- **D-02:** Il pavimento si sceglie **per casa intera, con il bagno a parte**: una scelta per
  le zone giorno/notte, mentre il bagno resta sempre gres/rivestimento. Nessuna ripartizione
  dei m² per stanza (il wizard non la raccoglie).

### Taratura dei coefficienti (CFG-04)
- **D-03:** Bozza ragionata di Claude, validata da Riccardo con checklist. Per ogni voce Claude
  propone un coefficiente motivato da UM e descrizione (es. pavimento come quota dei m²
  calpestabili, rivestimenti per numero di bagni), invece del `0.6 × TIPO_FACTOR` uniforme.
- **D-04:** **Primo deliverable della fase: un file Excel di taratura gia' impostato da
  Claude**, con per ogni voce: codice, descrizione, UM, prezzo cliente, tipo di
  ristrutturazione, coefficiente attuale, coefficiente proposto, motivazione, e colonne vuote
  per la decisione di Riccardo e le sue note. Insieme al file, Claude consegna l'**elenco
  preciso dei dati che gli servono** da Riccardo (quello che non si deduce dal computo), cosi'
  che lui possa compilare in modo mirato. Il file deve essere ricaricabile dal pannello nel
  formato piatto esistente (cella vuota = non toccato, `#CANCELLA#` per svuotare) o, se serve,
  con un foglio di revisione separato che un piano converte.
- **D-05:** Validazione automatica: **solo il test che conta le alternative** (CFG-02: nessuna
  sottocategoria catalogo, e nessun asse su A.6, include piu' di un'opzione nello stesso
  computo). Nessuna forchetta Pro/Free imposta da test; la plausibilita' dei totali la giudica
  Riccardo dal collaudo.

### Dove si risponde
- **D-06:** Le domande Pro stanno nella **pagina di dettaglio Pro**, in un pannello tipo
  "Affina la stima": ogni risposta ricalcola il computo. Il wizard non cambia. Si riusa
  `POST /me/stime/{id}/dettaglio-pro/risposte`, che gia' persiste le risposte in
  `risposte_pro_json` (schermata e PDF Pro restano allineati).
- **D-07:** Il dettaglio si vede **subito con i default gia' applicati**: ogni asse ha un'opzione
  default (es. finitura medio, pavimento gres), quindi il primo computo e' gia' senza
  alternative sommate e le risposte lo affinano.

### Curatela e collaudo
- **D-08:** L'assegnazione delle voci agli assi (quale voce e' base/medio/alto, quale posa e
  quale fornitura vanno con quale pavimento) la **propone Claude**, con una colonna
  "motivo", nello stesso Excel di D-04; Riccardo approva o corregge con checklist.
- **D-09:** Collaudo dal vivo (WIZ-04) con **l'account Pro che Riccardo ha gia'**, in locale,
  guidato da una checklist spuntabile con note (regola permanente del 2026-09-25).

### Claude's Discretion
- Forma tecnica degli assi (domanda `scelta_singola` Pro con effetti `includi` per opzione, o
  equivalente) e ordine delle migrazioni.
- Come il pannello "Affina la stima" riusa i componenti del wizard (`NumberStepper`,
  OptionCard) e come mostra i default.
- Cosa fare di `voce.livello` dopo la migrazione (colonna mantenuta per compatibilita' o
  dismessa), purche' nessun dato si perda.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Fase e requisiti
- `.planning/ROADMAP.md` §"Phase 09" — goal, success criteria, rischio dichiarato
- `.planning/REQUIREMENTS.md` — QST-05, CFG-01..04, WIZ-04
- `~/.claude/plans/il-punto-1-come-steady-comet.md` §"Fase 5 — Configuratore Pro e chiusura del bug" — ordine di risoluzione e criterio d'uscita (la "Fase 5" del piano e' la 09 qui)

### Decisioni delle fasi precedenti
- `.planning/phases/08.1-catalogo-domande-pagina-crud-e-file-excel/08.1-CONTEXT.md` — D-27..D-41: disattivare invece di cancellare, guardia D-28, effetti Pro gia' validati, seed che non riscrive la curatela
- `.planning/phases/08-export-import-excel/08-CONTEXT.md` — D-01..D-26: formato piatto dell'Excel, cella vuota, `#CANCELLA#`, staleness

### Codice da cui si parte
- `backend/app/services/effetti.py` — gli otto tipi, `TARGET_AMMESSI`, ordine di risoluzione Free
- `backend/app/services/dettaglio_pro.py` — motore Pro, `_voce_inclusa`, filtro per livello
- `backend/app/services/computo_parsing.py` — coefficienti bozza da sostituire
- `backend/app/models/domanda.py`, `backend/app/models/dettaglio_pro.py` — schema catalogo e computo
- `backend/app/routers/dettaglio_pro.py` — endpoint GET dettaglio e POST risposte
- `docs/seed-dettaglio-pro.json`, `docs/computo-base-reggio-emilia.xlsx` — sorgente delle voci

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `valida_effetto` / `TARGET_AMMESSI` (effetti.py): validano gia' i quattro effetti Pro.
- `risolvi_scelte()`: default, derivazioni e visibilita' gia' risolti prima degli effetti; il
  Pro deve passare dalla stessa funzione.
- Export/import Excel (`services/export_excel/`, `services/import_excel/`): formato piatto,
  diff in anteprima, guardia di staleness; base per il file di taratura.
- `NumberStepper`, OptionCard del wizard; `DettaglioProView` condiviso da home, pagina
  dedicata e "Le mie stime".

### Established Patterns
- Regole di dominio come dati in tabella, mai `if` sul codice di una domanda (ENG-02).
- Oracolo Free protetto: Reggio Emilia, 85 m², tipo totale = 47.985–70.575 €. La fase tocca
  solo il Pro, l'oracolo non deve muoversi.
- `DettaglioProService` e' Decimal puro e non importa il motore Free (D-01: Free e Pro non
  riconciliano).

### Integration Points
- `DettaglioProService.compute()` riceve le risposte Pro e il catalogo.
- `GET /api/v1/domande` serve il catalogo filtrato per tier.
- Pagina `/dettaglio-pro` e `DettaglioProView` per il pannello "Affina la stima".

</code_context>

<specifics>
## Specific Ideas

- Riccardo vuole sapere **in anticipo e con precisione quali dati servono** per la taratura,
  e riceverli come file Excel gia' impostato da compilare, non come domande sparse.
- Ogni verifica manuale della fase va consegnata come checklist spuntabile con note.

</specifics>

<deferred>
## Deferred Ideas

- Domande Pro oltre il nucleo: formato piastrelle, sanitari sospesi/a terra, doccia o vasca,
  miscelatori esterni/incasso, altezza rivestimento bagno, attacchi cucina, quali porte, quali
  muri recuperare, tapparelle e cassonetti — fase successiva.
- Pavimento per singolo ambiente con ripartizione dei m² — richiede un input che il wizard non
  raccoglie.
- Forchetta di plausibilita' Pro/Free imposta da test — scartata per ora (D-05).

</deferred>
