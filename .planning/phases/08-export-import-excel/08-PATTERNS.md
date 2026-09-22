# Phase 08: Export/import Excel dal pannello admin - Pattern Map

**Mapped:** 2026-09-22
**Files analyzed:** 17 (10 backend, 7 frontend)
**Analogs found:** 15 / 17 (2 parziali, segnalati in "No Analog Found")

Nota d'ambiente: i test backend girano con
`backend/.venv/Scripts/python.exe -m pytest` (il `python` di sistema non ha le
dipendenze); la suite completa impiega ~11 minuti.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `backend/app/models/export_log.py` (nuovo) | model | event-driven (audit write) | `backend/app/models/user.py::UserSession` | role-match |
| `backend/alembic/versions/00XX_export_log.py` (nuovo) | migration | batch (DDL additivo) | `backend/alembic/versions/0017_derivazione_risposta.py` | exact |
| `backend/app/schemas/admin_export.py` (nuovo) | model (schema Pydantic) | request-response | `backend/app/schemas/admin_domande.py` | exact |
| `backend/app/services/export_excel_service.py` (nuovo) | service | file-I/O (write) | `backend/app/services/pdf_service.py` (build_filename) + `listino_upload_service.py` (struttura modulo) | role-match |
| `backend/app/services/listino_upload_service.py` (esteso, D-01/D-03) | service | file-I/O (read) + CRUD | se stesso (`parse_computo`, `_voce_key`, `apply_diff_idempotent`) | exact |
| `backend/app/routers/admin/listini.py` (esteso: `GET /export.xlsx`) | route/controller | file-I/O + request-response | `backend/app/routers/dettaglio_pro.py::scarica_pdf_pro` | exact |
| `backend/app/routers/admin/domande.py` (esteso: `GET /export.xlsx`, CRUD domande/opzioni/effetti già presente) | route/controller | file-I/O + CRUD | se stesso (route CRUD già nel file) + `scarica_pdf_pro` per l'export | exact |
| `backend/app/routers/admin/coefficienti.py` (esteso: `GET /export.xlsx` con variante `?margine=true`) | route/controller | file-I/O + request-response | `scarica_pdf_pro` + se stesso per gating | exact |
| `backend/app/routers/admin/lead.py` (esteso: `GET /export.xlsx`, `require_staff`) | route/controller | file-I/O + request-response | `scarica_pdf_pro` + se stesso (`require_staff`) | exact |
| `backend/app/routers/admin/upload_listino.py` (esteso o affiancato per il formato piatto, D-01) | route/controller | file-I/O + CRUD | se stesso (`POST /preview` + `POST /confirm`) | exact |
| `backend/tests/test_export_import_roundtrip.py` (nuovo) | test | batch (round-trip) | `backend/tests/test_dettaglio_pro_livelli.py` (classe `TestSeedEAdmin`, in particolare `test_upload_excel_non_azzera_livello:261`) | exact |
| `frontend/src/api/admin/exportExcel.ts` (nuovo) | utility (api client) | file-I/O (blob download) | `frontend/src/api/admin/uploadListino.ts` (fetch diretto, non-JSON) | role-match (nessun analog per risposta blob, vedi sotto) |
| `frontend/src/api/admin/domande.ts` (nuovo) | utility (api client) | CRUD | `frontend/src/api/admin/listini.ts` | exact |
| `frontend/src/pages/admin/DomandeCrudPage.tsx` (nuovo, D-21) | component (pagina) | CRUD (master-detail) | `frontend/src/pages/admin/ListiniPage.tsx` (listino→categoria→voce) + `CoefficientiPage.tsx::ExtraTab` (badge attivo/non attivo) | exact |
| `frontend/src/pages/admin/CoefficientiPage.tsx` (esteso: sesta tab Anteprima, D-18) | component (pagina) | request-response | se stesso (pattern tab `MoltiplicatoriTab`/`ExtraTab`) | exact |
| `frontend/src/components/admin/ExcelUploadDialog.tsx` (esteso: badge stale + banner, D-11) | component | file-I/O (preview) | se stesso | exact |
| `frontend/src/pages/admin/ListiniPage.tsx` / `CoefficientiPage.tsx` / `LeadDashboardPage.tsx` (estese: toolbar Scarica/Carica, D-26) | component (pagina) | file-I/O + request-response | `ListiniPage.tsx` (bottone "Carica listino da Excel" già presente, riga 194-196) | exact |
| `frontend/src/pages/admin/LeadDashboardPage.tsx` (esteso: sezione "Download registrati", D-16) | component (pagina) | request-response (read-only list) | se stessa (`AdminTable` + `rows` mapping già nel file) | exact |

## Pattern Assignments

### `backend/app/models/export_log.py` (model, event-driven/audit)

**Analog:** `backend/app/models/user.py::UserSession` (id/user_id FK/timestamp) e
`backend/app/models/domanda.py::AttesaImmobile` (tabella semplice senza colonne
di margine).

**Import pattern:**
```python
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
```

**Core pattern — colonne minime richieste da D-15** (chi, cosa, quando, quante
righe, se includeva il margine):
```python
class ExportLog(Base):
    __tablename__ = "export_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False, index=True)
    risorsa: Mapped[str] = mapped_column(String(32), nullable=False)  # "listino"|"domande"|"parametri"|"lead"
    righe: Mapped[int] = mapped_column(nullable=False)
    include_margine: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
```
Nota: `listino.py` usa `Numeric(4,3)` per il coefficiente e `func.now()` per
`created_at` — stesso stile da riusare qui (vedi `models/listino.py:24`).

### `backend/alembic/versions/00XX_export_log.py` (migration, batch/DDL)

**Analog:** `backend/alembic/versions/0017_derivazione_risposta.py` — SOLO
`create_table`, nessuna modifica distruttiva, docstring che spiega il "perché"
prima del "come".

**Core pattern (righe 21-78 di 0017):**
```python
def upgrade() -> None:
    op.create_table(
        "export_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("risorsa", sa.String(length=32), nullable=False),
        sa.Column("righe", sa.Integer(), nullable=False),
        sa.Column("include_margine", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("export_log")
```
Verificare `down_revision` contro l'ultima head reale (`alembic heads`) prima
di fissare il numero — non assumere `0018` senza controllare se altre fasi
hanno già aggiunto migrazioni.

### `backend/app/schemas/admin_export.py` (schema Pydantic, request-response)

**Analog:** `backend/app/schemas/admin_domande.py` — stesso fork deliberato:
classi usate solo dalle route export/import, bound numerici e di lunghezza
ovunico (ASVS V5), mai lo stesso schema del layer pubblico.

**Core pattern (adattato da righe 21-48 di `admin_domande.py`):**
```python
class ExportLogOut(BaseModel):
    id: int
    user_id: int
    user_label: str  # nome o email, risolto dal router — mai l'id nudo in UI
    risorsa: str
    righe: int
    include_margine: bool
    created_at: datetime
```

### `backend/app/services/export_excel_service.py` (service, file-I/O write) — NUOVO

**Analog primario per la scrittura del file:** nessun modulo esistente scrive
`.xlsx` (openpyxl è oggi solo in lettura in `listino_upload_service.py`), ma
`openpyxl` è già in `backend/pyproject.toml` — nessuna dipendenza nuova.
**Analog per naming/streaming:** `backend/app/services/pdf_service.py`
(`build_filename`/`build_filename_pro`, righe 71-83) e il router che lo
consuma (`scarica_pdf_pro`, vedi sotto).

**Import pattern:**
```python
from __future__ import annotations

import io
from datetime import datetime, timezone

import openpyxl
from openpyxl.worksheet.worksheet import Worksheet
from sqlalchemy.orm import Session
```

**Naming convention da riusare (adattata da `pdf_service.py:78-82`):**
```python
def build_filename_listino(*, con_margine: bool = False) -> str:
    """`parametri-motore_con-margine_2026-09-22.xlsx` vs
    `parametri-motore_2026-09-22.xlsx` (contratto UI §B)."""
    data_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    marcatore = "_con-margine" if con_margine else ""
    return f"parametri-motore{marcatore}_{data_str}.xlsx"
```

**Core pattern — foglio ISTRUZIONI/AVVISO + timestamp export (D-09, D-11, D-13),
scrittura a `BytesIO` per essere passata a `StreamingResponse`:**
```python
def build_workbook(righe: list[dict], *, con_margine: bool = False) -> bytes:
    wb = openpyxl.Workbook()
    istruzioni: Worksheet = wb.active
    istruzioni.title = "ISTRUZIONI"
    istruzioni["A1"] = (
        "Cella vuota = campo non modificato. Per cancellare un valore "
        "esistente scrivi #CANCELLA# nella cella."
    )
    istruzioni["A2"] = f"Generato il: {datetime.now(timezone.utc).isoformat()}"
    if con_margine:
        avviso = wb.create_sheet("AVVISO", 0)
        avviso["A1"] = (
            "Questo file contiene il coefficiente impresa (margine). Uso "
            "riservato al ruolo admin. Non inoltrare."
        )

    dati = wb.create_sheet("dati")
    # ... header colonna id (D-03) in colonna A, poi le colonne esplicite ...

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
```

**Anti-leak (D-13):** il default NON deve includere `coefficiente_impresa` —
stessa disciplina di `schemas/admin_coefficienti.py`/`admin_upload.py`, qui
applicata scegliendo quali colonne aggiungere invece di quali serializzare.

### `backend/app/services/listino_upload_service.py` (service, file-I/O read + CRUD) — ESTESO

**Analog:** se stesso. `parse_computo` (riga 92) resta intatto per il formato
annidato del computo; il nuovo formato piatto (D-01) va riconosciuto
dall'header o da un foglio/marcatore dedicato (discrezione, vedi D-01 nota
"Claude's Discretion") con una funzione parallela, es.
`parse_flat_export(file_bytes) -> tuple[list[RigaIn], list[ScartoRowOut]]`,
che riusa `_voce_key`/`_sotto_key` **estese con la colonna id** (D-03):

**Chiave naturale da estendere (righe 74-89):**
```python
def _sotto_key(riga: VoceRigaIn) -> tuple[str, str | None, str | None]:
    if riga.sottocategoria_codice is not None:
        return (riga.categoria_code, riga.sottocategoria_codice, None)
    return (riga.categoria_code, None, riga.sottocategoria_nome)


def _voce_key(riga: VoceRigaIn) -> tuple[str, str | None, str | None]:
    sotto_key = _sotto_key(riga)
    if riga.codice is not None:
        return (*sotto_key, riga.codice)
    return (*sotto_key, riga.descrizione)
```
D-03: se la riga porta un `id` tecnico valorizzato, l'upsert deve risolvere
per `id` PRIMA di ricadere sulla chiave naturale sopra — stesso principio di
`_upsert_voce` (righe 246-280): mai un `DELETE` implicito (D-10), una riga
senza id nuova diventa un insert pieno (D-04).

**Upsert idempotente da riusare come riferimento (righe 246-280):** il
pattern "query per chiave -> update se trovato, altrimenti crea" si ripete
identico per ognuna delle nuove tabelle del catalogo domande e dei parametri
motore — vedi anche `crea_extra`/`crea_domanda` sotto per la variante
"upsert per chiave naturale singola colonna".

### `backend/app/routers/admin/*.py` — `GET .../export.xlsx` (route, file-I/O)

**Analog esatto per lo streaming del file:**
`backend/app/routers/dettaglio_pro.py:273-294`:
```python
@router.get("/stime/{stima_id}/pdf-pro")
def scarica_pdf_pro(
    stima_id: int,
    current_user: User = Depends(require_pro),
) -> StreamingResponse:
    with SessionLocal() as session:
        row = _get_owned_stima(session, stima_id, current_user)
        result, _risposte, _salvate = _compute_dettaglio(session, row)
        pdf_bytes = PdfService.render_pro(result, row, current_user)
        filename = build_filename_pro(row)
        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
```
Per l'export Excel: stesso scheletro, `media_type=
"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"`,
`Depends(require_admin)` su listini/domande/coefficienti,
`Depends(require_staff)` su lead (D-14, coerente con `routers/admin/lead.py`
righe 25-30). **Dopo lo streaming, scrivere la riga `export_log`** (D-15) —
commit separato dalla generazione del file, per non far fallire il download
se il logging fallisce in modo silenzioso (verificare in planning se
serve un try/except dedicato).

**Gating margine opt-in (D-13), analogo a query-param + `AlertDialog` lato
frontend:** `GET /admin/coefficienti/export.xlsx?margine=true`, sempre dietro
`require_admin` — nessun ruolo nuovo, la distinzione è nel contenuto del file
generato da `export_excel_service.build_workbook(..., con_margine=True)`.

### `backend/app/routers/admin/upload_listino.py` (route, CRUD) — ESTESO

**Analog:** se stesso, righe 41-92 (`POST /preview` + `POST /confirm`),
pattern round-trip stateless da non duplicare:
```python
@router.post("/preview", response_model=DiffPreviewOut)
async def preview_upload(
    file: UploadFile,
    target: str = Form(...),
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> DiffPreviewOut:
    ...
```
Il flusso a due passi resta identico per il formato piatto: aggiungere un
discriminatore sul `target`/sul body per instradare a
`parse_flat_export` invece di `parse_computo`, mantenendo
`compute_diff`/`apply_diff_idempotent` come punto di aggancio unico (D-01).
Il diff deve anche portare l'informazione "riga cambiata dopo il timestamp di
export" (D-11) — nuovo campo su `DiffRowOut` (`schemas/admin_upload.py:60-63`),
confrontando `updated_at`/equivalente della riga DB con il timestamp letto dal
foglio ISTRUZIONI del file caricato.

### `backend/tests/test_export_import_roundtrip.py` (test, batch) — NUOVO

**Analog:** `backend/tests/test_dettaglio_pro_livelli.py:261`
(`test_upload_excel_non_azzera_livello`), criterio d'uscita D-12 — un test che
conta, non un'ispezione a occhio:
```python
def test_upload_excel_non_azzera_livello(self, session):
    from app.schemas.admin_upload import VoceRigaIn
    from app.services.listino_upload_service import _upsert_voce as upsert_da_excel

    sotto = _sotto_gres(session)
    voce = _voci_di(session, sotto)[0]
    voce.livello = "alto"
    session.flush()

    upsert_da_excel(session, sotto, VoceRigaIn(...))
    session.flush()

    assert voce.prezzo_unitario_cliente == Decimal("99.00")  # il prezzo si aggiorna...
    assert voce.livello == "alto"  # ...il livello no.
```
Il test di round-trip a vuoto (D-12) segue la stessa forma fixture/sessione ma
copre l'intero giro: `export_excel_service.build_workbook()` →
`listino_upload_service.parse_flat_export()` → `compute_diff()` deve produrre
**zero righe modificate** quando il file è ricaricato identico. Verificare
`um`, `ordine`, prezzo — non solo `livello` — perché è esattamente la lacuna
che D-12 segnala nel test attuale.

### `frontend/src/api/admin/domande.ts` (api client, CRUD) — NUOVO

**Analog:** `frontend/src/api/admin/listini.ts` (righe 1-170), stesso
"Decimal-as-string wire format" da normalizzare con `toNumber()`:
```typescript
import { apiGet, apiPost, apiPatch, apiDelete } from "@/api/admin/client";

export interface DomandaOut {
  code: string;
  testo: string;
  // ...
  attiva: boolean;
}

export async function getDomande(): Promise<DomandaOut[]> {
  return apiGet<DomandaOut[]>("/admin/domande");
}

export async function createDomanda(payload: DomandaCreateInput): Promise<DomandaOut> {
  return apiPost<DomandaOut>("/admin/domande", payload);
}

export async function updateDomanda(code: string, payload: DomandaPatchInput): Promise<DomandaOut> {
  return apiPatch<DomandaOut>(`/admin/domande/${code}`, payload);
}
```
Nessun `deleteDomanda`: D-25 vieta il delete fisico, sostituito da
`updateDomanda(code, { attiva: false })` — riusa `apiPatch`, non serve
`apiDelete`.

### `frontend/src/api/admin/exportExcel.ts` (api client, file-I/O blob) — NUOVO, NESSUN ANALOG DIRETTO

**Analog parziale:** `frontend/src/api/admin/uploadListino.ts` (righe 84-111)
per lo scheletro fetch diretto con `credentials: "include"` — ma lì la
risposta è JSON, qui è un blob binario. Pattern da costruire:
```typescript
const API_BASE = import.meta.env.VITE_API_BASE as string | undefined;

export async function scaricaListinoExcel(): Promise<void> {
  if (!API_BASE) throw new Error("VITE_API_BASE non configurato");
  const response = await fetch(`${API_BASE}/admin/listini/export.xlsx`, {
    credentials: "include",
  });
  if (!response.ok) {
    throw new ApiError(response.status, `GET export fallita con status ${response.status}`);
  }
  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const filename = /filename="([^"]+)"/.exec(disposition)?.[1] ?? "export.xlsx";
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
```
Stesso `ApiError`/`extractErrorDetail` di `uploadListino.ts:70-78` per la
gestione errore. Ripetere per le quattro risorse (listino, domande,
parametri con `?margine=`, lead) — un modulo unico con funzioni parallele,
coerente con "un endpoint per risorsa" (D-02).

### `frontend/src/pages/admin/DomandeCrudPage.tsx` (component, CRUD master-detail) — NUOVO

**Analog:** `frontend/src/pages/admin/ListiniPage.tsx` per il pattern
master-detail annidato (listino → categoria → voce, righe 45-46, 225-322):
```typescript
const [selectedListinoId, setSelectedListinoId] = useState<number | null>(null);
const [selectedCategoriaId, setSelectedCategoriaId] = useState<number | null>(null);
// ... selezionare una riga rivela la tabella sottostante, deselezionare la collassa
```
Da riprodurre come `selectedDomandaCode` → `selectedOpzioneId` (D-24). Per il
toggle attiva/disattiva senza `AlertDialog` (D-25, nessun delete fisico),
l'analog è `CoefficientiPage.tsx::ExtraTab` (righe 363-365, badge
`Attivo`/`Non attivo`):
```tsx
<Badge key="attivo" variant={row.attivo ? "default" : "secondary"}>
  {row.attivo ? "Attivo" : "Non attivo"}
</Badge>
```
sostituendo il bottone `Trash2`/`AdminDeleteConfirm` con un bottone icona
`Power`/`Eye`/`EyeOff` che chiama direttamente `updateDomanda(code, {attiva: !row.attiva})`
— **nessun dialog di conferma**, azione reversibile (D-25, UI-SPEC §F.3).
Dialog crea/modifica: riuso letterale di `AdminCrudDialog`, stesso pattern di
`ListiniPage.tsx` righe 358-406 (campo `code` disabled in modifica, contesto
mostrato come testo statico non editabile).

### `frontend/src/pages/admin/CoefficientiPage.tsx` (component, sesta tab Anteprima) — ESTESO

**Analog:** se stesso — pattern tab esistente (righe 47-81 per lo shell
`Tabs`/`TabsList`/`TabsContent`, righe 83-158 per il contenuto di una tab
tipo con `useQuery` + `AdminTable`):
```tsx
<TabsList className="w-full">
  <TabsTrigger value="moltiplicatori">Moltiplicatori</TabsTrigger>
  {/* ... */}
  <TabsTrigger value="anteprima">Anteprima</TabsTrigger>
</TabsList>
{/* ... */}
<TabsContent value="anteprima">
  <AnteprimaTab />
</TabsContent>
```
Componenti del form da riusare direttamente (D-19, UI-SPEC §E.1):
`frontend/src/components/CityAutocomplete.tsx`,
`frontend/src/components/ui/number-stepper.tsx` (NumberStepper),
`frontend/src/components/DomandaField.tsx` — stessi componenti del wizard
pubblico, nessun clone. Backend consumato: `POST /admin/domande/anteprima`
(`routers/admin/domande.py:496-581`), già completo — contratto esatto in
`schemas/admin_domande.py:151-201` (`AnteprimaIn`/`AnteprimaOut`/
`AnteprimaCategoriaOut`/`EffettoTracciaOut`).

### `frontend/src/components/admin/ExcelUploadDialog.tsx` (component, file-I/O preview) — ESTESO

**Analog:** se stesso. Struttura preview già presente (righe 298-402) da
estendere con badge stale + banner (D-11, UI-SPEC §C), senza duplicare la
logica:
```tsx
<Badge className="border-[#FCD34D] bg-[#FFFBEB] text-[#B45309]">Modificata</Badge>
```
Da migrare ai token ambra dichiarati nello UI-SPEC (`bg-amber-bg
border-amber-border text-amber-fg`) invece dei valori hex cablati — stesso
punto segnalato esplicitamente nello UI-SPEC (§Color, righe 92-96). Aggiungere
un secondo badge ambra "Cambiata dopo l'export" nella stessa cella quando
`row.riga_modificata_dopo_export` è true (nuovo campo su `DiffRowOut`), più
un banner riassuntivo sopra la tabella (`rounded-lg border border-amber-border
bg-amber-bg px-4 py-3 text-sm text-amber-fg`) quando almeno una riga è stale.

### Toolbar Scarica/Carica su quattro pagine (D-26)

**Analog:** `frontend/src/pages/admin/ListiniPage.tsx` righe 191-201 — il
bottone "Carica listino da Excel" esiste già in quella identica posizione:
```tsx
<div className="flex flex-wrap items-center justify-between gap-3">
  <h1 className="text-lg font-semibold text-foreground">Listini e prezzi</h1>
  <div className="flex flex-wrap gap-2">
    <Button type="button" variant="outline" onClick={() => setUploadOpen(true)}>
      Carica listino da Excel
    </Button>
    <Button type="button" onClick={() => setListinoDialogOpen(true)}>
      Aggiungi listino
    </Button>
  </div>
</div>
```
Aggiungere "Scarica {risorsa}" (`variant="outline"`, icona `Download`) PRIMA
di "Carica file" in questo stesso blocco, su tutte e quattro le pagine
(`ListiniPage.tsx`, `DomandeCrudPage.tsx` una volta creata, `CoefficientiPage.tsx`,
`LeadDashboardPage.tsx`). Su `/admin/coefficienti` diventa `DropdownMenu`
split-button (D-13, UI-SPEC §B) — nessun analog esistente per il
`DropdownMenu`, verificare se il blocco shadcn è già installato
(`frontend/components.json`) prima di aggiungerlo.

### `frontend/src/pages/admin/LeadDashboardPage.tsx` (component, sezione download log) — ESTESO

**Analog:** se stessa — pattern `AdminTable` + `rows` mapping già nel file
(righe 135-159, 208-229):
```tsx
const rows = (leadsQuery.data ?? []).map((item) => [
  <div key="data" ...>{formatData(item.created_at)}</div>,
  // ...
]);
<AdminTable columns={[...]} isLoading={...} rows={rows} isEmpty={...} emptyHeading={...} emptyBody={...} />
```
Stessa `formatData()` (riga 41-43, `toLocaleDateString("it-IT")`) da riusare
per la colonna Data del log. Nuova query `useQuery<ExportLogOut[]>` verso un
nuovo endpoint `GET /admin/export-log` (o incorporato in uno dei router
esistenti), visibile per `allow={["admin","consulente"]}` già impostato su
questa pagina (riga 326).

## Shared Patterns

### `require_admin` / `require_staff` — gating export (CUR-03/CUR-04)
**Source:** `backend/app/dependencies/auth.py:66-78`
**Apply to:** tutte le route `GET .../export.xlsx` di listino/domande/
coefficienti (`require_admin`); export lead (`require_staff`, D-14).
```python
def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != ROLE_ADMIN:
        raise HTTPException(403, "Accesso riservato")
    return user

def require_staff(user: User = Depends(get_current_user)) -> User:
    if user.role not in STAFF_ROLES:
        raise HTTPException(403, "Accesso riservato")
    return user
```

### StreamingResponse + Content-Disposition per download file
**Source:** `backend/app/routers/dettaglio_pro.py:273-294`,
`backend/app/services/pdf_service.py:71-83`
**Apply to:** tutti e quattro gli endpoint export, sostituendo
`media_type="application/pdf"` con il MIME xlsx e `PdfService.render_pro()`
con `export_excel_service.build_workbook()`.

### Upsert per chiave naturale, mai un DELETE implicito (D-24 Fase 4)
**Source:** `backend/app/services/listino_upload_service.py:218-280`,
`backend/app/routers/admin/coefficienti.py:149-178` (`crea_extra`)
**Apply to:** `parse_flat_export`/import del formato piatto per tutte le
nuove tabelle (catalogo domande, parametri motore, forfait arredo) — stesso
pattern "query per chiave -> update se trovato, altrimenti crea", D-03 vi
aggiunge solo la risoluzione per `id` prima della chiave naturale.

### Anti-leak: nessun campo di margine negli schemi di risposta
**Source:** `backend/app/models/listino.py:37-38` (commento "SEGRETO"),
`backend/app/schemas/admin_domande.py:1-12` (docstring)
**Apply to:** `schemas/admin_export.py` e `export_excel_service.py` — il
coefficiente impresa entra SOLO nella variante `con_margine=True`, mai nello
schema/colonna di default.

### `AdminTable` + `AdminCrudDialog` + toast "Modifica salvata"
**Source:** `frontend/src/components/admin/AdminTable.tsx`,
`AdminCrudDialog.tsx`, uso in `frontend/src/pages/admin/CoefficientiPage.tsx`
(ogni tab)
**Apply to:** `DomandeCrudPage.tsx` (D-23) e la sezione "Download registrati"
(sola lettura, senza dialog).

### Empty state / error copy costanti di modulo
**Source:** `frontend/src/pages/admin/CoefficientiPage.tsx:33-35`
```typescript
const SAVE_ERROR = "Non siamo riusciti a salvare la modifica. Riprova.";
const EMPTY_HEADING = "Nessun elemento presente";
const EMPTY_BODY = "Aggiungi il primo elemento con il pulsante qui sopra, oppure carica un file.";
```
**Apply to:** `DomandeCrudPage.tsx` e qualunque nuova pagina/tab — riuso
letterale come richiesto dal Copywriting Contract dello UI-SPEC.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `frontend/src/api/admin/exportExcel.ts` (funzione di download blob) | utility | file-I/O (blob) | Nessun endpoint frontend esistente scarica un blob binario con `credentials: "include"`; tutti i client admin attuali (`api/admin/*.ts`) parlano solo JSON via `apiGet/apiPost/apiPatch/apiDelete`. Usare lo scheletro fetch di `uploadListino.ts` come base, adattando la lettura della risposta a `.blob()` invece di `.json()` — vedi Pattern Assignment sopra. |
| `backend/app/services/export_excel_service.py` (scrittura xlsx) | service | file-I/O (write) | Nessun modulo del backend scrive oggi un file `.xlsx` (openpyxl è usato solo in lettura in `listino_upload_service.py`). L'unico analog di scrittura-file-e-streaming è per PDF (`pdf_service.py` + `WeasyPrint`), riusabile solo per naming/Content-Disposition, non per l'API di scrittura del contenuto. |

## Metadata

**Analog search scope:** `backend/app/{routers,services,models,schemas,dependencies}/`,
`backend/alembic/versions/`, `backend/tests/`,
`frontend/src/{pages/admin,components/admin,components,api/admin}/`
**Files scanned:** ~25 file letti per intero (nessun file >2000 righe in questa fase)
**Pattern extraction date:** 2026-09-22
