# Phase 09: Configuratore Pro e chiusura del bug dei cataloghi - Research

**Researched:** 2026-09-25
**Domain:** Motore di calcolo parametrico (Python/SQLAlchemy), migrazione dati Alembic/SQLite, refactor di un motore esistente per farlo convergere su un catalogo dati condiviso col motore Free
**Confidence:** HIGH (codice esistente letto per intero, non ipotizzato)

## Summary

Questa fase non introduce tecnologia nuova: e' un refactor mirato di `DettaglioProService.compute()`
perche' smetta di usare il proprio meccanismo ad-hoc (`voce.livello` + `livelli_pro_json` +
`CoefficienteQuantitaVoce.domanda_mirata_key`) e usi invece lo stesso `app/services/effetti.py` /
`risolvi_scelte()` gia' scritto per il motore Free in Fase 05. Il lavoro e' quasi interamente
back-end: uno schema dati gia' pronto (`domanda`/`opzione_domanda`/`effetto_opzione`, con i quattro
tipi Pro `includi`/`escludi`/`fattore_quantita`/`quantita_per_unita` gia' validati da
`valida_effetto` dalla Fase 08.1), un formato Excel piatto gia' rotondo (`export_excel/import_excel`)
che copre esattamente le colonne che serve alla taratura, e un frontend che secondo la UI-SPEC
approvata non introduce alcun componente nuovo (solo dati diversi dietro `DomandaField` gia'
esistente).

Il punto piu' delicato non e' tecnico ma di **sequenza**: il primo deliverable della fase (D-04,
un file Excel di taratura + l'elenco preciso dei dati mancanti a Riccardo) e' un artefatto che
Claude deve produrre analizzando `docs/computo-base-reggio-emilia.xlsx` e il DB corrente, prima
di scrivere qualunque codice — e il piano deve trattarlo come un task standalone con verifica
umana bloccante, non come un side-effect di un altro task.

**Primary recommendation:** Ordinare il piano in tre fasi logiche — (1) migrazione dati additiva
+ generazione del file di taratura come primo deliverable verificabile da Riccardo, (2) refactor
del motore `DettaglioProService.compute()` per delegare a `effetti.py`/`risolvi_scelte()`, con
`CFG-02` come test-oracolo che chiude la fase, (3) pannello "Qualche dettaglio in piu'" esteso
secondo la UI-SPEC gia' approvata + collaudo dal vivo (WIZ-04). Non parallelizzare (1) e (2): il
motore nuovo legge dati che (1) deve prima popolare correttamente.

## User Constraints

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Ereditate (non si ridiscutono)**
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

**Perimetro delle domande Pro**
- **D-01:** Solo il **nucleo che chiude il bug**: (1) asse **finitura** base/medio/alto su
  B/C/D, (2) asse **tipo di pavimento** (gres / parquet / maxi lastra / mosaico) che governa
  sia le pose di A.6 sia le forniture di B, (3) i tre stepper **bagni / porte /
  condizionatori** dalla migrazione delle chiavi mirate. Il resto dell'elenco del piano
  (formato piastrelle, sanitari, doccia/vasca, miscelatori, rivestimento bagno, cucina, quali
  porte, muri, tapparelle) e' fuori fase.
- **D-02:** Il pavimento si sceglie **per casa intera, con il bagno a parte**: una scelta per
  le zone giorno/notte, mentre il bagno resta sempre gres/rivestimento. Nessuna ripartizione
  dei m² per stanza (il wizard non la raccoglie).

**Taratura dei coefficienti (CFG-04)**
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

**Dove si risponde**
- **D-06:** Le domande Pro stanno nella **pagina di dettaglio Pro**, in un pannello tipo
  "Affina la stima": ogni risposta ricalcola il computo. Il wizard non cambia. Si riusa
  `POST /me/stime/{id}/dettaglio-pro/risposte`, che gia' persiste le risposte in
  `risposte_pro_json` (schermata e PDF Pro restano allineati).
- **D-07:** Il dettaglio si vede **subito con i default gia' applicati**: ogni asse ha un'opzione
  default (es. finitura medio, pavimento gres), quindi il primo computo e' gia' senza
  alternative sommate e le risposte lo affinano.

**Curatela e collaudo**
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

### Deferred Ideas (OUT OF SCOPE)
- Domande Pro oltre il nucleo: formato piastrelle, sanitari sospesi/a terra, doccia o vasca,
  miscelatori esterni/incasso, altezza rivestimento bagno, attacchi cucina, quali porte, quali
  muri recuperare, tapparelle e cassonetti — fase successiva.
- Pavimento per singolo ambiente con ripartizione dei m² — richiede un input che il wizard non
  raccoglie.
- Forchetta di plausibilita' Pro/Free imposta da test — scartata per ora (D-05).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Descrizione | Research Support |
|----|-------------|------------------|
| QST-05 | Ogni chiave consumata dal motore Pro (`domanda_mirata_key`) ha una domanda corrispondente nel catalogo | §Architettura, §Migrazione: le tre chiavi bagni/porte/condizionatori diventano `Domanda(tipo_controllo="stepper")` con effetto `quantita_per_unita`; nessuna chiave libera resta nel motore |
| CFG-01 | Il motore Pro risolve gli effetti `includi`/`escludi`/`fattore_quantita`/`quantita_per_unita` dallo stesso catalogo del Free | §Refactor del motore: `DettaglioProService.compute()` chiama `risolvi_scelte(tier="pro")` + una nuova `risolvi_effetti_pro()` in `effetti.py`, non piu' `_voce_inclusa()`/`livelli_pro_json` |
| CFG-02 | Nessuna sottocategoria `catalogo` contiene più di una famiglia di alternative, verificato da un test che conta le voci | §Test oracolo CFG-02: pattern di test gia' presente in `test_dettaglio_pro_livelli.py`, da generalizzare a tutte le sottocategorie `catalogo` + agli assi su A.6 |
| CFG-03 | Migrazione senza perdita: `voce.livello` → asse `finitura`; `domanda_mirata_key` → domande `stepper` | §Migrazione: schema, ordine, tecnica SQLite batch-mode, backfill dei dati esistenti (21 voci gres livellate, 68 righe di effetti Free, 3 chiavi mirate) |
| CFG-04 | Coefficienti quantità tarati nella stessa fase | §Excel di taratura (D-04): riuso di `export_excel/import_excel/parametri.py` (foglio `coefficienti_pro`), gia' round-trip-safe |
| WIZ-04 | Percorso Pro del wizard esercitato dal vivo end-to-end con account Pro reale | §Collaudo: checklist manuale, nessun test automatico sostituisce D-09 |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Risoluzione domanda → opzione → effetto (finitura, pavimento, stepper) | API/Backend (`effetti.py`) | — | Gia' l'unico posto in cui una risposta diventa aritmetica; il Pro deve diventarne un secondo consumatore, non duplicare la logica |
| Filtro voci alternative per sottocategoria (chiusura del bug) | API/Backend (`dettaglio_pro.py`) | — | Puro calcolo server-side, Decimal, nessun dato di prezzo lato client |
| Taratura coefficienti quantità (CFG-04) | Database (via CRUD/export-import Excel) | API/Backend (validazione bound) | ENG-02: mai cablati nel codice; il file Excel e' solo un canale di scrittura verso `coefficiente_qta_voce` |
| Pannello "Qualche dettaglio in più" (domande Pro) | Frontend Server/Client (React) | API/Backend (`GET /me/opzioni-pro`, `GET /api/v1/domande?tier=pro`) | Le domande sono dati serviti dal catalogo, il client le disegna senza conoscerle per nome (`DomandaField`) |
| Round-trip Excel di taratura | Database/Storage (`export_excel`/`import_excel`) | API/Backend (`/admin/upload-listino`) | Canale gia' esistente e testato (CUR-01/02), non va reinventato per questa fase |
| Collaudo end-to-end Pro (WIZ-04) | Manuale (umano) | — | Nessun sostituto automatico per un giudizio di plausibilita' economica |

## Standard Stack

Nessuna libreria nuova. Stack invariato rispetto alle fasi precedenti:

### Core
| Componente | Versione | Ruolo in questa fase |
|---|---|---|
| FastAPI + SQLAlchemy 2.0 (Mapped/mapped_column) | invariato | `Domanda`/`OpzioneDomanda`/`EffettoOpzione` (models/domanda.py), `Sottocategoria`/`Voce`/`CoefficienteQuantitaVoce` (models/dettaglio_pro.py) |
| Alembic | invariato | Nuova migrazione additiva per il seed delle domande Pro + eventuale drop/keep di `voce.livello` |
| Pydantic v2 | invariato | `RisposteDomandeRequest`/`DettaglioProOut` (schemas/dettaglio_pro.py) da estendere per il nuovo asse pavimento |
| openpyxl (via `export_excel`/`import_excel`) | invariato | File di taratura D-04: riuso del foglio `coefficienti_pro` gia' esistente |
| React 19 + react-query + shadcn | invariato | `DettaglioProView.tsx`, `DomandaField.tsx`, `NumberStepper`, `OptionCard` — nessun componente nuovo per UI-SPEC |

Nessuna installazione richiesta: **Package Legitimacy Audit non applicabile** (nessun pacchetto
esterno nuovo in questa fase).

### Alternatives Considered
Nessuna: il vincolo esplicito di CONTEXT (`Ereditate: Tipi di effetto: insieme chiuso di otto...
Nessun tipo nuovo in questa fase`) chiude ogni alternativa architetturale — si tratta di
riusare `effetti.py` cosi' com'e', non di sostituirlo.

## Package Legitimacy Audit

Non applicabile: nessun pacchetto nuovo installato in questa fase (verificato leggendo
`backend/app/services/effetti.py`, `dettaglio_pro.py`, `computo_parsing.py`,
`export_excel/*`, `import_excel/*` — tutte dipendenze gia' presenti nel progetto).

## Architecture Patterns

### System Architecture Diagram

```
[Excel di taratura D-04]                    [Admin panel /admin/parametri]
   (compilato da Riccardo)                          │ upload
        │                                            ▼
        │ upload                          POST /admin/upload-listino/preview
        ▼                                  → import_excel/parametri.py
POST /admin/upload-listino/preview            (foglio "coefficienti_pro",
  → import_excel/parametri.py                  gia' esistente, D-04 lo riusa)
        │                                            │
        ▼                                            ▼
  coefficiente_qta_voce (DB)  ◄───────────────────────
        │
        │ letto da
        ▼
┌─────────────────────────────────────────────────────────────┐
│  DettaglioProService.compute(session, listino, mq, tipo,      │
│                               risposte, ...)                  │
│                                                                 │
│  1. risolvi_scelte(session, risposte, tier="pro")              │  ← STESSA funzione
│     → domande/opzioni attive per finitura/pavimento/stepper    │    del motore Free
│  2. risolvi_effetti_pro(...) [NUOVO in effetti.py]              │
│     → per ogni voce: includi/escludi/fattore_quantita/         │
│       quantita_per_unita risolti dal catalogo                  │
│  3. Filtro voci: esclusioni vincono → asse scelta_singola →    │
│     voci senza asse sempre incluse → quantita da                │
│     CoefficienteQuantitaVoce → fattore_quantita → scarta        │
│     sottocategorie vuote                                        │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
DettaglioProResult (Decimal, no coefficiente impresa)
        │
        ▼
GET/POST /me/stime/{id}/dettaglio-pro[/risposte]  (routers/dettaglio_pro.py, invariato nella forma)
        │
        ▼
DettaglioProView.tsx → pannello "Qualche dettaglio in più"
  (finitura esistente + NUOVO selettore pavimento via DomandaField
   + tre stepper migrati da Input grezzo a DomandaField/NumberStepper)
        │
        ▼
SottocategoriaAccordion (invariato, CFG-02 riduce solo il numero di voci mostrate)
```

### Recommended Project Structure

Nessuna nuova directory. File toccati (nessuno nuovo tranne la migrazione e — se necessario —
uno script di generazione del file di taratura):

```
backend/
├── alembic/versions/
│   └── 00NN_domande_pro_finitura_pavimento.py   # NUOVO: migrazione CFG-03
├── app/
│   ├── models/domanda.py                         # invariato (schema già generico)
│   ├── models/dettaglio_pro.py                   # voce.livello: mantenuta o deprecata (discrezione)
│   ├── services/effetti.py                        # ESTESO: risolvi_effetti_pro() o equivalente
│   ├── services/dettaglio_pro.py                  # RISCRITTO: compute() delega a effetti.py
│   ├── services/computo_parsing.py                 # ESTESO: coefficienti_per_voce() con bozza tarata
│   └── schemas/dettaglio_pro.py                    # ESTESO: campo pavimento in Risposte*/DettaglioProOut
├── scripts/
│   └── seed.py                                     # ESTESO: seed idempotente delle nuove Domanda/Opzione/Effetto Pro
└── tests/
    ├── test_dettaglio_pro.py                       # riscritti/estesi per il nuovo motore
    ├── test_dettaglio_pro_livelli.py                # generalizzato → test CFG-02
    └── test_effetti.py (se esiste) o nuovo           # risolvi_effetti_pro() unit test

frontend/src/
├── components/DettaglioProView.tsx                 # ESTESO secondo 09-UI-SPEC.md §A
├── components/DomandaField.tsx                      # invariato, riusato per pavimento + stepper
└── api/dettaglio-pro.ts                             # ESTESO: campo pavimento in RisposteDomande/payload
```

### Pattern 1: Un solo motore per la risoluzione domanda→effetto

**What:** `risolvi_scelte(session, risposte=risposte, tier="pro")` (già in `effetti.py`, già
usato dal Free) diventa il punto di ingresso anche per il Pro, al posto della logica ad-hoc di
`DettaglioProService._voce_inclusa()` basata su `livelli_pro_json`.

**When to use:** Ogni volta che una risposta utente deve diventare un filtro/quantita sul
computo Pro.

**Example (pattern esistente, da estendere):**
```python
# Source: backend/app/services/effetti.py (già presente, non ipotetico)
def risolvi_scelte(
    session: Session,
    *,
    risposte: dict[str, Any] | None,
    tier: str = TIER_FREE,
) -> ScelteRisolte:
    """... generalizza a TIER_PRO passando tier='pro' — la funzione è già
    parametrica sul tier, non richiede modifiche per essere chiamata dal Pro."""
```

Il lavoro nuovo è una funzione gemella di `risolvi_effetti_free()` per il ramo Pro:
```python
# Pattern da introdurre in effetti.py (non esiste ancora)
def risolvi_effetti_pro(
    session: Session,
    *,
    risposte: dict[str, Any] | None,
) -> "RisoluzionePro":
    """Traduce risposte Pro in: voci escluse, voci incluse per asse,
    fattori_quantita per voce/sottocategoria, quantita_per_unita per voce.
    Simmetrico a risolvi_effetti_free ma senza correzioni €/mq — qui il
    prodotto sono filtri e quantità, non importi."""
```

### Pattern 2: Ordine di risoluzione del filtro Pro (contratto CONTEXT, non negoziabile)

**What:** L'ordine esatto con cui le voci di una sottocategoria vengono incluse/escluse.

**Fonte:** `~/.claude/plans/il-punto-1-come-steady-comet.md` §Fase 5, ripreso identico in
`09-CONTEXT.md`.

```
1. Parti da tutte le voci del listino per quella sottocategoria.
2. Applica le ESCLUSIONI (tipo_effetto='escludi') — vincono sempre, a qualunque livello
   (categoria/sottocategoria/voce).
3. Per ogni asse a scelta singola (finitura, tipo_pavimento) che governa quella
   sottocategoria/voce, tieni SOLO le voci dell'opzione scelta o del suo default.
4. Le voci non governate da alcun asse restano SEMPRE incluse (generalizzazione della
   regola attuale `voce.livello IS NULL`).
5. Calcola la quantita': prima CoefficienteQuantitaVoce (coefficiente_qta_per_mq o
   domanda_mirata_key/default_conteggio — quest'ultimo canale sparisce con CFG-03, sostituito
   da quantita_per_unita), poi applica fattore_quantita se presente.
6. Scarta le sottocategorie rimaste vuote (comportamento attuale di `_voce_inclusa`/
   il controllo `if voce_rows and not voci: continue` già in dettaglio_pro.py).
```

Questo ordine è già implementato in forma equivalente nel codice attuale (`_voce_inclusa` +
`_quantita`), solo con un solo asse (finitura via `voce.livello`) invece di N assi generici.
Il refactor generalizza, non riscrive da zero.

### Pattern 3: Neutralità/retrocompatibilità durante la migrazione

**What:** Ogni passo della migrazione deve lasciare il motore bit-identico finché l'admin non
cura i nuovi dati — stessa disciplina già usata per `livello_finitura` (migrazione 0010) e per
il layer Free (PAR-02).

**Example (pattern già in uso, da ripetere):**
```python
# Source: backend/app/services/dettaglio_pro.py, _voce_inclusa() esistente
# "livello_scelto is None -> tutto incluso" e "voce_livello is None -> inclusa sempre"
# sono le due clausole che garantiscono la retrocompatibilità: vanno preservate
# come casi limite anche nel motore generalizzato basato su effetti.
```

### Anti-Patterns to Avoid

- **Duplicare la logica di risoluzione domanda→opzione nel Pro:** `_opzioni_scelte()`,
  `_visibili()`, `_applica_derivazioni()` sono già scritte in modo generico su `tier`. Scrivere
  un secondo percorso per il Pro invece di passare `tier="pro"` a `risolvi_scelte()` è
  esattamente l'errore che la Fase 05 (`ENG-02`) voleva evitare.
- **Introdurre un nono tipo di effetto per il pavimento o la finitura:** CONTEXT lo esclude
  esplicitamente ("Nessun tipo nuovo in questa fase"). Finitura e pavimento si modellano con
  `includi` per opzione su voce/sottocategoria — non serve altro.
- **Validare i totali Pro/Free con un test di forchetta:** D-05 lo scarta esplicitamente. Il
  solo test automatico richiesto è il conteggio delle alternative (CFG-02).
- **Trattare il file Excel di D-04 come un nuovo formato:** deve riusare
  `export_excel/import_excel/parametri.py` foglio `coefficienti_pro` (colonne
  `id, voce_id, voce_descrizione, tipo_code, coefficiente_qta_per_mq, domanda_mirata_key,
  default_conteggio`), non un formato ad-hoc. Le colonne aggiuntive per la taratura
  (`coefficiente_attuale`, `coefficiente_proposto`, `motivazione`, `decisione`, `note`) possono
  convivere nello stesso foglio: `leggi_foglio_piatto()` ignora silenziosamente ogni colonna non
  in `COLONNE_COEFF_PRO` (vedi Pitfall 3).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Risoluzione risposta→opzione (default, derivazioni, visibilità) | Un secondo resolver per il Pro | `risolvi_scelte(tier="pro")` in `effetti.py` | Già generico sul tier, già testato per il Free, evita una seconda fonte di verità |
| Formato Excel per la taratura | Un nuovo layout di colonne per il file di D-04 | Foglio `coefficienti_pro` di `export_excel/parametri.py` + colonne extra ignorate in lettura | CUR-01 (round-trip) e CUR-02 (colonna assente = non toccato) sono già garantiti da questo canale |
| Validazione dei quattro effetti Pro | Un validatore nuovo per `includi`/`escludi`/`fattore_quantita`/`quantita_per_unita` | `valida_effetto()` in `effetti.py` (già scritto in Fase 08.1) | `TARGET_AMMESSI` copre già i quattro tipi Pro con i bersagli ammessi corretti |
| Migrazione additiva con `updated_at`/`server_default=func.now()` su SQLite | `ALTER TABLE ... ADD COLUMN ... DEFAULT CURRENT_TIMESTAMP` diretto | Pattern a 3 passi (`add_column` nullable → backfill esplicito → `batch_alter_table` per NOT NULL + server_default) | SQLite rifiuta `ADD COLUMN` con default non costante — verificato dal fallimento reale della 0019, poi risolto e ripetuto identico nella 0020 |

**Key insight:** Questa fase ha un solo vero compito nuovo (generalizzare `_voce_inclusa` a N
assi arbitrari); tutto il resto — resolver domande, validazione effetti, round-trip Excel,
tecnica di migrazione SQLite — esiste già nel codice ed è stato scritto esplicitamente per
essere riusato qui (i commenti in `effetti.py` dicono letteralmente "dalla Fase 5... anche
`dettaglio_pro.py` lo importa").

## Runtime State Inventory

> Fase di migrazione dati (CFG-03): `voce.livello` → asse `finitura`; tre
> `domanda_mirata_key` → tre `Domanda` stepper. Inventario del runtime state.

| Categoria | Trovato | Azione richiesta |
|-----------|---------|-------------------|
| Dati salvati (DB) | `voce.livello`: valorizzato su 21 righe (tutte in B-FINITURE/PAVIMENTI E RIVESTIMENTI GRES, 7 base/7 medio/7 alto — misurato su `dev.db` il 2026-09-25 in CONTEXT). Le altre 6 sottocategorie `famiglia='catalogo'` hanno zero voci livellate. `coefficiente_qta_voce.domanda_mirata_key`: 78 righe `bagni`, 33 `porte`, 33 `condizionatori` — 144 righe totali senza domanda corrispondente nel catalogo. | Migrazione dati: le 21 righe con `livello` diventano opzioni dell'asse `finitura` via nuovi `EffettoOpzione(tipo_effetto='includi', target_voce_id=...)`; le 144 righe con `domanda_mirata_key` restano semanticamente sulle stesse voci ma la LETTURA della quantità migra da `coeff.domanda_mirata_key` (stringa libera) a un `EffettoOpzione(tipo_effetto='quantita_per_unita', target_voce_id=...)` legato alle tre nuove `Domanda` stepper — la colonna `domanda_mirata_key` può restare a DB per compatibilità storica (discrezione CONTEXT) ma il motore non deve più leggerla. |
| Config di servizi esterni live | Nessuna — il progetto non ha servizi esterni con configurazione fuori da git in questo dominio (verificato: nessuna menzione di n8n/Datadog/Tailscale/Cloudflare nel codice di questa fase). | Nessuna |
| Stato registrato a livello OS | Nessuno — nessun task scheduler, pm2, launchd/systemd coinvolto da questa fase (fase puramente applicativa/DB). | Nessuna |
| Secret/env var | Nessuno — questa fase non tocca configurazione, credenziali o env var. | Nessuna |
| Build artifact / pacchetti installati | Nessuno — nessuna dipendenza nuova, nessuno script di build da rigenerare. | Nessuna |

**Nota aggiuntiva (non del template ma rilevante):** `A-EDILE` (famiglia `gerarchica`) NON ha
`voce.livello` — le sue alternative (A.6.1 gres, A.6.2 parquet, A.6.5 maxi lastra, A.6.6
mosaico) oggi non hanno NESSUN meccanismo di esclusione: sono voci gerarchiche indipendenti
sommate sempre. La migrazione deve introdurre ex-novo gli `EffettoOpzione(tipo_effetto='includi')`
per collegarle all'asse `tipo_pavimento`, non solo migrare dati esistenti — è lavoro di
*creazione* di dati (curatela D-08), non di puro spostamento.

## Common Pitfalls

### Pitfall 1: SQLite rifiuta `ADD COLUMN ... DEFAULT CURRENT_TIMESTAMP`
**What goes wrong:** Una migrazione additiva con `server_default=func.now()` fallisce con
`Cannot add a column with non-constant default` — è esattamente il motivo per cui la migrazione
0019 di questo progetto ha dovuto essere riscritta.
**Why it happens:** SQLite ammette default non costanti solo dentro un `CREATE TABLE`, non in
`ALTER TABLE ADD COLUMN`.
**How to avoid:** Usare il pattern a 3 passi già stabilito nel progetto (0019, ripetuto in
0020): `add_column` nullable senza default → `UPDATE` esplicito di backfill → `batch_alter_table`
per stringere a NOT NULL + installare `server_default`. Per default COSTANTI (es. `attiva=1`) non
serve batch mode — `add_column` diretto basta (vedi 0020).
**Warning signs:** Qualunque nuova colonna con `nullable=False` + `server_default=func.now()` o
altra espressione non letterale sulle tabelle `domanda`/`opzione_domanda`/`effetto_opzione`.

### Pitfall 2: Doppio meccanismo di filtro coesistente a metà migrazione
**What goes wrong:** Se il refactor di `DettaglioProService.compute()` non è atomico rispetto
alla migrazione dati, si rischia una finestra in cui `voce.livello`/`livelli_pro_json` E il
nuovo sistema a effetti sono entrambi "vivi" ma disallineati — es. una voce esclusa dal vecchio
filtro per livello ma non ancora coperta da un `EffettoOpzione` equivalente, quindi inclusa due
volte o zero volte.
**Why it happens:** `_voce_inclusa()` e il futuro `risolvi_effetti_pro()` sono due fonti di
verità se convivono anche solo temporaneamente in produzione (dev.db locale, ma comunque).
**How to avoid:** Sequenziare la fase come (a) migrazione dati completa e verificata → (b) swap
del motore in un colpo solo (stesso commit/task) → mai un periodo con entrambi i meccanismi
attivi contemporaneamente su dati reali.
**Warning signs:** Un piano che propone di "migrare i dati" e "riscrivere compute()" come due
task indipendenti eseguibili in ordine qualsiasi.

### Pitfall 3: Colonne extra nel file di taratura che rompono l'ordine di apply
**What goes wrong:** Aggiungere `coefficiente_attuale`/`coefficiente_proposto`/`motivazione`/
`decisione`/`note` al foglio `coefficienti_pro` sembra richiedere di toccare
`COLONNE_COEFF_PRO` in `import_excel/parametri.py` — se lo si fa per errore, quelle colonne
diventano scrivibili a DB (`coefficiente_attuale` non esiste come colonna del modello →
`AttributeError` o scrittura silenziosa persa).
**Why it happens:** `leggi_foglio_piatto()` filtra le colonne SOLO contro `colonne_ammesse`
passato dal chiamante — è un parametro esplicito, non dedotto dallo schema del foglio.
**How to avoid:** Il file di D-04 aggiunge le colonne extra al foglio SENZA toccare
`COLONNE_COEFF_PRO` in `import_excel/parametri.py`: `leggi_foglio_piatto` le ignorerà
automaticamente in lettura (comportamento già documentato: "un admin che aggiunge una colonna
di appunti non deve far fallire l'import"). La colonna che l'admin userà per scrivere il valore
vero resta `coefficiente_qta_per_mq` (o `domanda_mirata_key`/`default_conteggio`, ma queste due
ultime probabilmente si svuotano con `#CANCELLA#` una volta migrate su `quantita_per_unita`).
**Warning signs:** Un piano che propone di estendere `COLONNE_COEFF_PRO` o il modello
`CoefficienteQuantitaVoce` con colonne di lavorazione (`motivazione`, `decisione`).

### Pitfall 4: `computo_parsing.py` è condiviso tra script dev e upload runtime admin
**What goes wrong:** `coefficienti_per_voce()` (in `computo_parsing.py`) è chiamata sia da
`scripts/extract_dettaglio_pro.py` (one-off, Fase 03) sia da `listino_upload_service.py`
(upload runtime admin, Fase 04/ADM-01). Cambiare la formula bozza `0.6 × TIPO_FACTOR` cambia
il comportamento di ENTRAMBI i percorsi, incluso il caricamento di un nuovo computo Excel da
pannello.
**Why it happens:** Il modulo è deliberatamente condiviso (vedi sua docstring), e non c'è modo
di distinguere "voce nuova caricata da admin dopo questa fase" da "voce del seed originale"
se non tramite la logica di `coefficienti_per_voce()` stessa.
**How to avoid:** Il refactor di CFG-04 deve decidere esplicitamente se la nuova formula
tarata (D-03) sostituisce la bozza `0.6 × TIPO_FACTOR` DENTRO `coefficienti_per_voce()` (cioè
diventa la bozza di default per ogni futuro upload) oppure se la taratura vive SOLO nei dati
esistenti (via il file Excel di D-04, applicata come UPDATE una tantum) lasciando
`coefficienti_per_voce()` come fallback bozza per voci future non ancora curate. CONTEXT non
lo specifica esplicitamente — è materia per la discussione in fase di planning, non lasciata
all'esecutore.
**Warning signs:** Un piano che tocca `coefficiente_qta_voce` via UPDATE diretto senza toccare
`computo_parsing.py`, o viceversa, senza una decisione esplicita su quale dei due (o entrambi)
è in scope.

### Pitfall 5: `_get_owned_stima` — 403 su stime Free storiche, non 404
**What goes wrong:** Testare il flusso Pro end-to-end (WIZ-04) con l'account Pro esistente,
ma su una stima creata quando l'account non era ancora Pro, produce un 403 legittimo
("Questa stima e' stata creata con il piano Free..."), non un bug.
**Why it happens:** `stima.tier` è congelato al momento del salvataggio, indipendente
dall'abbonamento corrente (vedi docstring di `routers/dettaglio_pro.py`).
**How to avoid:** Il collaudo D-09 deve creare/usare una stima salvata DOPO l'attivazione Pro,
non riusare una stima vecchia.
**Warning signs:** Un checklist di collaudo che non specifica esplicitamente "crea una nuova
stima da Pro" come primo passo.

## Code Examples

### Filtro attuale da generalizzare (punto di partenza esatto del refactor)
```python
# Source: backend/app/services/dettaglio_pro.py (letto per intero in questa ricerca)
@staticmethod
def _voce_inclusa(
    voce_livello: str | None, livello_selezionabile: bool, livello_scelto: str | None
) -> bool:
    if not livello_selezionabile:
        return True
    if livello_scelto is None:
        return True
    if voce_livello is None:
        return True
    return voce_livello == livello_scelto
```
Questa funzione, con un solo asse hardcoded (`livello`), è ciò che `risolvi_effetti_pro()` deve
sostituire con una versione che itera su N assi (finitura, tipo_pavimento) risolti dal catalogo.

### Pattern di risoluzione già generico sul tier (riusabile identico)
```python
# Source: backend/app/services/effetti.py
def risolvi_scelte(
    session: Session,
    *,
    risposte: dict[str, Any] | None,
    tier: str = TIER_FREE,
) -> ScelteRisolte:
    ...
    domande = (
        session.query(Domanda)
        .filter(Domanda.attiva.is_(True), Domanda.tier_minimo == tier)
        .order_by(Domanda.ordine, Domanda.code)
        .all()
    )
```

### Formato Excel già round-trip-safe per la taratura (D-04)
```python
# Source: backend/app/services/export_excel/parametri.py
COLONNE_COEFF_PRO = [
    "id", "voce_id", "voce_descrizione", "tipo_code",
    "coefficiente_qta_per_mq", "domanda_mirata_key", "default_conteggio",
]
```
```python
# Source: backend/app/services/import_excel/parametri.py
COLONNE_COEFF_PRO = {"id", "voce_id", "tipo_code", "coefficiente_qta_per_mq", "domanda_mirata_key", "default_conteggio"}
_CAMPI_NULLABLE_PER_FOGLIO[FOGLIO_COEFF_PRO] = {"coefficiente_qta_per_mq", "domanda_mirata_key", "default_conteggio"}
```

### Migrazione SQLite-safe (pattern da ripetere per CFG-03)
```python
# Source: backend/alembic/versions/0020_attiva_updated_at_catalogo.py
# Default costante -> add_column diretto, nessun batch mode necessario:
op.add_column(tabella, sa.Column("attiva", sa.Boolean(), nullable=False, server_default="1"))

# Default non costante (func.now()) -> 3 passi:
op.add_column(tabella, sa.Column("updated_at", sa.DateTime(), nullable=True))
op.execute(sa.text(f"UPDATE {tabella} SET updated_at = :adesso").bindparams(adesso=adesso))
with op.batch_alter_table(tabella) as batch:
    batch.alter_column("updated_at", existing_type=sa.DateTime(), nullable=False, server_default=sa.func.now())
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `voce.livello` (colonna String, un asse solo) come filtro di alternative Pro | Asse `finitura` come `Domanda`/`OpzioneDomanda`/`EffettoOpzione`, N assi possibili | Questa fase (CFG-03) | Aggiungere un asse futuro (es. formato piastrelle) torna lavoro da pannello admin |
| `coefficiente_qta_voce.domanda_mirata_key` (stringa libera, tre chiavi hardcoded in 3 file scollegati) | `EffettoOpzione(tipo_effetto='quantita_per_unita')` legato a una `Domanda` reale | Questa fase (QST-05/CFG-03) | Chiude il disallineamento fra `computo_parsing.py`, `schemas/dettaglio_pro.py` e `DettaglioProView.tsx` |
| `_voce_inclusa()` con un solo filtro binario | `risolvi_effetti_pro()` con esclusioni + N assi a scelta singola | Questa fase (CFG-01) | Il motore Pro converge sulla stessa infrastruttura del Free, un solo posto in cui una risposta diventa aritmetica |
| `computo_parsing.py`: `0.6 × TIPO_FACTOR` uniforme su ogni voce a mq | Coefficiente motivato per voce (D-03), proposto da Claude e validato da Riccardo | Questa fase (CFG-04) | Precisione reale invece che apparente — dichiarato esplicitamente come rischio se fatto DOPO invece che insieme (D-03/rischio dichiarato del piano) |

**Deprecated/outdated:**
- `RisposteDomandeRequest.bagni/porte/condizionatori` come campi Pydantic dedicati: con QST-05
  chiuso, il canale corretto per queste tre risposte diventa lo stesso meccanismo generico delle
  altre domande Pro (`risposte: dict[str, Any]` risolto da `risolvi_scelte`). Se lo schema
  Pydantic resta a campi dedicati per compatibilità con `DettaglioProView.tsx` attuale, va
  documentato come scelta deliberata di questa fase (impatta anche il payload
  `POST .../risposte`), non lasciato ambiguo.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Le voci di A.6 (A.6.1/A.6.2/A.6.5/A.6.6) sono le uniche alternative su A-EDILE da coprire con l'asse `tipo_pavimento`; non esistono altre famiglie di alternative gerarchiche in A-EDILE. | Runtime State Inventory, Pattern 2 | Se esistono altre sottocategorie A.n con pose alternative non taggate, CFG-02 (nessun asse su A.6 include più di un'opzione) potrebbe non coprire tutto il bug dichiarato nel rischio della fase — verificabile con una query sul seed reale prima di scrivere il piano. |
| A2 | Il refactor di `RisposteDomandeRequest`/`DettaglioProOut` (aggiunta del campo pavimento) non rompe la parità PDF/schermata già garantita da `_compute_dettaglio()`, perché quel meccanismo è generico rispetto ai campi trasportati. | Pattern 3, State of the Art | Se lo schema Pydantic Pro resta a campi dedicati invece di migrare a `dict[str, Any]` generico, serve comunque un campo `tipo_pavimento` esplicito coordinato tra backend/frontend/PDF template — rischio limitato, ma da verificare contro `pdf_service.py::render_pro`/`pdf_stima_pro.html` non letti in questa ricerca. |
| A3 | Il file di taratura Excel (D-04) può essere generato analizzando `docs/computo-base-reggio-emilia.xlsx` + lo stato attuale di `coefficiente_qta_voce` senza bisogno di dati che Riccardo non ha già fornito nel computo originale, salvo le eccezioni esplicitamente richieste (es. numero medio di bagni per fascia mq, già in `attesa_immobile`). | User Constraints §D-04 | Se la proposta di coefficienti richiede dati di dominio che non sono deducibili né dal computo né da `attesa_immobile` (es. superfici tipiche per singola voce), l'elenco "dati richiesti a Riccardo" del deliverable D-04 potrebbe essere più lungo del previsto — questo è comunque il meccanismo con cui D-04 lo gestisce (l'elenco preciso è parte del deliverable), quindi il rischio è di scope del task, non di fattibilità. |

## Open Questions

1. **`voce.livello` e `coefficiente_qta_voce.domanda_mirata_key`: colonna mantenuta o dismessa?**
   - What we know: CONTEXT lascia questa scelta a discrezione di Claude, purché nessun dato si
     perda.
   - What's unclear: se il piano deve includere un task esplicito di `DROP COLUMN` (con relativa
     migrazione reversibile) o se le colonne restano a DB come vestigia non lette dal motore.
   - Recommendation: mantenerle nella migrazione di questa fase (nessun DROP), documentarle come
     "storiche, non più lette dal motore" — riduce il rischio della migrazione SQLite (Pitfall 1)
     e rispetta alla lettera "nessuna riga di dato si perde" senza introdurre un secondo tipo di
     migrazione distruttiva nella stessa fase. Un DROP successivo, se voluto, è a costo quasi
     zero in una fase futura.

2. **`RisposteDomandeRequest` a campi dedicati vs. `dict[str, Any]` generico.**
   - What we know: il resto del catalogo (Free, wizard) usa già `risposte: dict[str, Any]`
     generico risolto da `risolvi_scelte()`. Il Pro oggi ha uno schema Pydantic a 3 campi fissi
     più `livelli: dict[str, str]`.
   - What's unclear: se QST-05/CFG-01 richiedono di generalizzare anche lo schema del payload
     HTTP (rompendo la forma attuale di `DettaglioProView.tsx`/`api/dettaglio-pro.ts`) o se è
     sufficiente che il MOTORE legga dal catalogo mentre l'API resta a campi dedicati per ora
     (il pavimento aggiunto come quarto campo esplicito).
   - Recommendation: la UI-SPEC approvata (09-UI-SPEC.md §A.1) implica che il pannello migra a
     `DomandaField` generico anche nel frontend — questo suggerisce che generalizzare anche lo
     schema Pydantic è la strada coerente con lo spirito della fase, ma è una decisione di design
     dell'API che il planner deve fissare esplicitamente in un task, non lasciare implicita.

3. **`pdf_service.py::render_pro` e `pdf_stima_pro.html` — impatto del nuovo asse pavimento.**
   - What we know: `_compute_dettaglio()` è il punto di calcolo condiviso da GET JSON e PDF, quindi
     il nuovo asse pavimento si propaga automaticamente al PDF via `DettaglioProResult`.
   - What's unclear: se il template PDF ha un riferimento hardcoded a `livelli`/`FIELD_LABELS`
     che va esteso per mostrare anche il pavimento scelto (parallelo al "Riepilogo collassato"
     lato UI-SPEC).
   - Recommendation: il planner deve includere un task di verifica/estensione di
     `pdf_stima_pro.html` — questa ricerca non ha letto quel file (fuori budget), va verificato
     in fase di planning o nel primo task di implementazione.

## Environment Availability

Non applicabile: fase puramente codice/DB/migrazione, nessuna dipendenza esterna nuova.
Ambiente già verificato nelle fasi precedenti: `backend/.venv` con tutte le dipendenze,
`backend/dev.db` a `0020 (head)`, `docs/computo-base-reggio-emilia.xlsx` presente in `docs/`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend/.venv/Scripts/python.exe -m pytest) |
| Config file | `backend/pytest.ini` o `pyproject.toml` (pattern esistente, non verificato in dettaglio in questa ricerca — invariato dalle fasi precedenti) |
| Quick run command | `backend/.venv/Scripts/python.exe -m pytest tests/test_dettaglio_pro.py tests/test_dettaglio_pro_livelli.py tests/test_dettaglio_pro_paywall.py tests/test_admin_dettaglio_pro.py tests/test_seed_dettaglio.py -x` |
| Full suite command | `backend/.venv/Scripts/python.exe -m pytest` (CLAUDE.md: ~11 minuti) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QST-05 | Nessuna `domanda_mirata_key` orfana: ogni chiave ha una `Domanda` corrispondente | unit | `pytest tests/test_seed_dettaglio.py -x` (da estendere) | ✅ esiste, da estendere |
| CFG-01 | `DettaglioProService.compute()` chiama `risolvi_scelte`/`risolvi_effetti_pro`, non più `_voce_inclusa`/`livelli_pro_json` | unit + guard statico (grep) | nuovo test in `test_dettaglio_pro.py` | ❌ Wave 0 — nuovo test |
| CFG-02 | Nessuna sottocategoria `catalogo` (né asse su A.6) include più di una famiglia di alternative | integration | pattern già presente in `test_dettaglio_pro_livelli.py`, da generalizzare a TUTTE le sottocategorie catalogo + A.6 | ⚠️ esiste ma copre solo GRES, da estendere — Wave 0 |
| CFG-03 | Migrazione upgrade→downgrade→upgrade pulita, nessun dato perso (21 righe livello, 144 righe domanda_mirata_key ancora leggibili anche se non più usate) | integration (migration test) | nuovo test in `tests/test_migrations.py` o equivalente (pattern: verificato in sessioni precedenti "0014 provata upgrade -> downgrade -> upgrade") | ❌ Wave 0 — nuovo test |
| CFG-04 | Coefficienti tarati applicati correttamente (round-trip Excel D-04) | integration | `pytest tests/test_admin_dettaglio_pro.py -x` (da estendere per il foglio esteso) | ✅ esiste, da estendere |
| WIZ-04 | Percorso Pro end-to-end | manual-only | checklist umana (D-09), nessun comando automatico | n/a — manuale per costruzione |

### Sampling Rate
- **Per task commit:** subset mirato sopra (`test_dettaglio_pro*.py` + `test_seed_dettaglio.py` + `test_admin_dettaglio_pro.py`)
- **Per wave merge:** `backend/.venv/Scripts/python.exe -m pytest` (suite completa, ~11 min)
- **Phase gate:** Full suite green prima di `/gsd:verify-work`, più il collaudo umano WIZ-04

### Wave 0 Gaps
- [ ] Generalizzare `test_dettaglio_pro_livelli.py` (o un nuovo `test_dettaglio_pro_alternative.py`) per contare le voci incluse su TUTTE le sottocategorie `famiglia='catalogo'` + sull'asse pavimento di A.6 — copre CFG-02 letteralmente ("verificato da un test che conta le voci incluse per sottocategoria")
- [ ] Nuovo test di migrazione upgrade/downgrade/upgrade per la migrazione CFG-03, seguendo il pattern già usato per 0014 (citato in STATE.md) e 0019/0020 (batch mode)
- [ ] Guard statico (grep o test dedicato) che verifichi che `dettaglio_pro.py` non legga più `voce.livello`/`livelli_pro_json`/`domanda_mirata_key` direttamente — analogo a `test_service_non_importa_il_motore_free` già citato nel piano sorgente

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applica | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | no (invariato) | `require_pro` già in essere, nessuna modifica |
| V3 Session Management | no (invariato) | cookie httpOnly già in essere |
| V4 Access Control | sì (invariato) | `_get_owned_stima` (ownership + tier check, già presente) — nessuna modifica di questa fase |
| V5 Input Validation | sì | `RisposteDomandeRequest`/estensione per pavimento: bound espliciti (`Field(ge=..., le=...)`), stesso pattern già in uso; se lo schema migra a `dict[str, Any]` generico (Open Question 2), va preservata la validazione dei bound numerici — il Free lo fa già validando contro il catalogo, non contro un range hardcoded |
| V6 Cryptography | no | nessun dato crittografico coinvolto |

### Known Threat Patterns per questo stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| Leak del coefficiente impresa tramite un nuovo campo dimenticato nello schema di risposta | Information Disclosure | `test_no_leak.py`/`test_no_leak_admin.py` esistenti — devono coprire anche i nuovi campi di `DettaglioProOut` (pavimento, eventuali nuovi assi); nessuna colonna di margine esiste su `Voce`/`Domanda`/`OpzioneDomanda`/`EffettoOpzione` per costruzione (D-10), quindi il rischio è strutturalmente basso ma va comunque riverificato dal test anti-leak ricorsivo |
| IDOR su `stima_id` nel nuovo payload risposte | Tampering | `_get_owned_stima` (id + user_id) già in essere, nessuna modifica necessaria |
| Import Excel malformato che scrive coefficienti fuori bound | Tampering | `import_excel/parametri.py::_risolvi_coeff_pro` già valida `>= 0` su `coefficiente_qta_per_mq`/`default_conteggio`; se si introduce un nuovo canale di scrittura per gli effetti Pro delle nuove domande, va applicato lo stesso pattern di validazione (`valida_effetto` già copre i quattro tipi Pro) |

## Sources

### Primary (HIGH confidence — codice del progetto, letto per intero in questa sessione)
- `backend/app/services/effetti.py` — vocabolario chiuso degli otto tipi di effetto, `risolvi_scelte()`, `risolvi_effetti_free()`, `valida_effetto()`
- `backend/app/services/dettaglio_pro.py` — `DettaglioProService.compute()`, `_voce_inclusa()`, `_quantita()` (stato pre-refactor)
- `backend/app/services/computo_parsing.py` — `coefficienti_per_voce()`, `TIPO_FACTOR`, `DOMANDA_MIRATA_KEYWORDS`
- `backend/app/models/domanda.py`, `backend/app/models/dettaglio_pro.py` — schema catalogo domande e schema computo Pro
- `backend/app/routers/dettaglio_pro.py`, `backend/app/schemas/dettaglio_pro.py` — endpoint e DTO attuali
- `backend/app/services/export_excel/parametri.py`, `backend/app/services/import_excel/parametri.py`, `backend/app/services/import_excel/flat.py` — formato Excel round-trip riusabile per D-04
- `backend/alembic/versions/0010_livello_finitura.py`, `0019_updated_at_curatela.py`, `0020_attiva_updated_at_catalogo.py` — tecnica di migrazione SQLite-safe, incluso il fallimento reale e la sua correzione (0019)
- `backend/tests/test_dettaglio_pro_livelli.py` — pattern di test esistente per il bug delle alternative
- `frontend/src/components/DettaglioProView.tsx`, `frontend/src/components/DomandaField.tsx`, `frontend/src/api/domande.ts`, `frontend/src/api/dettaglio-pro.ts` — stato attuale del frontend, punto di partenza per la UI-SPEC
- `.planning/phases/09-configuratore-pro/09-CONTEXT.md`, `.planning/phases/09-configuratore-pro/09-UI-SPEC.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md` — decisioni utente e stato di progetto
- `~/.claude/plans/il-punto-1-come-steady-comet.md` §Fase 5 — piano architetturale sorgente, ordine di risoluzione e criterio d'uscita

### Secondary (MEDIUM confidence)
Nessuna fonte esterna consultata: questa fase è interamente un refactor di codice esistente,
non richiede ricerca di libreria/framework esterno.

### Tertiary (LOW confidence)
Nessuna.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — nessuna libreria nuova, tutto verificato leggendo il codice
- Architettura: HIGH — il pattern di refactor (generalizzare `_voce_inclusa` via `effetti.py`) è
  esplicitamente previsto dai commenti del codice stesso ("dalla Fase 5... anche
  `dettaglio_pro.py` lo importa") e dal piano sorgente
- Pitfalls: HIGH per la parte migrazione SQLite (basata su un fallimento reale già avvenuto nel
  progetto, 0019); MEDIUM per gli Open Questions (schema Pydantic, PDF template) dove la
  ricerca non ha potuto leggere ogni file per vincoli di budget

**Research date:** 2026-09-25
**Valid until:** 30 giorni (dominio stabile — nessuna dipendenza esterna con release cadence)
