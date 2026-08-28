# Phase 4: Lead & pannello admin - Research

**Researched:** 2026-08-27
**Domain:** FastAPI CRUD admin panel + Excel bulk import (openpyxl) + transactional email lead flow, on an existing SQLAlchemy/Alembic + React/shadcn stack
**Confidence:** HIGH (grounded almost entirely in this repo's own established patterns; the only new technical surface is server-side .xlsx parsing, which is MEDIUM — openpyxl usage confirmed via repo's own working extraction script, not via fresh Context7 lookup)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Lead — form di contatto (LEAD-01)**
- D-01: Il contatto è solo per utenti loggati, disponibile sia da Free sia da Pro. Nome/email presi dall'account.
- D-02: Campi del form oltre a nome+email: telefono, messaggio libero, preferenza di contatto (email/telefono + fascia oraria).
- D-03: Al lead si allega uno snapshot della stima visualizzata al momento del contatto (Free o Pro): città/mq/tipo/totali a range copiati nel record Lead in modo autonomo (indipendente da stima_salvata, difendibile e leggibile anche se l'utente cancella la stima). Anti-leak: nessun dato impresa.

**Lead — notifica & destinatario (LEAD-02/03)**
- D-04: L'email del lead va al referente attivo della città (risolto via ComuneListino → Listino → Referente attivo con priorità).
- D-05: Città senza referente attivo → fallback al referente del listino di default (listino.is_default), che funge da catch-all globale. Nessuna modifica di schema. Il lead non si perde mai.
- D-06: Contenuto della notifica e del record: dati utente (nome/email/telefono/preferenza/messaggio) + riepilogo stima a range (città/mq/tipo/totali) + link al lead nella dashboard. Mai coefficiente/prezzo impresa (anti-leak assoluto verso i non-admin, vale anche per l'email al referente).
- D-07: Lead mai perso in caso di errore email: il record Lead viene sempre salvato prima/indipendentemente dall'invio SMTP; se l'invio fallisce il lead resta comunque in dashboard. (Meccanica esatta — flag di invio/retry — a discrezione del planner.)
- D-08: Conferma all'utente: dopo l'invio, messaggio a schermo di conferma + email di conferma ricezione all'utente, riusando email_service.

**Admin — CRUD prezzi & listini (ADM-01)**
- D-09: Editing prezzi con approccio ibrido: upload Excel del computo per il caricamento bulk di una città (crea listino + voci + mappatura città) + form CRUD granulare in-app per ritocchi puntuali su voci/categorie. Entrambi i percorsi devono essere idempotenti e non distruttivi (D-12 Fase 3).
- D-10: Admin proprietario del margine. L'admin vede e modifica coefficiente_impresa e base_eur_mq dal pannello. L'invariante anti-leak resta assoluto solo verso i non-admin (API/PDF utente finale): questi campi non compaiono mai in risposte esposte ai client non-admin.
- D-11: Effetto degli edit: le nuove stime (calcolate dopo l'edit) usano subito i nuovi valori; le stime già salvate e i PDF già generati restano immutabili (snapshot congelato). Nessun versioning/audit trail obbligatorio in v1 (a discrezione del planner se leggero).

**Admin — coefficienti parametrici (ADM-02)**
- D-12: In v1 l'admin può editare tutti i coefficienti del modello: moltiplicatori tipo×categoria; base_eur_mq per categoria; coefficienti quantità-per-m² del motore Pro; IVA per categoria ed extra (CSE/CSP, pratiche).

**Admin — città, mappature, tipi, testi (ADM-03)**
- D-13: Città/listino/mappatura: l'upload gestisce tutto (crea città, listino e mappatura ComuneListino), poi il form CRUD consente editing puntuale su ComuneListino, tipi di ristrutturazione ed extra.
- D-14: Testi/disclaimer editabili: i testi oggi hardcoded nel backend (city_resolver, schemi stima, disclaimer fallback/legali) migrano in una nuova tabella testi key/value (testo/impostazione: chiave → contenuto), con seed dei testi attuali. Il backend legge da DB invece che da costanti; l'admin li modifica da form.

**Admin — referenti & dashboard lead (ADM-04)**
- D-15: CRUD referenti completo per listino/città con flag attivo e priorità (schema già pronto). V1: un referente attivo per città; il referente del listino default fa da catch-all globale (D-05).
- D-16: Referente configurabile da subito, nessun seed pre-fatto: l'admin crea il referente dal pannello al primo avvio.
- D-17: Dashboard lead con stato del lead (nuovo/gestito) + nota aggiornabile dall'admin/referente. Vista: lista (data, città, nome, contatti, totale stima, stato) con filtri per città e stato, e dettaglio con lo snapshot stima completo.

**Upload Excel — validazione (D-12 Fase 3 = guardrail bloccante)**
- D-18: Flusso a due passi con preview: l'admin carica → il sistema valida e mostra un'anteprima del diff (righe nuove/modificate/errori) → l'admin conferma per applicare. Previene azzeramenti accidentali.
- D-19: Import parziale robusto: le righe valide vengono importate, le righe malformate/non riconosciute vengono scartate ed elencate all'admin per correzione. Un errore isolato non blocca l'intero import. Upsert per chiave naturale (idempotente).
- D-20: Vincoli upload: solo file .xlsx, solo require_admin, con limite di dimensione ragionevole (~10MB). Parsing sicuro. Struttura di riferimento in docs/computo-struttura-dettaglio.md.

**Struttura UI admin (net-new)**
- D-21: Area /admin protetta (route con require_admin) con navigazione a tab/sidebar tra le sezioni: Lead, Listini/Prezzi, Coefficienti, Città/Testi, Referenti. Riusa componenti e stile delle Fasi 1-3.

**Regole di dominio (portate avanti — non ri-discusse)**
- D-22: Anti-leak assoluto verso i non-admin. coefficiente_impresa/base_eur_mq/prezzi impresa/margini restano server-side e non compaiono in nessuna risposta API esposta ai client non-admin, nel PDF, nell'email al referente, né nello snapshot del lead. L'admin è l'unica eccezione (D-10).
- D-23: Output sempre a range anche nella stima allegata al lead e nelle viste utente.
- D-24: Guardrail database (propagato): ogni edit/upload admin deve restare idempotente e non azzerare i dati esistenti; ogni nuova migrazione deve preservare/rieseguire il seed del listino; Free e Pro leggono lo stesso listino per città.

### Claude's Discretion
- Schema esatto del modello Lead (colonne snapshot dedicate vs JSON, stato/nota, relazione a user/referente/comune) e della tabella testi key/value, purché rispetti D-03/D-14/D-17 e l'anti-leak.
- Meccanica esatta di retry/flag di invio email per il lead (D-07) e forma dell'audit/versioning listini se ritenuto leggero (D-11).
- Parser dell'upload Excel (mapping fogli→tabelle, gestione struttura non uniforme A-EDILE vs cataloghi B/C/D) e forma esatta della preview del diff (D-18/D-19), purché idempotente e non distruttivo.
- Layout preciso di ciascuna sezione admin e dei form (tabelle editabili inline vs modale), coerente con lo stile esistente.
- Set esatto di chiavi della tabella testi e valori iniziali di seed (dai testi hardcoded attuali).

### Deferred Ideas (OUT OF SCOPE)
- Contatto anonimo (senza login) — escluso da v1 (roadmap: lead da utente loggato Free/Pro). Eventuale abbassamento dell'attrito in v2.
- Versioning/audit trail dei listini — non obbligatorio in v1, altrimenti candidato a fase futura.
- Pagamento reale abbonamento Pro — resta stub (Fase 3), fuori scope.
- Portale completo rete professionisti (assegnazione lead, gestione partner, multi-referente attivo simultaneo) — visione futura; v1 resta a un referente attivo per città.
- Moltiplicatori-prezzo per zona geografica — v2, servono i dati.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LEAD-01 | Da ogni livello (Free e Pro) l'utente può richiedere il contatto di un professionista | Architecture Patterns (system diagram, Pattern 2/3), Screen Contract §A (UI-SPEC) — `LeadContactDialog` wired to existing `SoftWallCta` intent-redirect mechanism |
| LEAD-02 | Il lead (dati utente + stima) arriva via email e viene salvato nella dashboard admin | Pattern 2 (immutable snapshot `Lead`), Pattern 3 (referente resolution), Pitfall 4 (async email call site), Don't Hand-Roll (reuse `email_service.send_email`) |
| LEAD-03 | Il modello dati supporta più referenti per città (v1 con un unico referente configurato) | `Referente` model already exists (catalogo.py) — no schema change needed; Pattern 3 documents the resolution query ordering by `priorita` |
| ADM-01 | L'admin gestisce i listini prezzi per città (voci, prezzi unitari, coefficiente impresa) | Pattern 1 (anti-leak schema fork), Pattern 4 (two-step Excel upload), Project Structure (`admin/listini.py`, `admin/upload_listino.py`) |
| ADM-02 | L'admin gestisce i coefficienti parametrici del modello di stima | Project Structure (`admin/coefficienti.py`), Standard Stack / Don't Hand-Roll (shared natural-key diff helper) |
| ADM-03 | L'admin gestisce città, mappatura città→listino, tipi di ristrutturazione e testi/disclaimer | Project Structure (`admin/citta.py`, `admin/testi.py`), State of the Art (Testo table migration), Pitfall 5 (don't conflate the two disclaimer concepts) |
| ADM-04 | L'admin consulta i lead ricevuti e configura i referenti per città | Project Structure (`admin/lead.py`, `admin/referenti.py`), Validation Architecture (ADM-04 test map row), Screen Contract §C (UI-SPEC) |
</phase_requirements>


## Summary

Phase 4 is architecturally a **composition problem, not a new-technology problem**. Every piece it needs already has a working precedent in this codebase: session-cookie auth (`require_admin`/`get_current_user`), an idempotent-upsert seed script that already parses this exact Excel file with `openpyxl`, an immutable-snapshot pattern (`StimaSalvata`) to clone for the `Lead` snapshot, a fire-and-forget `send_email()` that already exists *because it was built for this phase*, and a `city_resolver.resolve_listino()` fallback pattern to extend for referente resolution. The two genuinely new things are (1) a stateful two-step upload/diff/confirm HTTP flow (no precedent in the repo — new pattern), and (2) moving `openpyxl` from a dev-only extraction script into a runtime backend dependency, which requires a `python-multipart` addition FastAPI needs for `UploadFile` (already present transitively, must be pinned explicitly).

The admin CRUD surface (listini/prezzi, coefficienti, città/testi, referenti) is five instances of the same shape: list + create + edit(dialog) + delete(confirm) + `require_admin` + Pydantic schema that must NEVER include `coefficiente_impresa`/`base_eur_mq` on non-admin endpoints but MUST include them on admin ones (D-10, a deliberate schema-level fork of `01-RESEARCH.md`'s existing anti-leak schema pattern). Reuse a single generic pattern (router module per entity, thin service functions, Pydantic `*In`/`*Out` schema pairs) rather than inventing a framework-level generic CRUD abstraction — five small routers is simpler to keep anti-leak-auditable than one generic one.

**Primary recommendation:** Build Phase 4 as seven new/extended backend routers (`lead`, `admin/lead`, `admin/listini`, `admin/coefficienti`, `admin/citta`, `admin/testi`, `admin/referenti`, `admin/upload-listino`) sharing one Alembic migration (0006) that adds `Lead` and `Testo` (key/value) tables plus a `richiede_referenti` seed step preserved via the existing idempotent `scripts/seed.py`. Frontend: one new `/admin` route tree with a shared `AdminTable`/`AdminCrudDialog` pattern (net-new components, composed from the newly-required shadcn `table`/`dialog`/`alert-dialog`/`select`/`switch`/`sonner` primitives per `04-UI-SPEC.md`), plus a `LeadContactDialog` wired into `SoftWallCta`'s existing "Contatta un professionista" button.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Lead capture form (contact CTA) | Browser / Client (React dialog) | API / Backend (validation, persistence) | Same split as existing forms (`EstimateForm`) — client renders/validates shape, server is source of truth for anti-leak and persistence |
| Lead snapshot construction | API / Backend | — | Server re-derives/copies the range snapshot server-side at submit time from the already-computed estimate context sent by the client, mirroring `StimaSalvata`'s pattern of freezing a client-shown payload without recomputation (D-09 Fase 2 precedent) — never trusts client-sent totals as authoritative without validating they match a real listino/comune/tipo/mq combination |
| Lead email notification | API / Backend | — | `email_service.send_email()` (async SMTP, log-fallback), called from the lead router after DB commit, never blocking the HTTP response on SMTP failure (D-07) |
| Admin CRUD (listini/coefficienti/città/testi/referenti) | API / Backend | Browser / Client (React admin forms) | Backend owns validation + anti-leak schema boundary; React is a thin CRUD UI over typed endpoints, same shape as existing auth/stima flows |
| Excel upload + diff/parse | API / Backend | Browser / Client (dropzone + diff render) | Parsing, natural-key diffing and idempotent upsert MUST happen server-side (security: never trust client-parsed Excel; D-19/D-20 guardrails are server-enforced) — client only uploads the file and renders the diff JSON the server returns |
| Coefficient/price storage | Database / Storage | — | Existing tables (`ListinoCategoria`, `Moltiplicatore`, `Voce`, `CoefficienteQuantitaVoce`, `Extra`) — Phase 4 adds write paths, not new storage concepts |
| Testi/disclaimer storage | Database / Storage | API / Backend (read-through replacing constants) | New `Testo` key/value table; `city_resolver.py`/`routers/stima.py` DISCLAIMER_TEMPLATE constant migrates to a DB read (D-14) |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| openpyxl | 3.1.5 [VERIFIED: PyPI registry, already installed in this repo] | Parse uploaded `.xlsx` computo files server-side | Already used by `backend/scripts/extract_dettaglio_pro.py` for this exact file format — zero new parsing logic to design, only relocate/adapt existing row-classification logic (header vs. voce, A-EDILE hierarchy vs. flat catalog) into a request-time service |
| python-multipart | pin to `>=0.0.21` [VERIFIED: PyPI registry — 0.0.32 latest, 0.0.21 already present transitively in this environment] | Required by FastAPI/Starlette to parse `multipart/form-data` (`UploadFile`) | FastAPI's own documentation mandates this as a required (undeclared-by-default) dependency for any file-upload endpoint; currently transitive-only in this repo (pulled in by an existing dep) — Phase 4 is the first phase to actually need `UploadFile`, so it must become an explicit `pyproject.toml` dependency, not an assumed transitive one |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| (none — no new libraries beyond the above two) | — | — | Everything else (diff computation, CRUD, key/value texts) is plain SQLAlchemy/Pydantic, matching every prior phase's "no new dependency" discipline |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| openpyxl | pandas + openpyxl engine | pandas would add a large new dependency (numpy transitively) purely for row iteration the repo already does natively with openpyxl in `extract_dettaglio_pro.py`; rejected — no net benefit, violates "reuse existing assets" instruction and CLAUDE.md's dependency-discipline precedent (every phase so far added the minimum) |
| A generic FastAPI admin/CRUD framework (e.g. SQLAdmin, FastAPI-Admin) | Hand-rolled routers per entity | Rejected: these frameworks assume they own the response schema, which conflicts directly with the anti-leak requirement that `coefficiente_impresa`/`base_eur_mq` must be filterable per-endpoint by role (D-10) — a generic admin framework would need to be fought/configured around this constraint more than it would save; also net-new dependency for a 5-entity CRUD surface this small |

**Installation (backend, uv):**
```bash
uv add --native-tls python-multipart
# openpyxl: move from [dependency-groups].dev to [project].dependencies (no reinstall needed, already present)
```

No new frontend package installs — the required shadcn components (`table`, `tabs`, `select`, `switch`, `alert-dialog`, `sonner`) are official shadcn registry primitives added via the shadcn CLI (`npx shadcn add table tabs select switch alert-dialog sonner`), not npm dependencies beyond what shadcn/radix already brings in (already-approved registries per `04-UI-SPEC.md` Registry Safety section — no new gate needed).

**Version verification:** `pip index versions openpyxl` → 3.1.5 (installed, latest). `pip index versions python-multipart` → 0.0.32 latest; 0.0.21 already present transitively; recommend pinning `>=0.0.21` (no known breaking changes in this range for the basic `UploadFile` use case) rather than forcing a bump, to avoid an unplanned transitive-dependency change mid-phase — confirm exact pin at implementation time with a fresh `pip index versions` check.

## Package Legitimacy Audit

> slopcheck was installed successfully but could not verify either package: this environment's `slopcheck install` targets the **npm** registry only and this is a Python/PyPI dependency addition — cross-ecosystem mismatch, plus the corporate proxy's self-signed TLS certificate blocked the npm registry call entirely (`SSLCertVerificationError`, see command output). Per the Package Legitimacy Gate's graceful degradation clause, both packages are tagged `[ASSUMED]` and the planner MUST gate their install behind a `checkpoint:human-verify` task — **however** both have strong independent precedent already in this exact repository, which the planner should weigh when deciding checkpoint friction:

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `openpyxl` | PyPI | ~15 yrs (long-standing project, current 3.1.5) | very high (standard Excel-in-Python library) | https://foss.heptapod.net/openpyxl/openpyxl (mirrored on PyPI/GitHub) | not verifiable (npm-only tool, network-blocked) — `[ASSUMED]` | Approved — **already installed and used** in this exact repo (`backend/scripts/extract_dettaglio_pro.py`), already passed a `blocking-human` checkpoint and explicit user approval in Phase 3 (`STATE.md`: "Checkpoint blocking-human per openpyxl... approvato dall'utente"). Moving it from dev- to runtime-dependency scope is a config change, not a new install — planner may treat re-checkpointing as lower friction than a first-time install, but a checkpoint is still recommended since its *runtime exposure surface* changes (dev-only script → public-facing upload endpoint). |
| `python-multipart` | PyPI | long-standing (Starlette/FastAPI ecosystem dependency) | very high (implicit dependency of nearly every FastAPI file-upload app) | https://github.com/Kludex/python-multipart | not verifiable (npm-only tool, network-blocked) — `[ASSUMED]` | Approved — **already present transitively** in this environment (`pip index versions` shows 0.0.21 installed) and is FastAPI's own documented required package for `UploadFile`/`Form` handling; no alternative exists in the FastAPI ecosystem. Recommend a lightweight checkpoint (explicit pin in `pyproject.toml`) rather than a full new-package review, since it is not actually a new install. |

**Packages removed due to slopcheck [SLOP] verdict:** none — slopcheck did not run against the correct registry for either package (see note above), no verdict was produced.
**Packages flagged as suspicious [SUS]:** none.

*Both packages above are tagged `[ASSUMED]` per the graceful-degradation rule. The planner must insert a `checkpoint:human-verify` before either install/scope-change, even though both have strong existing-repo precedent — the checkpoint should note the precedent explicitly so the user isn't re-litigating a decision already made in Phase 3.*

## Architecture Patterns

### System Architecture Diagram

```
[Browser: Free/Pro result screen]
        │  click "Contatta un professionista"
        ▼
  ┌─────────────────────┐   anonymous → redirect /registrati?intent=contatta (existing intent mechanism)
  │ SoftWallCta.tsx      │───────────────────────────────────────────────────────────────────────────┐
  └─────────┬────────────┘                                                                            │
            │ logged in                                                                                │
            ▼                                                                                          │
  ┌─────────────────────┐  POST /api/v1/lead {nome,email,telefono,messaggio,preferenza,fascia,         │
  │ LeadContactDialog    │        snapshot: {citta,mq,tipo,totale_min,totale_max}}                     │
  └─────────┬────────────┘                                                                              │
            ▼                                                                                          │
  ┌─────────────────────────────┐  1. persist Lead row (ALWAYS succeeds before any SMTP attempt, D-07) │
  │ POST /lead router            │  2. resolve referente: ComuneListino→Listino→Referente(attivo)      │
  │ (require login, not require │     fallback: Listino(is_default=True)→Referente(attivo) (D-04/D-05) │
  │  _admin)                    │  3. send_email() to referente  (never raises — logs on failure)      │
  └─────────┬────────────────────  4. send_email() confirmation to user (D-08)                        │
            ▼                                                                                          │
  ┌─────────────────────┐                                                                              │
  │ Lead table (DB)      │◀── independent of stima_salvata: snapshot columns copied at submit time     │
  └─────────┬────────────┘     (D-03 — "autonomo... difendibile e leggibile anche se l'utente cancella  │
            │                    la stima")                                                             │
            ▼                                                                                          │
  ┌─────────────────────────────┐
  │ GET /admin/lead (require_admin) → Lead dashboard list+filter+detail (stato/nota update, ADM-04)     │
  └─────────────────────────────┘                                                                       ◀┘

[Admin CRUD — 5 sections, all require_admin]
  /admin/listini      ──CRUD──▶ Listino, ListinoCategoria, Sottocategoria, Voce  (coefficiente_impresa/
                                 base_eur_mq visible ONLY here, D-10)
  /admin/coefficienti ──CRUD──▶ Moltiplicatore, ListinoCategoria.base_eur_mq, CoefficienteQuantitaVoce,
                                 Categoria.iva_pct, Extra
  /admin/citta        ──CRUD──▶ ComuneListino, TipoRistrutturazione, Extra (mapping only; upload owns bulk)
  /admin/testi         ──CRUD──▶ Testo (new key/value table) — replaces DISCLAIMER_TEMPLATE constant and
                                 any other hardcoded disclaimer/legal string (D-14)
  /admin/referenti      ──CRUD──▶ Referente (attivo/priorita, D-15/D-16)

[Excel upload — two-step, D-18/D-19/D-20]
  Browser dropzone → POST /admin/upload-listino/preview (multipart, .xlsx only, ≤10MB)
        │  server: openpyxl parse → classify rows → compute diff vs DB by natural key
        │          (nuove / modificate / scarti-con-motivo) → returns diff JSON, NOTHING WRITTEN YET
        ▼
  Browser renders diff table + scarti panel
        │  admin clicks "Conferma import"
        ▼
  POST /admin/upload-listino/confirm {diff_token or re-submitted parsed payload}
        │  server: re-validates, applies idempotent upsert by natural key (never deletes/zeroes existing
        │          rows not present in the file — D-24 blocking guardrail), commits
        ▼
  DB updated → immediate effect on next EstimationService/DettaglioProService.compute() call (D-11) —
               already-frozen StimaSalvata/Lead snapshots are untouched by construction (they don't
               re-read these tables, they store frozen values)
```

### Recommended Project Structure
```
backend/app/
├── models/
│   ├── lead.py                 # NEW: Lead (snapshot columns + stato/nota)
│   └── testo.py                # NEW: Testo (key/value)
├── schemas/
│   ├── lead.py                 # LeadCreate (public-facing, bounded), LeadOut (admin-only), LeadUpdate (nota/stato)
│   ├── admin_listino.py        # Admin-only In/Out pairs INCLUDING coefficiente_impresa/base_eur_mq
│   ├── admin_coefficienti.py
│   ├── admin_citta.py
│   ├── admin_testi.py
│   ├── admin_referenti.py
│   └── admin_upload.py         # DiffPreview{nuove,modificate,scarti} response shape
├── services/
│   ├── lead_service.py         # referente resolution (extends city_resolver pattern), snapshot build
│   └── listino_upload_service.py  # openpyxl parse + natural-key diff + idempotent upsert (adapt
│                                   # extract_dettaglio_pro.py's row-classification logic, moved to
│                                   # request-time, security-hardened: size/type guard, no arbitrary
│                                   # sheet/cell trust)
├── routers/
│   ├── lead.py                 # POST /api/v1/lead (require login)
│   └── admin/
│       ├── lead.py              # GET /admin/lead, GET /admin/lead/{id}, PATCH /admin/lead/{id}
│       ├── listini.py           # CRUD listino/listino_categoria/sottocategoria/voce
│       ├── coefficienti.py      # CRUD moltiplicatore/coeff_qta_voce/extra/iva
│       ├── citta.py             # CRUD comune_listino/tipo_ristrutturazione
│       ├── testi.py             # CRUD testo
│       ├── referenti.py         # CRUD referente
│       └── upload_listino.py    # POST /preview, POST /confirm
└── alembic/versions/0006_lead_testo.py   # Lead + Testo tables, seed preserved (D-24)

frontend/src/
├── pages/admin/
│   ├── AdminLayout.tsx          # sidebar/tabs shell (§B UI-SPEC), require_admin client guard
│   ├── LeadDashboardPage.tsx
│   ├── ListiniPage.tsx
│   ├── CoefficientiPage.tsx
│   ├── CittaTestiPage.tsx
│   └── ReferentiPage.tsx
├── components/admin/
│   ├── AdminTable.tsx           # generic table+skeleton+empty-state shell (composition, not a
│   │                             # "framework" — each page still declares its own columns/schema)
│   ├── AdminCrudDialog.tsx      # generic add/edit dialog shell (form injected by page)
│   ├── AdminDeleteConfirm.tsx   # alert-dialog wrapper, entity name interpolated
│   └── ExcelUploadDialog.tsx    # 3-step upload/diff/confirm flow (§E UI-SPEC)
├── components/
│   └── LeadContactDialog.tsx    # NEW — wired from SoftWallCta's existing "Contatta un professionista"
├── api/
│   ├── lead.ts                  # postLead
│   └── admin/
│       ├── client.ts             # NEW: apiPatch/apiPut/apiDelete (client.ts today only has GET/POST)
│       ├── lead.ts
│       ├── listini.ts
│       ├── coefficienti.ts
│       ├── citta.ts
│       ├── testi.ts
│       ├── referenti.ts
│       └── uploadListino.ts
```

### Pattern 1: Anti-leak schema fork for admin vs. non-admin responses (extends 01-RESEARCH.md Pattern 1)
**What:** Every entity that carries `coefficiente_impresa`/`base_eur_mq`/margin-shaped fields gets **two** Pydantic response schemas: a `*AdminOut` (includes the sensitive fields, used only under `require_admin`) and, where the same entity is ever read by a non-admin endpoint, a `*PublicOut` (excludes them). Never one schema with an optional/conditionally-populated sensitive field — the existing codebase's discipline is a *closed field set per schema class*, not runtime field hiding.
**When to use:** Every admin CRUD schema for `ListinoCategoria`, `Voce`-adjacent pricing (if ever exposed non-admin, which it currently is not), `Moltiplicatore`.
**Example:**
```python
# Source: existing pattern, app/schemas/stima.py (CategoriaOut has NO coefficiente_impresa field at all)
class ListinoCategoriaAdminOut(BaseModel):
    id: int
    categoria_code: str
    base_eur_mq: Decimal
    coefficiente_impresa: Decimal  # admin-only — this class is NEVER used outside require_admin routes

class ListinoCategoriaAdminIn(BaseModel):
    base_eur_mq: Decimal = Field(gt=0)
    coefficiente_impresa: Decimal = Field(gt=0, le=1)
```

### Pattern 2: Immutable-snapshot Lead (extends 02-RESEARCH.md Pattern 3 / `StimaSalvata`)
**What:** `Lead` copies scalar snapshot fields (`citta`, `mq`, `tipo`, `totale_min`, `totale_max`) directly onto the `Lead` row at submit time, exactly like `StimaSalvata`. No foreign key to `StimaSalvata` is required to read the snapshot back (D-03: "indipendente da stima_salvata, difendibile e leggibile anche se l'utente cancella la stima") — an optional nullable FK to `stima_salvata.id` MAY be added for traceability/analytics but must never be required for rendering the lead detail.
**When to use:** `Lead` model design (Claude's Discretion per CONTEXT.md).
**Example:**
```python
# Source: adapted from app/models/stima_salvata.py (this repo)
class Lead(Base):
    __tablename__ = "lead"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False, index=True)
    stima_salvata_id: Mapped[int | None] = mapped_column(ForeignKey("stima.id"), nullable=True)  # optional trace-back
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    preferenza_contatto: Mapped[str] = mapped_column(String(16), nullable=False)  # "email" | "telefono"
    fascia_oraria: Mapped[str | None] = mapped_column(String(32), nullable=True)
    messaggio: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    # Snapshot indipendente (D-03) — mai coefficiente/prezzo impresa (D-22)
    citta: Mapped[str] = mapped_column(String(200), nullable=False)
    mq: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    totale_min: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    totale_max: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    referente_id: Mapped[int | None] = mapped_column(ForeignKey("referente.id"), nullable=True)
    email_inviata: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")  # D-07 flag
    stato: Mapped[str] = mapped_column(String(16), nullable=False, default="nuovo", server_default="nuovo")  # D-17
    nota: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
```

### Pattern 3: Referente resolution as a `city_resolver`-shaped service (D-04/D-05)
**What:** `resolve_referente(session, citta) -> Referente` mirrors `resolve_listino()`'s exact two-branch shape: look up `ComuneListino` by slug → `Listino` → active `Referente` (order by `priorita`); if no row, or the found listino has no active referente, fall back to `Listino(is_default=True)`'s active referente. **No schema change** — D-05 is explicit that the "global catch-all" is simply the default listino's active referente, not a new concept.
**When to use:** Called once, inside the lead router, right after persisting the `Lead` row (never before — D-07 ordering).
**Example:**
```python
# Source: pattern adapted from app/services/city_resolver.py (this repo)
def resolve_referente(session: Session, citta: str) -> Referente | None:
    listino, _fallback = resolve_listino(session, citta)
    referente = (
        session.query(Referente)
        .filter_by(listino_id=listino.id, attivo=True)
        .order_by(Referente.priorita)
        .first()
    )
    if referente is not None:
        return referente
    default_listino = session.query(Listino).filter_by(is_default=True).one()
    if default_listino.id == listino.id:
        return None  # no active referente anywhere — lead still saved, dashboard is the safety net (D-07)
    return (
        session.query(Referente)
        .filter_by(listino_id=default_listino.id, attivo=True)
        .order_by(Referente.priorita)
        .first()
    )
```

### Pattern 4: Two-step Excel upload with server-held diff (D-18/D-19)
**What:** `POST /preview` parses + diffs but **writes nothing**; the diff result (including every row's proposed values) is returned to the client in full — the client re-POSTs the exact same parsed payload (not just a confirmation flag) to `POST /confirm`, which re-validates and applies. This avoids needing server-side session/cache state for the "pending upload" between steps (no Redis, no server session table) — the browser is the only place the pending diff is held between preview and confirm, consistent with this stateless-API codebase's existing patterns (no session-based multi-step flows exist elsewhere in the repo).
**When to use:** `admin/upload_listino.py` router design.
**Example:**
```python
# Source: new pattern for this repo, no direct precedent — designed from D-18/D-19/D-20 constraints
@router.post("/admin/upload-listino/preview")
def preview_upload(file: UploadFile, user=Depends(require_admin), db: Session = Depends(get_db)) -> DiffPreviewOut:
    _validate_upload(file)  # .xlsx magic bytes + size <=10MB (D-20)
    rows = parse_computo_xlsx(file.file)  # reuses extract_dettaglio_pro.py's row-classification logic
    diff = compute_diff(db, rows)  # natural-key comparison: nuove / modificate / scarti(reason)
    return DiffPreviewOut(nuove=diff.nuove, modificate=diff.modificate, scarti=diff.scarti)

@router.post("/admin/upload-listino/confirm")
def confirm_upload(payload: DiffConfirmIn, user=Depends(require_admin), db: Session = Depends(get_db)) -> ImportResultOut:
    applied = apply_diff_idempotent(db, payload)  # upsert by natural key, NEVER deletes rows absent from file (D-24)
    db.commit()
    return ImportResultOut(righe_importate=applied)
```

### Anti-Patterns to Avoid
- **Client-side Excel parsing (e.g. SheetJS in the browser):** never parse the upload client-side even for preview — D-20 requires server-side validation, and the diff must be computed against live DB state the client cannot see.
- **Deleting/truncating rows not present in the uploaded file:** the D-24 guardrail is explicit — upload is additive/updating only; removing a `Voce`/`ListinoCategoria` row must be a separate, deliberate CRUD delete action with its own `alert-dialog` confirmation, never an implicit side-effect of a bulk upload.
- **A single generic Pydantic schema with `Optional[Decimal] coefficiente_impresa = None`** shared between admin and public endpoints: even if the field is `None` for public responses, this pattern is fragile (one missed `exclude` call away from a leak) and breaks with this repo's established "closed field set per response class" discipline.
- **Blocking the lead HTTP response on SMTP send:** `send_email()` is `async` but has no timeout/retry visible in its current implementation — call it, but the row MUST be committed to the DB first (D-07), and a slow/failing SMTP call should not be allowed to make the user-facing "richiesta inviata" response hang; consider `await`-ing it inline (simplest, matches existing reset-password pattern) but treat any exception as already-handled (the function is documented "never raises") — do not wrap in extra try/except that could mask new failure modes silently.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Excel row parsing | A new bespoke XML/zip reader | `openpyxl` (already in repo) | Already solved in `extract_dettaglio_pro.py`; the row-classification heuristics (header vs. voce, A-EDILE hierarchy edge case) took real iteration in Phase 3 (see STATE.md Pitfall) — re-deriving them would repeat that cost |
| Natural-key diffing | Ad-hoc nested loops per entity type | A small shared `diff_by_natural_key(existing_rows, incoming_rows, key_fn)` helper reused across listino/voce/coefficiente diffing | Five near-identical CRUD sections and one upload flow all need the same "compare by natural key, classify new/changed/unchanged" logic — write it once as a small pure function, not five times |
| Admin-only field exposure gating | A runtime permission-check decorator on individual Pydantic fields | Separate `*AdminOut`/`*PublicOut` schema classes (Pattern 1 above) | Matches the repo's existing, already-audited (grep-verified anti-leak) discipline; a field-level runtime gate would be a new, unaudited security mechanism |
| CRUD boilerplate (5 entities) | A generic admin-framework or code-generator | Five small, near-identical router modules following one copy-pasted template | At this scale (5 entities, ~1 file each) a framework adds more indirection than it saves, and — critically — fights the anti-leak schema-fork requirement (see Alternatives Considered) |

**Key insight:** Nothing in Phase 4 requires new infrastructure (no cache layer, no background job queue, no file storage service for the uploaded Excel — it's parsed in-memory per-request and discarded). The temptation to add a task queue for "large" Excel imports should be resisted: the computo file is ~500KB (`docs/computo-base-reggio-emilia.xlsx`, 543KB) and even multi-city uploads are well within a synchronous request/response parse+diff+upsert cycle (sub-second to low-single-digit-seconds range for hundreds of rows) — do not add Celery/RQ/background workers for this.

## Common Pitfalls

### Pitfall 1: Reusing `extract_dettaglio_pro.py`'s logic verbatim instead of hardening it for untrusted input
**What goes wrong:** The existing script assumes a known-good, single, developer-controlled file (`docs/computo-base-reggio-emilia.xlsx`) and has no size/type/malformed-workbook guards — it will happily raise unhandled exceptions (500s) on a corrupt or adversarial `.xlsx`.
**Why it happens:** The row-classification logic (header vs. voce detection, A-EDILE hierarchy state machine) is genuinely reusable and correct — the temptation is to import the script's functions as-is.
**How to avoid:** Extract the *pure classification functions* (`_is_header_row`, `_coefficienti_per_voce`-equivalent for the price/UM columns, the A.0 synthetic-sottocategoria state machine) into a shared module importable from both the dev script and the new runtime service, wrap every openpyxl call site in the runtime service with try/except that produces a row entry in the "scarti" list (D-19) rather than raising, and validate file size/extension *before* attempting to open the workbook.
**Warning signs:** Any unhandled `openpyxl.utils.exceptions.InvalidFileException` or `KeyError` reaching the HTTP layer as a 500 instead of a structured "riga scartata" entry.

### Pitfall 2: Treating "idempotent" upsert as "last-write-wins" without natural-key stability
**What goes wrong:** `Sottocategoria`/`Voce` upsert-by-natural-key already has a subtlety in this repo: natural key is `(listino_id, categoria_code, codice-or-nome)` for sottocategoria and `(sottocategoria_id, codice-or-descrizione)` for voce — if an admin edits a `descrizione` via the CRUD form for a code-less catalog voce (B/C/D families), the natural key silently changes and the *next* Excel upload will treat it as a brand-new row (duplicate) rather than matching the edited one, because the key is derived from mutable descriptive text, not a stable ID.
**Why it happens:** `seed.py`'s existing upsert logic was designed for a stable seed source, not for a scenario where BOTH the CRUD form and the Excel upload can mutate the same row's natural-key fields independently.
**How to avoid:** For the CRUD-edit path on code-less (B/C/D) voci/sottocategorie, either (a) prevent editing the `descrizione`/`nome` field that participates in the natural key from the CRUD form (only allow price/UM edits), or (b) accept the risk and document it as a known v1 limitation (duplicate rows possible after CRUD-rename + re-upload) — this must be an explicit planner decision, not silently inherited from the seed script's assumptions.
**Warning signs:** Duplicate `Voce` rows with near-identical descriptions after a CRUD edit followed by a re-upload of the same source file.

### Pitfall 3: Forgetting `python-multipart` breaks FastAPI startup silently-late
**What goes wrong:** FastAPI does not fail at import time if `python-multipart` is missing — it fails at *request* time on the first `UploadFile`/`Form` endpoint hit, with a runtime error, not a startup error. Since Phase 4 is the first phase using file uploads, this is easy to miss in local dev if the package happens to already be present transitively (as it currently is, 0.0.21) but is not pinned, and could be silently removed/downgraded by an unrelated future `uv sync` if another package's transitive requirement changes.
**Why it happens:** Undeclared transitive dependencies are invisible until they disappear.
**How to avoid:** Add `python-multipart` explicitly to `pyproject.toml` `[project].dependencies` (not dev) as part of Wave 0, and add a smoke test that hits the upload-preview endpoint with a real multipart body (not just unit-testing the parsing function directly) so a missing/broken multipart stack fails CI, not production.
**Warning signs:** `RuntimeError: Form data requires "python-multipart" to be installed.` at request time in logs.

### Pitfall 4: `email_service.send_email` is `async` — calling it from a sync SQLAlchemy request handler
**What goes wrong:** Every existing router in this repo (`stime_salvate.py`, `stima.py`, `admin.py`) uses **sync** `def` handlers with the sync `Session` pattern (`db: Session = Depends(get_db)`), but `send_email()` is an `async def`. The existing reset-password flow (`auth.py`) already solved this — check its exact pattern (`await` inside an `async def` route handler, or a sync wrapper) before reinventing it for the lead router.
**Why it happens:** Mixing sync DB access with an async SMTP call requires either making the whole route handler `async def` (FastAPI supports this fine, sync DB calls just block the event loop briefly — acceptable at this traffic scale) or wrapping the async call with `asyncio.run()`/a sync bridge (worse — avoid).
**How to avoid:** Read `app/routers/auth.py`'s existing `password-dimenticata`/`reimposta-password` handlers (they already call `send_email`) and copy their exact sync/async route-handler pattern verbatim for the new `lead` router — do not re-derive this.
**Warning signs:** `TypeError: object NoneType can't be used in 'await' expression` or a coroutine-never-awaited warning if the call site is wrong.

### Pitfall 5: `city_resolver.resolve_listino` fallback returns a `Listino`, not a disclaimer string — don't conflate the two disclaimer sources
**What goes wrong:** There are now **two** distinct fallback/disclaimer concepts that must not be merged: (a) the existing EST-06 "città senza listino proprio" disclaimer (`DISCLAIMER_TEMPLATE` in `routers/stima.py`, migrating to the `Testo` table per D-14), and (b) the new "città senza referente attivo" fallback (D-05, silent — no user-facing disclaimer, purely an internal routing decision for the email). Migrating (a) to the `Testo` table must not accidentally introduce a user-facing message for (b), which D-05 explicitly describes as invisible to the end user ("Il lead non si perde mai" — the user just sees the normal success confirmation).
**Why it happens:** Both are "fallback to default" concepts using the same `Listino.is_default` flag, inviting a mental merge.
**How to avoid:** Keep the `Testo` table entry for the EST-06 disclaimer separate and unrelated to referente resolution; the referente fallback (D-05) has NO corresponding `Testo` row and NO user-facing string at all in v1.
**Warning signs:** A user-facing "nessun referente disponibile per la tua città" message appearing anywhere in the lead confirmation flow — this contradicts D-05/D-06.

## Code Examples

### Extending `client.ts` with PATCH/PUT/DELETE for admin CRUD
```typescript
// Source: extending the existing pattern in frontend/src/api/client.ts (this repo) —
// current file only has apiGet/apiPost; Phase 4's admin CRUD needs the other three verbs.
export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  if (!API_BASE) throw new Error("VITE_API_BASE non configurato (vedi frontend/.env.example)");
  const response = await fetch(`${API_BASE}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new ApiError(response.status, `PATCH ${path} fallita con status ${response.status}`);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export async function apiDelete(path: string): Promise<void> {
  if (!API_BASE) throw new Error("VITE_API_BASE non configurato (vedi frontend/.env.example)");
  const response = await fetch(`${API_BASE}${path}`, { method: "DELETE", credentials: "include" });
  if (!response.ok) throw new ApiError(response.status, `DELETE ${path} fallita con status ${response.status}`);
}
```

### Admin route ownership pattern (403 vs 404 — extends existing anti-IDOR discipline)
```python
# Source: pattern from app/routers/stime_salvate.py (this repo's existing 404-not-403 anti-IDOR discipline)
# Admin routes differ: there is no per-row ownership check (any admin can edit any row), only the
# require_admin gate itself. Do NOT apply the anti-IDOR 404 pattern here — a missing row under
# require_admin is a plain 404, not a security-sensitive ownership boundary.
@router.patch("/admin/referenti/{referente_id}")
def update_referente(referente_id: int, payload: ReferenteAdminIn, user=Depends(require_admin), db=Depends(get_db)):
    referente = db.get(Referente, referente_id)
    if referente is None:
        raise HTTPException(404, "Referente non trovato")
    ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `openpyxl` used only as a `backend/scripts/` dev tool, never imported under `app/` (03-RESEARCH.md Pitfall 4 rule) | `openpyxl` becomes a runtime dependency imported under `app/services/listino_upload_service.py` | This phase (Phase 4) | The Phase 3 rule "never import openpyxl under app/" is being deliberately superseded by this phase's requirement — the planner should explicitly note this as an intentional precedent change, not an oversight, so a future phase/reviewer doesn't flag it as a Pitfall-4 violation |
| Hardcoded Python string constants for disclaimers (`DISCLAIMER_TEMPLATE` in `routers/stima.py`) | DB-backed `Testo` key/value table, read at request time | This phase (D-14) | Every call site that currently does `DISCLAIMER_TEMPLATE.format(...)` must be changed to a DB read; watch for caching implications — no caching layer exists yet, each request re-queries `Testo`, acceptable at this traffic scale, but note it as a discretionary future optimization, not a blocker |

**Deprecated/outdated:**
- The Phase 3 rule confining `openpyxl` to `backend/scripts/` only is superseded by Phase 4's requirement — see State of the Art table above.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `openpyxl` and `python-multipart` are legitimate, non-hallucinated packages (name/registry existence confirmed via `pip index versions`, but slopcheck itself could not verify due to npm/network mismatch) | Package Legitimacy Audit | Low — both are extremely well-established, and `openpyxl` is already running in production-adjacent code in this exact repo since Phase 3; risk is essentially theoretical |
| A2 | `python-multipart` version `0.0.21` (currently transitively installed) is sufficient for basic `UploadFile` handling without needing the 0.0.32 latest | Standard Stack | Low-medium — if a security fix or bugfix in 0.0.22-0.0.32 is actually needed for large-file handling, an explicit version bump may be required; verify at implementation time |
| A3 | The lead-referente resolution fallback (D-05) should re-implement `resolve_listino`'s branch shape rather than call it directly and then re-query — this is a design choice, not confirmed against any external source, purely inferred from the existing `city_resolver.py` code style | Architecture Patterns Pattern 3 | Low — functionally equivalent either way, purely a code-organization preference the planner/executor can override |
| A4 | Async/sync mixing for `send_email()` should follow whatever pattern `app/routers/auth.py`'s password-reset flow already uses, without having re-read that file's exact route-handler signature in this research session | Common Pitfalls Pitfall 4 | Medium — if the existing pattern turns out to be more complex than assumed (e.g., a background-task wrapper), the planner should have the executor read `auth.py`'s exact reset-password handler before writing the lead router, not copy this research's simplified description verbatim |

**Note on A4:** this file was not re-read in full during this research session (only `email_service.py`/`auth.py`'s dependency usage was inspected via other files) — the planner should instruct the executor to read `backend/app/routers/auth.py`'s `password-dimenticata`/`reimposta-password` handlers directly before implementing the lead router's email call.

## Open Questions (RESOLVED)

> **Stato:** tutte e 3 le domande sono state RISOLTE in fase di pianificazione (Fase 4). Approccio adottato per ciascuna:
>
> - **Q1 (set di chiavi `Testo` e valori seed, D-14) — RESOLVED (piano 04-03):** scope v1 limitato alle stringhe backend-owned e business-meaningful. Chiave minima seedata: `disclaimer_fallback_citta` (migrazione del `DISCLAIMER_TEMPLATE` di `routers/stima.py`), più opzionale `email_conferma_lead_subject`. NON si migrano la copy UI del frontend né l'HTML completo delle email (fuori scope v1). Il backend legge via `testo_service.get_testo()` con fallback in-code; l'admin edita da `/admin/testi` (UI in 04-09).
> - **Q2 (round-trip diff: re-invio completo vs token server) — RESOLVED (piani 04-05/04-08):** adottato il **round-trip stateless** (Pattern 4): il client re-invia a `/confirm` il payload diff completo + la destinazione (`target`), senza cache/sessione server per il pending upload. Scala adeguata (~500KB il file computo). Nessun Redis/tabella sessione introdotti.
> - **Q3 (stabilità natural-key delle voci code-less B/C/D, Pitfall 2) — RESOLVED (piano 04-02, Blocker #2):** adottata la mitigazione "no edit descrizione via CRUD": lo schema `VoceAdminIn` espone SOLO `prezzo_cliente` e `um`; `descrizione`/`codice` NON sono editabili dal CRUD. Così la chiave naturale resta stabile e un successivo upload Excel ri-matcha la riga per chiave anziché duplicarla. Nessun cambio di schema DB richiesto.

### Dettaglio originale delle domande (per contesto)


1. **Exact set of `Testo` table keys and their seed values (D-14, discretion)**
   - What we know: at minimum the EST-06 fallback disclaimer (`DISCLAIMER_TEMPLATE` in `routers/stima.py`) must migrate; `04-UI-SPEC.md` Open Question 5 leaves the full key set to the planner.
   - What's unclear: whether other strings (PDF footer/legal text, empty-state copy, lead confirmation email subject/body template) should also become DB-editable in v1, or stay as frontend/template-hardcoded copy.
   - Recommendation: scope v1 `Testo` migration to backend-owned, business-meaningful strings only (disclaimers, referente-fallback-adjacent copy if any is added later) — do NOT migrate frontend UI copy (that's a frontend i18n concern, out of scope) or the email templates' full HTML body (too complex for a plain key/value row; if email template editability is wanted, that's a v2 feature, not implied by D-14's "testi/disclaimer" scope).

2. **Whether the Excel-upload diff-preview payload should be re-submitted whole from client to `/confirm`, or referenced by a server-side token/cache**
   - What we know: Pattern 4 above proposes a stateless round-trip (client re-sends the full parsed diff back to `/confirm`).
   - What's unclear: for a large listino (hundreds of rows), the JSON payload size for a full round-trip could be non-trivial (though still well within normal request-size limits — the computo file itself is only ~500KB).
   - Recommendation: stateless round-trip is fine at this data scale; if the planner prefers a server-side short-lived cache (e.g., an in-memory dict keyed by a UUID token with a TTL) to avoid re-sending the full payload, that's a valid v1-scoped alternative — no data-scale reason forces one approach over the other, this is purely an implementation-ergonomics choice.

3. **CRUD-edit natural-key stability for code-less (B/C/D family) voci/sottocategorie (Pitfall 2)**
   - What we know: the seed script's upsert natural key for code-less rows includes the mutable `nome`/`descrizione` field.
   - What's unclear: whether this is an acceptable v1 limitation or needs a schema change (e.g., adding a stable surrogate natural key independent of description).
   - Recommendation: flag explicitly to the planner as a decision point — simplest v1 mitigation is to disable descrizione-editing via CRUD for code-less rows (price/UM only editable), sidestepping the problem entirely without a schema change.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| openpyxl | Excel upload parsing (D-18/D-19/D-20) | ✓ | 3.1.5 (already installed, dev scope — needs promotion to runtime) | — |
| python-multipart | `UploadFile` handling for the upload endpoint | ✓ (transitive, unpinned) | 0.0.21 installed / 0.0.32 latest | — must be pinned explicitly, no viable fallback (FastAPI hard-requires it for multipart) |
| SMTP (dev fallback via `email_service.py`) | Lead notification + confirmation emails (D-07/D-08) | ✓ (log-fallback works without real SMTP creds) | n/a | Already has a documented, tested fallback — no action needed |
| Postgres/SQLite (existing) | `Lead`/`Testo` tables, all CRUD | ✓ | unchanged from prior phases | — |

**Missing dependencies with no fallback:** none — `python-multipart` requires explicit pinning but is already present.
**Missing dependencies with fallback:** none blocking.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 (backend, already configured and used in every prior phase — 107 passed/4 skip as of Phase 3 completion) |
| Config file | `backend/pyproject.toml` (existing pytest config, unchanged) |
| Quick run command | `uv run pytest backend/tests/test_lead.py -x` (per new test file, adjust path) |
| Full suite command | `uv run pytest` (from `backend/`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LEAD-01 | Loggato Free/Pro puo' richiedere contatto | integration | `pytest backend/tests/test_lead.py::test_post_lead_authenticated -x` | ❌ Wave 0 |
| LEAD-02 | Lead salvato + email al referente | integration | `pytest backend/tests/test_lead.py::test_lead_persisted_and_email_sent -x` | ❌ Wave 0 |
| LEAD-03 | Multi-referente per città, fallback default | unit | `pytest backend/tests/test_lead.py::test_resolve_referente_fallback_default -x` | ❌ Wave 0 |
| ADM-01 | Admin CRUD listini/prezzi + upload | integration | `pytest backend/tests/test_admin_listini.py -x` + `pytest backend/tests/test_upload_listino.py -x` | ❌ Wave 0 |
| ADM-02 | Admin CRUD coefficienti | integration | `pytest backend/tests/test_admin_coefficienti.py -x` | ❌ Wave 0 |
| ADM-03 | Admin CRUD città/testi/tipi | integration | `pytest backend/tests/test_admin_citta.py -x` + `pytest backend/tests/test_admin_testi.py -x` | ❌ Wave 0 |
| ADM-04 | Admin dashboard lead + CRUD referenti | integration | `pytest backend/tests/test_admin_lead.py -x` + `pytest backend/tests/test_admin_referenti.py -x` | ❌ Wave 0 |
| Anti-leak (D-10/D-22) | `coefficiente_impresa`/`base_eur_mq` never in non-admin responses, present in admin ones | unit (recursive grep-style, per existing `test_no_leak.py` pattern) | `pytest backend/tests/test_no_leak.py -x` (extend existing file) | ✅ file exists, extend with Phase 4 cases |
| D-24 guardrail | Upload/CRUD never zeroes existing data, migration preserves seed | integration | `pytest backend/tests/test_upload_listino.py::test_upload_does_not_zero_existing_rows -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** targeted test file for the task's router/service.
- **Per wave merge:** `uv run pytest` (full backend suite) + `npx tsc --noEmit` (frontend).
- **Phase gate:** Full suite green before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `backend/tests/test_lead.py` — covers LEAD-01/02/03
- [ ] `backend/tests/test_admin_listini.py`, `test_admin_coefficienti.py`, `test_admin_citta.py`, `test_admin_testi.py`, `test_admin_referenti.py` — covers ADM-01..04 CRUD
- [ ] `backend/tests/test_admin_lead.py` — covers ADM-04 dashboard
- [ ] `backend/tests/test_upload_listino.py` — covers D-18/D-19/D-20/D-24
- [ ] Extend existing `backend/tests/test_no_leak.py` with Phase 4 admin-vs-public schema cases
- [ ] No new framework/config install needed — pytest already fully configured

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | yes (reused) | Existing `get_current_user`/session-cookie mechanism — no change needed for the lead endpoint (requires login) |
| V3 Session Management | yes (reused) | Existing DB-backed opaque session, unchanged |
| V4 Access Control | yes | `require_admin` on all 7+ admin routers (server-side role check, never client-trusted) — this phase is the FIRST to exercise `require_admin` at scale (previously only a stub `/admin/ping`); every new admin route MUST use the dependency, verified by a router-level grep/test sweep, not per-route memory |
| V5 Input Validation | yes | Pydantic `*In` schemas bound all admin CRUD input (numeric ranges on prices/coefficients — e.g. `coefficiente_impresa` should be `Field(gt=0, le=1)`, matching the 0.5–0.65 domain range observed in seed data); the lead form (`LeadCreate`) bounds `messaggio` length, `preferenza_contatto` to an enum, `telefono` format |
| V6 Cryptography | no new surface | No new crypto — reuses existing session/password infra untouched |
| V12 File Upload (mapped from ASVS 12.x, ASVS v4 numbering) | yes — new for this phase | `.xlsx`-only extension AND content-type check, magic-byte/openpyxl-parseability check (not just extension trust), 10MB size cap enforced server-side before full read into memory (D-20), never execute/eval anything from the file, never trust sheet names/cell formulas (openpyxl by default does not evaluate formulas unless explicitly requested — do not request formula evaluation) |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| Malicious/oversized `.xlsx` upload (zip bomb, XXE-adjacent in legacy Excel XML) | Denial of Service | Size cap (10MB) enforced BEFORE reading file content into `openpyxl.load_workbook()`; openpyxl uses `defusedxml`-hardened parsing internally for modern versions — confirm 3.1.5 still uses safe XML parsing (it does, per openpyxl's own security posture, though this specific claim is [ASSUMED] from general library knowledge, not re-verified via Context7/official docs in this session) |
| Non-admin reaching an admin CRUD endpoint by guessing the URL | Elevation of Privilege | `require_admin` dependency on every route — this is a hard, non-negotiable requirement given D-10 makes admin endpoints the ONLY place `coefficiente_impresa` is ever exposed; a single missing `Depends(require_admin)` on one admin router is a full anti-leak breach, not just an access-control bug |
| Lead form spam / unauthenticated abuse | Denial of Service / Tampering | Login already required (D-01) — this alone is a meaningful barrier; consider reusing the existing `slowapi` rate limiter (already used on `/stima` and `/login`) on the lead POST endpoint, since anti-abuse for a real-world contact form is a reasonable v1 concern even though CONTEXT.md doesn't explicitly mandate it — planner's discretion, low-cost given the limiter module already exists |
| Excel upload used as a vector to inject arbitrary prices (e.g., negative prices, absurd `coefficiente_impresa` outside 0-1) | Tampering | Same Pydantic-style bounds validation applied to parsed rows as to CRUD form input — the diff/upsert service must NOT trust raw cell values as final; validate ranges (price > 0, `coefficiente_impresa` in (0,1], UM in an allowed set) before including a row in "nuove"/"modificate", otherwise route it to "scarti" with a validation-failure reason |

## Sources

### Primary (HIGH confidence — direct repo inspection)
- `backend/app/models/catalogo.py`, `listino.py`, `dettaglio_pro.py`, `stima_salvata.py` — schema/anti-leak precedent
- `backend/app/services/email_service.py`, `city_resolver.py`, `estimation.py` — reusable service patterns
- `backend/app/dependencies/auth.py` — `require_admin`/`get_current_user` contract
- `backend/app/routers/admin.py`, `stima.py` — existing router shape, `DISCLAIMER_TEMPLATE` location
- `backend/scripts/extract_dettaglio_pro.py`, `scripts/seed.py` — openpyxl parsing logic and idempotent-upsert precedent to adapt
- `backend/alembic/versions/0005_dettaglio_pro.py` — migration chain starting point
- `backend/pyproject.toml`, `frontend/package.json` — current dependency inventory
- `docs/computo-struttura-dettaglio.md` — source Excel structure reference
- `.planning/phases/04-lead-pannello-admin/04-CONTEXT.md`, `04-UI-SPEC.md` — locked decisions and UI contract
- `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, `CLAUDE.md` — requirement IDs, project history, domain rules

### Secondary (MEDIUM confidence)
- `pip index versions openpyxl` / `python-multipart` — registry existence and version currency (executed this session)

### Tertiary (LOW confidence — flagged for validation)
- openpyxl's internal XML-parsing safety posture (zip-bomb/XXE mitigation) — stated from general library knowledge, not re-verified against openpyxl's own changelog/security docs in this session; low risk given the admin-only, size-capped, single-purpose use case, but the planner should not treat this claim as verified

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — both new dependencies already present/precedented in this exact repo, versions confirmed via PyPI
- Architecture: HIGH — every pattern grounded in an existing, working file in this repo; the one genuinely novel piece (two-step upload flow) is clearly marked as new with no false precedent claimed
- Pitfalls: MEDIUM-HIGH — Pitfalls 1-2 and 5 are grounded in direct code/STATE.md inspection; Pitfall 4 (async/sync email call site) is flagged as needing a fresh read of `auth.py` at implementation time rather than fully verified here (see Assumption A4)

**Research date:** 2026-08-27
**Valid until:** 30 days (stable internal stack, no fast-moving external dependency)
