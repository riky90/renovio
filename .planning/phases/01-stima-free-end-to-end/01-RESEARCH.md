# Phase 1: Stima Free end-to-end — Research

**Researched:** 2026-08-24
**Domain:** Server-side parametric cost estimator (full-stack web app: FastAPI + React + PostgreSQL)
**Confidence:** HIGH (stack + architecture verified; seed model already fixed by user)

## Summary

Questa fase costruisce end-to-end un estimatore parametrico anonimo: da `(città, mq, tipo)` a una stima Free a range con 4 categorie, IVA differenziata ed extra. Non c'è auth, non c'è persistenza utente, non ci sono voci di dettaglio: il valore centrale (la stima) deve arrivare intero e affidabile. Il vincolo architetturale dominante è che **il calcolo avviene interamente server-side** e **il coefficiente/prezzo impresa non lascia mai il backend** — questo dirige sia il contratto API sia la scelta di quali campi i modelli Pydantic di risposta possono serializzare.

Lo stack raccomandato è quello già in uso dall'utente e ottimale per il caso: **FastAPI 0.141 + SQLAlchemy 2.0 + Alembic** sul backend Python, **React 19 + Vite + TypeScript** sul frontend, **PostgreSQL 16** come DB (deploy Railway). Il dato monetario si tratta con **`Decimal` / `Numeric`, mai `float`**. L'autocomplete città usa un **dataset ISTAT comuni bundlato in locale** (nessuna API esterna, nessun problema privacy): la città seleziona solo il listino, con fallback su Reggio Emilia + disclaimer.

Il data model deve nascere già multi-listino, multi-referente ed estensibile a sotto-voci (Fase 3), pur essendo esercitato in Fase 1 solo con il seed RE. Il seed proviene da `docs/seed-coefficienti-base.json` (già pronto, machine-readable) tramite uno script di seed idempotente.

**Primary recommendation:** FastAPI + SQLAlchemy 2.0 (Numeric/Decimal per la valuta) + PostgreSQL; calcolo in un `EstimationService` server-side; contratto API `POST /api/v1/stima` che restituisce **solo** range aggregati per categoria + totale + breakdown IVA + flag fallback, **senza mai** basi €/m², moltiplicatori o coefficiente impresa; autocomplete comuni da dataset ISTAT bundlato; seed idempotente dal JSON esistente.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Calcolo stima (€/m² × molt. × mq, range, IVA, extra) | API / Backend | — | Il coefficiente impresa è margine interno: il calcolo DEVE stare dove il segreto non esce (D-11, EST-05). |
| Lettura prezzi/coefficienti | Database | API | ENG-02: prezzi in DB, mai nel codice. |
| Mappatura città → listino + fallback | API / Backend | Database | La logica di fallback (D-07) è una decisione di dominio, non presentabile al client. |
| Autocomplete comuni | Browser / Client | API opzionale | Dataset statico ISTAT bundlato: matching puro UI, nessun prezzo coinvolto. |
| Validazione input (mq, tipo, città) | API / Backend | Browser | Difesa server-side (ASVS V5); il client valida solo per UX. |
| Presentazione 4 card + totale + disclaimer | Browser / Client | — | Rendering puro di dati già calcolati e sanitizzati dal server. |
| Seed listino RE | Database | Backend (script) | ENG-03: bozza coefficienti dal file computo. |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.13.14 | Runtime backend | Installato in locale [VERIFIED: `python --version`]; allineato ai progetti FastAPI dell'utente. |
| FastAPI | 0.141.1 | Framework API | Standard de-facto per API Python tipizzate; validazione via Pydantic integrata; usato dall'utente [VERIFIED: PyPI]. |
| Pydantic | 2.13.4 | Schemi request/response, validazione | Il gate perfetto per "non serializzare l'impresa": i response model dichiarano solo i campi ammessi [VERIFIED: PyPI]. |
| pydantic-settings | 2.15.0 | Config da env (DB URL, CORS) | Pattern standard 12-factor per FastAPI [VERIFIED: PyPI]. |
| SQLAlchemy | 2.0.52 | ORM / data layer | ORM Python di riferimento; `Numeric`→`Decimal` nativo per la valuta; astrae SQLite/Postgres [VERIFIED: PyPI]. |
| Alembic | 1.19.1 | Migrazioni schema | Compagno canonico di SQLAlchemy; le migrazioni versionano lo schema che Fase 4 estenderà [VERIFIED: PyPI]. |
| psycopg | 3.3.4 | Driver PostgreSQL | Driver Postgres moderno (v3), consigliato per SQLAlchemy 2.0 [VERIFIED: PyPI]. Installare come `psycopg[binary]` su Railway. |
| uvicorn | 0.52.4 | ASGI server | Server ASGI standard per FastAPI [VERIFIED: PyPI]. |
| PostgreSQL | 16.x | Database relazionale | Relazionale richiesto da "prezzi in DB"; addon nativo Railway; `NUMERIC` esatto per valuta [CITED: railway.app docs]. |

### Frontend
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 19.2.8 | UI | Coerente con gli altri progetti dell'utente [VERIFIED: npm]. |
| Vite | 8.2.2 | Build/dev server | Toolchain frontend dell'utente; dev server veloce [VERIFIED: npm]. |
| TypeScript | 5.9.x | Tipizzazione | Il contratto API tipizzato previene drift client/server. **Nota:** npm `typescript@7.0.2` è il canale next/preview — usare la linea **5.9 stabile** per produzione [VERIFIED: npm; versione 7 è preview]. |
| @tanstack/react-query | 5.102.2 | Data fetching/stato server | Gestione idiomatica della chiamata `POST /stima` (loading/error/cache) [VERIFIED: npm]. |
| Tailwind CSS | 4.3.3 | Styling | Rapido per le 4 card + totale; coerente con UI hint [VERIFIED: npm]. Opzionale ma raccomandato. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| slowapi | 0.1.10 | Rate limiting | Anti-scraping del modello di prezzo sull'endpoint pubblico `/stima` [VERIFIED: PyPI]. Consigliato (ASVS). |
| python-slugify | 8.0.4 | Normalizzazione nomi comune | Match robusto città (accenti/maiuscole) verso il listino [VERIFIED: PyPI]. |
| pytest | 9.1.1 | Test backend | Test unitari del motore di calcolo (i valori di plausibilità nel seed sono già oracoli) [VERIFIED: PyPI]. |
| comuni-json (dataset) | snapshot | Elenco comuni ISTAT+CAP bundlato | Autocomplete offline (7.904 comuni) [CITED: github.com/matteocontrini/comuni-json]. Vedi sezione "City input UX". |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PostgreSQL | SQLite (locale) | SQLite ok per dev, ma su Railway conviene Postgres da subito per evitare sorprese di dialetto e per il multi-utente futuro. SQLAlchemy `Numeric` funziona su entrambi; **evitare divergenze test/prod** usando Postgres anche in CI. |
| SQLAlchemy ORM | SQLModel | SQLModel unisce Pydantic+SQLAlchemy ma è più giovane e nasconde controllo sui campi; per il vincolo "non esporre impresa" preferisco **schemi Pydantic espliciti separati** dalle entità ORM. |
| psycopg3 | asyncpg | asyncpg è più veloce ma richiede motore async ovunque; per il carico di Fase 1 psycopg3 (sync o async) è più semplice e compatibile con Alembic. |
| Dataset bundlato | API Google Places/comuni esterna | API esterna introduce dipendenza di rete, costi e privacy (invio testo utente a terzi). Dataset statico = zero dipendenze runtime. |

**Installation (backend):**
```bash
uv add "fastapi==0.141.1" "uvicorn[standard]==0.52.4" "sqlalchemy==2.0.52" \
       "alembic==1.19.1" "psycopg[binary]==3.3.4" "pydantic==2.13.4" \
       "pydantic-settings==2.15.0" "slowapi==0.1.10" "python-slugify==8.0.4"
uv add --dev "pytest==9.1.1"
```
(`uv` 0.9.25 è installato in locale [VERIFIED: `uv --version`]. In alternativa `pip install`.)

**Installation (frontend):**
```bash
npm create vite@latest frontend -- --template react-ts
npm install @tanstack/react-query@5 tailwindcss@4
```

## Package Legitimacy Audit

> slopcheck 0.6.1 è stato installato ma **non ha potuto verificare**: (1) usa di default il registry npm anche per pacchetti Python, e (2) il proxy SSL aziendale (self-signed cert nella catena) blocca le sue chiamate a `registry.npmjs.org`. Verifica eseguita manualmente sui registry corretti via `pip index versions` (PyPI) e `npm view` (npm), che passano attraverso il cert aziendale.

| Package | Registry | Verifica | slopcheck | Disposition |
|---------|----------|----------|-----------|-------------|
| fastapi | PyPI | 0.141.1 esiste | degraded (SSL) | Approved — pacchetto canonico |
| sqlalchemy | PyPI | 2.0.52 esiste | degraded | Approved — pacchetto canonico |
| alembic | PyPI | 1.19.1 esiste | degraded | Approved — pacchetto canonico |
| pydantic | PyPI | 2.13.4 esiste | degraded | Approved — pacchetto canonico |
| pydantic-settings | PyPI | 2.15.0 esiste | degraded | Approved |
| psycopg | PyPI | 3.3.4 esiste | degraded | Approved — pacchetto canonico |
| uvicorn | PyPI | 0.52.4 esiste | degraded | Approved — pacchetto canonico |
| slowapi | PyPI | 0.1.10 esiste | degraded | Approved (supporting) |
| python-slugify | PyPI | 8.0.4 esiste | degraded | Approved (supporting) |
| react / react-dom | npm | 19.2.8 esiste | n/a | Approved — canonico |
| vite | npm | 8.2.2 esiste | n/a | Approved — canonico |
| @tanstack/react-query | npm | 5.102.2 esiste | n/a | Approved — canonico |
| typescript | npm | usare 5.9 stabile (7.0.2 = preview) | n/a | Approved con vincolo di versione |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged [SUS]:** none — tutti pacchetti a downloads elevatissimi e provenienza nota (documentazione ufficiale). **Nota per il planner:** poiché slopcheck non ha potuto girare, valgono comunque come pacchetti canonici verificati manualmente su PyPI/npm; non serve checkpoint umano su questi nomi notissimi, ma se il planner vuole massima cautela può aggiungere un singolo `checkpoint:human-verify` prima del primo `uv add`.

## Architecture Patterns

### System Architecture Diagram

```
[Browser / React]
   |  utente digita: città (autocomplete da JSON comuni bundlato), mq, tipo
   |  --- POST /api/v1/stima  { citta, mq, tipo }  (JSON) --->
   v
[FastAPI router]  -- valida input (Pydantic StimaRequest: mq>0, tipo enum, città str)
   |
   v
[EstimationService]  (server-side, SEGRETO qui dentro)
   |   1. risolve città -> listino (slug match) | non trovato -> listino default RE, fallback=True
   |   2. carica da DB: base €/m² per categoria, moltiplicatori[tipo], range_pct[tipo],
   |                    iva[categoria], extra, (coeff. impresa = caricato ma NON usato per il cliente)
   |   3. per categoria: imponibile = base*molt*mq; min/max = imponibile*(1∓range_pct)
   |   4. iva_categoria = imponibile * iva_pct  (per categoria, NON sul totale)
   |   5. extra (fissi) sommati; totale = Σ(categorie con IVA) + Σ(extra con IVA)
   |   6. arrotonda SOLO i valori finali (Decimal ROUND_HALF_UP)
   v
[DB PostgreSQL]  listino, listino_categoria (base+coeff impresa), categoria(iva),
                 tipo_ristrutturazione(range_pct), moltiplicatore, extra, comune_listino_map, referente
   |
   v
[StimaResponse Pydantic]  -- serializza SOLO: categorie[{code,nome,imponibile_min/max,iva_pct,iva_min/max,totale_min/max}],
   |                          extra[], totale{}, fallback:bool, disclaimer:str|null, valuta
   |   (NESSUN campo base_eur_mq / moltiplicatore / coeff_impresa nel modello di risposta)
   v
[Browser / React]  <--- render: riepilogo input + 4 card categoria (range) + totale IVA incl. in evidenza + disclaimer + CTA soft-wall
```

### Recommended Project Structure
```
ristruttura-stima/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, rate limit, router include
│   │   ├── config.py            # pydantic-settings (DATABASE_URL, CORS_ORIGINS)
│   │   ├── db.py                # engine, SessionLocal, Base
│   │   ├── models/              # entità SQLAlchemy (listino, categoria, ...)
│   │   ├── schemas/             # Pydantic StimaRequest / StimaResponse (gate anti-leak)
│   │   ├── services/
│   │   │   └── estimation.py    # EstimationService: TUTTA la matematica, server-side
│   │   ├── routers/
│   │   │   └── stima.py         # POST /api/v1/stima
│   │   └── data/
│   │       └── comuni.json      # dataset ISTAT bundlato (servito via GET /comuni)
│   ├── alembic/                 # migrazioni
│   ├── scripts/seed.py          # seed idempotente da docs/seed-coefficienti-base.json
│   └── tests/test_estimation.py # oracoli dalla tabella di plausibilità del seed
└── frontend/
    ├── src/
    │   ├── api/stima.ts         # tipi TS del contratto + fetch
    │   ├── components/{CityAutocomplete,EstimateForm,CategoryCard,TotalCard}.tsx
    │   └── pages/EstimatePage.tsx
    └── ...
```

### Pattern 1: Response schema come gate anti-leak (SQLAlchemy 2.0 + Pydantic)
**What:** Le entità ORM contengono `coefficiente_impresa` e `base_eur_mq`; i modelli Pydantic di risposta NON hanno quei campi. Il service costruisce esplicitamente il DTO di output, non fa mai `Response.model_validate(orm_row)` su entità che contengono il segreto.
**When to use:** Ogni endpoint che tocca dati di prezzo.
```python
# Source: pattern SQLAlchemy 2.0 typed + Pydantic v2 [CITED: docs.sqlalchemy.org/en/20/orm, docs.pydantic.dev/2/]
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Numeric

class ListinoCategoria(Base):                    # ENTITÀ: contiene il segreto
    __tablename__ = "listino_categoria"
    base_eur_mq: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    coefficiente_impresa: Mapped[Decimal] = mapped_column(Numeric(4, 3))  # MAI serializzato

class CategoriaOut(BaseModel):                    # RISPOSTA: nessun campo segreto
    code: str
    nome: str
    imponibile_min: Decimal
    imponibile_max: Decimal
    iva_pct: Decimal
    iva_min: Decimal
    iva_max: Decimal
    totale_min: Decimal
    totale_max: Decimal
```

### Pattern 2: Calcolo in Decimal, arrotondamento solo in uscita
```python
# Source: docs.python.org/3/library/decimal [CITED]
from decimal import Decimal, ROUND_HALF_UP
def eur(x: Decimal) -> Decimal:
    return x.quantize(Decimal("1"), rounding=ROUND_HALF_UP)   # euro interi in output

imponibile = base_eur_mq * moltiplicatore * Decimal(mq)       # tutto Decimal
imp_min = imponibile * (Decimal(1) - range_pct)
imp_max = imponibile * (Decimal(1) + range_pct)
iva_min = imp_min * iva_pct                                    # IVA PER CATEGORIA
totale_min = imp_min + iva_min
# quantize SOLO alla fine, sui campi che vanno in risposta
```

### Pattern 3: Risoluzione città → listino con fallback
```python
# slug match robusto ad accenti/maiuscole
from slugify import slugify
def resolve_listino(session, citta: str) -> tuple[Listino, bool]:
    row = session.query(ComuneListino).filter_by(comune_slug=slugify(citta)).one_or_none()
    if row:
        return row.listino, False                 # listino proprio
    default = session.query(Listino).filter_by(is_default=True).one()   # Reggio Emilia
    return default, True                          # fallback=True -> disclaimer
```

### Anti-Patterns to Avoid
- **`float` per la valuta:** errori di arrotondamento cumulativi. Usa `Decimal`/`Numeric(12,2)`.
- **`Response.model_validate(orm_entity)` su entità con il segreto:** rischia di serializzare `coefficiente_impresa`. Costruisci il DTO a mano nel service.
- **IVA sul totale invece che per categoria:** EST-03 impone aliquote diverse per categoria; l'IVA va calcolata su ciascun imponibile di categoria e poi sommata.
- **Esporre base €/m² o moltiplicatori nel JSON:** anche senza il coefficiente impresa, esporre la formula permette di reverse-engineerare i margini. Restituisci solo range aggregati.
- **Calcolo lato client:** violerebbe D-11/EST-05. Il client riceve numeri già finiti.
- **Coefficienti hardcoded nel service:** ENG-02 li vuole in DB. Il service li legge, non li contiene.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Migrazioni schema | Script SQL a mano | Alembic | Versioning, upgrade/downgrade, Fase 4 estende lo schema. |
| Valuta/arrotondamento | Math su float + `round()` | `Decimal` + `Numeric` | Precisione esatta, ROUND_HALF_UP controllato. |
| Elenco comuni | Digitare/scrapare comuni | Dataset ISTAT bundlato (comuni-json) | 7.904 comuni, aggiornati, con CAP/provincia. |
| Validazione input | `if`/`else` manuali | Pydantic v2 | Coercizione tipi, bound su mq, enum su tipo, messaggi 422 automatici. |
| Rate limiting | Contatori a mano | slowapi | Anti-scraping su endpoint pubblico. |
| Normalizzazione nomi città | `.lower().replace()` sparso | python-slugify | Gestisce accenti, apostrofi, spazi in modo consistente. |
| Config da env | `os.getenv` sparso | pydantic-settings | Validazione + default centralizzati. |

**Key insight:** In un estimatore parametrico il rischio non è la matematica (banale) ma la **precisione monetaria** e la **superficie di leak**. Entrambi sono problemi risolti da librerie standard: `Decimal`/`Numeric` per la prima, schemi Pydantic espliciti per la seconda.

## Data Model (prescrittivo)

Progettato multi-listino, multi-referente, estensibile a sotto-voci (Fase 3) e admin-editable (Fase 4). In Fase 1 popolato solo dal seed RE.

```
listino
  id PK · nome ('Reggio Emilia') · citta_riferimento · valuta ('EUR')
  is_default BOOL (RE=true) · attivo BOOL · created_at
  # is_default guida il fallback (D-07)

categoria            # riferimento fisso: le 4 categorie
  code PK ('A-EDILE'|'B-FINITURE'|'C-SERRAMENTI'|'D-PRODOTTI')
  nome · ordine · iva_pct NUMERIC(4,3)   # 0.100 / 0.220 (EST-03; Serramenti default 0.220 provvisorio, D-12)

listino_categoria    # €/m² base + margine, per (listino, categoria)
  id PK · listino_id FK · categoria_code FK
  base_eur_mq NUMERIC(12,2)              # prezzo CLIENTE per m² (riferimento = totale/molt.1.0)
  coefficiente_impresa NUMERIC(4,3)      # SEGRETO server-side (0.65/0.6/0.55/0.5), MAI serializzato
  UNIQUE(listino_id, categoria_code)

tipo_ristrutturazione   # riferimento: 3 tipi
  code PK ('leggera'|'moderata'|'totale') · nome · ordine
  range_pct NUMERIC(4,3)                 # 0.100 / 0.150 / 0.200 (D-04)

moltiplicatore        # per (tipo, categoria) — 12 righe
  id PK · tipo_code FK · categoria_code FK · valore NUMERIC(4,3)
  UNIQUE(tipo_code, categoria_code)
  # v1: globale. Estensibile aggiungendo listino_id nullable in futuro senza rompere.

extra                 # CSE/CSP, pratiche (D-13)
  code PK · nome · importo NUMERIC(12,2) · iva_pct NUMERIC(4,3)
  tipo_calcolo ENUM('fisso','percentuale') DEFAULT 'fisso'   # predisposizione futura
  attivo BOOL
  # in v1: fissi, inclusi nel totale. Finanziamento NON modellato (out of scope).

comune_listino        # mappa città -> listino (solo RE in Fase 1)
  id PK · comune_nome · comune_slug (UNIQUE) · codice_istat NULL · listino_id FK
  # città non presente qui -> fallback su listino.is_default

referente             # multi-referente day 1 (D dominio #6) — schema pronto, NON usato in Fase 1
  id PK · listino_id FK (o citta) · nome · email · telefono NULL · attivo BOOL · priorita INT
  # nessun endpoint in Fase 1; esiste solo per non migrare di nuovo in Fase 4

# Predisposizione Fase 3 (NON creare ora, ma lasciare spazio):
#   voce (sotto-voce a.1/a.2) con categoria_code FK + quantita_per_mq — Fase 3
```

**Note di design:**
- IVA a livello `categoria` (è legale, uguale tra città). Se un giorno servisse override per listino, si aggiunge una tabella ponte senza rompere.
- `moltiplicatore` e `tipo_ristrutturazione.range_pct` globali in v1; la struttura consente di renderli per-listino con una FK nullable.
- Il coefficiente impresa vive in `listino_categoria` ma **non compare in nessuno schema Pydantic di risposta**.

## API Contract (prescrittivo)

**`POST /api/v1/stima`**

Request:
```json
{ "citta": "Modena", "mq": 85, "tipo": "moderata" }
```
Validazione (Pydantic): `mq` intero `> 0` e `<= 2000` (bound anti-abuso); `tipo` enum `leggera|moderata|totale`; `citta` stringa 1..100 char.

Response `200`:
```json
{
  "input": { "citta": "Modena", "mq": 85, "tipo": "moderata" },
  "fallback": true,
  "disclaimer": "Stima basata sul listino di Reggio Emilia, non ancora tarata su Modena.",
  "valuta": "EUR",
  "categorie": [
    { "code": "A-EDILE", "nome": "Edile",
      "imponibile_min": 0, "imponibile_max": 0,
      "iva_pct": 0.10, "iva_min": 0, "iva_max": 0,
      "totale_min": 0, "totale_max": 0 }
    /* B-FINITURE, C-SERRAMENTI, D-PRODOTTI */
  ],
  "extra": [
    { "code": "CSE_CSP", "nome": "CSE/CSP", "importo": 800, "iva_pct": 0.22 },
    { "code": "pratiche", "nome": "Pratiche amministrative", "importo": 1500, "iva_pct": 0.22 }
  ],
  "totale": { "imponibile_min": 0, "imponibile_max": 0, "iva_min": 0, "iva_max": 0, "totale_min": 0, "totale_max": 0 }
}
```
(valori `0` = placeholder di forma; i reali derivano dal calcolo.)

**Campi VIETATI nella risposta:** `base_eur_mq`, `moltiplicatore`, `coefficiente_impresa`, `prezzo_impresa`. Verifica in test: assert che il JSON serializzato non contenga queste chiavi.

**Endpoint di supporto:** `GET /api/v1/comuni?q=<prefix>` — opzionale; in alternativa l'autocomplete è 100% client-side sul JSON bundlato (preferibile, zero round-trip). Se servito dal backend, restituisce solo `[{nome, provincia}]`, nessun dato di prezzo.

**Errori:** `422` per input invalido (Pydantic automatico); `429` da slowapi se rate-limit superato.

## City input UX

- **Dataset:** `comuni-json` di matteocontrini — JSON con tutti i comuni ISTAT + CAP + provincia [CITED: github.com/matteocontrini/comuni-json]. È uno snapshot (dataset del 2020 nel repo originale): i comuni cambiano di rado, ma **verificare/aggiornare lo snapshot al momento del bundling** (assumere ~7.900 comuni). In alternativa il file ufficiale `Elenco-comuni-italiani.xlsx` di ISTAT [CITED: istat.it/storage/codici-unita-amministrative] convertito a JSON in fase di build.
- **Approccio:** bundlare il JSON in `frontend/src/data/comuni.json` (o servirlo statico). Autocomplete client-side con filtro per prefisso su nome normalizzato (`slugify`/`toLocaleLowerCase('it')`), debounce ~150ms. Nessuna API esterna → nessuna latenza, nessun costo, nessun invio del testo utente a terzi (privacy).
- **Ruolo:** la città seleziona SOLO il listino (D-06). Qualunque testo è accettato; se non mappato a un listino → fallback RE + disclaimer (D-07). L'autocomplete è UX, non un vincolo: l'utente può anche digitare una città non in lista.

## Seed (dal JSON esistente)

`docs/seed-coefficienti-base.json` è già machine-readable e completo (base €/m², moltiplicatori, range_pct, IVA, extra). Script `scripts/seed.py` **idempotente** (upsert per chiave naturale, ri-eseguibile senza duplicare):

1. Crea/aggiorna `listino` RE con `is_default=true`.
2. Popola `categoria` (4) con `iva_pct` da `iva_categoria`.
3. Popola `listino_categoria`: `base_eur_mq` da `base_eur_mq`; `coefficiente_impresa` dai valori 0.65/0.6/0.55/0.5 (mappare A→0.65, B→0.6, C→0.55, D→0.5 come da CLAUDE.md / foglio `listini` — **confermare la mappatura categoria↔coefficiente**).
4. Popola `tipo_ristrutturazione` (3) con `range_pct` da `range_pct_tipo`.
5. Popola `moltiplicatore` (12) da `moltiplicatori_tipo`.
6. Popola `extra` (CSE_CSP=800, pratiche=1500), `iva_pct` provvisoria 0.22 (confermare).
7. Popola `comune_listino` con la sola riga Reggio Emilia → listino RE.

**Oracoli di test:** la tabella "Verifica di plausibilità" del seed (`60/85/110 mq` × 3 tipi con IVA+extra) fornisce range attesi — usarli come test di regressione del motore (`tests/test_estimation.py`). Es. `85 mq · totale` deve dare ~`€47.424 – €71.136`.

## Common Pitfalls

### Pitfall 1: Valuta in float
**What goes wrong:** somme e IVA producono `123.4500000001`, arrotondamenti incoerenti tra categorie e totale.
**Why:** IEEE-754 non rappresenta esattamente i decimali.
**How to avoid:** `Decimal` ovunque, `Numeric(12,2)` in DB, `quantize(ROUND_HALF_UP)` solo sull'output.
**Warning signs:** cifre decimali sporche nei test; totale ≠ somma delle categorie.

### Pitfall 2: IVA sul totale invece che per categoria
**What goes wrong:** con aliquote 10%/22% miste, applicare un'aliquota unica sul totale falsa la cifra (EST-03).
**How to avoid:** IVA su ciascun imponibile di categoria, poi somma; extra con propria IVA.
**Warning signs:** il breakdown IVA non torna sommando le categorie.

### Pitfall 3: Leak del margine interno
**What goes wrong:** `coefficiente_impresa`/`base_eur_mq`/moltiplicatori finiscono nel JSON o nei log.
**How to avoid:** schemi Pydantic di risposta senza quei campi; costruzione manuale del DTO; test che asserisce l'assenza delle chiavi; non loggare l'entità ORM completa.
**Warning signs:** `model_validate` diretto su entità ORM; response model che eredita dall'entità.

### Pitfall 4: Ordine di arrotondamento
**What goes wrong:** arrotondare a euro le categorie e poi sommare dà un totale ≠ dal totale arrotondato a valle.
**How to avoid:** decidere la regola e testarla — raccomandato: calcolare tutto in Decimal pieno, sommare, **poi** arrotondare sia le categorie sia il totale; documentare che "il totale può differire di ±1€ dalla somma visiva" oppure arrotondare le categorie e definire il totale come loro somma. Scegliere una regola e renderla un test.
**Warning signs:** discrepanza di 1€ tra somma card e totale in evidenza.

### Pitfall 5: Range non sempre mostrato
**What goes wrong:** categorie con moltiplicatore ~0 (es. Serramenti in leggera = 0.10, o casi ~0) potrebbero mostrare `€0–€0`; l'utente percepisce un bug.
**How to avoid:** D-05 impone sempre un range; gestire esplicitamente il caso valore basso/zero (mostrare `€0` è ok ma con label chiara "non previsto in questo tipo").
**Warning signs:** card vuote o `NaN`.

### Pitfall 6: Matching città fragile
**What goes wrong:** "Reggio Emilia" vs "reggio emilia" vs "Reggio nell'Emilia" non matcha → fallback erroneo sul proprio listino.
**How to avoid:** slug normalizzato per il match; per RE mappare gli alias noti ("Reggio Emilia", "Reggio nell'Emilia").
**Warning signs:** RE stessa entra in fallback.

## Runtime State Inventory

Non applicabile: fase **greenfield**, nessun rename/refactor/migrazione di stato esistente.
- Stored data: nessuno (DB creato ora).
- Live service config: nessuna.
- OS-registered state: nessuno.
- Secrets/env: solo `DATABASE_URL`/`CORS_ORIGINS` da creare ex-novo.
- Build artifacts: nessuno.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Backend | ✓ | 3.13.14 | — |
| uv | Gestione deps Python | ✓ | 0.9.25 | pip |
| Node.js | Frontend build | ✓ | 24.16.0 | — |
| npm | Frontend deps | ✓ | 11.13.0 | — |
| PostgreSQL (locale) | DB dev | ✗ | — | SQLite in dev via SQLAlchemy (schema identico); Postgres su Railway in deploy |
| Docker | (non richiesto) | ✗ | — | Non necessario per Fase 1 |

**Missing con fallback:** PostgreSQL locale assente → per lo sviluppo si può usare **SQLite** (SQLAlchemy astrae; `Numeric`→`Decimal` funziona), **ma** il target di deploy è Postgres su Railway. Raccomandazione: installare Postgres locale o usare un container per parità dev/prod; se si sviluppa su SQLite, girare i test anche su Postgres prima del deploy. **Non un blocco.**
**Missing bloccanti:** nessuno.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SQLAlchemy 1.x `Column`/`declarative_base` | SQLAlchemy 2.0 `Mapped[]`/`mapped_column` | 2.0 (2023) | Tipizzazione statica, meno boilerplate. Usare lo stile 2.0. |
| Pydantic v1 (`.dict()`, `Config`) | Pydantic v2 (`model_dump()`, `model_config`) | v2 (2023) | API diverse; FastAPI 0.141 richiede Pydantic v2. |
| psycopg2 | psycopg (v3) | 2021+ | Driver moderno, migliore async; usare v3 con SQLAlchemy 2.0. |
| CRA (create-react-app) | Vite | 2023+ | CRA deprecato; Vite standard. |

**Deprecated/outdated:** create-react-app (usare Vite); SQLAlchemy 1.x style (usare 2.0 typed); Pydantic v1.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Mappatura categoria→coefficiente impresa: A=0.65, B=0.6, C=0.55, D=0.5 | Seed | Basso per Fase 1 (il coeff. non impatta l'output cliente), ma va confermato dal foglio `listini` prima di usarlo in Fase 3/PDF. |
| A2 | IVA Serramenti/Porte = 22% provvisorio | Data model / Seed | Medio: cambia il totale. Già marcato come parametro admin (D-12). |
| A3 | Extra CSE/CSP e pratiche con IVA 22% e importo fisso | Data model | Medio: l'IVA sugli extra non è specificata nel seed; confermare aliquota e se fissi vs %. |
| A4 | Regola di arrotondamento: calcolo in Decimal pieno, quantize a euro in output | Pitfall 4 | Basso: scelta di presentazione; da fissare come test. |
| A5 | Il coefficiente impresa non serve al calcolo del prezzo CLIENTE Free (base €/m² è già prezzo cliente) | Architecture | Medio: se il base nel seed fosse prezzo impresa e non cliente, il calcolo sballerebbe. Il seed dice "prezzi unitari del listino RE" = prezzo cliente; confermare. |
| A6 | Snapshot dataset comuni ~7.900 voci accettabile | City UX | Basso: comuni cambiano di rado; aggiornare snapshot al bundling. |
| A7 | TypeScript linea 5.9 stabile (non npm `7.0.2` preview) | Stack | Basso: usare 5.9 evita instabilità di preview. |

## Open Questions (RESOLVED)

1. **Mappatura categoria ↔ coefficiente impresa (0.65/0.6/0.55/0.5)** — **RESOLVED.** Mappatura fissata: A→0.65, B→0.6, C→0.55, D→0.5. È margine interno: seedato in `listino_categoria.coefficiente_impresa`, **mai esposto al client** in Fase 1 (non impatta l'output cliente). Da riconfermare sul foglio `listini` prima dell'uso in Fase 3/PDF.
2. **IVA reale Serramenti/Porte e IVA sugli extra** — **RESOLVED.** Default **0.22** sia per Serramenti/Porte sia per gli extra (CSE/CSP, pratiche), modellato come **parametro admin** in DB (editabile in Fase 4). Nessun blocco per Fase 1.
3. **`base_eur_mq` è prezzo cliente o impresa?** — **RESOLVED.** È il **prezzo cliente** (€/m² di listino). Confermato dal seed e dagli oracoli di plausibilità riconcilianti (85 mq totale = €47.985–€70.575); il coefficiente impresa resta un margine interno non usato nel calcolo del prezzo cliente Free.
4. **Regola totale vs somma categorie (arrotondamento)** — **RESOLVED.** Regola di riconciliazione vincolante: il **±range_pct si applica SOLO ai 4 subtotali di categoria** (lavori, IVA per categoria inclusa); gli **extra sono fissi** (CSE/CSP €800 + pratiche €1.500, +22% IVA = €2.806 lordo), **mai scalati** dal range. **Totale mostrato = Σ(range delle 4 categorie) + extra fissi**, così le card + extra riconciliano col totale entro ±1€. Calcolo in Decimal pieno, `quantize` a euro (ROUND_HALF_UP) solo in uscita. Fissata come test di regressione in Plan 02.

## Security Domain

**ASVS Level 1** (`security_enforcement: true`, `security_asvs_level: 1`, `block_on: high`). Fase 1 è anonima e senza auth: la superficie principale è **information disclosure** (il margine) e **input validation**.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Nessun login in Fase 1 (Fase 2). |
| V3 Session Management | no | Nessuna sessione. |
| V4 Access Control | parziale | Endpoint pubblico; nessun dato utente. Admin/CRUD sono Fase 4. |
| V5 Input Validation | **yes** | Pydantic v2: `mq` int bounded, `tipo` enum, `citta` maxlen. |
| V6 Cryptography | no | Nessun segreto crittografico in Fase 1 (solo DATABASE_URL da gestire via env, non in git). |
| V7 Error Handling/Logging | yes | Non loggare entità ORM col coefficiente; messaggi 422 generici. |
| V13 API | yes | CORS ristretto agli origin noti; rate limit (slowapi) sull'endpoint pubblico. |

### Known Threat Patterns for FastAPI + Postgres estimator
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Leak del coefficiente/margine impresa nel JSON o nei log | Information Disclosure | Schemi Pydantic di risposta senza campi segreti; test che asserisce l'assenza; niente log dell'entità ORM. |
| Scraping del modello di prezzo via chiamate ripetute | Information Disclosure | Rate limiting (slowapi); esporre solo range aggregati, mai base/moltiplicatori. |
| SQL injection | Tampering | SQLAlchemy ORM parametrizzato (mai string-format di query). |
| Input malevolo (mq enorme/negativo, tipo arbitrario) | Tampering / DoS | Validazione Pydantic con bound; `422` automatico. |
| CORS troppo permissivo (`*`) | Spoofing | Whitelist origin via pydantic-settings. |
| Secret (`DATABASE_URL`) in git | Info Disclosure | `.env` non versionato; su Railway variabili d'ambiente. |

## Sources

### Primary (HIGH confidence)
- PyPI via `pip index versions` — fastapi 0.141.1, sqlalchemy 2.0.52, alembic 1.19.1, pydantic 2.13.4, pydantic-settings 2.15.0, psycopg 3.3.4, uvicorn 0.52.4, slowapi 0.1.10, python-slugify 8.0.4 [VERIFIED].
- npm via `npm view` — react 19.2.8, vite 8.2.2, @tanstack/react-query 5.102.2, tailwindcss 4.3.3, typescript (5.9 stabile / 7.x preview) [VERIFIED].
- Ambiente locale — python 3.13.14, node 24.16.0, npm 11.13.0, uv 0.9.25 [VERIFIED].
- `docs/seed-coefficienti-base.json` + `docs/seed-listino-reggio-emilia.md` — modello e oracoli di plausibilità [progetto].
- CLAUDE.md, CONTEXT.md, REQUIREMENTS.md, ROADMAP.md — vincoli di dominio [progetto].

### Secondary (MEDIUM confidence)
- github.com/matteocontrini/comuni-json — dataset comuni ISTAT+CAP (snapshot da verificare al bundling) [CITED].
- istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.xlsx — fonte ufficiale ISTAT [CITED].
- docs.sqlalchemy.org/en/20, docs.pydantic.dev/2, docs.python.org/3/library/decimal — pattern [CITED].
- railway.app docs — addon PostgreSQL [CITED].

### Tertiary (LOW confidence)
- Mappatura categoria↔coefficiente e IVA serramenti/extra — da confermare sul file computo (vedi Assumptions/Open Questions).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versioni verificate sui registry corretti; stack coerente con i progetti dell'utente.
- Architecture / data model: HIGH — vincoli di dominio chiari; modello estensibile mappato ai requisiti Fasi 3/4.
- Seed / motore: HIGH — input già machine-readable con oracoli di plausibilità; restano 2-3 conferme di taratura (Assumptions).
- Pitfalls / security: HIGH — pattern noti per estimatori valuta + FastAPI.

**Research date:** 2026-08-24
**Valid until:** ~2026-09-23 (stack stabile; ri-verificare versioni minori prima dell'install).

## RESEARCH COMPLETE
