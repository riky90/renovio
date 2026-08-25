# Phase 2: Account & PDF - Pattern Map

**Mapped:** 2026-08-25
**Files analyzed:** 24
**Analogs found:** 22 / 24

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `backend/app/models/user.py` (User, UserSession, PasswordResetToken) | model | CRUD | `backend/app/models/listino.py` | role-match |
| `backend/app/models/stima_salvata.py` (StimaSalvata) | model | CRUD (snapshot write-once) | `backend/app/models/catalogo.py` (Referente FK pattern) + RESEARCH Pattern 3 | role-match |
| `backend/alembic/versions/0002_*.py` | migration | batch/DDL | `backend/alembic/versions/0001_initial_schema.py` | exact |
| `backend/app/schemas/auth.py` (RegistrazioneRequest, LoginRequest, UserOut) | schema | request-response | `backend/app/schemas/stima.py` | exact (anti-leak closed-field pattern) |
| `backend/app/schemas/stima_salvata.py` (StimaSalvataCreate/Out) | schema | request-response | `backend/app/schemas/stima.py` | exact |
| `backend/app/dependencies/auth.py` (get_current_user, require_admin) | middleware | request-response | `backend/app/limiter.py` (shared-instance-module pattern) + RESEARCH Pattern 1 | role-match |
| `backend/app/services/auth_service.py` (hash/verify, session, google convergence) | service | CRUD | `backend/app/services/estimation.py` (Session-in, dataclass-out service shape) | role-match |
| `backend/app/services/email_service.py` | service | event-driven (fire email) | no direct analog — `backend/app/config.py` for env-driven settings shape | no analog |
| `backend/app/services/pdf_service.py` | service | transform (snapshot → PDF bytes) | `backend/app/services/estimation.py` (pure server-side compute, no client input trusted) | role-match |
| `backend/app/routers/auth.py` | controller/router | request-response | `backend/app/routers/stima.py` | exact |
| `backend/app/routers/stime_salvate.py` (`/me/stime`, `/me/stime/{id}`, `/me/stime/{id}/pdf`) | controller/router | CRUD + streaming (PDF) | `backend/app/routers/stima.py` | exact |
| `backend/app/main.py` (MODIFIED — add SessionMiddleware, include new routers) | config | request-response | itself (existing file) | exact |
| `backend/app/config.py` (MODIFIED — add SECRET_KEY, SMTP_*, GOOGLE_*, OAUTH_SESSION_SECRET) | config | — | itself (existing file) | exact |
| `backend/app/templates/pdf_stima.html` | template | transform | no analog (no templates dir exists yet) | no analog |
| `frontend/src/api/auth.ts` | api-client | request-response | `frontend/src/api/stima.ts` | exact |
| `frontend/src/api/client.ts` (MODIFIED — add `credentials: "include"`, POST helper) | utility | request-response | itself (existing file) | exact |
| `frontend/src/hooks/useAuth.ts` | hook | request-response (react-query) | `frontend/src/pages/EstimatePage.tsx` (useMutation usage) | role-match |
| `frontend/src/routes/RegistratiPage.tsx` | component (page) | request-response | `frontend/src/pages/EstimatePage.tsx` + `frontend/src/components/EstimateForm.tsx` | role-match |
| `frontend/src/routes/AccediPage.tsx` | component (page) | request-response | `frontend/src/pages/EstimatePage.tsx` + `EstimateForm.tsx` | role-match |
| `frontend/src/routes/PasswordDimenticataPage.tsx` / `ReimpostaPasswordPage.tsx` | component (page) | request-response | `EstimateForm.tsx` (form + inline validation) | role-match |
| `frontend/src/routes/LeMieStimePage.tsx` | component (page) | CRUD (list + detail) | `frontend/src/pages/EstimatePage.tsx` (skeleton/empty/error state handling) | role-match |
| `frontend/src/components/AccountMenu.tsx` | component | event-driven (menu) | `frontend/src/components/SoftWallCta.tsx` (Button + state pattern) | role-match |
| `frontend/src/components/SoftWallCta.tsx` (MODIFIED) | component | event-driven | itself (existing file) | exact |
| `frontend/src/App.tsx` (MODIFIED — add router) | config | — | itself (existing file) | exact |

## Pattern Assignments

### `backend/app/routers/auth.py` and `backend/app/routers/stime_salvate.py` (controller, request-response)

**Analog:** `backend/app/routers/stima.py`

**Imports pattern** (lines 18-35):
```python
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Request

from app.db import SessionLocal
from app.limiter import limiter
from app.schemas.stima import (
    CategoriaOut,
    ExtraOut,
    StimaInputEcho,
    StimaRequest,
    StimaResponse,
    TotaleOut,
)
from app.services.city_resolver import resolve_listino
from app.services.estimation import EstimationService
```
Replicate exactly: router declared with `APIRouter(prefix="/auth", tags=["auth"])` / `APIRouter(prefix="/me", tags=["stime"])`, `SessionLocal()` opened with `with ... as session:` per request (no dependency-injected DB session exists yet in this codebase — this is the established pattern, don't introduce `Depends(get_db)` unless also refactoring `stima.py`, which is out of scope).

**Rate limiting pattern** (lines 55-57):
```python
@router.post("", response_model=StimaResponse)
@limiter.limit("20/minute")
def crea_stima(payload: StimaRequest, request: Request) -> StimaResponse:
```
Apply `@limiter.limit(...)` to `/auth/login` and `/auth/registrati` per RESEARCH Security Domain (e.g. `5/minute`). `request: Request` parameter is required by slowapi even if unused otherwise.

**Response-building discipline (anti-leak, D-13)** (lines 62-115):
The router NEVER returns an ORM entity or a `.dict()`/`model_validate` of one. It explicitly constructs `CategoriaOut(...)`, `TotaleOut(...)`, `StimaResponse(...)` field-by-field from the internal dataclass result. **Replicate identically** for `UserOut` (never serialize `User.password_hash`) and for `StimaSalvataOut` (never serialize any raw `Listino`/`ListinoCategoria` FK data — only what was already in `risultato_json`).

**Session-scoped DB usage** — the whole handler body runs inside `with SessionLocal() as session:` — the same block must wrap `get_current_user`'s cookie-to-user lookup and any auth mutation (login/registrati/logout).

---

### `backend/app/schemas/auth.py` and `backend/app/schemas/stima_salvata.py` (schema, request-response)

**Analog:** `backend/app/schemas/stima.py`

**Full closed-field pattern** (lines 1-73, whole file is the pattern):
```python
"""Request/response schemas ... The response models ... declare ONLY the
fields in the API contract ... no `base_eur_mq`, `moltiplicatore`,
`coefficiente_impresa`, or `prezzo_impresa` anywhere in this module."""

from __future__ import annotations
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field

class TipoEnum(str, Enum):
    leggera = "leggera"
    ...

class StimaRequest(BaseModel):
    citta: str = Field(min_length=1, max_length=100)
    mq: int = Field(ge=1, le=2000)
    tipo: TipoEnum

class StimaResponse(BaseModel):
    input: StimaInputEcho
    fallback: bool
    ...
```
Apply this exact style to `UserOut` (fields: `id`, `email`, `nome`, `role`, `created_at` — **never** `password_hash`), `RegistrazioneRequest`/`LoginRequest` (bounded `email: EmailStr`, `password: str = Field(min_length=8)`, `nome: str = Field(min_length=1, max_length=200)` per UI-SPEC validation copy), and `StimaSalvataOut` (mirrors `StimaResponse` shape exactly since it comes from `risultato_json`, plus `id`, `created_at`).

---

### `backend/app/models/user.py` and `backend/app/models/stima_salvata.py` (model, CRUD)

**Analog:** `backend/app/models/listino.py` and `backend/app/models/catalogo.py`

**Mapped-column style, FK, server_default, secret-field comment convention** (listino.py lines 1-38):
```python
"""Listino entities. `coefficiente_impresa` is the internal margin secret:
mapped on the ORM entity only, NEVER referenced by any Pydantic response
schema..."""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base

class Listino(Base):
    __tablename__ = "listino"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    valuta: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR", server_default="EUR")
    is_default: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
```
Apply the same style for `User` (`id`, `email` unique+index, `password_hash: str | None` — nullable to support Google-only signup per D-05, `nome`, `role: Mapped[str]` default `"user"`, `created_at`). Add a **module docstring flagging `password_hash` as the secret field**, same convention as `coefficiente_impresa`'s comment — never serialized by any Pydantic schema.

For `UserSession`: `id: Mapped[str]` (the opaque `session_id`, primary key — not autoincrement), `user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))`, `expires_at: Mapped[datetime]`, `created_at` server_default `func.now()` — mirrors the `Referente`/`ComuneListino` FK-to-parent pattern in `catalogo.py` (lines 62-86).

**JSON column for snapshot (dev/prod portability):** use `sqlalchemy.types.JSON` (generic), NOT `postgresql.JSONB`, per RESEARCH Environment Availability note (`JSONB` doesn't exist on SQLite, which is the dev DB per `db.py`'s conditional `connect_args`). Follow `Numeric(12, 2)` for `totale_min`/`totale_max` scalar columns exactly as `ListinoCategoria.base_eur_mq` does (line 36).

---

### `backend/alembic/versions/0002_*.py` (migration, batch/DDL)

**Analog:** `backend/alembic/versions/0001_initial_schema.py` (whole file, lines 1-114)

Replicate: `revision`/`down_revision` header block (set `down_revision = '0001'`), `op.create_table(...)` calls with explicit `sa.Column(...)`/`sa.ForeignKeyConstraint(...)`/`sa.PrimaryKeyConstraint(...)`/`sa.UniqueConstraint(...)`, symmetric `downgrade()` dropping tables in reverse FK order. New tables: `user`, `user_session`, `password_reset_token`, `stima` (FK to `user.id`). No data migration needed (net-new tables only).

---

### `backend/app/dependencies/auth.py` (middleware, request-response)

**Analog:** `backend/app/limiter.py` (shared-instance-in-its-own-module pattern, to avoid circular imports) + RESEARCH Pattern 1 (already vetted against this codebase)

**Shared-module pattern** (limiter.py, whole file):
```python
"""Shared slowapi Limiter instance.

Defined in its own module (not `main.py`) so routers can import and
decorate endpoints ... without a circular import on `app.main`.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
```
Same reasoning applies to `get_current_user`/`require_admin`: put them in their own module (`app/dependencies/auth.py`) importing `SessionLocal` from `app.db`, not from `app.main`, so `routers/auth.py` and `routers/stime_salvate.py` can `Depends()` them without circularity. Use the concrete `get_current_user`/`require_admin` code already drafted in RESEARCH.md Pattern 1 (Cookie dependency, 401/403 via `HTTPException`) verbatim — it was written specifically for this codebase's conventions.

---

### `backend/app/services/auth_service.py` and `pdf_service.py` (service, CRUD / transform)

**Analog:** `backend/app/services/estimation.py`

**Service shape: static methods, Session-in, dataclass/typed-out, Decimal discipline** (lines 59-119):
```python
class EstimationService:
    """Server-side calculation: (listino, mq, tipo) -> StimaResult."""

    @staticmethod
    def compute(session: Session, listino: Listino, mq: int, tipo: str) -> StimaResult:
        ...
        imponibile = lc.base_eur_mq * molt.valore * Decimal(mq)
        ...
        cat_min = _eur(categoria_totale * (Decimal("1") - range_pct))
```
Apply the same `@staticmethod`-on-a-class-with-no-instance-state shape to `AuthService` (`hash_password`, `verify_password`, `create_session`, `get_or_create_user_by_email` for Google convergence D-05) and to `PdfService.render(stima: StimaSalvata, user: User) -> bytes`. Critically: **`pdf_service.py` must NEVER import or call `EstimationService.compute()`** — it reads only `StimaSalvata.risultato_json` (RESEARCH Pitfall 5 / D-09 immutability). Use RESEARCH's Code Examples (`hash_password`/`verify_password` via argon2-cffi, `render_pdf` via Jinja2+WeasyPrint) as the concrete starting point — they were written specifically for this stack.

---

### `frontend/src/api/auth.ts` (api-client, request-response)

**Analog:** `frontend/src/api/stima.ts`

**Fetch + typed request/response + normalization pattern** (lines 1-4, 135-157):
```typescript
import { ApiError } from "@/api/client";
...
export async function postStima(request: StimaRequest): Promise<StimaResponse> {
  const API_BASE = import.meta.env.VITE_API_BASE as string | undefined;
  if (!API_BASE) {
    throw new Error("VITE_API_BASE non configurato (vedi frontend/.env.example)");
  }
  const response = await fetch(`${API_BASE}/stima`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new ApiError(response.status, `POST /stima fallita con status ${response.status}`);
  }
  const raw = (await response.json()) as RawStimaResponse;
  return normalizeResponse(raw);
}
```
**Critical addition (RESEARCH Pitfall 4):** every auth/session fetch call MUST add `credentials: "include"` to the `fetch()` options — this does not exist anywhere in the current codebase and is required for the httpOnly cookie to be sent cross-origin in dev. Apply to `postRegistrazione`, `postLogin`, `postLogout`, `getMe`, `postSalvaStima`, `getStoricoStime`, `getStimaDettaglio`, `getPdfDownload`. If Decimal-as-string normalization applies to any auth/stima-salvata numeric field, reuse `normalizeResponse`/`toNumber` verbatim (lines 104-133).

**Also modify `frontend/src/api/client.ts`:** the shared `apiGet` helper (lines 21-33) currently has no `credentials: "include"` and no POST helper — add both, keeping the same `ApiError` class and `API_BASE` guard-clause style (lines 9-19).

---

### `frontend/src/routes/*.tsx` auth pages (component, request-response)

**Analog:** `frontend/src/pages/EstimatePage.tsx` (mutation/loading/error/success state machine) + `frontend/src/components/EstimateForm.tsx` (not read in full, but referenced as the "hand-rolled validation" baseline in UI-SPEC — inspect it directly when implementing, since UI-SPEC explicitly says it's an acceptable equivalent to shadcn `form`)

**react-query mutation + state branching pattern** (EstimatePage.tsx lines 23-41):
```typescript
const mutation = useMutation<StimaResponse, Error, EstimateFormValues>({
  mutationFn: postStima,
});
...
const showResult = mutation.isSuccess && result;
const showLoading = mutation.isPending;
const showError = mutation.isError;
```
Replicate for login/registration mutations: `useMutation({ mutationFn: postLogin })`, same `isPending`/`isError`/`isSuccess` branching for the loading/error/success card states described in UI-SPEC §G ("Auth form submitting").

**Card shell + centered layout** (EstimatePage.tsx line 44):
```typescript
<main className="mx-auto flex min-h-svh w-full max-w-[480px] flex-col gap-8 px-4 py-8 sm:max-w-[640px] sm:px-6 sm:py-12 lg:py-16">
```
UI-SPEC §B/§C specify `max-width: 400px` for the auth card — narrower than the estimate flow's 480/640px, so don't copy the width token, only the centering/padding/gap convention.

**Error alert pattern** (lines 72-82):
```typescript
<Alert variant="destructive">
  <AlertDescription>{ERROR_COPY}</AlertDescription>
</Alert>
```
Reuse verbatim for "credenziali non valide" / "email già registrata" per UI-SPEC §C.

---

### `frontend/src/components/AccountMenu.tsx` (component, event-driven)

**Analog:** `frontend/src/components/SoftWallCta.tsx` (whole file, lines 1-58)

**Button + local state + `cn()` conditional class pattern:**
```typescript
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function SoftWallCta() {
  const [feedback, setFeedback] = useState<string | null>(null);
  function handleClick() { setFeedback(FEEDBACK); }
  return ( ... )
}
```
`AccountMenu` swaps the local-state feedback pattern for shadcn `dropdown-menu` + `avatar` (net-new installs per UI-SPEC), but keeps the same "small, self-contained component importing only `ui/*` primitives + `cn`" shape.

**`SoftWallCta.tsx` itself is MODIFIED, not net-new** — its own current code (lines 5-11, `SECONDARY_CTAS` array and `handleClick`) is the direct base to edit: 2 of 4 buttons (`"Scarica PDF"`, `"Salva / crea account"`) change from `onClick={handleClick}` (soft-wall feedback) to real navigation/mutation per UI-SPEC §A; `"Passa a Pro"` and `"Contatta un professionista"` keep `onClick={handleClick}` unchanged.

---

## Shared Patterns

### Anti-leak closed-field response schemas (D-13, binding)
**Source:** `backend/app/schemas/stima.py` (whole file) + `backend/app/routers/stima.py` lines 62-115
**Apply to:** `schemas/auth.py`, `schemas/stima_salvata.py`, `routers/auth.py`, `routers/stime_salvate.py`, `templates/pdf_stima.html`
Never `model_validate`/`.dict()` an ORM entity toward the client. Always hand-build the Pydantic response object field-by-field. `User.password_hash`, `Listino.coefficiente_impresa`, `ListinoCategoria.base_eur_mq` must never appear in any schema, router return, or Jinja2 template context.

### Decimal discipline for monetary fields
**Source:** `backend/app/services/estimation.py` `_eur()` (lines 28-30) + `backend/app/routers/stima.py` `_split_imponibile_iva()` (lines 42-52)
**Apply to:** `models/stima_salvata.py` (`Numeric(12,2)` columns), `services/pdf_service.py` (reads Decimal from JSON — note: JSON round-trip loses Decimal type, so `risultato_json` values come back as `str`/`float`; the PDF template must format with the same `Intl`/Python `Decimal(str(...))` re-hydration discipline, never re-derive/recompute).

### DB session-per-request via `SessionLocal()` context manager
**Source:** `backend/app/routers/stima.py` line 58 (`with SessionLocal() as session:`)
**Apply to:** `routers/auth.py`, `routers/stime_salvate.py`, `dependencies/auth.py`. No `Depends(get_db)` generator exists in this codebase yet — stay consistent with the established pattern rather than introducing a new DI style, unless the planner explicitly decides to refactor.

### Rate limiting via shared `limiter` instance
**Source:** `backend/app/limiter.py` (whole file) + usage in `backend/app/routers/stima.py` lines 55-56
**Apply to:** `routers/auth.py` (`/auth/login`, `/auth/registrati` — RESEARCH Security Domain recommends e.g. `5/minute` for login to mitigate credential stuffing).

### CORS/cookie cross-origin dev config (RESEARCH Pitfall 4, Open Question 1)
**Source:** `backend/app/main.py` lines 17-23 (`CORSMiddleware(allow_credentials=True, ...)` — **already present**, confirms Open Question 1 answered: no change needed here) + `frontend/src/api/client.ts`/`stima.ts` (currently missing `credentials: "include"` — must be added)
**Apply to:** every new frontend fetch call touching auth/session endpoints.

### react-query mutation/loading/error/success state machine
**Source:** `frontend/src/pages/EstimatePage.tsx` lines 23-41, 56-116
**Apply to:** all new auth/account pages (`RegistratiPage`, `AccediPage`, `PasswordDimenticataPage`, `ReimpostaPasswordPage`, `LeMieStimePage`).

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `backend/app/services/email_service.py` | service | event-driven | No email/SMTP integration exists in Phase 1; use RESEARCH.md's `aiosmtplib`-based abstraction (astrazione SMTP dietro env vars) as the primary reference, styled like `config.py`'s `Settings` class for the `SMTP_HOST/PORT/USER/PASSWORD/FROM` env vars. |
| `backend/app/templates/pdf_stima.html` | template | transform | No `templates/` directory or Jinja2 usage exists yet. Build from UI-SPEC §H content contract (branding, palette, layout order) + RESEARCH's `render_pdf` Code Example, not from an existing analog. |

## Metadata

**Analog search scope:** `backend/app/` (models, schemas, services, routers, db.py, config.py, limiter.py, main.py), `backend/alembic/versions/`, `frontend/src/` (api, components, pages, App.tsx)
**Files scanned:** ~24 (all backend/app Python files, all frontend/src TS/TSX files except `ui/*` shadcn primitives and `lib/*` utilities, which are stable installed components not pattern sources)
**Pattern extraction date:** 2026-08-25
