# Phase 09: Configuratore Pro e chiusura del bug dei cataloghi - Pattern Map

**Mapped:** 2026-09-25
**Files analyzed:** 14 (backend 10, frontend 4) + 1 standalone deliverable (Excel di taratura, no code analog)
**Analogs found:** 14 / 14 (all files are refactors/extensions of existing files — analogs are largely the files themselves, pre-refactor state, plus one cross-domain sibling for each new pattern)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `backend/alembic/versions/00NN_domande_pro_finitura_pavimento.py` | migration | batch | `backend/alembic/versions/0010_livello_finitura.py` (additive) + `0019_updated_at_curatela.py` (SQLite 3-step non-constant default) | exact (two analogs cover the two migration shapes needed) |
| `backend/app/services/effetti.py` (extend: `risolvi_effetti_pro`) | service | transform | same file, `risolvi_effetti_free()` (lines 495-566) + `_applica_effetto_free()` (569-651) | exact (sibling function, same module) |
| `backend/app/services/dettaglio_pro.py` (rewrite `compute()`) | service | CRUD (read-heavy compute) | same file, pre-refactor `_voce_inclusa()`/`_quantita()` (257-298) | exact (self-refactor) |
| `backend/app/services/computo_parsing.py` (extend `coefficienti_per_voce`) | utility | transform | same file (65-94) | exact (self-refactor) |
| `backend/app/models/dettaglio_pro.py` (`Voce.livello` deprecation note) | model | CRUD | same file + `backend/app/models/domanda.py` (EffettoOpzione shape) | exact |
| `backend/app/schemas/dettaglio_pro.py` (extend Risposte*/DettaglioProOut) | schema | request-response | same file (99-108, `RisposteDomandeRequest`) | exact (self-refactor) |
| `backend/app/routers/dettaglio_pro.py` (`_compute_dettaglio`, `_to_out`) | route/controller | request-response | same file (166-270) | exact (self-refactor, no route shape change expected) |
| `backend/scripts/seed.py` (extend `seed_domande`) | utility (seed) | batch/idempotent-upsert | same file, `seed_domande()` (521-611) + `_crea_effetto_se_manca()` (678-711) | exact |
| `backend/tests/test_dettaglio_pro_livelli.py` → generalize to CFG-02 | test | integration | same file (`TestFiltroPuro`, `TestRetrocompatibilita`, 76-120) | exact (self-refactor) |
| `backend/tests/test_effetti.py` (new, unit for `risolvi_effetti_pro`) | test | unit | `backend/app/services/effetti.py` docstrings/structure (no existing `test_effetti.py` found — see No Analog) | role-match |
| `frontend/src/components/DettaglioProView.tsx` (extend §A UI-SPEC) | component | request-response (react-query) | same file (30-332), esp. livelli selector block (201-242) as template for pavimento `OptionCard` grid | exact (self-refactor) |
| `frontend/src/api/dettaglio-pro.ts` (extend payload with `tipo_pavimento` / generic risposte) | service (API client) | request-response | same file (38-222), `RisposteDomande`/`normalizeDettaglioPro` | exact (self-refactor) |
| `frontend/src/components/DomandaField.tsx` | component | request-response | itself (invariant, reused as-is) — no changes needed | exact (already generic, no work) |
| Excel di taratura (D-04 deliverable) | file-I/O (generation script/one-off) | batch | `backend/app/services/export_excel/parametri.py` foglio `coefficienti_pro` (41-49, 114-132, 184-186) | exact (reuse existing sheet, add extra ignored columns) |

## Pattern Assignments

### `backend/alembic/versions/00NN_domande_pro_finitura_pavimento.py` (migration, batch)

**Analog 1 — additive migration with new table + nullable columns:** `backend/alembic/versions/0010_livello_finitura.py` (full file, 63 lines)

```python
# Source: backend/alembic/versions/0010_livello_finitura.py, lines 39-54
op.create_table(
    'livello_finitura',
    sa.Column('code', sa.String(length=16), nullable=False),
    sa.Column('nome', sa.String(length=100), nullable=False),
    sa.Column('ordine', sa.Integer(), server_default='0', nullable=False),
    sa.Column('descrizione', sa.String(length=300), nullable=True),
    sa.Column('is_default', sa.Boolean(), server_default='0', nullable=False),
    sa.PrimaryKeyConstraint('code'),
)
op.add_column(
    'categoria',
    sa.Column('livello_selezionabile', sa.Boolean(), server_default='0', nullable=False),
)
op.add_column('voce', sa.Column('livello', sa.String(length=16), nullable=True))
op.add_column('stima', sa.Column('livelli_pro_json', sa.JSON(), nullable=True))
```
Downgrade mirrors with `drop_column`/`drop_table` in reverse order (lines 57-62). **NESSUN backfill** — NULL è il valore corretto, retrocompatibilità garantita per costruzione.

**Analog 2 — SQLite 3-step pattern for NOT NULL + non-constant server_default:** `backend/alembic/versions/0019_updated_at_curatela.py` (full file, 100 lines)

```python
# Source: backend/alembic/versions/0019_updated_at_curatela.py, lines 75-86
for tabella in _TABELLE:
    op.add_column(tabella, sa.Column("updated_at", sa.DateTime(), nullable=True))
    op.execute(
        sa.text(f"UPDATE {tabella} SET updated_at = :adesso").bindparams(adesso=adesso)
    )
    with op.batch_alter_table(tabella) as batch:
        batch.alter_column(
            "updated_at",
            existing_type=sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        )
```
**Only needed if** the new migration introduces a NOT NULL column with a non-constant default (e.g. `Domanda.tier_minimo` already has a constant default so plain `add_column` suffices, per `0020_attiva_updated_at_catalogo.py` pattern — constant default -> no batch mode needed).

**What CFG-03 needs concretely:** no new table (Domanda/OpzioneDomanda/EffettoOpzione already exist from Fase 08.1) — this migration is pure DATA migration (backfill rows), not schema. If a schema change is still needed (e.g. nothing structural is required per RESEARCH, this may end up being a **data-only migration**, i.e. an `op.execute()` block or, per project convention, a seed-time backfill in `scripts/seed.py` rather than Alembic). Check `docs/seed-dettaglio-pro.json` shape before deciding.

---

### `backend/app/services/effetti.py` — new `risolvi_effetti_pro()` (service, transform)

**Analog:** same file, `risolvi_effetti_free()` (lines 495-566) is the structural template; `_applica_effetto_free()` (569-651) is the per-effect dispatcher template.

**Imports already present** (lines 60-76): `Decimal`, `Session`, `Categoria`, `Sottocategoria`, `Voce`, `Domanda`, `EffettoOpzione`, `OpzioneDomanda` — no new imports expected.

**Core pattern to mirror** (risolvi_effetti_free, lines 495-528):
```python
def risolvi_effetti_free(
    session: Session, *, mq: int, tipo: str, risposte: dict[str, Any] | None,
) -> RisoluzioneFree:
    scelte = risolvi_scelte(session, risposte=risposte, tier=TIER_FREE)
    opzioni_attive = scelte.opzioni
    if not opzioni_attive:
        return _VUOTA
    domande = scelte.domande
    effetti_per_opzione: dict[int, list[EffettoOpzione]] = {o.id: [] for o in opzioni_attive}
    for e in (
        session.query(EffettoOpzione)
        .filter(
            EffettoOpzione.opzione_id.in_(list(effetti_per_opzione)),
            EffettoOpzione.attivo.is_(True),
            EffettoOpzione.tipo_effetto.in_(sorted(TIPI_EFFETTO_FREE)),
        )
        .order_by(EffettoOpzione.id)
        .all()
    ):
        if e.tipo_code is None or e.tipo_code == tipo:
            effetti_per_opzione[e.opzione_id].append(e)
    ...
```
`risolvi_effetti_pro()` swaps `TIPI_EFFETTO_FREE` for `TIPI_EFFETTO_PRO` (already defined, line 97-99: `{TIPO_INCLUDI, TIPO_ESCLUDI, TIPO_FATTORE_QUANTITA, TIPO_QUANTITA_PER_UNITA}`) and `TIER_FREE` for `TIER_PRO` (line 114) in the `risolvi_scelte()` call — the resolver call itself needs zero changes.

**Ordering contract (CONTEXT Pattern 2, non-negotiable):** exclusions win > single-choice axis keeps only chosen/default option's voices > un-governed voices always included > quantity chain > discard empty subcategories. This is a NEW aggregation shape (not per-category euro sums like Free, but per-voce include/exclude/quantity-factor sets) — build a new `RisoluzionePro` dataclass mirroring `RisoluzioneFree` (lines 174-181) but with `voci_escluse: set[int]`, `voci_incluse_per_asse: dict[str, set[int]]` (keyed by asse/domanda_code), `fattori_quantita: dict[int, Decimal]`, `quantita_per_unita: dict[int, Decimal]`.

**Error handling pattern** (from `_applica_effetto_free`, lines 569-612): never raise mid-compute — return a traced "not applied" result with `nota`, same discipline for a malformed Pro effetto row (e.g. `TIPO_QUANTITA_PER_UNITA` with `valore is None`).

---

### `backend/app/services/dettaglio_pro.py` — rewrite `compute()` (service, CRUD/read-heavy)

**Analog:** same file's pre-refactor `_voce_inclusa()` (257-279) + `_quantita()` (281-298) + the main `compute()` loop (127-255).

**Imports pattern** (lines 27-36) — add `from app.services import effetti` (or the specific `risolvi_effetti_pro`/`risolvi_scelte` names) alongside existing:
```python
from __future__ import annotations
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from sqlalchemy.orm import Session
from app.models.catalogo import Categoria, LivelloFinitura, TipoRistrutturazione
from app.models.dettaglio_pro import CoefficienteQuantitaVoce, Sottocategoria, Voce
from app.models.listino import Listino
```

**Core pattern to replace** (the filter that CFG-01 eliminates):
```python
# Source: backend/app/services/dettaglio_pro.py, lines 175-181 (TO BE REPLACED)
voce_rows_incluse = [
    v
    for v in voce_rows
    if DettaglioProService._voce_inclusa(
        v.livello, cat.livello_selezionabile, livello_scelto
    )
]
```
becomes a lookup against the pre-computed `RisoluzionePro` (voce.id in `voci_escluse` -> drop; voce.id present in any `voci_incluse_per_asse` set but not the active one -> drop; voce.id ungoverned -> keep). **Same discard-empty-subcategory guard must be preserved** (lines 209-213, 228-234):
```python
if voce_rows and not voci:
    continue
...
if not sotto_rows:
    continue
```

**Quantity chain to extend** (lines 281-298, `_quantita()`): keep `coefficiente_qta_per_mq` branch as-is; the `domanda_mirata_key` branch is replaced by reading `quantita_per_unita` from the resolved `RisolzionePro` for that voce, then applying `fattore_quantita` if present — this is the CFG-01/QST-05 core work.

**Retrocompatibility discipline (Pattern 3 from RESEARCH):** the docstring already states the invariant to preserve: "`livello_scelto is None -> tutto incluso`" and "`voce_livello is None -> inclusa sempre`" — the generalized version must keep an equivalent "no governing effetto -> always included" clause.

---

### `backend/app/services/computo_parsing.py` — extend `coefficienti_per_voce()` (utility, transform)

**Analog:** same file, current uniform-bozza implementation (lines 65-94).

```python
# Source: backend/app/services/computo_parsing.py, lines 65-94 (current uniform bozza to replace/extend per D-03)
def coefficienti_per_voce(um: str, descrizione: str) -> dict:
    um_norm = (um or "").strip().lower()
    coeff: dict[str, dict] = {}
    if um_norm in MQ_UM:
        for tipo in TIPI:
            coeff[tipo] = {"coefficiente_qta_per_mq": round(0.6 * TIPO_FACTOR[tipo], 4)}
    elif um_norm in ML_UM:
        for tipo in TIPI:
            coeff[tipo] = {"coefficiente_qta_per_mq": round(0.15 * TIPO_FACTOR[tipo], 4)}
    elif um_norm in CAD_UM:
        domanda_key = detect_domanda_mirata(descrizione)
        ...
```
**Pitfall 4 (RESEARCH):** this function is shared between `scripts/extract_dettaglio_pro.py` (one-off) and `listino_upload_service.py` (runtime admin upload). The planner must decide explicitly whether D-03's tarata formula replaces the bozza INSIDE this function (affecting every future upload) or lives only as a one-time UPDATE applied via the Excel channel — do not silently pick one in the plan.

---

### `backend/app/schemas/dettaglio_pro.py` — extend Risposte*/DettaglioProOut (schema, request-response)

**Analog:** same file, `RisposteDomandeRequest` (99-108) and `DettaglioProOut` (78-96).

```python
# Source: backend/app/schemas/dettaglio_pro.py, lines 99-108 (current, 3 hardcoded fields)
class RisposteDomandeRequest(BaseModel):
    bagni: int = Field(ge=0, le=20)
    porte: int = Field(ge=0, le=100)
    condizionatori: int = Field(ge=0, le=50)
    livelli: dict[str, str] | None = None
```
**Open Question 2 (RESEARCH):** planner must fix explicitly whether this migrates to a generic `risposte: dict[str, Any]` (matching Free's `risolvi_scelte()` contract and the UI-SPEC's `DomandaField`-driven frontend) or keeps dedicated fields plus a new `tipo_pavimento: str | None`. **Validation pattern to keep either way:** `Field(ge=..., le=...)` bounds (V5 ASVS), same as `StimaRequest.mq` — if migrating to generic dict, bounds move server-side via catalog validation (same as Free), not a hardcoded range.

---

### `backend/app/routers/dettaglio_pro.py` — `_compute_dettaglio`/`_to_out` (route, request-response)

**Analog:** same file (166-270) — single source of truth for GET/POST/pdf-pro, must stay that way.

```python
# Source: backend/app/routers/dettaglio_pro.py, lines 166-184
def _compute_dettaglio(session: Session, row: StimaSalvata) -> tuple[DettaglioProResult, dict, bool]:
    listino, _fallback = resolve_listino(session, row.citta)
    risposte_salvate = row.risposte_pro_json is not None
    risposte = row.risposte_pro_json or {}
    livelli = row.livelli_pro_json or {}
    result = DettaglioProService.compute(session, listino, row.mq, row.tipo, risposte, livelli)
    return result, risposte, risposte_salvate
```
Any change to `DettaglioProService.compute()`'s signature (e.g. adding `tipo_pavimento`) must be threaded through this single function — never duplicate the call elsewhere (PDF Pitfall from Open Question 3: verify `PdfService.render_pro` / `pdf_stima_pro.html` don't have a second calculation path).

**Ownership/tier gate pattern to keep untouched** (`_get_owned_stima`, 135-163): 404-then-403 ordering, no changes needed this phase.

---

### `backend/scripts/seed.py` — extend `seed_domande()` for new Pro domande (utility, batch idempotent upsert)

**Analog:** same file, `seed_domande()` (521-611) + `_crea_effetto_se_manca()` (678-711).

```python
# Source: backend/scripts/seed.py, lines 544-586 — create-if-missing pattern, MUST be preserved
for d_data in data.get("domande", []):
    domanda = session.get(Domanda, d_data["code"])
    if domanda is None:
        domanda = Domanda(code=d_data["code"], testo=d_data["testo"], ...)
        session.add(domanda)
        session.flush()
    # else: gia' presente -> curatela del pannello, non si tocca.
    for o_data in d_data.get("opzioni", []):
        opzione = session.query(OpzioneDomanda).filter_by(
            domanda_code=domanda.code, code=o_data["code"]
        ).one_or_none()
        if opzione is None:
            opzione = OpzioneDomanda(domanda_code=domanda.code, code=o_data["code"], ...)
            session.add(opzione)
            session.flush()
        for e_data in o_data.get("opzioni", []):
            _crea_effetto_se_manca(session, opzione, e_data)
```
**D-41 constraint (non-negotiable):** the new `finitura`/`tipo_pavimento`/3-stepper seed rows follow the exact same create-if-missing discipline — the seed NEVER overwrites curatela on an existing row. New JSON source data likely extends `docs/seed-dettaglio-pro.json` (verify exact source key before writing the plan).

`_crea_effetto_se_manca()` (678-711) is the natural-key dedup pattern for the new `includi`/`quantita_per_unita` effetti rows this migration creates (natural key = opzione_id + tipo_effetto + target_* + tipo_code, excluding `valore`).

---

### `backend/tests/test_dettaglio_pro_livelli.py` → generalize to CFG-02 test (test, integration)

**Analog:** same file (full read, 481 lines total; first 120 shown here).

```python
# Source: backend/tests/test_dettaglio_pro_livelli.py, lines 40-73 — fixture + helper pattern to reuse
@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)
    with testing_session_local() as s:
        seed(s, load_seed_data())
        yield s

def _compute(session, **kwargs):
    listino, _ = resolve_listino(session, "Reggio Emilia")
    return DettaglioProService.compute(session, listino, mq=85, tipo="totale", risposte={}, **kwargs)
```
```python
# Source: lines 76-95 — pure-function test class pattern for the filter logic (mirror for risolvi_effetti_pro)
class TestFiltroPuro:
    def test_categoria_non_selezionabile_include_tutto(self):
        assert DettaglioProService._voce_inclusa("alto", False, "base") is True
    ...

class TestRetrocompatibilita:
    def test_oracolo_per_voce_invariato(self, session):
        result = _compute(session)
        voce = next(v for cat in result.categorie for sotto in cat.sottocategorie
                     for v in sotto.voci if v.codice == "A.1.1.1")
        assert voce.quantita_stimata == Decimal("51.00")
        assert voce.prezzo_min == Decimal("1836")
        assert voce.prezzo_max == Decimal("2754")
```
**CFG-02 test to generalize:** current file only asserts single-family behavior for GRES (`_sotto_gres`, `_voci_di`, `_descrizioni_sotto` helpers at lines 50-73). New test must iterate ALL `famiglia='catalogo'` subcategories + the A.6 axis on A-EDILE, asserting `len(voci_alternative_incluse) <= 1` per subcategory/asse. Same fixture, same `_compute()` helper, same oracle-protection style (`test_oracolo_per_voce_invariato`).

---

### `backend/tests/test_effetti.py` (new, unit for `risolvi_effetti_pro`) — No strong analog

No `test_effetti.py` exists yet. Closest structural pattern: `test_dettaglio_pro_livelli.py::TestFiltroPuro` (pure-function-style unit tests, no DB) combined with the module docstring's own worked examples in `effetti.py` (lines 8-58). Build fixtures the same way `test_dettaglio_pro_livelli.py` does (in-memory SQLite + `seed()`), test `risolvi_effetti_pro()` directly against seeded Pro domande.

---

### `frontend/src/components/DettaglioProView.tsx` (component, request-response)

**Analog:** same file's existing livelli selector block, to be the exact template for the new pavimento `OptionCard` grid (§A.2 UI-SPEC).

```tsx
// Source: frontend/src/components/DettaglioProView.tsx, lines 201-242 — OptionCard-equivalent grid pattern to replicate for pavimento
{categorieConLivello.length > 0 && livelliDisponibili.length > 0 && (
  <div className="flex flex-col gap-4">
    <p className="text-sm text-muted-foreground">{LIVELLI_SUBHEADING}</p>
    {categorieConLivello.map((categoria) => (
      <div key={categoria.code} className="flex flex-col gap-2">
        <Label>{categoria.nome}</Label>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {livelliDisponibili.map((livello) => {
            const selected = (livelliInput[categoria.code] ?? categoria.livello_scelto) === livello.code;
            return (
              <button ... className={cn("relative flex min-h-11 flex-col gap-1 rounded-lg border px-4 py-3 text-left transition-all",
                selected ? "border-primary bg-accent shadow-sm ring-1 ring-primary" : "border-border bg-card hover:border-primary/40 hover:bg-accent/40")}>
```
UI-SPEC §A.2 requires `grid grid-cols-2 gap-3` (fixed 2x2, not `sm:grid-cols-3`) — deviate from this exact template on the grid class only, keep the `OptionCard`/button styling identical. **Prefer using the real `OptionCard` from `EstimateFormFields.tsx` via `DomandaField`** per UI-SPEC §A.1 rather than hand-rolling another inline button block — this hand-rolled livelli block predates `DomandaField` and is NOT the pattern to copy structurally, only visually.

```tsx
// Source: lines 244-259 — Input-based stepper block TO BE REPLACED by DomandaField/NumberStepper (§A.3)
<div className="flex flex-col gap-3">
  {(Object.keys(FIELD_LABELS) as (keyof RisposteDomande)[]).map((field) => (
    <div key={field} className="flex flex-col gap-1">
      <Label htmlFor={field}>{FIELD_LABELS[field]}</Label>
      <Input id={field} inputMode="numeric" min={0} value={risposteInput[field]}
        onChange={(e) => handleFieldChange(field, e.target.value)} className="tabular-nums" />
    </div>
  ))}
</div>
```
Replace with `<DomandaField domanda={...} valore={...} onChange={...} />` per catalog-sourced `domanda.testo` (no more `FIELD_LABELS` constant) — see `DomandaField.tsx` analog below.

**Validation state to REMOVE** (§A.3, Copywriting Contract): `isValid()` (46-51), `validationError` (135), `VALIDATION_COPY` (26) — `NumberStepper` makes an invalid state structurally impossible, this whole block is deleted, not migrated.

---

### `frontend/src/api/dettaglio-pro.ts` (service/API client, request-response)

**Analog:** same file, `RisposteDomande` interface (38-42) and `normalizeDettaglioPro` (123-156).

```typescript
// Source: frontend/src/api/dettaglio-pro.ts, lines 38-42 (current, fixed shape — extend or genericize per Open Question 2)
export interface RisposteDomande {
  bagni: number;
  porte: number;
  condizionatori: number;
}
```
```typescript
// Source: lines 119-121 — Decimal-as-string normalization pattern, reuse verbatim for any new numeric field
function toNumber(value: unknown): number {
  return typeof value === "number" ? value : Number(value);
}
```
If `tipo_pavimento` is added as a 4th dedicated field (rather than migrating to generic risposte), it is a plain string code — no `toNumber()` needed, same pass-through style as `livelli`/`livelli_disponibili` (lines 111-116, explicitly NOT passed through `toNumber`).

---

### `frontend/src/components/DomandaField.tsx` — no changes, full reuse

**Analog:** itself. Already renders `stepper`/`scelta_singola` generically via `isNumerico()` + `NumberStepper` + `OptionCard` (lines 50-112). UI-SPEC §A.1 confirms zero pixel changes needed here — the 3 stepper fields and the new pavimento selector both route through this component unmodified, driven by `domanda.tipo_controllo` from the catalog.

```tsx
// Source: frontend/src/components/DomandaField.tsx, lines 93-111 — scelta_singola rendering, used as-is for pavimento
return (
  <div className={cn("grid grid-cols-1 gap-3", domanda.opzioni.length === 2 ? "sm:grid-cols-2" : "sm:grid-cols-3")}>
    {domanda.opzioni.map((opzione) => (
      <OptionCard key={opzione.code} nome={opzione.etichetta} descrizione={opzione.descrizione ?? ""}
        selected={valore === opzione.code} onSelect={() => onChange(opzione.code)} />
    ))}
  </div>
);
```
**Caveat (UI-SPEC §A.2):** the generic grid rule (`opzioni.length === 2 ? "sm:grid-cols-2" : "sm:grid-cols-3"`) produces an unbalanced layout for pavimento's 4 options in the 640px-wide panel. UI-SPEC calls this an explicit exception requiring `grid grid-cols-2 gap-3` fixed at all breakpoints — this means `DomandaField.tsx` itself may need a small conditional (e.g. `opzioni.length === 4 ? "grid-cols-2" : ...`) OR the panel wraps pavimento's rendering differently. Planner must decide whether this is a `DomandaField.tsx` change (small, affects all 4-option future questions too) or a one-off override — flag as an explicit task.

---

### Excel di taratura (D-04 deliverable) — file-I/O, batch

**Analog:** `backend/app/services/export_excel/parametri.py`, foglio `coefficienti_pro` (COLONNE_COEFF_PRO, lines 41-49; `_righe_coeff_pro`, 114-132; wiring in `build_workbook_parametri`, 184-186).

```python
# Source: backend/app/services/export_excel/parametri.py, lines 41-49
COLONNE_COEFF_PRO = [
    "id", "voce_id", "voce_descrizione", "tipo_code",
    "coefficiente_qta_per_mq", "domanda_mirata_key", "default_conteggio",
]
```
```python
# Source: backend/app/services/import_excel/parametri.py, lines 64, 74, 84
FOGLIO_COEFF_PRO = "coefficienti_pro"
COLONNE_COEFF_PRO = {"id", "voce_id", "tipo_code", "coefficiente_qta_per_mq", "domanda_mirata_key", "default_conteggio"}
_CAMPI_NULLABLE_PER_FOGLIO[FOGLIO_COEFF_PRO] = {"coefficiente_qta_per_mq", "domanda_mirata_key", "default_conteggio"}
```
**D-04 delivery mechanism:** generate a workbook using the SAME `coefficienti_pro` sheet, with EXTRA columns appended for curatela (`coefficiente_attuale`, `coefficiente_proposto`, `motivazione`, `decisione`, `note`) that `import_excel/parametri.py::leggi_foglio_piatto()` will silently ignore on re-import (confirmed by `colonne_ammesse` filtering behavior, Pitfall 3 in RESEARCH — do NOT add these to `COLONNE_COEFF_PRO` in `import_excel/parametri.py`, that would make them writable and break the model). This is likely a standalone one-off script (e.g. `backend/scripts/genera_excel_taratura.py`), not a route — no UI contract applies (UI-SPEC explicitly excludes this file from its scope).

## Shared Patterns

### Idempotent seed (create-if-missing, never overwrite curatela)
**Source:** `backend/scripts/seed.py`, `seed_domande()` (lines 544-586, 678-711)
**Apply to:** any new `Domanda`/`OpzioneDomanda`/`EffettoOpzione` rows created by CFG-03's migration/seed step. Never update an existing row's fields — only `session.get()`/`filter_by().one_or_none()` then create-if-None.

### Single resolver for domanda→opzione (no second resolver)
**Source:** `backend/app/services/effetti.py::risolvi_scelte()` (lines 442-492), already parametric on `tier`
**Apply to:** `DettaglioProService.compute()` — call `risolvi_scelte(session, risposte=risposte, tier="pro")` directly, never re-implement default/visibility/derivation resolution inside `dettaglio_pro.py`.

### Effetto validation (no new validator)
**Source:** `backend/app/services/effetti.py::valida_effetto()` (lines 219-274), `TARGET_AMMESSI` (120-129)
**Apply to:** any new admin-facing write path for the new Pro effetti rows (finitura/pavimento/stepper) — reuse as-is, already covers all four Pro effect types.

### Excel round-trip safety (cell empty = untouched, `#CANCELLA#` = clear)
**Source:** `backend/app/services/export_excel/parametri.py` + `backend/app/services/import_excel/parametri.py` (`FOGLIO_COEFF_PRO`/`COLONNE_COEFF_PRO`/`_CAMPI_NULLABLE_PER_FOGLIO`)
**Apply to:** the D-04 Excel deliverable — reuse the `coefficienti_pro` sheet verbatim, never invent a new flat format.

### DTO anti-leak discipline (closed dataclass/BaseModel fields, no margine)
**Source:** `backend/app/services/dettaglio_pro.py` module docstring (lines 8-25) + `backend/app/schemas/dettaglio_pro.py` module docstring (1-12)
**Apply to:** any new field added to `DettaglioProResult`/`DettaglioProOut` for the pavimento axis — must go through the same `_to_out()` field-by-field mapping in `routers/dettaglio_pro.py` (never `model_validate` on an ORM entity), and `test_no_leak.py`/`test_no_leak_admin.py` must be extended to cover it (per RESEARCH Security Domain).

### DomandaField-driven rendering (no hardcoded field labels)
**Source:** `frontend/src/components/DomandaField.tsx` (full file) + wizard usage pattern
**Apply to:** `DettaglioProView.tsx`'s 3 stepper fields and new pavimento selector — replace `FIELD_LABELS` constant and hand-rolled `<Input>`/button blocks with `<DomandaField domanda={...} valore={...} onChange={...} />`, sourcing `domanda.testo`/`domanda.help`/`domanda.opzioni` from `GET /api/v1/domande?tier=pro` (or equivalent), not from client-side constants.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `backend/tests/test_effetti.py` (new) | test | unit | No existing unit-test file for `effetti.py` in isolation — closest is `test_dettaglio_pro_livelli.py::TestFiltroPuro` (pure-function style) and the module's own worked docstring examples. Build fresh using that style. |
| `backend/scripts/genera_excel_taratura.py` (or equivalent, if a standalone script is chosen for D-04) | utility (one-off script) | batch | No prior one-off Excel-generation script exists in `backend/scripts/` beyond `extract_dettaglio_pro.py` (which parses FROM Excel, not generates TO Excel with curatela columns). Use `export_excel/parametri.py::build_workbook_parametri` + `export_excel/workbook.py::scrivi_foglio_dati` as the closest building blocks, but the "add extra curatela columns + motivazione text" logic is new. |
| `backend/tests/test_migrations.py` (new, upgrade/downgrade/upgrade for CFG-03) | test | integration | RESEARCH notes a prior pattern existed for migration 0014 (cited in STATE.md) but no file was read in this pass — planner should locate that pattern before writing the plan, or fall back to the `0010`/`0019` upgrade/downgrade symmetry already shown above as the template. |

## Metadata

**Analog search scope:** `backend/app/services/`, `backend/app/models/`, `backend/app/schemas/`, `backend/app/routers/`, `backend/alembic/versions/`, `backend/scripts/`, `backend/tests/`, `frontend/src/components/`, `frontend/src/api/`
**Files scanned:** 14 read in full or targeted ranges (effetti.py, dettaglio_pro.py service, computo_parsing.py, models/domanda.py, models/dettaglio_pro.py, schemas/dettaglio_pro.py, routers/dettaglio_pro.py, export_excel/parametri.py, import_excel/parametri.py grep, scripts/seed.py §521-732, alembic 0010/0019, tests/test_dettaglio_pro_livelli.py §1-120, frontend DettaglioProView.tsx, DomandaField.tsx, api/dettaglio-pro.ts)
**Pattern extraction date:** 2026-09-25
