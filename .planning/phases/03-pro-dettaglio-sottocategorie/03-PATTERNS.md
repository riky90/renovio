# Phase 3: Pro & dettaglio sottocategorie - Pattern Map

**Mapped:** 2026-08-26
**Files analyzed:** 23 (new/modified, backend + frontend)
**Analogs found:** 23 / 23

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|---------------|
| `backend/app/models/dettaglio_pro.py` (Sottocategoria, Voce, CoefficienteQuantitaVoce) | model | CRUD (seed-populated, read-only at runtime) | `backend/app/models/catalogo.py` + `backend/app/models/listino.py` | exact |
| `backend/app/models/subscription.py` (Subscription) | model | CRUD | `backend/app/models/user.py` (`UserSession`) | role-match |
| `backend/app/models/stima_salvata.py` (MODIFIED: add `risposte_pro_json`) | model | CRUD | same file, existing `risultato_json` column | exact (self) |
| `backend/app/services/dettaglio_pro.py` (DettaglioProService) | service | transform (Decimal calc) | `backend/app/services/estimation.py` | exact |
| `backend/app/services/pdf_service.py` (MODIFIED: add `render_pro`) | service | file-I/O (PDF render) | same file, existing `render()` | exact (self) |
| `backend/app/services/subscription_service.py` (or inline in router — Pro status check helper) | service | CRUD | `backend/app/dependencies/auth.py` (`get_current_user`) | role-match |
| `backend/app/schemas/dettaglio_pro.py` (closed DTOs) | model (DTO) | transform | `backend/app/schemas/stima.py` | exact |
| `backend/app/schemas/subscription.py` (SubscriptionOut, stub-activation request/response) | model (DTO) | transform | `backend/app/schemas/auth.py` (`UserOut`) | exact |
| `backend/app/schemas/auth.py` (MODIFIED: `UserOut.pro: bool`) | model (DTO) | transform | same file | exact (self) |
| `backend/app/dependencies/auth.py` (MODIFIED: add `require_pro`) | middleware | request-response (auth guard) | same file, existing `require_admin` | exact (self) |
| `backend/app/routers/dettaglio_pro.py` (`GET .../dettaglio-pro`, `POST .../risposte`) | route/controller | request-response | `backend/app/routers/stime_salvate.py` | exact |
| `backend/app/routers/subscription.py` (`POST /me/pro/attiva`) | route/controller | request-response | `backend/app/routers/stima.py` (POST-compute-return pattern) + `stime_salvate.py` (auth-gated pattern) | role-match |
| `backend/app/routers/dettaglio_pro.py` (`GET .../pdf-pro`) | route/controller | file-I/O (PDF streaming) | `backend/app/routers/stime_salvate.py::scarica_pdf_stima` | exact |
| `backend/scripts/seed.py` (MODIFIED: extend `seed()` with sottocategoria/voce/coefficiente upserts) | utility (seed) | batch (idempotent upsert) | same file, existing upsert loops | exact (self) |
| `docs/seed-dettaglio-pro.json` | config | batch (seed data) | `docs/seed-coefficienti-base.json` | exact |
| `backend/alembic/versions/0004_pro_dettaglio.py` | migration | batch | `backend/alembic/versions/0003_stima_salvata.py` | exact |
| `backend/app/templates/pdf_stima_pro.html` | template | transform (Jinja2 render) | `backend/app/templates/pdf_stima.html` | exact |
| `backend/tests/test_dettaglio_pro.py` | test | unit | `backend/tests/test_estimation.py` | exact |
| `backend/tests/test_dettaglio_pro_paywall.py` | test | integration | `backend/tests/test_no_leak.py` (client/session fixture shape) + admin-guard tests in `test_auth_endpoints.py` | role-match |
| `backend/tests/test_subscription.py` | test | integration | `backend/tests/test_no_leak.py` (seeded-DB fixture pattern) | role-match |
| `backend/tests/test_pdf_pro.py` | test | integration | `backend/tests/test_pdf.py` | exact |
| `frontend/src/pages/PassaAProPage.tsx` | component (page) | request-response | `frontend/src/routes/RegistratiPage.tsx` | role-match |
| `frontend/src/pages/DettaglioProPage.tsx` | component (page) | request-response | `frontend/src/pages/EstimatePage.tsx` | exact |
| `frontend/src/components/SottocategoriaAccordion.tsx` | component | transform (presentation of API data) | `frontend/src/components/CategoryCard.tsx` | role-match |
| `frontend/src/components/SoftWallCta.tsx` (MODIFIED: "Passa a Pro" navigates, Pro variant) | component | request-response (navigation) | same file (existing `handleSalvaClick`/`navigate` pattern) | exact (self) |
| `frontend/src/components/CategoryCard.tsx` (MODIFIED: locked-teaser strip) | component | transform | same file | exact (self) |
| `frontend/src/api/dettaglio-pro.ts` (API client functions) | service (api client) | request-response | `frontend/src/api/stima.ts` | exact |
| `frontend/src/api/subscription.ts` (`postAttivaPro`) | service (api client) | request-response | `frontend/src/api/auth.ts` (`postLogin`-style mutation) | role-match |
| `frontend/src/App.tsx` (MODIFIED: add `/passa-a-pro`, `/dettaglio-pro` routes) | route (router config) | — | same file | exact (self) |

## Pattern Assignments

### `backend/app/models/dettaglio_pro.py` (model, CRUD)

**Analog:** `backend/app/models/listino.py` + `backend/app/models/catalogo.py`

**Imports pattern** (listino.py lines 6-12):
```python
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
```

**Core pattern — FK'd child table hanging off `Listino`, natural-key `UniqueConstraint`** (listino.py lines 27-38):
```python
class ListinoCategoria(Base):
    """€/m² base (prezzo CLIENTE) + margine impresa, per (listino, categoria)."""

    __tablename__ = "listino_categoria"
    __table_args__ = (UniqueConstraint("listino_id", "categoria_code", name="uq_listino_categoria"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    listino_id: Mapped[int] = mapped_column(ForeignKey("listino.id"), nullable=False)
    categoria_code: Mapped[str] = mapped_column(ForeignKey("categoria.code"), nullable=False)
    base_eur_mq: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    # SEGRETO: margine interno. Mai serializzato in nessuna risposta.
    coefficiente_impresa: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
```

**Anti-leak module docstring convention** (listino.py lines 1-4) — copy this discipline verbatim, and per D-10/research Anti-Pattern, do **NOT** add a `coefficiente_impresa`/`prezzo_impresa` column on `Voce` at all (stronger posture than Free's "map it but never serialize it" — there's simply nothing to leak):
```python
"""Listino entities. `coefficiente_impresa` is the internal margin secret:
mapped on the ORM entity only, NEVER referenced by any Pydantic response
schema (see 01-RESEARCH.md Pattern 1 - response schema as anti-leak gate).
"""
```

**Shape to apply (from RESEARCH.md, not copied verbatim from any single file — original design constrained by D-02/D-03):**
```python
class Sottocategoria(Base):
    __tablename__ = "sottocategoria"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    listino_id: Mapped[int] = mapped_column(ForeignKey("listino.id"), nullable=False)
    categoria_code: Mapped[str] = mapped_column(ForeignKey("categoria.code"), nullable=False)
    codice: Mapped[str | None] = mapped_column(String(16), nullable=True)  # nullable — B/C/D have none (Pitfall 1)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    famiglia: Mapped[str] = mapped_column(String(16), nullable=False)  # 'gerarchica' | 'catalogo'
    ordine: Mapped[int] = mapped_column(nullable=False)

class Voce(Base):
    __tablename__ = "voce"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sottocategoria_id: Mapped[int] = mapped_column(ForeignKey("sottocategoria.id"), nullable=False)
    codice: Mapped[str | None] = mapped_column(String(16), nullable=True)
    descrizione: Mapped[str] = mapped_column(String(300), nullable=False)
    um: Mapped[str] = mapped_column(String(16), nullable=False)  # mq | cad | ml | ac
    prezzo_unitario_cliente: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    # NO coefficiente_impresa / prezzo_impresa column — see Anti-Pattern above.

class CoefficienteQuantitaVoce(Base):
    __tablename__ = "coefficiente_qta_voce"
    __table_args__ = (UniqueConstraint("voce_id", "tipo_code", name="uq_coeff_voce_tipo"),)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    voce_id: Mapped[int] = mapped_column(ForeignKey("voce.id"), nullable=False)
    tipo_code: Mapped[str] = mapped_column(ForeignKey("tipo_ristrutturazione.code"), nullable=False)
    coefficiente_qta_per_mq: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    domanda_mirata_key: Mapped[str | None] = mapped_column(String(32), nullable=True)  # 'bagni'|'porte'|'condizionatori'
    default_conteggio: Mapped[int | None] = mapped_column(nullable=True)
```

---

### `backend/app/models/subscription.py` (model, CRUD)

**Analog:** `backend/app/models/user.py` (`UserSession`)

**Pattern — 1:1-ish child table with nullable expiry + state string** (user.py lines 45-61):
```python
class UserSession(Base):
    __tablename__ = "user_session"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="sessions")
```

**Apply for `Subscription` (D-06: state + nullable expiry, not a boolean):**
```python
class Subscription(Base):
    __tablename__ = "subscription"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False, index=True)
    stato: Mapped[str] = mapped_column(String(16), nullable=False, default="inattivo", server_default="inattivo")
    scaduta_il: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    piano_code: Mapped[str | None] = mapped_column(String(32), nullable=True)  # placeholder, D-07 "production-shaped"
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
```

---

### `backend/app/dependencies/auth.py` (middleware, request-response) — MODIFIED

**Analog:** same file, existing `require_admin` (lines 45-48)

**Exact pattern to mirror for `require_pro`** (auth.py lines 28-48, full file already read):
```python
def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Accesso riservato")
    return user
```

**New `require_pro` (mirrors `require_admin`'s 401-then-403 layering, plus the naive/aware datetime guard already used in `get_current_user` lines 38-40):**
```python
def require_pro(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    sub = db.query(Subscription).filter_by(user_id=user.id).one_or_none()
    now = datetime.now(timezone.utc)
    scaduta_il = sub.scaduta_il if sub else None
    if scaduta_il is not None and scaduta_il.tzinfo is None:
        scaduta_il = scaduta_il.replace(tzinfo=timezone.utc)
    is_active = sub is not None and sub.stato == "attivo" and (scaduta_il is None or scaduta_il > now)
    if not is_active:
        raise HTTPException(403, "Funzione riservata agli utenti Pro")
    return user
```
Import `Subscription` from the new `app.models.subscription`; keep `get_db`/`get_current_user` untouched above it in the same module (own-module pattern, no circular import — same rationale as the file's own docstring, lines 1-9).

---

### `backend/app/services/dettaglio_pro.py` (service, transform)

**Analog:** `backend/app/services/estimation.py`

**Imports + module docstring convention** (estimation.py lines 1-24):
```python
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.models.catalogo import Categoria, Extra, Moltiplicatore, TipoRistrutturazione
from app.models.listino import Listino, ListinoCategoria
```

**Anti-leak dataclass discipline — hand-build closed dataclasses, never expose internal fields** (estimation.py lines 33-56):
```python
@dataclass(frozen=True)
class CategoriaEstimata:
    code: str
    nome: str
    iva_pct: Decimal
    totale_min: Decimal
    totale_max: Decimal
```

**Core calc pattern — Decimal-pure, `_eur()` quantize helper, per-item loop building output objects** (estimation.py lines 28-30, 62-119):
```python
def _eur(value: Decimal) -> Decimal:
    """Quantize to whole euro (ROUND_HALF_UP) — used only on output fields."""
    return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

class EstimationService:
    @staticmethod
    def compute(session: Session, listino: Listino, mq: int, tipo: str) -> StimaResult:
        tipo_row = session.query(TipoRistrutturazione).filter_by(code=tipo).one()
        range_pct = tipo_row.range_pct
        # ... loop categorie, build closed dataclasses, sum into running totals
```

**Apply to `DettaglioProService.compute(session, listino, mq, tipo, risposte)`** — same static-method-on-class shape, same `_eur()` reuse, same "never read/return `coefficiente_impresa`" discipline (here: the column doesn't even exist on `Voce`, per the model pattern above), same per-tipo `range_pct` reused for the D-11 range (RESEARCH Pattern 4 — reuse `TipoRistrutturazione.range_pct`, do not invent a new field). Range application: `voce_min = _eur(totale * (1 - range_pct))`, `voce_max = _eur(totale * (1 + range_pct))`, `totale = quantita_stimata * prezzo_unitario_cliente`.

**Never reconcile with `EstimationService` output** (D-01) — do not import `EstimationService` into this module and do not compare totals.

---

### `backend/app/services/pdf_service.py` (service, file-I/O) — MODIFIED, add `render_pro`

**Analog:** same file, existing `render()` (lines 43-63) — deliberate asymmetry per RESEARCH Pattern 3

**Existing lazy-import + template-render pattern to mirror exactly:**
```python
class PdfService:
    @staticmethod
    def render(stima: StimaSalvata, user: User) -> bytes:
        from weasyprint import HTML  # lazy import — GTK3/Windows caveat

        template = _env.get_template("pdf_stima.html")
        filename = build_filename(stima)
        html_content = template.render(
            stima=stima.risultato_json,
            nome=user.nome,
            data_generazione=datetime.now().strftime("%d/%m/%Y"),
            filename=filename,
        )
        return HTML(string=html_content, base_url=str(TEMPLATES_DIR)).write_pdf()
```

**Add `render_pro(dettaglio: DettaglioProResult, stima: StimaSalvata, user: User) -> bytes`** — same lazy `from weasyprint import HTML`, same `_env.get_template(...)` call but against the new `pdf_stima_pro.html`, BUT unlike `render()` this new method is explicitly allowed (required, per D-09) to receive an already-computed `DettaglioProResult` from the router (which called `DettaglioProService.compute()` live) — update the module docstring (lines 1-9) to document this asymmetry explicitly, per Pitfall 2: "Unlike `render()`, `render_pro()` renders a live-computed result, not a frozen snapshot — this is intentional (D-09), do not `git blame`-fix it to match `render()`."

Reuse `build_filename()` (lines 36-40) unmodified or extend with a `-dettaglio` suffix per UI-SPEC §E (non-blocking, executor's choice).

---

### `backend/app/schemas/dettaglio_pro.py` (DTO, transform)

**Analog:** `backend/app/schemas/stima.py`

**Closed-fields anti-leak docstring + pattern** (stima.py lines 1-8, 36-46):
```python
"""Request/response schemas for POST /api/v1/stima.

`StimaRequest` bounds untrusted input (ASVS V5, T-03-02). The response
models ... declare ONLY the fields in the API contract — no
`base_eur_mq`, `moltiplicatore`, `coefficiente_impresa`, or
`prezzo_impresa` anywhere in this module (T-03-01, EST-05).
"""

class CategoriaOut(BaseModel):
    code: str
    nome: str
    imponibile_min: Decimal
    imponibile_max: Decimal
    iva_pct: Decimal
    ...
```

**Apply the same discipline to `VoceOut` / `SottocategoriaOut` / `CategoriaDettagliataOut` / `DettaglioProOut`** — explicit closed field lists only (`codice`, `descrizione`, `um`, `quantita_stimata`, `prezzo_min`, `prezzo_max`), never `model_validate()` on the `Voce`/`Sottocategoria` ORM rows directly.

**Bounded input validation for targeted-question answers** (stima.py line 26, `StimaRequest.mq`):
```python
mq: int = Field(ge=1, le=2000)
```
Apply the same `Field(ge=0, le=<reasonable cap>)` bound to `bagni`/`porte`/`condizionatori` in the `RisposteDomandeRequest` schema (ASVS V5).

---

### `backend/app/schemas/auth.py` (DTO, transform) — MODIFIED

**Analog:** same file, `UserOut` (lines 27-32)

```python
class UserOut(BaseModel):
    id: int
    email: EmailStr
    nome: str
    role: str
    created_at: datetime
```
Add `pro: bool` between `role` and `created_at`, built explicitly in the router (never client-writable) — same hand-built-DTO discipline the module docstring already states (lines 1-7).

---

### `backend/app/routers/dettaglio_pro.py` (controller, request-response)

**Analog:** `backend/app/routers/stime_salvate.py`

**Router-module docstring convention + auth-gated ownership pattern** (stime_salvate.py lines 1-11, 95-121):
```python
"""... Every endpoint sits behind Depends(get_current_user) ... GET
list/detail/pdf are filtered by user_id == current_user.id; detail/pdf
return 404 (not 403) when the row belongs to another user or doesn't
exist, so ownership is never leaked (anti-IDOR, ASVS V4)."""

@router.get("/stime/{stima_id}", response_model=StimaSalvataOut)
def dettaglio_stima(
    stima_id: int,
    current_user: User = Depends(get_current_user),
) -> StimaSalvataOut:
    with SessionLocal() as session:
        stmt = select(StimaSalvata).where(
            StimaSalvata.id == stima_id,
            StimaSalvata.user_id == current_user.id,
        )
        row = session.execute(stmt).scalar_one_or_none()
        if row is None:
            raise HTTPException(404, "Stima non trovata")
        ...
```

**Apply for `GET /me/stime/{stima_id}/dettaglio-pro`:** identical ownership-filter + 404-not-403 shape, PLUS `Depends(require_pro)` layered on top of `Depends(get_current_user)` (403 for non-Pro, per D-08/Pattern 2) — reads `row.citta`/`row.mq`/`row.tipo` (scalar columns, not `risultato_json`) and the optional `row.risposte_pro_json`, resolves `listino` via `resolve_listino` (reuse `app/services/city_resolver.py`, same as `routers/stima.py` line 34), then calls `DettaglioProService.compute(...)`.

**PDF endpoint pattern to mirror exactly** (stime_salvate.py lines 124-148, `scarica_pdf_stima`):
```python
@router.get("/stime/{stima_id}/pdf")
def scarica_pdf_stima(
    stima_id: int,
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    with SessionLocal() as session:
        stmt = select(StimaSalvata).where(
            StimaSalvata.id == stima_id,
            StimaSalvata.user_id == current_user.id,
        )
        row = session.execute(stmt).scalar_one_or_none()
        if row is None:
            raise HTTPException(404, "Stima non trovata")

        pdf_bytes = PdfService.render(row, current_user)
        filename = build_filename(row)

        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
```
For `GET /me/stime/{stima_id}/pdf-pro`: same shape + `Depends(require_pro)`, but call `DettaglioProService.compute(...)` first (live), then `PdfService.render_pro(dettaglio, row, current_user)` — per Pitfall 2, this MUST call the exact same `DettaglioProService.compute()` used by the JSON detail endpoint, with identical arguments (including `risposte_pro_json`), so the two never drift.

**`POST /me/stime/{stima_id}/dettaglio-pro/risposte`** (persist targeted-question answers) — same `Depends(get_current_user)` + ownership-filter shape as `salva_stima` (stime_salvate.py lines 45-68), but does an UPDATE on the existing `StimaSalvata` row's `risposte_pro_json` column instead of an INSERT.

---

### `backend/app/routers/subscription.py` (`POST /me/pro/attiva`)

**Analog:** `backend/app/routers/stima.py` (compute-and-return shape) + auth-gated pattern from `stime_salvate.py`

**Rate-limit pattern to reuse** (stima.py lines 55-56):
```python
@router.post("", response_model=StimaResponse)
@limiter.limit("20/minute")
def crea_stima(payload: StimaRequest, request: Request) -> StimaResponse:
```
Apply `@limiter.limit(...)` (a stricter rate, e.g. `10/minute`) to `POST /me/pro/attiva` per RESEARCH's Security Domain note (stub-activation spam) — same `from app.limiter import limiter` import as `routers/stima.py` line 25.

**Upsert-on-user pattern** — no direct analog for "upsert a subscription row"; closest shape is the `seed.py` upsert idiom (`.filter_by(...).one_or_none()` then create-or-update), applied here inside the router against `Subscription.user_id == current_user.id`.

---

### `backend/scripts/seed.py` (utility, batch) — MODIFIED

**Analog:** same file, existing upsert-by-natural-key loops (already read in full, lines 76-171)

**Exact upsert idiom to replicate for sottocategoria/voce/coefficiente** (seed.py lines 105-118, `listino_categoria` upsert):
```python
for code, base in data["base_eur_mq"].items():
    lc = session.query(ListinoCategoria).filter_by(listino_id=listino.id, categoria_code=code).one_or_none()
    if lc is None:
        lc = ListinoCategoria(
            listino_id=listino.id,
            categoria_code=code,
            base_eur_mq=_dec(base),
            coefficiente_impresa=COEFFICIENTE_IMPRESA[code],
        )
        session.add(lc)
    else:
        lc.base_eur_mq = _dec(base)
        lc.coefficiente_impresa = COEFFICIENTE_IMPRESA[code]
```
Apply the identical `.filter_by(natural_key).one_or_none()` → create-or-update shape for `sottocategoria` (key: `listino_id` + `categoria_code` + `codice`-or-`nome`), `voce` (key: `sottocategoria_id` + `codice`-or-`descrizione`), and `coefficiente_qta_voce` (key: `voce_id` + `tipo_code`) — inside the SAME `seed(session, data=None)` function (D-12 guardrail: do not create `seed_dettaglio_pro.py`, extend the one function). Load `docs/seed-dettaglio-pro.json` the same way `SEED_JSON_PATH`/`load_seed_data()` load `docs/seed-coefficienti-base.json` (lines 34, 71-73).

---

### `backend/alembic/versions/0004_pro_dettaglio.py` (migration)

**Analog:** `backend/alembic/versions/0003_stima_salvata.py` (already read in full)

**Exact revision-chain and `create_table`/`add_column` shape:**
```python
revision: str = '0004'
down_revision: Union[str, Sequence[str], None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table('sottocategoria', ...)
    op.create_table('voce', ...)
    op.create_table('coefficiente_qta_voce', ...)
    op.create_table('subscription', ...)
    op.add_column('stima', sa.Column('risposte_pro_json', sa.JSON(), nullable=True))

def downgrade() -> None:
    op.drop_column('stima', 'risposte_pro_json')
    op.drop_table('subscription')
    op.drop_table('coefficiente_qta_voce')
    op.drop_table('voce')
    op.drop_table('sottocategoria')
```
Column definitions follow the exact `sa.Column(..., nullable=...)` / `sa.ForeignKeyConstraint` / `sa.PrimaryKeyConstraint` idiom from 0003 (lines 23-36) and the `server_default='0'` boolean convention already used there. **D-12 guardrail: this migration must not run against a DB that then loses its seed** — plan a "migrate then reseed" step, not a standalone migration-only task.

---

### `backend/app/templates/pdf_stima_pro.html` (template)

**Analog:** `backend/app/templates/pdf_stima.html` (not yet read in full — locate and reuse its `@page`/header/footer CSS block, Jinja2 `{{ }}` variable structure, and the `stima=...`/`nome=...`/`data_generazione=...` context-variable naming convention already established by `PdfService.render()` (pdf_service.py lines 57-62)). New: multi-page loop `{% for categoria in dettaglio.categorie %}` → `{% for sottocategoria in categoria.sottocategorie %}` → `{% for voce in sottocategoria.voci %}`, using WeasyPrint's native `@page`/`break-inside: avoid` CSS (no new library, per RESEARCH "Don't Hand-Roll").

---

### `backend/tests/test_dettaglio_pro.py` (test, unit)

**Analog:** `backend/tests/test_estimation.py` (already read in full)

**In-memory SQLite + seeded session fixture pattern:**
```python
@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine)
    with testing_session_local() as s:
        seed(s, load_seed_data())
        yield s
```
Apply identically, but seed data must also load `docs/seed-dettaglio-pro.json` (extend `seed()` per the seed.py pattern above so this fixture picks it up automatically with no test-file changes needed). Pin at least one concrete oracle value the same way `test_primary_oracle_85mq_totale` pins `47985..70575` (lines 30-37) — compute one A-EDILE voce's `quantita_stimata`/range by hand from the seed JSON and assert on it exactly.

---

### `backend/tests/test_dettaglio_pro_paywall.py` (test, integration)

**Analog:** `backend/tests/test_no_leak.py` (already read in full) for the TestClient + seeded-engine-swap fixture; conceptually mirrors an admin-guard 401/403/200 matrix test (search `test_auth_endpoints.py` for the existing `require_admin` test if present, same shape applies to `require_pro`).

**Fixture pattern to reuse verbatim (test_no_leak.py lines 35-61):**
```python
@pytest.fixture(autouse=True, scope="module")
def _seeded_db(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db") / "test_x.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine)
    with testing_session_local() as s:
        seed(s, load_seed_data())
        s.commit()
    original_session_local = db_module.SessionLocal
    db_module.SessionLocal = testing_session_local
    yield
    db_module.SessionLocal = original_session_local

@pytest.fixture()
def client():
    return TestClient(app)
```
Test matrix: anonymous → 401; authenticated non-Pro → 403; authenticated Pro (seed a `Subscription(stato="attivo")` row directly in the fixture) → 200.

---

### `backend/tests/test_pdf_pro.py` (test, integration)

**Analog:** `backend/tests/test_pdf.py` (already read in part — WeasyPrint native-lib availability skip pattern)

**Skip-gracefully-without-GTK3 pattern to reuse verbatim (test_pdf.py lines 47-59):**
```python
def _weasyprint_native_lib_available() -> bool:
    if importlib.util.find_spec("weasyprint") is None:
        return False
    try:
        import weasyprint  # noqa: F401
    except OSError:
        return False
    return True

WEASYPRINT_NATIVE_AVAILABLE = _weasyprint_native_lib_available()
```
Byte-generating tests decorated with `@pytest.mark.skipif(not WEASYPRINT_NATIVE_AVAILABLE, ...)`; ownership/401/403/anti-import-of-EstimationService-in-Free-render guards stay unconditional. Extend `FORBIDDEN_SUBSTRINGS` (test_no_leak.py lines 18-23, test_pdf.py lines 39-44) to also run against the Pro PDF/detail payload.

---

## Shared Patterns

### Anti-leak closed-DTO discipline
**Source:** `backend/app/schemas/stima.py` (module docstring, lines 1-8) + `backend/app/models/listino.py` (module docstring, lines 1-4)
**Apply to:** `dettaglio_pro.py` schemas, `Voce`/`Sottocategoria`/`Subscription` models, `pdf_stima_pro.html`
```python
"""... The response models declare ONLY the fields in the API contract —
no `base_eur_mq`, `moltiplicatore`, `coefficiente_impresa`, or
`prezzo_impresa` anywhere in this module."""
```
Never `model_validate()` an ORM row directly into a response schema; always hand-build field-by-field (see `routers/stima.py` lines 62-78 for the canonical hand-build loop).

### Server-side auth guard (401 then 403 layering)
**Source:** `backend/app/dependencies/auth.py` (`get_current_user` + `require_admin`, full file read)
**Apply to:** every Pro-gated route via new `require_pro` dependency — `Depends(get_current_user)` for 401, then `Depends(require_pro)` for 403, exactly mirroring `require_admin`'s layering. Never gate Pro data client-side only (D-08).

### Idempotent upsert-by-natural-key seeding
**Source:** `backend/scripts/seed.py` (`seed()` function, full file read, lines 76-171)
**Apply to:** all new sottocategoria/voce/coefficiente/subscription-adjacent seed data — extend the SAME `seed()` function, do not create a second script (D-12 guardrail).

### Ownership filter + 404-not-403 anti-IDOR
**Source:** `backend/app/routers/stime_salvate.py` (`dettaglio_stima`, `scarica_pdf_stima`, lines 95-148)
**Apply to:** `GET/POST /me/stime/{id}/dettaglio-pro*`, `GET /me/stime/{id}/pdf-pro` — `.where(StimaSalvata.id == stima_id, StimaSalvata.user_id == current_user.id)`, `HTTPException(404, "Stima non trovata")` when absent, never a 403 that reveals existence.

### Lazy WeasyPrint import
**Source:** `backend/app/services/pdf_service.py` (`render()`, lines 47-53)
**Apply to:** `render_pro()` — `from weasyprint import HTML` inside the method body, not at module top, so the app stays importable/testable without native GTK3 libs on Windows dev.

### Frontend result-screen CTA cluster + navigate-on-click
**Source:** `frontend/src/components/SoftWallCta.tsx` (`handleSalvaClick`, lines 34-36) and `frontend/src/routes/RegistratiPage.tsx` (`intent`/`pendingStima` router-state pattern, lines 33-37, 62-78)
**Apply to:** "Passa a Pro" button behavior change (navigate to `/passa-a-pro` instead of soft-wall toast) and the anonymous-user-reaching-upgrade-screen flow (route through `/registrati?intent=pro` reusing the exact `location.state as { pendingStima?: ... }` idiom, generalized to a Pro-intent payload if needed).

### TanStack Query mutation + loading/error/success button states
**Source:** `frontend/src/components/PdfDownloadButton.tsx` (full file read)
**Apply to:** "Attiva Pro" stub button on `PassaAProPage.tsx` — identical `useMutation` + `mutation.isPending`/`mutation.isError` → spinner/disabled/inline-destructive-text shape, same `Loader2` icon usage.

### API client fetch wrapper + Decimal-string-to-number normalization
**Source:** `frontend/src/api/stima.ts` (full file read, `normalizeResponse`/`toNumber` pattern, lines 104-133; `postStima`/`scaricaPdf` fetch shape, lines 139-157, 226-261)
**Apply to:** `frontend/src/api/dettaglio-pro.ts` — new `getDettaglioPro(stimaId)`, `postRisposteDettaglioPro(stimaId, risposte)`, `scaricaPdfPro(stimaId)` (mirrors `scaricaPdf` byte-for-byte, including the `Content-Disposition` filename parsing) — because the Pro detail response also carries Pydantic `Decimal` fields serialized as JSON strings, reuse the same `toNumber`/normalize-at-the-boundary discipline for `quantita_stimata`/`prezzo_min`/`prezzo_max`.

## No Analog Found

None — every file in the Phase 3 scope has at least a role-match analog already in the codebase (per RESEARCH.md's own framing: "Every piece of Phase 3 infrastructure already has a proven sibling in Phase 1/2 code in this exact repository").

## Metadata

**Analog search scope:** `backend/app/{models,services,schemas,dependencies,routers}/`, `backend/scripts/`, `backend/alembic/versions/`, `backend/tests/`, `frontend/src/{components,pages,routes,api,hooks}/`
**Files scanned:** 24 read in full or targeted (listino.py, catalogo.py, user.py, stima_salvata.py, estimation.py, pdf_service.py, auth.py [dependencies], seed.py, stima.py [schema+router], stima_salvata.py [schema+router], auth.py [schema], 0003_stima_salvata.py, test_no_leak.py, test_estimation.py, test_pdf.py, SoftWallCta.tsx, CategoryCard.tsx, TotalCard.tsx, PdfDownloadButton.tsx, EstimatePage.tsx, RegistratiPage.tsx, App.tsx, useAuth.ts, stima.ts [api])
**Pattern extraction date:** 2026-08-26
