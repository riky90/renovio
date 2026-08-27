# Phase 3: Pro & dettaglio sottocategorie - Research

**Researched:** 2026-08-26
**Domain:** New Pydantic/SQLAlchemy sub-domain (bottom-up parametric engine + subscription/paywall + extended PDF) inside an existing FastAPI + React app. No new external service integration — everything is an extension of Phase 1/2 patterns already in this codebase.
**Confidence:** MEDIUM-HIGH — architecture/patterns are directly grounded in the existing codebase (HIGH); the exact quantity-estimation coefficients and catalog-family aggregation strategy are domain judgment calls with no external authority to verify against (flagged LOW/ASSUMED throughout, per CONTEXT.md's own "Claude's Discretion" grant).

## Summary

Phase 3 adds no new runtime dependencies and no new third-party service — it is a same-stack extension (FastAPI + SQLAlchemy + Alembic + Pydantic v2 backend, React + TanStack Query + shadcn frontend, WeasyPrint/Jinja2 PDF). The work is almost entirely **domain modeling and business logic**, not library research: (1) a new DB schema for sottocategorie/voci/coefficienti-quantità extending `Listino`, (2) a `Subscription`-style "tessera Pro" table plus a `require_pro` FastAPI dependency mirroring the existing `require_admin` pattern, (3) a second calculation service (`DettaglioProService`, parallel to `EstimationService`) that is bottom-up and deliberately does NOT reconcile with the Free totals, and (4) an extension of the existing `PdfService`/Jinja2 template pipeline for a multi-page Pro PDF.

The single most important engineering fact, verified directly against `docs/computo-base-reggio-emilia.xlsx` in this session, is that the sheet layout differs in **two structural families**: `A-EDILE` is a 3-level coded hierarchy (Sezione → Sottocategoria `A.n` → Voce `A.n.m`, with lettered variants `a/b/c…`), while `B-FINITURE`/`C-SERRAMENTI`/`D-PRODOTTI` are flat, header-grouped product catalogs with no numeric codes at all. A schema built only around the `A-EDILE` shape will not fit the other three categories. This research proposes a single schema (`Sottocategoria`/`Voce`) that fits both families by making the `codice` column nullable and adding a `famiglia` discriminator — verified achievable because both sheets share the same four data columns (`descrizione`, `UM`, `Qta`, `Prezzo Unitario cliente`) once you strip presentation-only formatting.

**Primary recommendation:** Extend the existing seed pipeline (`backend/scripts/seed.py` + a new `docs/seed-dettaglio-pro.json`) with `Sottocategoria`/`Voce`/`CoefficienteQuantitaVoce` tables under a new Alembic migration `0004`; add a `Subscription` table + `require_pro` dependency for the paywall; build `DettaglioProService.compute()` as a bottom-up sibling to `EstimationService.compute()`, computed **on-demand** (never frozen) from the `StimaSalvata` snapshot's `citta`/`mq`/`tipo`, per D-09; and extend `PdfService`/`pdf_stima.html` with a second Jinja2 template for the multi-page Pro document. No new package needs to be installed; `openpyxl`/`pandas` are already present in `backend/.venv` (used for one-off Excel extraction) but are **not** declared in `backend/pyproject.toml` — if a runtime or repeatable seed-generation script needs them, add `openpyxl` as an explicit dependency (do not rely on the implicit venv state, which may not survive a clean `uv sync`).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Pro subscription state (tessera) | API / Backend | Database / Storage | Server-owned source of truth; client never self-reports Pro status (D-08) |
| Paywall enforcement | API / Backend | — | Must gate the endpoint itself, not just hide UI (D-08, explicit user requirement) |
| Bottom-up quantity/price calculation | API / Backend | Database / Storage (coefficients/prices) | Same tier as `EstimationService` (Free); anti-leak boundary is a backend concern only |
| Targeted-question answers (bagni/porte/condizionatori) | Browser / Client (input) | API / Backend (persistence + defaults) | Client collects input; server persists + applies default-if-skipped logic so PDF and detail view stay consistent |
| Pro detail rendering (accordion/rows) | Browser / Client | — | Pure presentation of already-anti-leak-filtered API data |
| PDF Pro generation | API / Backend | — | WeasyPrint/Jinja2 render must happen server-side (existing Phase 2 pattern); browser only triggers download |
| Payment-stub activation flow | API / Backend | Browser / Client (form) | "Production-shaped": server owns the state transition even though no real charge occurs |
| Seed data for sottocategorie/voci | Database / Storage | — | Same convention as Phase 1 (ENG-02): DB-resident, never hardcoded in the engine |

## User Constraints (from CONTEXT.md)

<user_constraints>

### Locked Decisions

- **D-01:** Il dettaglio Pro è ricostruito **bottom-up** dalle voci del computo ed è una stima **più precisa** del Free. **Non deve riconciliare** con il totale di categoria della Fase 1 — sono misure diverse, è accettabile e atteso che i due numeri differiscano.
- **D-02:** Fonte dati = i fogli di dettaglio dell'Excel (`docs/computo-base-reggio-emilia.xlsx`), prezzi Reggio Emilia. A-EDILE = gerarchia a codici (11 macro-sottocategorie, 91 voci `X.n.m`, alcune con varianti a/b/c). B-FINITURE/C-SERRAMENTI/D-PRODOTTI = cataloghi piatti raggruppati per intestazione, no sotto-codici — il "dettaglio" è scelta prodotto + quantità.
- **D-03:** I dati Pro vivono nello stesso seed idempotente (estensione di `backend/scripts/seed.py` + `docs/seed-coefficienti-base.json`), con nuove tabelle + nuova migrazione Alembic. Prezzi = RE; altre città via upload admin in Fase 4 sullo stesso schema.
- **D-04:** La colonna Qta è sempre 0 nel file. I prezzi unitari esistono già; il motore Pro deve stimare le quantità da `(mq, tipo)`. Approccio **ibrido**: coefficienti quantità-per-m² editabili (admin, Fase 4) + poche domande mirate all'utente sulle voci a conteggio ad alto impatto (es. bagni, porte, condizionatori).
- **D-05:** Regola UM: dove UM=mq il prezzo è al metro quadro → quantità = frazione dei mq dell'appartamento (coefficiente per-m²). `cad` (a pezzo) → conteggio (domanda mirata o preset per mq). `ml` (metro lineare) → proporzionale ai mq (proxy perimetro). `ac`/a corpo (forfait) → importo fisso o per tipo.
- **D-06:** Stato Pro modellato come **tessera abbonamento** (record subscription: stato + data scadenza nullable), non un semplice flag booleano.
- **D-07:** Attivazione v1: flusso completo "production-shaped" con step di pagamento **stub** (nessun addebito reale) che attiva la tessera. In produzione basterà accendere il pagamento reale. L'admin può anche attivare Pro a mano.
- **D-08:** Paywall lato server: il dettaglio Pro è protetto sull'endpoint in base allo stato Pro dell'account, non solo nascosto nella UI.
- **D-09:** Estensione del generatore PDF esistente (WeasyPrint, `app/services/pdf_service.py`) con sottocategorie/voci/quantità. Calcolo **on-demand** dagli input dello snapshot salvato (città, mq, tipo — conservati apposta in Fase 2, D-09) — non serve congelare un secondo snapshot. Output sempre a range, anti-leak.
- **D-10:** Anti-leak esteso al Pro: `coefficiente_impresa`/`base_eur_mq`/prezzi impresa/margini restano server-side e non compaiono in nessuna risposta API del dettaglio né nel PDF Pro. La colonna J=0.65 del foglio `listini` è margine interno.
- **D-11:** Output sempre a range, anche nel dettaglio Pro e nel PDF Pro.
- **D-12 (guardrail bloccante):** Ogni nuova migrazione della Fase 3 deve preservare o rieseguire il seed del listino (idempotente) — mai lasciare il DB senza listino di default. Free e Pro leggono lo STESSO listino per città (stesso record `Listino`), non due basi-prezzi divergenti (i totali possono comunque differire per metodo di calcolo diverso, D-01). Vincolo da propagare alla Fase 4.

### Claude's Discretion

- Schema esatto delle nuove tabelle (sottocategoria / voce / coefficiente-quantità), purché estenda lo schema esistente `Listino`/`ListinoCategoria`/`Categoria` senza romperlo e resti predisposto al multi-città (Fase 4).
- Meccanica UI precisa del paywall e della schermata dettaglio (accordion per sottocategoria vs tabella), coerente coi componenti Fase 1 (`CategoryCard`, `TotalCard`).
- Scelta esatta di come rappresentare lo stub di pagamento (bottone/modale/pagina) e il record subscription, purché D-06/D-07 siano rispettati.
- Set esatto delle "domande mirate" sulle quantità (D-04) e dei coefficienti quantità-per-m² iniziali — proposta in planning/research, taratura successiva da admin.

### Deferred Ideas (OUT OF SCOPE)

- Pagamento reale + prezzo abbonamento Pro definito → post-v1 (in v1 solo lo stub production-shaped).
- Upload Excel multi-città + CRUD admin su listini/voci/coefficienti/quantità → Fase 4 (in Fase 3 solo seed RE).
- Taratura fine dei coefficienti quantità-per-m² e del set di domande mirate → iterazione post-lancio via pannello admin (Fase 4).
- Lead / contatto professionista dal livello Pro → Fase 4.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PRO-01 | L'utente Pro vede l'apertura per sottocategorie (a.1/a.2…) con voci e quantità stimate | New `Sottocategoria`/`Voce` schema (§Standard Stack/Architecture) + `DettaglioProService` bottom-up engine (§Architecture Patterns, §Code Examples) |
| PRO-02 | Il dettaglio sottocategorie è dietro paywall (abbonamento Pro) | `Subscription` model + `require_pro` FastAPI dependency mirroring `require_admin` (§Architecture Patterns Pattern 2, §Don't Hand-Roll) |
| PRO-03 | Gestione dell'abbonamento (attivazione/stato Pro sull'account) | `Subscription` "tessera" table, stub activation endpoint, admin manual-activation endpoint (§Architecture Patterns Pattern 2) |
| PDF-02 | L'utente Pro può scaricare un PDF dettagliato brandizzato con le sottocategorie | Extend `PdfService`/Jinja2 template pipeline, on-demand recompute (not frozen snapshot) per D-09 (§Architecture Patterns Pattern 3, §Pitfalls) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Mai esporre il prezzo impresa.** Coefficiente impresa e prezzo impresa restano server-side, mai nel client o nel PDF utente. For Phase 3 this extends to any Pro voce-level data: the simplest and safest implementation is to **never even store an impresa-price column on the new `Voce` table** — seed only the client-facing unit price (Excel column `Prezzo Unitario` cliente), so there is nothing to accidentally leak at the schema level, not just at the schema-response level.
- **Output sempre a range** (min–max), mai un numero secco — applies per-voce, per-sottocategoria (if subtotals shown), and to the Pro PDF, per D-11.
- **Prezzi e coefficienti in database, mai cablati nel codice** — the `coefficiente_qta_per_mq` values (and the eventual per-question defaults) must be seeded rows, not Python constants, mirroring `ENG-02`.
- **Città = selettore del listino.** New Pro tables must hang off `Listino` (or a table joined to it) so Fase 4's multi-city upload can reuse the same schema without a rewrite.
- **IVA differenziata per categoria** — the Pro engine reuses the existing `Categoria.iva_pct` and `Extra` machinery is untouched; no new IVA logic is needed for Phase 3 (Pro detail is a further breakdown of the four categories' internal composition, IVA is still applied at category level as it always was).
- **Modello dati multi-referente per città dal giorno 1** — not directly relevant to Phase 3, no action needed here.

## Standard Stack

### Core (unchanged — no new dependencies)
| Library | Version (pinned in repo) | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.141.1 | API layer | Already the project standard (Phase 1/2) |
| SQLAlchemy | 2.0.52 | ORM | Already the project standard |
| Alembic | 1.19.1 | Migrations | Already the project standard |
| Pydantic | 2.13.4 | Schemas / anti-leak DTOs | Already the project standard |
| WeasyPrint | >=69.0 | PDF rendering | Already the project standard (Phase 2, PDF-01) |
| Jinja2 | >=3.1.6 | PDF templating | Already the project standard |
| React 19 + TanStack Query + react-router 8 + shadcn (radix-vega) | pinned in `frontend/package.json` | Frontend | Already the project standard |

**[VERIFIED: repo]** All versions above read directly from `backend/pyproject.toml` and `frontend/package.json` in this session — no registry lookup needed since these are already-installed project dependencies, unchanged by Phase 3.

### Supporting — net-new for Phase 3
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `accordion` (shadcn/radix) | matches installed shadcn CLI (4.19.0) | Sottocategoria disclosure in the Pro detail screen | Already specified and approved in `03-UI-SPEC.md` — install via `npx shadcn@latest add accordion` from `frontend/` |
| `openpyxl` (dev-only, optional) | 3.1.5 confirmed present in `backend/.venv` | One-off re-extraction of A-EDILE/B/C/D sheet data into `docs/seed-dettaglio-pro.json` if the planner chooses a script-driven extraction rather than a hand-authored JSON | **[ASSUMED]** — present in the venv but **not declared** in `backend/pyproject.toml`; do not assume it survives a clean `uv sync`. Add explicitly as a dev dependency (`uv add --dev openpyxl`) if a repeatable extraction script is planned, or skip entirely and hand-author the seed JSON from the `docs/computo-struttura-dettaglio.md` reference table (already committed) — no code needs `openpyxl` at runtime either way. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| New `Sottocategoria`/`Voce` tables | Store the whole Pro catalog as one big JSON blob on `Listino` (like `risultato_json` on `StimaSalvata`) | Rejected: violates ENG-02 spirit (coefficients/prices must be admin-editable rows in Fase 4, not an opaque blob) and makes per-voce quantity coefficients impossible to query/update individually. |
| `Subscription` table | Boolean `is_pro` column on `User` | Explicitly rejected by D-06 — no expiry/renewal support without a later migration. |
| Server-side paywall via `require_pro` dependency | Client-side route guard only | Explicitly rejected by D-08 — a modified/self-built client could bypass a client-only gate. |
| On-demand Pro detail recompute | Freeze a second `risultato_pro_json` snapshot at "unlock" time (mirroring Free's `StimaSalvata` pattern) | Explicitly rejected by D-09 — recompute keeps the Pro detail responsive to admin-tuned coefficients (Fase 4) without needing a re-save flow; it also means the Pro detail is NOT immutable the way the Free snapshot is — this is a deliberate, documented asymmetry, not an oversight (see Pitfall 2 below). |

**Installation (if `accordion` not yet added):**
```bash
cd frontend
npx shadcn@latest add accordion
```
No backend package installation required for the core feature — `openpyxl` is optional/dev-only per above.

**Version verification:** No new runtime packages are being introduced, so no registry lookup is required beyond confirming the already-pinned versions in `pyproject.toml`/`package.json` (done above via direct file read, not a network call — `[VERIFIED: repo]`).

## Package Legitimacy Audit

No new external packages are proposed for runtime installation in this phase (the only net-new item, shadcn's `accordion` block, is pulled from the already-trusted shadcn official registry already in use since Phase 1/2 — see `03-UI-SPEC.md` Registry Safety section, which classifies it "not required" for vetting). `openpyxl` is an optional, dev-only, already-present tool for one-off data extraction, not a shipped dependency.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| openpyxl (dev-only, optional) | PyPI | 15+ yrs (long-established) | very high (millions/wk) | github.com/openpyxl/openpyxl | not run this session — see note | Approved if added; `[ASSUMED]` re: exact current PyPI metadata, not independently re-verified via `pip index versions` in this session |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

*slopcheck was not installed/run in this research session (no new runtime package requires it — `accordion` is a shadcn registry block, not a package-manager dependency, and `openpyxl` is optional/dev-only and already present). If the planner decides to formally add `openpyxl` as a dev dependency, gate that specific install behind a `checkpoint:human-verify` per the standing package-legitimacy protocol, since it was not run through slopcheck in this session.*

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Browser (React)                                                          │
│                                                                            │
│  Result screen (existing)          Upgrade screen        Pro detail       │
│  ┌─────────────────┐   click        ┌──────────────┐  ┌────────────────┐  │
│  │ "Passa a Pro" /  │──navigate───▶ │ /passa-a-pro │  │ /dettaglio-pro  │  │
│  │ "Vedi dettaglio  │               │ (stub pay)   │  │ (accordion,     │  │
│  │  Pro"            │               └──────┬───────┘  │  targeted Qs)   │  │
│  └─────────────────┘                        │          └───────┬────────┘  │
└──────────────────────────────────────────────┼──────────────────┼──────────┘
                                                │ POST               │ GET/POST
                                                ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ FastAPI (backend)                                                         │
│                                                                            │
│  POST /me/pro/attiva ──▶ upsert Subscription (stub, no real charge)       │
│                                                                            │
│  GET  /me/stime/{id}/dettaglio-pro ──▶ require_pro ──▶                    │
│       DettaglioProService.compute(listino, mq, tipo, risposte)            │
│       reads Sottocategoria/Voce/CoefficienteQuantitaVoce (DB)             │
│       ──▶ anti-leak DTO (range only, no prezzo/coeff impresa)             │
│                                                                            │
│  POST /me/stime/{id}/dettaglio-pro/risposte ──▶ persist bagni/porte/      │
│       condizionatori answers (drives recompute + PDF consistency)         │
│                                                                            │
│  GET  /me/stime/{id}/pdf-pro ──▶ require_pro ──▶ same compute() call ──▶  │
│       PdfService.render_pro() (Jinja2 + WeasyPrint, multi-page)           │
│                                                                            │
│  GET  /auth/me ──▶ UserOut now includes `pro: bool` (derived from         │
│       Subscription) so the frontend knows which CTA/route to show         │
└─────────────────────────────────────────────────────────────────────────┘
                                                │
                                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PostgreSQL / SQLite dev                                                   │
│  Listino ──1:N── Sottocategoria ──1:N── Voce ──1:N── CoefficienteQuantitaVoce│
│  User ──1:1── Subscription                                                │
│  StimaSalvata (existing, Phase 2) — read-only source of citta/mq/tipo     │
│    for on-demand Pro compute; optionally extended with a nullable         │
│    risposte_pro_json column to persist targeted-question answers         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure
```
backend/
├── app/
│   ├── models/
│   │   ├── listino.py            # existing — unchanged
│   │   ├── catalogo.py           # existing — unchanged
│   │   ├── dettaglio_pro.py      # NEW — Sottocategoria, Voce, CoefficienteQuantitaVoce
│   │   └── subscription.py       # NEW — Subscription ("tessera Pro")
│   ├── services/
│   │   ├── estimation.py         # existing Free engine — unchanged
│   │   ├── dettaglio_pro.py      # NEW — DettaglioProService.compute() bottom-up
│   │   └── pdf_service.py        # extended — render_pro() alongside render()
│   ├── schemas/
│   │   └── dettaglio_pro.py      # NEW — closed anti-leak DTOs for the Pro detail response
│   ├── dependencies/
│   │   └── auth.py               # extended — require_pro() alongside require_admin()
│   ├── routers/
│   │   └── dettaglio_pro.py      # NEW — /me/stime/{id}/dettaglio-pro, /me/pro/attiva
│   └── templates/
│       └── pdf_stima_pro.html    # NEW — multi-page Pro PDF template
├── alembic/versions/
│   └── 0004_pro_dettaglio.py     # NEW — sottocategoria/voce/coefficiente/subscription tables
└── scripts/
    └── seed.py                   # extended — upserts sottocategoria/voce/coefficiente rows
docs/
└── seed-dettaglio-pro.json       # NEW — RE sottocategorie/voci/coefficienti (parallel to seed-coefficienti-base.json)
frontend/
├── src/
│   ├── pages/
│   │   ├── PassaAProPage.tsx     # NEW — §B upgrade/payment-stub screen
│   │   └── DettaglioProPage.tsx  # NEW — §C detail screen
│   └── components/
│       ├── SoftWallCta.tsx       # modified — "Passa a Pro" now navigates
│       ├── CategoryCard.tsx      # modified — locked-teaser strip for Free users
│       └── SottocategoriaAccordion.tsx  # NEW — shadcn accordion wrapper per §C.3
```

### Pattern 1: Bottom-up Pro engine as a sibling service, not a fork of `EstimationService`

**What:** `DettaglioProService.compute(session, listino, mq, tipo, risposte) -> DettaglioProResult` — a new, independent Decimal-pure calculation, structurally parallel to `EstimationService.compute()` (same "hand-build result dataclasses, never `model_validate` an ORM row" anti-leak discipline) but with a different aggregation shape (per-voce, grouped by sottocategoria, grouped by categoria) and a different range strategy (see Pattern 4 below).

**When to use:** Any time the Pro detail is requested — both the JSON detail endpoint and the PDF endpoint call the exact same service function, so the on-screen numbers and the downloaded PDF numbers can never drift apart (a real risk if two independent code paths compute the same thing).

**Example (structure, following the existing `EstimationService` shape exactly):**
```python
# Source: pattern extrapolated from backend/app/services/estimation.py (verified in this session)
@dataclass(frozen=True)
class VoceEstimata:
    codice: str | None
    descrizione: str
    um: str
    quantita_stimata: Decimal
    prezzo_min: Decimal
    prezzo_max: Decimal

@dataclass(frozen=True)
class SottocategoriaEstimata:
    codice: str | None
    nome: str
    voci: list[VoceEstimata]

@dataclass(frozen=True)
class CategoriaDettagliata:
    code: str
    nome: str
    sottocategorie: list[SottocategoriaEstimata]

@dataclass(frozen=True)
class DettaglioProResult:
    categorie: list[CategoriaDettagliata]

class DettaglioProService:
    @staticmethod
    def compute(
        session: Session, listino: Listino, mq: int, tipo: str, risposte: dict[str, int]
    ) -> DettaglioProResult:
        ...  # per Voce: quantita = coefficiente_qta_per_mq * mq, OR risposte.get(domanda_mirata_key, default_conteggio)
        ...  # NEVER read/return coefficiente_impresa — this table doesn't even have that column (see Pattern 2 anti-leak)
```

### Pattern 2: `require_pro` dependency, mirroring `require_admin` exactly

**What:** A new FastAPI dependency in `app/dependencies/auth.py`, structurally identical to the existing `require_admin`, checking `Subscription.stato == "attivo"` (and non-expired) instead of `User.role == "admin"`.

**When to use:** On every route that returns Pro detail data or the Pro PDF (D-08 — server-side gate, not just a UI hide).

**Example:**
```python
# Source: pattern extrapolated from backend/app/dependencies/auth.py (verified in this session)
def require_pro(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    sub = db.query(Subscription).filter_by(user_id=user.id).one_or_none()
    now = datetime.now(timezone.utc)
    is_active = sub is not None and sub.stato == "attivo" and (sub.scaduta_il is None or sub.scaduta_il > now)
    if not is_active:
        raise HTTPException(403, "Funzione riservata agli utenti Pro")
    return user
```
This mirrors the existing 401-then-403 layering (`get_current_user` → 401 if unauthenticated; `require_pro`/`require_admin` → 403 if authenticated but not authorized) — no new auth pattern introduced.

### Pattern 3: On-demand PDF recompute (deliberate asymmetry with the Free PDF)

**What:** Unlike `PdfService.render()` (Free), which is contractually forbidden from calling any estimation engine (it only reads the frozen `StimaSalvata.risultato_json` — see the existing module docstring, verified in this session), the Pro PDF path is REQUIRED to call `DettaglioProService.compute()` live, because D-09 explicitly says no second frozen snapshot is needed.

**When to use:** `GET /me/stime/{id}/pdf-pro` reads `StimaSalvata.citta`/`mq`/`tipo` (already-persisted scalar columns from Phase 2) plus any persisted targeted-question answers, calls `resolve_listino` + `DettaglioProService.compute()`, and renders through a new `pdf_stima_pro.html` template — architecturally the mirror image of the Free path, and this asymmetry must be documented in the module docstring so a future maintainer doesn't "fix" it by making Pro match Free's frozen-snapshot rule.

**Example:**
```python
# Source: pattern extrapolated from backend/app/services/pdf_service.py (verified in this session)
class PdfService:
    @staticmethod
    def render_pro(dettaglio: "DettaglioProResult", stima: StimaSalvata, user: User) -> bytes:
        from weasyprint import HTML  # same lazy-import pattern, same GTK3/Windows caveat
        template = _env.get_template("pdf_stima_pro.html")
        html_content = template.render(dettaglio=dettaglio, stima=stima, nome=user.nome, ...)
        return HTML(string=html_content, base_url=str(TEMPLATES_DIR)).write_pdf()
```

### Pattern 4: Range strategy for per-voce and per-sottocategoria figures

**What:** D-11 requires every Pro figure to be a range, but each `Voce` only has a single client unit price in the source Excel — there is no natural "min/max" at the line-item level the way Free has min/max across the ±% applied to whole-category totals.

**Recommendation (discretionary, ASSUMED — flag for planner/user confirmation):** Reuse the exact same `TipoRistrutturazione.range_pct` value already seeded for Free (per tipo: leggera 0.10, moderata 0.15, totale 0.20 — `[VERIFIED: repo]`, read directly from `docs/seed-coefficienti-base.json`), applied uniformly to each voce's `quantita_stimata * prezzo_unitario_cliente`: `voce_min = totale * (1 - range_pct)`, `voce_max = totale * (1 + range_pct)`. This reuses an already-approved, already-admin-editable coefficient rather than inventing a new one, and keeps the "why do Free and Pro ranges differ in spread" story simple: they use the same range_pct, but apply it to a different (bottom-up vs top-down) base amount, consistent with D-01's "different measure, not a discrepancy" framing.

### Anti-Patterns to Avoid

- **Don't store `coefficiente_impresa`/`prezzo_impresa` on the new `Voce` table at all.** The Free schema keeps the margin coefficient on the ORM entity and relies entirely on response-schema discipline to keep it off the wire (`ListinoCategoria.coefficiente_impresa`, verified in this session). For Phase 3, the stronger and simpler anti-leak posture is to **not persist it in the first place** for Pro voci — there is no product requirement for the Pro tier to expose or even compute an impresa margin at line-item granularity, and a column that doesn't exist can't be leaked by a future schema-response mismatch.
- **Don't let the "flat catalog" families (B/C/D) force per-SKU quantity questions.** The Excel sheets for B-FINITURE/C-SERRAMENTI/D-PRODOTTI list dozens of individual product options per group (e.g., many gres tile finishes under "PAVIMENTI E RIVESTIMENTI GRES" — confirmed in this session by reading the sheet directly). Enumerating every SKU as its own "voce" with an independent quantity estimate is almost certainly not viable for v1 — see Open Question 1 below for the recommended aggregation strategy.
- **Don't recompute Free totals when computing Pro detail, and don't attempt to reconcile them.** D-01 is explicit and intentional; a plan step that says "verify Pro subtotal matches Free category total" is a scope violation, not a quality check.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Subscription expiry/active check | Custom date-math scattered across routers | A single `require_pro` dependency (Pattern 2) that centralizes the active/expired logic | Same principle as the existing `require_admin`/`get_current_user` centralization — one place to get the timezone-aware comparison right (the codebase already has a documented naive/aware datetime gotcha in `get_current_user`, verified in this session at `app/dependencies/auth.py:38`) |
| Multi-page paginated PDF layout | Manual page-break byte-counting or a new PDF library | WeasyPrint's native CSS `@page`/`break-inside: avoid` rules (already the project's PDF engine since Phase 2) | No new technology needed; WeasyPrint fully supports print CSS pagination — this is explicitly called out as an assumption in `03-UI-SPEC.md` Open Question 4 and is standard WeasyPrint behavior, not a stretch |
| Accordion disclosure UI | Hand-rolled `useState` show/hide + custom ARIA | shadcn's `accordion` (Radix primitive) | Already the approved choice in `03-UI-SPEC.md`; Radix accordion ships correct keyboard/ARIA behavior for free |
| Idempotent upsert-by-natural-key seeding | A new seeding helper/pattern | Extend `backend/scripts/seed.py`'s existing `.filter_by(...).one_or_none()` upsert loop | D-03 explicitly requires reusing the same seed file/pattern; a second seeding mechanism would violate D-12's "never leave the DB without a default listino" guardrail by adding a second code path that could fall out of sync |

**Key insight:** Every piece of Phase 3 infrastructure (paywall gate, PDF rendering, idempotent seeding) already has a proven sibling in Phase 1/2 code in this exact repository. The research risk here is not "which library to pick" — it's "did you copy the sibling pattern faithfully," because a subtly different anti-leak discipline or a subtly different upsert key is where regressions will come from, not unfamiliar technology.

## Common Pitfalls

### Pitfall 1: Two structurally different Excel layouts collapsed into one schema, incorrectly
**What goes wrong:** Building the `Sottocategoria`/`Voce` schema only against `A-EDILE`'s coded hierarchy, then discovering B/C/D don't fit (no codes, header rows instead of a `Sottocategoria` code, dozens of product lines per group).
**Why it happens:** `A-EDILE` is the only family CONTEXT.md describes in detail with concrete numbers (11 macro-sottocategorie, 91 voci); it's tempting to design the schema entirely around it and treat B/C/D as an afterthought.
**How to avoid:** Design `Sottocategoria.codice` and `Voce.codice` as **nullable** from the start, add a `famiglia` discriminator (`'gerarchica' | 'catalogo'`) on `Sottocategoria`, and verify the seed-extraction step against at least one row from each of the four sheets before writing the migration. This session directly confirmed via `openpyxl` that B-FINITURE header rows have only column A populated (all of UM/Qta/Prezzo/Totale are `None`) while item rows have all five populated — that's the practical signal to use when parsing group boundaries.
**Warning signs:** A migration or seed script that references `A.n.m`-style codes as a required (non-nullable) field, or that has category-specific `if categoria_code == "A-EDILE"` branches deep inside the calculation service rather than confined to the seed/extraction step.

### Pitfall 2: Pro PDF drifting from the on-screen Pro detail
**What goes wrong:** If the JSON detail endpoint and the PDF endpoint each independently call `resolve_listino` + build their own aggregation logic, a future edit to one path (e.g., a rounding tweak) can silently desync the numbers a user sees on-screen from the numbers in their downloaded PDF.
**Why it happens:** The Free PDF pattern (read only a frozen snapshot) doesn't apply here (D-09), so there's no snapshot to force agreement — the discipline has to be enforced by code structure instead (both endpoints delegate to the exact same `DettaglioProService.compute()` call).
**How to avoid:** Both routes must call the identical service function with identical arguments (including the same persisted targeted-question answers — see Pitfall 3). Add a test that calls both code paths with the same inputs and asserts byte-for-byte identical numeric output, analogous to the existing `test_no_leak.py` discipline.
**Warning signs:** A PDF-specific "helper" function in `pdf_service.py` that reimplements any part of the quantity/price math instead of calling into `dettaglio_pro.py`.

### Pitfall 3: Targeted-question answers not persisted, so PDF and detail-view disagree
**What goes wrong:** UI-SPEC §C.2 shows the targeted-question card collapsing to a summary ("Bagni: 2 · Porte: 5...") after being answered once, implying persistence across views of the same saved estimate — but if the answers only live in frontend component state, a user who answers the questions, views the detail, then clicks "Scarica PDF dettagliato" without revisiting the questions will get a PDF computed with *default* (skipped) assumptions instead of their actual answers, silently contradicting what they saw on screen.
**Why it happens:** The natural backend shape (compute-on-demand, no second snapshot per D-09) has no obvious place to persist `{bagni, porte, condizionatori}` unless explicitly added.
**How to avoid:** Add a small nullable JSON column (or a 1:1 side table) on `StimaSalvata`, e.g. `risposte_pro_json`, written by `POST /me/stime/{id}/dettaglio-pro/risposte` and read by both the detail GET and the PDF GET. This is a genuine design decision not fully specified in CONTEXT.md/UI-SPEC — flagged as Open Question 2 below for explicit planner confirmation, but the pitfall itself (silent PDF/screen drift) is real regardless of which persistence mechanism is chosen.
**Warning signs:** A plan that has the frontend re-POST the targeted-question answers as query params on the PDF download link — this technically works but is fragile (URL length limits, and the "skip" default-behavior copy in UI-SPEC implies server-side default logic, not client-side).

### Pitfall 4: `openpyxl`/`pandas` silently missing after a clean environment rebuild
**What goes wrong:** Both packages are present in `backend/.venv` right now (verified in this session: `openpyxl==3.1.5`, `pandas==2.3.3`) but **absent from `backend/pyproject.toml`/`uv.lock`** (verified: zero matches for either name). A seed-extraction script written against them will work on this machine today and fail with `ModuleNotFoundError` on any fresh clone, CI run, or `uv sync --frozen`.
**Why it happens:** They were likely installed ad hoc (e.g., by a previous research/discussion session reading the Excel) without being registered as a project dependency.
**How to avoid:** Either (a) don't write a runtime/repo script that imports them — hand-author `docs/seed-dettaglio-pro.json` once, offline, the same way `docs/seed-coefficienti-base.json` was apparently produced (it's marked "DRAFT auto-generato" but isn't backed by any committed extraction script either, per this session's `find`), or (b) if a repeatable extraction script is wanted, run `uv add --dev openpyxl --native-tls` (matching the project's established proxy-bypass pattern from Phase 1/2 decisions) so it's a tracked dependency.
**Warning signs:** `import openpyxl` or `import pandas` appearing anywhere under `backend/app/` (runtime code) rather than confined to a one-off `backend/scripts/` extraction utility gated by the dev-dependency group.

### Pitfall 5: Migration/seed cycle reproducing the Phase 2 `dev.db` incident (D-12)
**What goes wrong:** Already happened once in this project (STATE.md: a migration cycle reset `dev.db`, and the un-reseeded engine then threw `NoResultFound`). A Phase 3 migration that adds `sottocategoria`/`voce`/`coefficiente_qta_per_mq`/`subscription` tables is exactly the kind of change likely to prompt a local DB reset during development.
**Why it happens:** Alembic migrations and the idempotent seed script are two separate manual steps; nothing currently enforces "always reseed after migrate" as a single atomic local dev command.
**How to avoid:** Extend `scripts/seed.py`'s `seed()` function (not a second script) to also upsert the new sottocategoria/voce/coefficiente rows in the same call, so the existing `uv run python scripts/seed.py` remains the single command that repairs a reset dev DB for *both* Free and Pro data. Do not create a separate `seed_pro.py`.
**Warning signs:** A new standalone `scripts/seed_dettaglio_pro.py` file — this violates D-12's "single idempotent seed" guardrail even if each script is individually idempotent, because a developer who only remembers to run one of the two after a DB reset ends up with a half-seeded system.

## Code Examples

### Extending `UserOut` to expose Pro status (drives frontend CTA branching)
```python
# Source: pattern extrapolated from backend/app/schemas/auth.py (verified in this session)
class UserOut(BaseModel):
    id: int
    email: EmailStr
    nome: str
    role: str
    pro: bool  # NEW — derived from Subscription, never a client-writable field
    created_at: datetime
```
The `_to_user_out()` builder in `routers/auth.py` (verified in this session at line 49-50) already hand-builds this DTO field-by-field from the ORM entity — the same discipline extends trivially: `pro=subscription_is_active(session, user)`.

### Alembic migration shape (extends the existing 0001→0002→0003 chain)
```python
# Source: pattern extrapolated from backend/alembic/versions/0003_stima_salvata.py (verified present, chain confirmed: 0001_initial_schema.py, 0002_auth_tables.py, 0003_stima_salvata.py)
# revision = "0004", down_revision = "0003"
def upgrade() -> None:
    op.create_table("sottocategoria", ...)         # FK -> categoria.code, nullable codice, famiglia discriminator
    op.create_table("voce", ...)                    # FK -> sottocategoria.id, nullable codice, um, prezzo_unitario_cliente
    op.create_table("coefficiente_qta_voce", ...)    # FK -> voce.id + tipo_ristrutturazione.code, coefficiente_qta_per_mq, domanda_mirata_key nullable, default_conteggio nullable
    op.create_table("subscription", ...)             # FK -> user.id, stato, scaduta_il nullable, created_at
    op.add_column("stima", sa.Column("risposte_pro_json", sa.JSON(), nullable=True))  # if Pitfall 3's recommendation is adopted
```

## State of the Art

Not applicable in the traditional sense (no external ecosystem shift to track) — this phase is internal domain modeling on a stack that hasn't changed since Phase 1/2. The one relevant "state of the art" note: WeasyPrint's multi-page/print-CSS support is mature and stable across the versions in this project's compatible range (`>=69.0`); no deprecated API surface was found relevant to adding a second, longer template.

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Free: single-snapshot-only PDF (`PdfService.render`, never recomputes) | Pro: on-demand recompute PDF (`PdfService.render_pro`, always recomputes) | This phase (D-09) | Two different immutability guarantees coexist in the same service class — must be documented clearly in code, not just in planning docs, or a future refactor will "fix" the asymmetry incorrectly (Pitfall 2) |

**Deprecated/outdated:** Nothing in this phase deprecates prior work — Phase 1's `EstimationService`/Free flow and Phase 2's auth/PDF/snapshot flow are all reused as-is, unmodified except for the two additive touch points already called out (`UserOut.pro`, `SoftWallCta` navigation behavior).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Per-voce/per-sottocategoria range should reuse the existing `TipoRistrutturazione.range_pct` (10/15/20%) rather than a new Pro-specific range coefficient | Architecture Patterns, Pattern 4 | If the user actually wants an independent Pro range coefficient, the schema needs one more seeded field (`range_pct_pro` per tipo) — low migration cost if caught during planning, higher cost if built into the engine and discovered post-implementation |
| A2 | Catalog families (B/C/D) should be aggregated to gruppo-level (one representative price range + one quantity estimate per group) rather than enumerating every individual product SKU as its own voce | Architecture Patterns "Anti-Patterns to Avoid", Open Question 1 | If the real intent is full per-SKU enumeration, the UI accordion row-count balloons (dozens of rows per gruppo) and the "domande mirate" quantity-estimation approach (D-04) doesn't obviously extend to picking among many similar products — this is the single highest-impact open question for the planner |
| A3 | Targeted-question answers (bagni/porte/condizionatori) should be persisted server-side (new nullable JSON/column on `StimaSalvata`) rather than re-submitted by the client on every PDF download | Common Pitfalls, Pitfall 3 | If persistence is skipped, the PDF and the on-screen detail can silently show different numbers after a user answers the targeted questions — a real correctness bug, not just a UX nicety |
| A4 | No impresa-price/margin data should be stored at all on the new `Voce` table (stronger anti-leak posture than "store it but never serialize it") | Project Constraints, Architecture Patterns "Anti-Patterns to Avoid" | If a later phase (e.g., Fase 4 admin margin reporting) actually needs a Pro-tier margin figure, this decision would require a schema migration to add the column back — low risk since CLAUDE.md's non-negotiable rule is "never expose," and Fase 4 scope (per REQUIREMENTS.md ADM-01) is about listino/voci/prezzo management, which doesn't obviously require voce-level Pro margin figures |
| A5 | `require_pro` returns 403 (mirroring `require_admin`) rather than 402 Payment Required | Architecture Patterns, Pattern 2 | Cosmetic/API-semantics only — easy to change in one place if the planner prefers 402; doesn't affect data model or business logic |

**If this table is empty:** N/A — see entries above; all are genuine domain-modeling judgment calls flagged for planner/user confirmation per CONTEXT.md's own "Claude's Discretion" grant, not verifiable against an external authority.

## Open Questions (RESOLVED during planning)

> **Resolution note (added post-planning):** All three questions were resolved and carried into the plans.
> Q1 (catalog-family representation) → **RESOLVED** per Recommendation (gruppo-level aggregation, Assumption A2) in 03-02 and 03-03 assumptions blocks.
> Q2 (targeted-answer persistence) → **RESOLVED** as nullable `risposte_pro_json` column on `StimaSalvata` (03-02 Task 2; consumed by 03-03/03-04).
> Q3 (`Subscription.piano_code`) → **RESOLVED** — nullable `piano_code` added now (03-01 Task 1).

1. **How should the flat-catalog families (B-FINITURE/C-SERRAMENTI/D-PRODOTTI) be represented in the Pro detail, given dozens of product-level lines per group?**
   - What we know: The Excel sheets (verified directly in this session) have no sub-codes for these three categories — just header rows ("MATERIALI DI FINITURA" → "PAVIMENTI E RIVESTIMENTI GRES" → individual product descriptions, each with its own UM/price). CONTEXT.md's own framing ("il dettaglio qui è scelta prodotto + quantità") implies per-product choice, but no UI mechanism for arbitrary product selection is in scope for Phase 3 (targeted questions are limited to bagni/porte/condizionatori per D-04's examples, and CONTEXT.md explicitly defers "quali voci esatte sono le voci-chiave" and product-catalog tuning to Fase 4 admin).
   - What's unclear: Whether v1 should (a) enumerate every product line under its group heading with an admin-preset default quantity coefficient (large row count, matches the UI-SPEC's literal "same voce-row layout" language most closely), or (b) aggregate to one representative range per group (smaller, more usable v1, but is a step away from literal per-product enumeration).
   - Recommendation: Aggregate to gruppo-level for v1 (Assumption A2), explicitly framed in the seed data as "gruppo = 1 Sottocategoria row with famiglia='catalogo'" and each *individual product line* becomes a `Voce` row under it with the SAME per-mq-style coefficient applied per group (not per product) — i.e., the group's total estimated quantity is split proportionally or the group is shown with just a min/max price range spanning its cheapest-to-priciest product and a single group-level quantity. Confirm with the user/planner before implementation, since this is the single highest-leverage schema decision in the phase.

2. **Where do targeted-question answers persist, and does the plan need a new column/table for them?**
   - What we know: UI-SPEC §C.2 implies persistence within a saved estimate's lifecycle (collapses to a summary once answered); D-09 says compute happens on-demand from the existing `StimaSalvata` scalar columns, with no mention of a second snapshot for the *answers* specifically (only for the *result*).
   - What's unclear: Whether a nullable `risposte_pro_json` column on `StimaSalvata` (Code Examples above) is the right shape, versus a dedicated `RispostaDomandaMirata` side table (more normalized, more Fase-4-upload-friendly if the question set grows).
   - Recommendation: Start with the simpler nullable JSON column on `StimaSalvata` (Pitfall 3) — it mirrors the existing `risultato_json` convention on the same table and avoids a join for what is, in v1, at most 3 integer fields. Revisit as a normalized table only if Fase 4 needs per-question admin configuration beyond a fixed 3-field set.

3. **Does the Subscription "tessera" need a `piano`/`prezzo` field now, even while the payment step is stubbed?**
   - What we know: D-06/D-07 require expiry-awareness and a "production-shaped" activation flow; D-07 explicitly defers "prezzo abbonamento Pro definito" to post-v1.
   - What's unclear: Whether the `Subscription` table should have an empty/nullable `piano_code` placeholder column now (cheap to add, avoids a future migration) or be added only when real pricing lands.
   - Recommendation: Add a nullable `piano_code: str | None` column now at near-zero cost, matching the project's own "production-shaped" philosophy (D-07) of building the full shape ahead of the real payment integration — but this is non-blocking; the planner can equally choose to add it in the future migration without materially changing v1 behavior.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| WeasyPrint native GTK3/Pango/Cairo runtime | PDF Pro generation (PDF-02) | ✗ (Windows dev machine, same known Phase 2 gap) | — | Same as Phase 2: byte-generating PDF tests skip on this machine via the existing runtime-probe pattern in `test_pdf.py` (verified in this session); production (Railway/Debian) has native GTK3, not blocking |
| Google OAuth (proxy TLS) | Not directly used by Phase 3 | ✗ (known, unrelated, pre-existing Phase 2 gap) | — | Not applicable to this phase's scope |
| `openpyxl`/`pandas` | Optional one-off seed-data extraction only | ✓ (present in `backend/.venv`, unpinned) | openpyxl 3.1.5, pandas 2.3.3 | If unavailable in a future environment: hand-author the seed JSON from `docs/computo-struttura-dettaglio.md` instead of scripting extraction (Pitfall 4) |
| shadcn CLI / `accordion` registry block | Frontend Pro detail UI | ✓ (shadcn 4.19.0 already initialized in `frontend/components.json`, confirmed in `03-UI-SPEC.md`) | matches installed CLI | None needed |

**Missing dependencies with no fallback:** none — the one native-runtime gap (WeasyPrint/GTK3) already has an established, accepted fallback pattern from Phase 2 (skip locally, verify in production).

**Missing dependencies with fallback:** WeasyPrint GTK3 (skip-and-defer-to-production, established precedent); `openpyxl`/`pandas` (hand-author seed JSON instead of scripting, if not formally added as a dependency).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 (backend, `[VERIFIED: repo]` from `pyproject.toml`) |
| Config file | none dedicated — pytest discovers `backend/tests/*.py` (existing convention, 11 test files present) |
| Quick run command | `cd backend && uv run pytest tests/test_dettaglio_pro.py -x` (new file, mirrors `test_estimation.py`/`test_stime_salvate.py` naming) |
| Full suite command | `cd backend && uv run pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PRO-01 | Pro user sees sottocategoria/voce/quantity detail; Free user does not | unit + integration | `pytest tests/test_dettaglio_pro.py -x` | ❌ Wave 0 |
| PRO-02 | Detail endpoint returns 403 for non-Pro authenticated user, 401 for anonymous | integration | `pytest tests/test_dettaglio_pro_paywall.py -x` | ❌ Wave 0 |
| PRO-03 | Stub activation transitions Subscription to active; admin manual-activation works; expired subscription is treated as non-Pro | unit + integration | `pytest tests/test_subscription.py -x` | ❌ Wave 0 |
| PDF-02 | Pro PDF renders (byte-generating test skips gracefully without GTK3, same pattern as `test_pdf.py`); anti-leak check on Pro PDF/detail payload extended | integration | `pytest tests/test_pdf_pro.py -x` (extend `test_no_leak.py`'s recursive key/substring check to include the new endpoints) | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_dettaglio_pro.py tests/test_subscription.py -x` (fast, targeted)
- **Per wave merge:** `uv run pytest` (full backend suite, currently 66/66 passing + 2 skipped per STATE.md)
- **Phase gate:** Full suite green before `/gsd:verify-work`, plus `npx tsc --noEmit` clean on frontend (existing convention every prior plan in this project has followed)

### Wave 0 Gaps
- [ ] `backend/tests/test_dettaglio_pro.py` — covers PRO-01 (bottom-up calc correctness, range application, catalog-family aggregation)
- [ ] `backend/tests/test_dettaglio_pro_paywall.py` — covers PRO-02 (`require_pro` 401/403/200 matrix, mirroring `test_auth_endpoints.py`'s admin-guard test shape)
- [ ] `backend/tests/test_subscription.py` — covers PRO-03 (stub activation, expiry logic, admin manual activation)
- [ ] `backend/tests/test_pdf_pro.py` — covers PDF-02, extending the existing `test_no_leak.py`/`test_pdf.py` recursive anti-leak pattern to the new endpoints and template
- [ ] Extend `backend/tests/test_no_leak.py`'s `LEAKED_KEYS`/`LEAKED_SUBSTRINGS` fixtures (verified present at lines 19-30) to run against the new Pro detail response and PDF HTML, not just the existing Free response

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (reused, unchanged) | Existing `get_current_user` (opaque DB-backed session cookie) — no change needed |
| V3 Session Management | yes (reused, unchanged) | Existing `UserSession` server-side revocation — no change needed |
| V4 Access Control | yes (new) | New `require_pro` dependency (Pattern 2) — server-side authorization check on every Pro-gated route, mirroring the existing `require_admin` (already ASVS V4-compliant per Phase 2) |
| V5 Input Validation | yes (new) | Targeted-question answer payload must be bounded (e.g., `bagni`/`porte`/`condizionatori` as `int = Field(ge=0, le=some_reasonable_cap)`), same pattern as `StimaRequest.mq` bounds (`ge=1, le=2000`, verified in `schemas/stima.py`) |
| V6 Cryptography | no | No new crypto surface in this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| IDOR on `/me/stime/{id}/dettaglio-pro` (accessing another user's saved estimate's Pro detail) | Elevation of Privilege / Information Disclosure | Reuse the existing `.filter_by(id=stima_id, user_id=current_user.id)` + 404-not-403 pattern already established in `routers/stime_salvate.py` (verified in this session) — do not introduce a separate ownership-check style for the new routes |
| Paywall bypass via direct API call (Free user calling the Pro detail endpoint directly, bypassing the UI redirect) | Elevation of Privilege | `require_pro` server-side dependency (D-08, Pattern 2) — this is the entire point of the explicit user requirement; a plan that only gates the frontend route violates PRO-02 |
| Response-schema leak of `coefficiente_impresa`/`prezzo_impresa`/margin data in the new Pro DTOs or PDF template | Information Disclosure | Same closed-field Pydantic DTO discipline as `schemas/stima.py`/`schemas/stima_salvata.py` (verified pattern in this session) — plus the stronger recommendation in this research to not even persist an impresa-price column on `Voce` (Anti-Patterns to Avoid) |
| Rate-limit gap on `/me/pro/attiva` (stub activation spammed) | Denial of Service (minor) | Apply the same `@limiter.limit(...)` decorator pattern already used on `/auth/login`/`/auth/registrati` (verified `slowapi` usage in `app.limiter`) — low severity since it's a stub with no real payment/cost, but consistent with the project's existing rate-limiting convention |

## Sources

### Primary (HIGH confidence — direct codebase/file inspection in this session)
- `backend/app/models/listino.py`, `backend/app/models/catalogo.py`, `backend/app/models/user.py`, `backend/app/models/stima_salvata.py` — existing schema, anti-leak conventions
- `backend/app/services/estimation.py`, `backend/app/services/pdf_service.py` — existing engine/PDF patterns to mirror
- `backend/app/dependencies/auth.py`, `backend/app/routers/auth.py`, `backend/app/routers/stima.py`, `backend/app/routers/stime_salvate.py` — existing auth/paywall-adjacent/endpoint patterns
- `backend/app/schemas/stima.py`, `backend/app/schemas/stima_salvata.py`, `backend/app/schemas/auth.py` — existing DTO conventions
- `backend/scripts/seed.py`, `docs/seed-coefficienti-base.json` — existing idempotent seed pattern
- `backend/pyproject.toml`, `frontend/package.json` — pinned dependency versions
- `docs/computo-struttura-dettaglio.md` — canonical structural summary of the source Excel (referenced by CONTEXT.md as required reading)
- `docs/computo-base-reggio-emilia.xlsx` — read directly via `openpyxl` in this session (sheets `A-EDILE`, `B-FINITURE`) to verify the two structural families first-hand, including the header-row-vs-item-row detection signal used in Pitfall 1
- `.planning/phases/03-pro-dettaglio-sottocategorie/03-CONTEXT.md`, `03-UI-SPEC.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, `CLAUDE.md` — upstream constraints

### Secondary (MEDIUM confidence)
- None — no external web sources were needed for this phase; it is entirely internal domain modeling on an already-established stack.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new runtime dependencies; all versions read directly from repo files, not training-data recall
- Architecture: HIGH for the mirrored patterns (paywall dependency, seed extension, PDF service split) since each has a direct sibling already in the codebase; MEDIUM for the exact new-table schema shape since it's original design, not a copy
- Pitfalls: HIGH for the codebase-grounded ones (dev.db reset, GTK3, openpyxl-not-declared); MEDIUM for the domain-judgment ones (catalog aggregation, range strategy) since they're genuinely open questions, not established facts

**Research date:** 2026-08-26
**Valid until:** No external dependency drift risk (no new packages); valid until CONTEXT.md decisions or the source Excel change — effectively as long as Phase 3 remains unplanned/unimplemented, i.e. no fixed expiry.
