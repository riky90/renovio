# Phase 4: Lead & pannello admin - Pattern Map

**Mapped:** 2026-08-27
**Files analyzed:** 34 (backend: 19, frontend: 15 — net-new or modified)
**Analogs found:** 30 / 34 (4 have no direct repo precedent, flagged below with RESEARCH.md fallback)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `backend/app/models/lead.py` | model | CRUD (immutable-snapshot write, mutable stato/nota) | `backend/app/models/stima_salvata.py` | exact (immutable-snapshot pattern) |
| `backend/app/models/testo.py` | model | CRUD (key/value) | `backend/app/models/catalogo.py::Extra` (simple flat table) | role-match |
| `backend/app/schemas/lead.py` (LeadCreate/LeadOut/LeadUpdate) | schema | request-response | `backend/app/schemas/stima_salvata.py` + `schemas/stima.py` (closed-field anti-leak) | exact |
| `backend/app/schemas/admin_listino.py` | schema | request-response (admin, anti-leak fork) | `backend/app/models/listino.py` docstring pattern (Pattern 1, RESEARCH.md) — no existing admin schema file | new-pattern (documented, no repo precedent yet) |
| `backend/app/schemas/admin_coefficienti.py` | schema | request-response | `backend/app/schemas/dettaglio_pro.py` (nested Out DTOs) | role-match |
| `backend/app/schemas/admin_citta.py` | schema | request-response | `backend/app/schemas/stima.py` (closed DTO discipline) | role-match |
| `backend/app/schemas/admin_testi.py` | schema | CRUD | `backend/app/schemas/auth.py` (simple in/out pairs) | role-match |
| `backend/app/schemas/admin_referenti.py` | schema | CRUD | `backend/app/schemas/auth.py` | role-match |
| `backend/app/schemas/admin_upload.py` (DiffPreviewOut/DiffConfirmIn/ImportResultOut) | schema | file-I/O (diff/preview) | none (new pattern, D-18/D-19) | no-analog |
| `backend/app/services/lead_service.py` (resolve_referente, build_snapshot) | service | event-driven (resolution + side-effect email) | `backend/app/services/city_resolver.py` | exact |
| `backend/app/services/listino_upload_service.py` | service | file-I/O (parse+diff+upsert) | `backend/scripts/extract_dettaglio_pro.py` (parsing logic) + `backend/scripts/seed.py` (upsert-by-natural-key logic) | role-match (adapt, hardened) |
| `backend/app/routers/lead.py` | router | request-response (POST, login required) | `backend/app/routers/stime_salvate.py` (POST endpoint, `get_current_user`, session-per-request) | exact |
| `backend/app/routers/admin/lead.py` | router | CRUD (list/detail/patch, admin) | `backend/app/routers/stime_salvate.py` (list+detail with ownership filter, adapted to require_admin) | role-match |
| `backend/app/routers/admin/listini.py` | router | CRUD | `backend/app/routers/dettaglio_pro.py` (nested entity read) + `backend/app/routers/admin.py` (require_admin stub) | role-match |
| `backend/app/routers/admin/coefficienti.py` | router | CRUD | `backend/app/routers/admin.py` (require_admin stub) | role-match |
| `backend/app/routers/admin/citta.py` | router | CRUD | `backend/app/routers/admin.py` | role-match |
| `backend/app/routers/admin/testi.py` | router | CRUD | `backend/app/routers/admin.py` | role-match |
| `backend/app/routers/admin/referenti.py` | router | CRUD | `backend/app/routers/admin.py` | role-match |
| `backend/app/routers/admin/upload_listino.py` | router | file-I/O (two-step preview/confirm) | none — new pattern (RESEARCH.md Pattern 4); nearest shape is `backend/app/routers/stime_salvate.py`'s POST-then-commit structure | no-analog (new pattern, documented in RESEARCH.md) |
| `backend/alembic/versions/0006_lead_testo.py` | migration | batch (schema DDL) | `backend/alembic/versions/0005_dettaglio_pro.py` | exact |
| `backend/scripts/seed.py` (extend with Testo seed) | utility | batch (idempotent upsert) | itself — extend, same upsert-by-natural-key convention | exact |
| `frontend/src/components/LeadContactDialog.tsx` | component | request-response (form + POST) | `frontend/src/components/SoftWallCta.tsx` (CTA trigger) + `frontend/src/routes/RegistratiPage.tsx`/`AccediPage.tsx` (dialog-less form, adapt to dialog) | role-match |
| `frontend/src/components/SoftWallCta.tsx` (modify) | component | request-response | itself (existing `handleSoftWallClick` soft-wall to be replaced with real dialog open / anonymous redirect) | exact (modify in place) |
| `frontend/src/pages/admin/AdminLayout.tsx` | component | request-response (shell/guard) | `frontend/src/pages/EstimatePage.tsx` (top-level page shell w/ AccountMenu) + `frontend/src/routes/LeMieStimePage.tsx` (auth-guard `Navigate` pattern) | role-match |
| `frontend/src/pages/admin/LeadDashboardPage.tsx` | component | CRUD (list+detail+filter) | `frontend/src/routes/LeMieStimePage.tsx` (list/detail toggle via `useState<selectedId>`, `useQuery`, empty state) | exact |
| `frontend/src/pages/admin/ListiniPage.tsx` | component | CRUD | `frontend/src/routes/LeMieStimePage.tsx` (list pattern) — table replaces the button-list | role-match |
| `frontend/src/pages/admin/CoefficientiPage.tsx` | component | CRUD | same as ListiniPage | role-match |
| `frontend/src/pages/admin/CittaTestiPage.tsx` | component | CRUD | same as ListiniPage | role-match |
| `frontend/src/pages/admin/ReferentiPage.tsx` | component | CRUD | same as ListiniPage | role-match |
| `frontend/src/components/admin/AdminTable.tsx` | component | CRUD (generic table shell) | none in repo (first `table`-primitive use) — compose from `frontend/src/routes/LeMieStimePage.tsx`'s skeleton/empty-state conventions | no-analog (new shadcn primitive, documented pattern) |
| `frontend/src/components/admin/AdminCrudDialog.tsx` | component | CRUD (generic dialog shell) | `frontend/src/components/ui/dialog.tsx` (primitive) + `frontend/src/routes/RegistratiPage.tsx` (form-in-card submit pattern) | role-match |
| `frontend/src/components/admin/AdminDeleteConfirm.tsx` | component | event-driven (destructive confirm) | none (first `alert-dialog` use in repo) — new pattern, shadcn primitive composition only | no-analog |
| `frontend/src/components/admin/ExcelUploadDialog.tsx` | component | file-I/O (3-step upload/diff/confirm) | none (new pattern, D-18/D-19/D-20) | no-analog |
| `frontend/src/api/client.ts` (add apiPatch/apiDelete) | utility | request-response | itself (`apiGet`/`apiPost` in same file) | exact |
| `frontend/src/api/lead.ts` | utility | request-response | `frontend/src/api/stima.ts` (`postStima`, `postSalvaStima`) | exact |
| `frontend/src/api/admin/*.ts` (lead, listini, coefficienti, citta, testi, referenti, uploadListino) | utility | CRUD / file-I/O | `frontend/src/api/stima.ts` (`getStoricoStime`, `getStimaDettaglio` GET+normalize pattern) | role-match |
| `frontend/src/App.tsx` (add `/admin/*` routes) | route | request-response | itself (existing `createBrowserRouter` array) | exact |

## Pattern Assignments

### `backend/app/models/lead.py` (model, CRUD/immutable-snapshot)

**Analog:** `backend/app/models/stima_salvata.py` (full file read above, 50 lines)

**Core pattern** (mirrors lines 25-49 of the analog — scalar frozen columns + no FK dependency for rendering):
```python
# Source: app/models/stima_salvata.py — same freeze-at-write-time shape.
class StimaSalvata(Base):
    __tablename__ = "stima"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False, index=True)
    citta: Mapped[str] = mapped_column(String(200), nullable=False)
    mq: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    totale_min: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    totale_max: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
```

**Apply to `Lead`:** copy this exact scalar-freeze shape for `citta`/`mq`/`tipo`/`totale_min`/`totale_max` (D-03), add lead-specific columns (`nome`, `email`, `telefono`, `preferenza_contatto`, `fascia_oraria`, `messaggio`, `referente_id` nullable FK, `email_inviata` bool D-07, `stato` D-17, `nota`). RESEARCH.md Pattern 2 (lines 284-312 of `04-RESEARCH.md`) already gives the exact target column set — use it verbatim, it was derived directly from this analog.

**Referente FK note:** `Referente` already exists at `backend/app/models/catalogo.py` lines 74-86 (`listino_id`, `nome`, `email`, `telefono`, `attivo`, `priorita`) — `Lead.referente_id` is a nullable `ForeignKey("referente.id")`, no changes needed to `Referente` itself.

---

### `backend/app/models/testo.py` (model, CRUD key/value)

**Analog:** `backend/app/models/catalogo.py::Extra` (lines 49-59) — simplest existing flat CRUD-shaped table (code PK + attivo flag).

**Core pattern:**
```python
# Source: app/models/catalogo.py lines 49-59
class Extra(Base):
    __tablename__ = "extra"
    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    importo: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    iva_pct: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    tipo_calcolo: Mapped[str] = mapped_column(String(32), nullable=False, default="fisso", server_default="fisso")
    attivo: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="1")
```

**Apply to `Testo`:** `chiave: Mapped[str] = mapped_column(String(100), primary_key=True)`, `valore: Mapped[str] = mapped_column(String(...), nullable=False)` (or `Text` if long-form disclaimer content), plus `updated_at` via `func.now()` + `onupdate=func.now()` (no existing precedent for `onupdate` in this repo — verify SQLite/Postgres portability at implementation time, `stima_salvata.py`/`catalogo.py` never use `onupdate`).

---

### `backend/app/schemas/lead.py` (schema, request-response, anti-leak closed DTOs)

**Analog:** `backend/app/schemas/stima.py` (full file, 74 lines) + `backend/app/schemas/stima_salvata.py` (not re-read here — same discipline, referenced by `stime_salvate.py` router already read above).

**Closed-field DTO pattern** (mirrors `stima.py` lines 36-63 — response models declare ONLY contract fields):
```python
# Source: app/schemas/stima.py lines 48-54 — ExtraOut has NO impresa-side field at all.
class ExtraOut(BaseModel):
    code: str
    nome: str
    importo: Decimal
    iva_pct: Decimal
```

**Apply to `LeadCreate`/`LeadOut`/`LeadUpdate`:**
- `LeadCreate` (public, bound input): `telefono`, `messaggio` (`Field(max_length=2000)`), `preferenza_contatto` (Enum "email"|"telefono"), `fascia_oraria` optional, plus the snapshot fields (`citta`, `mq`, `tipo`, `totale_min`, `totale_max`) — bounded the same way `StimaRequest` bounds `mq` (`Field(ge=1, le=2000)` at `stima.py` line 26).
- `LeadOut` (admin-only, `require_admin` routes): includes `id`, `stato`, `nota`, `created_at`, `email_inviata`, full snapshot — **never** includes `coefficiente_impresa`/`base_eur_mq` (there is no such field on `Lead` per D-22, so this is naturally satisfied, but note it explicitly per Pattern 1 discipline).
- `LeadUpdate` (admin PATCH): `stato: str`, `nota: str | None` only — narrowest possible closed schema, mirrors `RisposteDomandeRequest`-style narrow input schemas in `schemas/dettaglio_pro.py`.

---

### `backend/app/schemas/admin_listino.py` / `admin_coefficienti.py` (schema, anti-leak fork — NEW pattern for this repo)

**Analog:** No existing admin-exposing schema file in the repo (Phase 1-3 never exposed `coefficiente_impresa`). Base the fork discipline on the *ORM entity* `backend/app/models/listino.py` (lines 27-38, `ListinoCategoria`) plus the closed-DTO convention from `schemas/stima.py`.

**Pattern (from `04-RESEARCH.md` Pattern 1, grounded directly in this repo's model comments):**
```python
# Source: app/models/listino.py lines 36-38 (ORM entity, docstring: "mai
# referenziato da nessuno schema di risposta" — Phase 4 breaks that
# invariant ONLY for the admin-scoped schema below, D-10).
class ListinoCategoriaAdminOut(BaseModel):
    id: int
    categoria_code: str
    base_eur_mq: Decimal
    coefficiente_impresa: Decimal  # admin-only — NEVER reused outside require_admin routes

class ListinoCategoriaAdminIn(BaseModel):
    base_eur_mq: Decimal = Field(gt=0)
    coefficiente_impresa: Decimal = Field(gt=0, le=1)
```

**Critical rule (binding, D-10/D-22):** this `*AdminOut`/`*AdminIn` pair is a **separate class** from any non-admin-facing schema for the same entity. Never add an `Optional[Decimal] = None` sensitive field to a schema shared with non-admin endpoints — matches the closed-field-set discipline already audited in `schemas/stima.py`/`schemas/dettaglio_pro.py`.

---

### `backend/app/services/lead_service.py` (service, event-driven — referente resolution)

**Analog:** `backend/app/services/city_resolver.py` (full file, 32 lines)

**Core pattern** (mirrors lines 17-31 exactly — two-branch resolution: dedicated row, else default):
```python
# Source: app/services/city_resolver.py — the analog itself, verbatim
def resolve_listino(session: Session, citta: str) -> tuple[Listino, bool]:
    slug = slugify(citta)
    row = session.query(ComuneListino).filter_by(comune_slug=slug).one_or_none()
    if row is not None:
        listino = session.get(Listino, row.listino_id)
        return listino, False
    default = session.query(Listino).filter_by(is_default=True).one()
    return default, True
```

**Apply to `resolve_referente`:** `04-RESEARCH.md` Pattern 3 (lines 314-339) already extends this exact shape — call `resolve_listino()` first, then query `Referente` filtered by `listino_id`+`attivo=True` ordered by `priorita`, falling back to the default listino's active referente if none found on the resolved listino. Use it as-is; it is a direct, faithful extension of this analog, not a re-derivation.

**Email call-site pattern (async/sync mixing) — analog:** `backend/app/routers/auth.py` lines 121-155 (`password_dimenticata`, `async def` route handler that `await`s `send_email()` after a sync DB commit inside a `with SessionLocal()` block):
```python
# Source: app/routers/auth.py lines 130-153 — exact shape to replicate for
# the lead router: sync DB writes inside `with SessionLocal()`, THEN await
# send_email() as a plain top-level statement (no extra try/except — the
# function is documented "never raises", per email_service.py docstring).
with SessionLocal() as session:
    user = session.query(User).filter_by(email=payload.email).one_or_none()
    if user is not None:
        ...
        session.add(PasswordResetToken(...))
        session.commit()
        reset_link = f"{settings.FRONTEND_URL}/reimposta-password?token={token}"
        await send_email(to=user.email, subject="Reimposta la tua password", html_body=(...))
```
Apply verbatim to `routers/lead.py`: make the route handler `async def`, persist `Lead` row + `session.commit()` FIRST (D-07 ordering), THEN `await send_email(...)` to the referente, THEN `await send_email(...)` confirmation to the user — both after commit, both un-wrapped (no try/except masking).

---

### `backend/app/services/listino_upload_service.py` (service, file-I/O — parse+diff+upsert)

**Analogs:** `backend/scripts/extract_dettaglio_pro.py` (docstring + first 60 lines read — row-classification heuristics for A-EDILE hierarchy vs. flat B/C/D catalogs) + `backend/scripts/seed.py` (lines 1-120 read — idempotent upsert-by-natural-key convention, e.g. `_upsert_sottocategoria` lines 92-116).

**Upsert-by-natural-key pattern to reuse** (source: `scripts/seed.py` lines 92-116):
```python
def _upsert_sottocategoria(session: Session, listino: Listino, sotto_data: dict) -> Sottocategoria:
    categoria_code = sotto_data["categoria_code"]
    codice = sotto_data.get("codice")
    nome = sotto_data["nome"]
    query = session.query(Sottocategoria).filter_by(listino_id=listino.id, categoria_code=categoria_code)
    query = query.filter_by(codice=codice) if codice is not None else query.filter_by(codice=None, nome=nome)
    sotto = query.one_or_none()
    if sotto is None:
        sotto = Sottocategoria(listino_id=listino.id, categoria_code=categoria_code, codice=codice,
                                nome=nome, famiglia=sotto_data["famiglia"], ordine=sotto_data.get("ordine", 0))
        session.add(sotto)
        session.flush()
    else:
        sotto.nome = nome
        sotto.famiglia = sotto_data["famiglia"]
        sotto.ordine = sotto_data.get("ordine", 0)
    return sotto
```

**Row-classification heuristic to reuse** (source: `scripts/extract_dettaglio_pro.py` docstring lines 8-25 — header vs. voce detection by which columns are populated; A-EDILE codice hierarchy `A.n`/`A.n.m` vs. flat B/C/D catalogs grouped by header row).

**Hardening required (RESEARCH.md Pitfall 1, binding):** unlike the dev script, every `openpyxl` call site in the runtime service must be wrapped so malformed rows become a "scarti" entry (D-19) instead of raising — the analog script has NO such guards (single-purpose, developer-controlled input) and must NOT be imported/called as-is without adding: file-size check before `load_workbook()`, `.xlsx`-only extension check, try/except per row producing a `{riga, motivo}` scarto dict, and numeric-range validation (price > 0, `coefficiente_impresa` in (0,1]) before classifying a row as "nuova"/"modificata".

---

### `backend/app/routers/lead.py` (router, request-response, POST + login required)

**Analog:** `backend/app/routers/stime_salvate.py` lines 45-68 (`salva_stima` — `Depends(get_current_user)`, `with SessionLocal()`, freeze-on-write, `BaseModel` inline response DTO).

**Core pattern:**
```python
# Source: app/routers/stime_salvate.py lines 45-68
@router.post("/stime", response_model=StimaSalvataCreatedOut, status_code=201)
def salva_stima(
    payload: StimaSalvataCreate,
    current_user: User = Depends(get_current_user),
) -> StimaSalvataCreatedOut:
    with SessionLocal() as session:
        row = StimaSalvata(user_id=current_user.id, ...)
        session.add(row)
        session.commit()
        session.refresh(row)
        return StimaSalvataCreatedOut(id=row.id, created_at=row.created_at)
```

**Apply to `POST /api/v1/lead`:** same `Depends(get_current_user)` guard (D-01, login required — not `require_admin`, not anonymous), same `with SessionLocal()` + commit-then-refresh shape. Per the email-call-site pattern above, this route must be `async def` (unlike this analog which stays sync) because it `await`s `send_email()` after commit — copy `auth.py`'s async shape for the email portion, keep `stime_salvata.py`'s DB-write shape for the persistence portion.

---

### `backend/app/routers/admin/lead.py`, `listini.py`, `coefficienti.py`, `citta.py`, `testi.py`, `referenti.py` (routers, CRUD, admin)

**Analog (guard):** `backend/app/routers/admin.py` (full file, 20 lines — `require_admin` dependency wiring):
```python
# Source: app/routers/admin.py — the entire file, exact shape to replicate
# per new admin router module.
router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/ping")
def ping(user=Depends(require_admin)) -> dict[str, str]:
    return {"status": "ok"}
```

**Analog (404-not-403 for missing rows, admin variant):** `04-RESEARCH.md` "Code Examples" section (lines 436-448) — grounded in `stime_salvate.py`'s anti-IDOR discipline but explicitly notes admin routes use plain 404 (no ownership check, only the `require_admin` gate):
```python
@router.patch("/admin/referenti/{referente_id}")
def update_referente(referente_id: int, payload: ReferenteAdminIn, user=Depends(require_admin), db=Depends(get_db)):
    referente = db.get(Referente, referente_id)
    if referente is None:
        raise HTTPException(404, "Referente non trovato")
    ...
```

**Analog (list+detail GET shape):** `backend/app/routers/stime_salvate.py` lines 71-92 (`lista_stime` — `select()` + `.scalars().all()` + list comprehension into DTOs) — reuse this exact `select`/`scalars`/`.all()` shape for every admin list endpoint, swapping the `user_id` filter for admin's unfiltered (or filtered-by-query-param, e.g. `?citta=`/`?stato=` for the lead dashboard, D-17) query.

**Every admin router file MUST:**
1. `router = APIRouter(prefix="/admin/<entity>", tags=["admin-<entity>"])`.
2. Every route function signature includes `user=Depends(require_admin)` — a router-level grep/test sweep (RESEARCH.md Security Domain V4) should verify this at implementation time, not rely on memory.
3. Use `get_db: Session = Depends(get_db)` from `app.dependencies.auth` (already used by `stime_salvate.py`/`dettaglio_pro.py` implicitly via `SessionLocal()`; `get_db` is the `Depends`-injectable form defined in `dependencies/auth.py` lines 31-33 — prefer it for admin routers since they take `db` as a parameter rather than opening `with SessionLocal()` inline, matching the `require_admin`/`update_referente` example above).

---

### `backend/app/routers/admin/upload_listino.py` (router, file-I/O, two-step — NEW pattern)

**No direct analog in repo.** RESEARCH.md Pattern 4 (lines 341-359) is the authoritative design — stateless round-trip, client re-submits the full parsed diff to `/confirm`:
```python
# Source: 04-RESEARCH.md Pattern 4, lines 347-358 — new pattern, no repo precedent
@router.post("/admin/upload-listino/preview")
def preview_upload(file: UploadFile, user=Depends(require_admin), db: Session = Depends(get_db)) -> DiffPreviewOut:
    _validate_upload(file)  # .xlsx magic bytes + size <=10MB (D-20)
    rows = parse_computo_xlsx(file.file)
    diff = compute_diff(db, rows)
    return DiffPreviewOut(nuove=diff.nuove, modificate=diff.modificate, scarti=diff.scarti)

@router.post("/admin/upload-listino/confirm")
def confirm_upload(payload: DiffConfirmIn, user=Depends(require_admin), db: Session = Depends(get_db)) -> ImportResultOut:
    applied = apply_diff_idempotent(db, payload)  # upsert by natural key, NEVER deletes (D-24)
    db.commit()
    return ImportResultOut(righe_importate=applied)
```
Combine with the `require_admin` guard pattern from `admin.py` above and the size/type validation guardrails from RESEARCH.md Security Domain (V12 File Upload).

---

### `backend/alembic/versions/0006_lead_testo.py` (migration)

**Analog:** `backend/alembic/versions/0005_dettaglio_pro.py` (full file, 67 lines)

**Core pattern (exact structure to replicate, including revision chaining):**
```python
# Source: backend/alembic/versions/0005_dettaglio_pro.py — full structural analog
revision: str = '0006'
down_revision: Union[str, Sequence[str], None] = '0005'

def upgrade() -> None:
    op.create_table('lead',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        # ... snapshot + contact + stato/nota columns ...
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table('testo',
        sa.Column('chiave', sa.String(length=100), nullable=False),
        sa.Column('valore', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('chiave'),
    )

def downgrade() -> None:
    op.drop_table('testo')
    op.drop_table('lead')
```

**D-24 guardrail (binding):** this migration ONLY creates new tables (`lead`, `testo`) — it must NOT alter/drop any existing table's data. If admin-editable columns need a new nullable column on an existing table (e.g., none currently identified), follow `0005`'s `op.add_column(..., nullable=True)` pattern (line 58) — additive only, never destructive.

---

### `frontend/src/api/client.ts` (utility — add apiPatch/apiDelete)

**Analog:** itself, lines 21-58 (`apiGet`/`apiPost` in the same file — extend in place, do not create a new file).

**Exact pattern to add** (already fully specified in `04-RESEARCH.md` Code Examples, lines 412-433, matching this file's existing `apiGet`/`apiPost` conventions verbatim — same `API_BASE` guard, same `ApiError` throw, same `credentials: "include"`, same 204 short-circuit):
```typescript
// Source: existing app pattern in frontend/src/api/client.ts lines 21-58,
// extended per 04-RESEARCH.md Code Examples section.
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

---

### `frontend/src/api/lead.ts`, `frontend/src/api/admin/*.ts` (utility, request-response/CRUD)

**Analog:** `frontend/src/api/stima.ts` — specifically the `postSalvaStima`/`getStoricoStime`/`getStimaDettaglio` trio (lines 191-219) which already use `apiPost`/`apiGet` from `client.ts` (not the raw-`fetch` pattern used by `postStima`/`scaricaPdf` at the top of that file, which predates `client.ts`).

**Core pattern (mirrors lines 196-212):**
```typescript
// Source: frontend/src/api/stima.ts lines 196-212
export async function postSalvaStima(payload: StimaResponse): Promise<{ id: number }> {
  return apiPost<{ id: number }>("/me/stime", payload);
}

export async function getStoricoStime(): Promise<StimaSalvataListItem[]> {
  const raw = await apiGet<RawStimaSalvataListItem[]>("/me/stime");
  return raw.map((item) => ({ ...normalize numeric fields... }));
}
```

**Apply to `api/lead.ts`:** `postLead(payload: LeadCreateInput): Promise<{ id: number }>` via `apiPost("/lead", payload)`.
**Apply to `api/admin/*.ts`:** each file exports `listX`/`getX`/`createX`/`updateX` (`apiPatch`)/`deleteX` (`apiDelete`) using the same `apiGet`/`apiPost`/`apiPatch`/`apiDelete` wrappers — no raw `fetch` calls (the raw-fetch style at the top of `stima.ts` is legacy/pre-`client.ts`, do not replicate it for new admin files).

**Decimal-as-string wire format (binding, carries over):** every numeric field coming from a Pydantic `Decimal` (prices, coefficients, IVA) is serialized as a JSON string by FastAPI — replicate `stima.ts`'s `toNumber()`/`normalizeResponse()` pattern (lines 104-133) for any admin API file reading `base_eur_mq`/`coefficiente_impresa`/`prezzo_unitario_cliente` etc.

---

### `frontend/src/components/LeadContactDialog.tsx` (component, request-response form)

**Analogs:** `frontend/src/components/SoftWallCta.tsx` (full file, 136 lines — trigger button + `useState` feedback pattern, `handleSalvaClick`-style `navigate()` with `state: { pendingStima: result }` for the anonymous branch) + `frontend/src/routes/RegistratiPage.tsx` (not re-read here, but same form-submission convention as `EstimatePage.tsx`'s `useMutation` usage).

**Trigger/redirect pattern to replace** (source: `SoftWallCta.tsx` lines 38-40, currently a stub):
```typescript
// Source: frontend/src/components/SoftWallCta.tsx lines 38-40 — CURRENT
// stub behavior to REPLACE per D-01/D-21 (§A UI-SPEC): anonymous still
// redirects (reuse handleSalvaClick's exact navigate+state shape below),
// logged-in now opens LeadContactDialog instead of setFeedback(FEEDBACK).
function handleSoftWallClick() {
  setFeedback(FEEDBACK);
}
// Redirect-with-intent pattern to reuse for the anonymous branch (lines 42-44):
function handleSalvaClick() {
  navigate("/registrati?intent=save", { state: { pendingStima: result } });
}
```
Apply: anonymous click → `navigate("/registrati?intent=contatta", { state: { pendingStima: result } })` (same mechanism, new intent value per UI-SPEC §A); logged-in click → open `<LeadContactDialog>` as a controlled `dialog` (see `components/ui/dialog.tsx` primitive), passing `result` (current `StimaResponse`) for the read-only snapshot panel and `useAuth().user` for name/email prefill.

**Form submission pattern (mutation + success/error branching):** reuse `EstimatePage.tsx`'s `useMutation<StimaResponse, Error, EstimateFormValues>` shape (lines 31-33) — `LeadContactDialog` should use `useMutation({ mutationFn: postLead })` with the same `isPending`/`isSuccess`/`isError` branching already established across `EstimatePage.tsx`/`SoftWallCta.tsx`'s save flow.

---

### `frontend/src/pages/admin/AdminLayout.tsx` (component, shell + guard)

**Analog:** `frontend/src/routes/LeMieStimePage.tsx` lines 28-50 (auth-guard `Navigate` pattern) + `frontend/src/pages/EstimatePage.tsx` lines 70-92 (top-level page shell with `AccountMenu`/`Skeleton` header pattern).

**Guard pattern (mirrors `LeMieStimePage.tsx` lines 48-50):**
```typescript
// Source: frontend/src/routes/LeMieStimePage.tsx lines 48-50
const { user, isLoading: isAuthLoading } = useAuth();
if (!isAuthLoading && !user) {
  return <Navigate to="/accedi" replace />;
}
```
**Apply to `AdminLayout`:** same shape, but the condition is `!isAuthLoading && (!user || user.role !== "admin")` → render the §B "Accesso negato" block (UI-SPEC) instead of a bare redirect, since the server-side 403 is the real gate and this is purely the client-side render of that state (never flash real admin data — fetch admin data only after the guard passes).

**Header pattern (mirrors `EstimatePage.tsx` lines 72-84):** reuse the exact `AccountMenu`/`Skeleton` conditional rendering for the shared header row, adding the neutral "Admin" `badge` next to the wordmark per UI-SPEC §B.

---

### `frontend/src/pages/admin/LeadDashboardPage.tsx` (component, CRUD list+detail)

**Analog:** `frontend/src/routes/LeMieStimePage.tsx` (full file, 155 lines) — the list/detail toggle via `useState<selectedId>`, `useQuery` with `enabled: selectedId !== null`, loading `Skeleton` rows, and the true-empty vs. no-precedent-for-filtered-empty state.

**Core list/detail toggle pattern (mirrors lines 28-46, 70-102):**
```typescript
// Source: frontend/src/routes/LeMieStimePage.tsx lines 28-46
const [selectedId, setSelectedId] = useState<number | null>(null);
const storicoQuery = useQuery<StimaSalvataListItem[]>({
  queryKey: ["storico-stime"],
  queryFn: getStoricoStime,
  enabled: !!user,
});
const dettaglioQuery = useQuery({
  queryKey: ["stima-dettaglio", selectedId],
  queryFn: () => getStimaDettaglio(selectedId as number),
  enabled: selectedId !== null && !isPro,
});
```
**Apply to `LeadDashboardPage`:** `useQuery(["admin-leads", cittaFilter, statoFilter], ...)` for the list (§C UI-SPEC, `table` component instead of the button-list at lines 129-147), `useQuery(["admin-lead-detail", selectedId], ...)` for the detail dialog — same enabled-gating discipline. The "no leads at all" empty state (lines 112-125) is a direct structural analog for §C's true-empty state; the filtered-empty state (UI-SPEC §C, "Nessun lead corrisponde ai filtri") has no repo precedent — implement as a lighter inline message per the UI-SPEC copy table, no illustration.

---

### `frontend/src/components/admin/AdminTable.tsx`, `AdminCrudDialog.tsx`, `AdminDeleteConfirm.tsx`, `ExcelUploadDialog.tsx` (components, NEW shadcn primitives — no direct analog)

**No repo precedent** — these are the first uses of `table`, `alert-dialog`, `tabs`, `select`, `switch`, `sonner` in this codebase (all confirmed net-new in `04-UI-SPEC.md` "New shadcn components required", lines 29-36). Closest structural analogs for surrounding conventions only:
- Empty-state/skeleton conventions: `frontend/src/routes/LeMieStimePage.tsx` lines 104-125 (loading `Skeleton` array + empty-state block).
- Dialog chrome conventions: `frontend/src/components/ui/dialog.tsx` (primitive, already installed) — reuse as-is, do not restyle.
- Toast/success feedback conventions: no existing `sonner` use — introduce per UI-SPEC exactly as specified (`sonner` toast "Modifica salvata" etc.), no repo precedent to deviate from.
- Icon-button accessible-name discipline (binding, UI-SPEC §D.2): every edit/delete icon button needs an explicit `aria-label` — no existing repo icon-only button to copy from; follow the UI-SPEC text verbatim (`aria-label="Modifica"` / `aria-label="Elimina"`).

**Recommendation:** these four files should be built directly from `04-UI-SPEC.md` §B–§E (already fully specified with exact copy, spacing, and state tables) rather than from a codebase analog — the planner should reference UI-SPEC sections directly in the plan's action items for these files.

---

### `frontend/src/App.tsx` (route registration)

**Analog:** itself, lines 1-26 — the existing flat `createBrowserRouter([...])` array.

**Pattern:**
```typescript
// Source: frontend/src/App.tsx lines 11-20 — existing flat route array
const router = createBrowserRouter([
  { path: "/", element: <EstimatePage /> },
  { path: "/le-mie-stime", element: <LeMieStimePage /> },
  // ...
]);
```
**Apply:** add `{ path: "/admin", element: <AdminLayout /> }` with nested routes for `/admin/lead`, `/admin/listini`, `/admin/coefficienti`, `/admin/citta-testi`, `/admin/referenti` (either as `children` of the layout route using `<Outlet />`, or as flat sibling paths each wrapping `<AdminLayout>{...}</AdminLayout>` — no existing nested-route precedent in this repo's flat array, so either approach is a reasonable first introduction; flat sibling paths keep closer parity with the existing all-flat convention).

## Shared Patterns

### `require_admin` guard (backend, all 7 admin routers)
**Source:** `backend/app/dependencies/auth.py` lines 53-56
**Apply to:** every route function in `routers/admin/*.py` — `user=Depends(require_admin)` on every single endpoint, no exceptions (D-10/D-22 make this the ONLY gate protecting `coefficiente_impresa`/`base_eur_mq` exposure).
```python
def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Accesso riservato")
    return user
```

### `get_current_user` guard (backend, lead router)
**Source:** `backend/app/dependencies/auth.py` lines 36-50
**Apply to:** `routers/lead.py`'s single POST endpoint (D-01, login required, not admin-only).

### Async email call-site (backend, lead router)
**Source:** `backend/app/routers/auth.py` lines 121-155 (`password_dimenticata`)
**Apply to:** `routers/lead.py` — `async def` route handler, sync DB commit first, `await send_email(...)` after, no try/except wrapping (function documented never-raising, see `services/email_service.py` lines 1-14 docstring).

### Closed-DTO / anti-leak schema fork (backend, all admin + lead schemas)
**Source:** `backend/app/schemas/stima.py` (whole file) — closed-field-set discipline; `04-RESEARCH.md` Pattern 1 (lines 267-282) — the admin-fork extension of it.
**Apply to:** every Pydantic response schema touching `coefficiente_impresa`/`base_eur_mq`/margin-shaped fields — always a separate `*AdminOut` class, never an optional field on a shared schema.

### Idempotent upsert-by-natural-key (backend, upload service + CRUD write paths)
**Source:** `backend/scripts/seed.py` lines 92-116 (`_upsert_sottocategoria`)
**Apply to:** `services/listino_upload_service.py`'s diff/apply logic (D-19/D-24) — same "query by natural key, update-in-place or insert" shape, never delete rows absent from the incoming payload.

### `apiGet`/`apiPost`/`apiPatch`/`apiDelete` fetch wrapper (frontend, all new API files)
**Source:** `frontend/src/api/client.ts` lines 21-58 (existing) + RESEARCH.md Code Examples (new `apiPatch`/`apiDelete` to add, lines 412-433)
**Apply to:** every file under `frontend/src/api/lead.ts` and `frontend/src/api/admin/*.ts` — no raw `fetch()` calls, always go through these four wrappers.

### `useAuth()` role/session hook (frontend, admin guard + lead form prefill)
**Source:** `frontend/src/hooks/useAuth.ts` (whole file, 58 lines) — `user`, `isLoading`, `login`/`logout`/`registrazione` mutations, all invalidating `["me"]`.
**Apply to:** `AdminLayout.tsx` (role check `user?.role === "admin"`), `LeadContactDialog.tsx` (prefill `nome`/`email` from `user`).

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `backend/app/schemas/admin_upload.py` | schema | file-I/O | First diff-preview response shape in this repo; built directly from D-18/D-19 requirements, no prior admin/upload endpoint exists (RESEARCH.md Pattern 4 is the authoritative design). |
| `backend/app/routers/admin/upload_listino.py` | router | file-I/O (two-step) | RESEARCH.md explicitly flags this as "new pattern for this repo, no direct precedent" — stateless preview/confirm round-trip has no prior multi-step HTTP flow in the codebase. |
| `frontend/src/components/admin/AdminTable.tsx` | component | CRUD | First use of the shadcn `table` primitive; no existing repo table (`LeMieStimePage.tsx` uses a button-list, not a `<table>`). Build directly from UI-SPEC §C/§D. |
| `frontend/src/components/admin/ExcelUploadDialog.tsx` | component | file-I/O | First dropzone/multi-step-upload UI in the frontend; no existing file-upload component to adapt. Build directly from UI-SPEC §E (fully specified, 3 steps + state table). |

## Metadata

**Analog search scope:** `backend/app/{models,schemas,services,routers,dependencies}/`, `backend/alembic/versions/`, `backend/scripts/`, `frontend/src/{components,pages,routes,api,hooks}/`
**Files scanned:** ~50 (all non-`.venv`/non-`node_modules` source files under `backend/app`, `backend/alembic/versions`, `backend/scripts`, `frontend/src`)
**Pattern extraction date:** 2026-08-27
