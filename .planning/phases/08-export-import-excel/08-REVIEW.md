---
phase: 08-export-import-excel
reviewed: 2026-09-22T00:00:00Z
depth: standard
files_reviewed: 35
files_reviewed_list:
  - backend/alembic/versions/0018_export_log.py
  - backend/alembic/versions/0019_updated_at_curatela.py
  - backend/app/models/__init__.py
  - backend/app/models/arredo.py
  - backend/app/models/catalogo.py
  - backend/app/models/dettaglio_pro.py
  - backend/app/models/export_log.py
  - backend/app/models/lead.py
  - backend/app/models/listino.py
  - backend/app/routers/admin/__init__.py
  - backend/app/routers/admin/coefficienti.py
  - backend/app/routers/admin/export_log.py
  - backend/app/routers/admin/import_excel.py
  - backend/app/routers/admin/lead.py
  - backend/app/routers/admin/listini.py
  - backend/app/routers/admin/upload_listino.py
  - backend/app/schemas/admin_export.py
  - backend/app/schemas/admin_import.py
  - backend/app/schemas/admin_upload.py
  - backend/app/services/export_excel/__init__.py
  - backend/app/services/export_excel/lead.py
  - backend/app/services/export_excel/listino.py
  - backend/app/services/export_excel/parametri.py
  - backend/app/services/export_excel/workbook.py
  - backend/app/services/import_excel/__init__.py
  - backend/app/services/import_excel/flat.py
  - backend/app/services/import_excel/lead.py
  - backend/app/services/import_excel/parametri.py
  - backend/app/services/import_excel/registry.py
  - backend/app/services/listino_upload_service.py
  - backend/tests/test_export_excel_listino.py
  - backend/tests/test_export_import_roundtrip.py
  - backend/tests/test_export_lead_traccia.py
  - backend/tests/test_export_margine.py
  - backend/tests/test_import_lead.py
  - backend/tests/test_import_parametri.py
  - backend/tests/test_import_stale.py
  - frontend/src/api/admin/anteprima.ts
  - frontend/src/api/admin/exportExcel.ts
  - frontend/src/api/admin/exportLog.ts
  - frontend/src/api/admin/importExcel.ts
  - frontend/src/api/admin/uploadListino.ts
  - frontend/src/components/admin/AnteprimaTab.tsx
  - frontend/src/components/admin/DiffPreviewTable.tsx
  - frontend/src/components/admin/ExcelUploadDialog.tsx
  - frontend/src/components/admin/FlatImportDialog.tsx
  - frontend/src/lib/adminCopy.ts
  - frontend/src/lib/tipoRistrutturazione.ts
  - frontend/src/pages/admin/CoefficientiPage.tsx
  - frontend/src/pages/admin/LeadDashboardPage.tsx
  - frontend/src/pages/admin/ListiniPage.tsx
findings:
  critical: 3
  warning: 3
  info: 1
  total: 7
status: issues_found
---

# Phase 08: Code Review Report

**Reviewed:** 2026-09-22
**Depth:** standard
**Files Reviewed:** 35 (backend + frontend)
**Status:** issues_found

## Summary

Reviewed export/import Excel for listino, parametri, lead. The margin anti-leak
discipline (regola di dominio #1) holds up well end-to-end: `coefficiente_impresa`
never appears in a default export, the opt-in variant is admin-gated redundantly
(route + resolver + write function), and `Voce`/`Lead` structurally cannot carry
margin columns. That part is solid and well tested (`test_export_margine.py`,
`test_import_parametri.py`).

The second priority — data loss / silent overwrite from import — is where this
phase has real gaps. Three confirmed bugs, none covered by any existing test — the first two
provable by tracing the code, the third reproduced by running the migration:

1. `listino_upload_service.py`'s natural-key upsert path (`_upsert_sottocategoria`/
   `_upsert_voce`) ignores `VoceRigaIn.campi_presenti` and unconditionally
   overwrites fields with placeholder defaults — contradicting the "campo assente
   = non toccato" invariant the same module enforces correctly on the id-based
   path. Triggered by the ordinary, advertised workflow of adding a new voce to
   an existing sottocategoria via the flat re-upload.
2. The generic import round-trip (`/admin/import-excel/{lead,parametri}`) loses
   the `#CANCELLA#`→cancellation signal between preview and confirm: the
   frontend reconstructs `RigaPiattaIn.valori` straight from `valori_nuovi`
   (which can legitimately contain `null` for a cancelled field) but always
   sends `campi_da_cancellare: []`. Backend string-field resolvers then do
   `str(None)` and write the literal text `"None"` to the database instead of
   NULL — for `lead.nota` and `coefficienti_pro.domanda_mirata_key`.
3. Migration `0019` uses `server_default=sa.func.now()` on nine `add_column`
   calls, which SQLite rejects (`Cannot add a column with non-constant
   default`). `DATABASE_URL` defaults to SQLite, so `alembic upgrade head`
   fails and the `updated_at` columns exist only in the metadata-built test
   schema, never in a migrated database. Found on 2026-09-23 while bringing the
   local database up to head.

## Critical Issues

### CR-01: Natural-key upsert silently overwrites untouched fields, resetting them to placeholder defaults

**File:** `backend/app/services/listino_upload_service.py:454-479` (`_upsert_sottocategoria`), `:482-516` (`_upsert_voce`), called from `:619-621`

**Issue:**
`apply_diff_idempotent` dispatches on `riga.id`:
- when `riga.id is not None` it uses `_resolve_per_id` + `_applica_sottocategoria`/`_applica_voce`, which correctly apply **only** the fields present in `riga.campi_presenti` (the D-09 invariant: "campo assente dal file = campo non toccato").
- when `riga.id is None` it falls through to `_upsert_sottocategoria`/`_upsert_voce`, which resolve the row by **natural key** and then unconditionally overwrite `sotto.nome`/`sotto.famiglia`/`sotto.ordine` and `voce.descrizione`/`voce.um`/`voce.prezzo_unitario_cliente`/`voce.ordine` from the `VoceRigaIn` instance — with no `campi_presenti` check at all.

For rows coming from `parse_computo` (legacy computo format) this is fine and intentional: `campi_presenti is None` there means "every field is genuinely present." But `parse_flat_listino` also produces `riga.id is None` rows whenever a row in the flat file has no `id` — which is the **documented, supported way to add a new voce under an existing sottocategoria** (`_CAMPI_RICHIESTI_RIGA_NUOVA` deliberately does not require `sottocategoria_ordine`, `codice`, or `livello`). In that case:
- `_upsert_sottocategoria` looks up the natural key, finds the **existing** sottocategoria (only the voce is new), and overwrites `sotto.ordine` with `_campo_intero(valori, "sottocategoria_ordine")`, which **defaults silently to `0`** whenever the column is blank/absent — resetting the real ordering of an existing sottocategoria that the file was never meant to touch.
- The same unconditional-overwrite shape applies to `voce.ordine` (defaults to `0`) whenever an *existing* voce is matched via natural key instead of by id (e.g. an admin clears/loses the `id` cell of a row being edited by hand in the re-downloaded flat file — plausible copy/paste error, and not defended against).

This directly contradicts the module's own advertised guarantee (`VoceRigaIn.campi_presenti` docstring, `_applica_voce`/`_applica_sottocategoria` docstrings) and matches the review's top data-loss concern: an import can zero out a field the file never intended to touch, with no scarto and no error surfaced to the admin.

None of the existing round-trip tests exercise this path: `TestPreservazioneCampi`, `TestColonnaAssenteNonAzzera`, and `TestTokenCancella` in `test_export_import_roundtrip.py` all operate on rows with a real `id` (id-based path); `TestRigaSenzaId` only covers a *genuinely* new sottocategoria+voce pair, where the overwrite is harmless because there's nothing existing to clobber.

**Fix:** Make `_upsert_sottocategoria`/`_upsert_voce` respect `riga.campi_presenti` the same way `_applica_sottocategoria`/`_applica_voce` already do, e.g.:
```python
def _upsert_sottocategoria(db: Session, listino_id: int, riga: VoceRigaIn) -> Sottocategoria:
    ...
    sotto = query.one_or_none()
    presenti = riga.campi_presenti  # None => legacy "all present" (parse_computo)
    if sotto is None:
        sotto = Sottocategoria(..., ordine=riga.sottocategoria_ordine if presenti is None or "sottocategoria_ordine" in presenti else 0, ...)
        db.add(sotto)
        db.flush()
    else:
        if presenti is None or "sottocategoria_nome" in presenti:
            sotto.nome = riga.sottocategoria_nome
        if presenti is None or "sottocategoria_famiglia" in presenti:
            sotto.famiglia = riga.sottocategoria_famiglia
        if presenti is None or "sottocategoria_ordine" in presenti:
            sotto.ordine = riga.sottocategoria_ordine
    return sotto
```
and analogously for `_upsert_voce`.

### CR-02: `#CANCELLA#` round-trip through the generic import UI writes the literal string `"None"` instead of NULL

**File:** `frontend/src/components/admin/FlatImportDialog.tsx:74-76` (`toRigaPiattaIn`), `backend/app/services/import_excel/lead.py:169-170` (`_risolvi`), `backend/app/services/import_excel/parametri.py:315-319` (`_risolvi_coeff_pro`), `backend/app/schemas/admin_import.py:41-56` (`DiffRigaOut.valori_nuovi`)

**Issue:**
When a preview diff represents a `#CANCELLA#` cancellation, the affected field's new value in `DiffRigaOut.valori_nuovi` is Python/JSON `None` (see `lead.py` `diff()`: `validati["nota"] = None` → `cambiati["nota"] = (precedente, None)` → `valori_nuovi["nota"] = None`; same shape in `parametri.py` for `coefficienti_pro`).

`FlatImportDialog.toRigaPiattaIn` reconstructs the `/confirm` payload as:
```ts
function toRigaPiattaIn(row: DiffRigaOut): RigaPiattaIn {
  return { foglio: row.foglio, id: row.id, valori: row.valori_nuovi, campi_da_cancellare: [] };
}
```
It always sends `campi_da_cancellare: []`, so the `null` stays embedded inside `valori` instead of being moved to `campi_da_cancellare` (the channel the backend actually uses to distinguish "cancel" from "real value", per `admin_import.py`'s own docstring). The Python test helper `_a_riga_piatta_in` in `test_import_lead.py`/`test_import_parametri.py` reconstructs the payload the exact same (buggy) way — which is why no test catches this.

On `/confirm`, the backend re-resolves and does:
```python
# lead.py _risolvi
if "nota" in r.valori:
    validati["nota"] = str(r.valori["nota"])   # str(None) == "None"
```
```python
# parametri.py _risolvi_coeff_pro
if "domanda_mirata_key" in r.valori:
    chiave = str(r.valori["domanda_mirata_key"]).strip()   # str(None) == "None", non-empty
    ...
    validati["domanda_mirata_key"] = chiave
```
Both write the **literal three-character string `"None"`** to the database, silently corrupting the field instead of nulling it. (Integer-typed nullable fields — `referente_id`, `default_conteggio`, `coefficiente_qta_per_mq` — fail safely instead, because `int(None)`/`Decimal(str(None))` raise and the row is scarted; only the string-typed nullable columns are actually corrupted.)

This is reachable by any admin/staff who: uploads a flat export, edits a nullable text cell to `#CANCELLA#` (an officially documented, supported action per `ISTRUZIONI!A1`), previews, and clicks "Conferma import" in `FlatImportDialog` — the standard UI flow for both the `lead` and `parametri` resources.

**Fix:** In `toRigaPiattaIn` (and in the Python test helper, and anywhere else that reconstructs `RigaPiattaIn` from a `DiffRigaOut`), split out `null` values:
```ts
function toRigaPiattaIn(row: DiffRigaOut): RigaPiattaIn {
  const valori: Record<string, unknown> = {};
  const campiDaCancellare: string[] = [];
  for (const campo of row.campi_modificati) {
    const v = row.valori_nuovi[campo];
    if (v === null) campiDaCancellare.push(campo);
    else valori[campo] = v;
  }
  return { foglio: row.foglio, id: row.id, valori, campi_da_cancellare: campiDaCancellare };
}
```
As defense in depth, the backend resolvers should also treat an explicit `None` reaching a string-typed branch as invalid input (scarto) rather than stringifying it, so a similar client bug can never silently corrupt data again.

### CR-03: Migration `0019` cannot be applied on SQLite, so the phase's own schema change never reaches a dev database

**File:** `backend/alembic/versions/0019_updated_at_curatela.py:31-39` (all nine `add_column` calls)

**Issue:**
Every column is added as `sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False)`. On SQLite, `ALTER TABLE ... ADD COLUMN` only accepts a *constant* default, so `DEFAULT CURRENT_TIMESTAMP` is rejected outright:

```
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) Cannot add a column with non-constant default
[SQL: ALTER TABLE sottocategoria ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL]
```

`alembic upgrade head` therefore fails on the very first statement and the whole migration is a no-op. `backend/.env` and the `DATABASE_URL` default in `backend/app/config.py:19` are both `sqlite:///./dev.db`, so this is the configuration every developer actually runs: the local database is stuck at revision `0018` and the nine `updated_at` columns simply do not exist there.

The test suite does not catch this because the tests build their schema from the SQLAlchemy metadata (`create_all`), not by running the migration chain — so the columns are present in tests and absent in any database that was migrated. That divergence is the real defect: the staleness guard (D-11) that plan `08-08` delivers is untestable and unusable against a migrated database, and anything reading `updated_at` raises `OperationalError: no such column` there.

**Fix:** Add the column as nullable with no server default, backfill the existing rows with an explicit timestamp, then tighten the constraint in a way SQLite supports (`batch_alter_table`, which rebuilds the table):

```python
def upgrade() -> None:
    for tabella in _TABELLE:
        op.add_column(tabella, sa.Column("updated_at", sa.DateTime(), nullable=True))
        op.execute(sa.text(f"UPDATE {tabella} SET updated_at = :adesso").bindparams(adesso=datetime.now(timezone.utc)))
        with op.batch_alter_table(tabella) as batch:
            batch.alter_column("updated_at", existing_type=sa.DateTime(), nullable=False,
                               server_default=sa.func.now())
```

The backfilled instant stays earlier than any export generated afterwards, so the property the original docstring relies on — the first re-import does not mark every row as stale — is preserved.

As a guard against the next migration that passes tests and fails on a real database, the gap-closure work should add a check that runs the full `alembic upgrade head` chain against a throwaway SQLite file.

## Warnings

### WR-01: `bool()` coercion of manually-edited Excel cells is truthy for any non-empty string

**File:** `backend/app/services/import_excel/parametri.py:282` (`extra.attivo`), `:388` (`forfait_arredo.attivo`); comparison-side variant in `backend/app/services/import_excel/lead.py:101-102` (`email_inviata`)

**Issue:** `validati["attivo"] = bool(r.valori["attivo"])` round-trips correctly when the cell was never touched (openpyxl preserves the native boolean type from export). But if an admin manually edits the cell and types e.g. `"FALSE"`, `"no"`, or `"0"` as text (easy to do, Excel doesn't enforce a boolean cell type), `bool("FALSE")` and `bool("0")` are both `True` in Python — the row silently stays/becomes active when the admin's intent was clearly to deactivate it. The same pattern in `lead.py`'s `_valori_uguali` (`bool(valore_db) == bool(valore_file)` for `email_inviata`) can produce a false "field diverges" scarto that blocks an otherwise-valid `stato`/`nota` update, for a column the admin never meant to touch.

**Fix:** Normalize truthy/falsy text explicitly, e.g.:
```python
def _to_bool(v: object) -> bool | None:
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in ("true", "1", "si", "sì", "x"):
        return True
    if s in ("false", "0", "no", ""):
        return False
    return None  # -> scarto, not a silent guess
```

### WR-02: `parametri.py apply()` silently drops a new `listino_categoria` row when the margin is absent, with no scarto and a mismatched applied-count

**File:** `backend/app/services/import_excel/parametri.py:634-643`

**Issue:** For a brand-new `listino_categoria` row (`ris.esistente is None`), `apply()` requires `coefficiente_impresa` (NOT NULL column) to be present and `is_admin=True`; otherwise it does a bare `continue` — the row was already shown to the admin in the preview's `nuove` list (via `diff()`), so `/confirm` returning a `righe_applicate` count lower than `len(nuove) + len(modificate)` with no explanation is confusing, and nothing in the response tells the admin which row silently failed or why. The code comment even acknowledges this as a "limite noto, non esercitato dai test."

**Fix:** Either reject this case at `diff()` time with a proper `ScartoRowOut` (so the admin sees it in the preview's scarti list before confirming), or have `apply()` return per-row failure info instead of a single aggregate count.

### WR-03: Frontend `VoceRiga`/`DiffRow` types omit `id` and `campi_presenti`, relying on accidental JS pass-through

**File:** `frontend/src/api/admin/uploadListino.ts:20-31` (`VoceRiga` interface), `frontend/src/components/admin/ExcelUploadDialog.tsx:110-113`

**Issue:** The backend's `VoceRigaIn` always carries `id` and `campi_presenti` over the wire, and `_upsert_voce`/`_applica_voce`'s correctness for the id-based path (see CR-01) depends entirely on `campi_presenti` surviving the preview→confirm round trip. The TS `VoceRiga` interface declares neither field. It works today only because `normalizeDiffRow` (`uploadListino.ts:72-78`) passes `raw.riga` through unchanged and `ExcelUploadDialog` re-sends `r.riga` verbatim — the real runtime object still has both fields, the TS type is just wrong. The moment any future code reconstructs a `VoceRiga` object field-by-field (e.g. to let the admin hand-edit a row before confirming, a natural next feature for this dialog), `id`/`campi_presenti` would be silently dropped and every affected row would fall onto the unconditional-overwrite path described in CR-01.

**Fix:** Declare `id: number | null` and `campi_presenti: string[] | null` on `VoceRiga`/`RawDiffRow` so the type system reflects the actual wire contract and catches future regressions.

## Info

### IN-01: `apply()` counts no-op rows as "applicate"

**File:** `backend/app/services/import_excel/parametri.py:609-651`, `backend/app/services/import_excel/lead.py:294-307`

**Issue:** When a resolved row has an `id` but the file carries no fields that actually differ from the database (`campi_aggiornati`/`validati` empty), `apply()` still increments `applicate`/`righe_applicate`. The count reported to the admin ("N righe applicate") therefore isn't strictly "N righe cambiate," which can be mildly misleading for a round-trip-at-rest confirm.

**Fix:** Only count a row as applied if at least one field was actually set, or rename the reported number in the UI copy to avoid implying "changed."

---

_Reviewed: 2026-09-22_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
