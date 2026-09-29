# Phase 10: Risultato leggibile e tetto di budget - Pattern Map

**Mapped:** 2026-09-29
**Files analyzed:** 27 (6 nuovi backend/frontend + 21 modificati)
**Analogs found:** 27 / 27 (1 solo parziale: la geometria PDF senza JS)

Decisioni A1/A2 (10-RESEARCH.md, fondo) già confermate: budget = colonna `stima.budget_eur` fuori da catalogo e motore; Pro confrontato su totale IVA inclusa calcolato server-side in `_compute_dettaglio`.

## File Classification

| File nuovo / modificato | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `backend/alembic/versions/0024_budget_eur_su_stima.py` (nuovo) | migration | additiva | `alembic/versions/0009_stima_tier.py` | exact |
| `backend/app/models/stima_salvata.py` (mod) | model | CRUD | stesso file, colonna `tier` / `livelli_pro_json` (righe 253-271) | exact |
| `backend/app/schemas/stima.py` (mod: `ConfrontoFinitureOut`, `StimaResponse.confronto_finiture`) | schema | request-response | `ArredoOut` + `StimaResponse.arredo` (stesso file) | exact |
| `backend/app/schemas/stima_salvata.py` (mod: `budget_eur`, `BudgetIn/Out`) | schema | CRUD | `PreferenzeProIn` / `StimaSalvataCreate` (stesso file) | exact |
| `backend/app/schemas/dettaglio_pro.py` (mod) | schema | request-response | `DettaglioProOut` (stesso file, campi con default) | exact |
| `backend/app/services/risultato.py` (nuovo) | service (funzioni pure) | transform | `_split_imponibile_iva` in `routers/stima.py` (riga 78-90) + `_fmt_eur` in `pdf_service.py` | role-match |
| `backend/app/services/effetti.py` (mod: costante `DOMANDA_LIVELLO_FINITURE`) | config/costante | — | `DOMANDA_FINITURA` (riga 146) | exact |
| `backend/app/routers/stima.py` (mod: confronto) | controller | request-response | stesso file (`crea_stima`, `_arredo_out`) | exact |
| `backend/app/routers/stime_salvate.py` (mod: salva budget, `PUT budget`, `dettaglio_stima`) | controller | CRUD | `salva_stima` / `dettaglio_stima` (stesso file) | exact |
| `backend/app/routers/dettaglio_pro.py` (mod: `_compute_dettaglio`, `_to_out`) | controller | request-response | stesso file | exact |
| `backend/app/services/dettaglio_pro.py` (lettura, eventualmente nessuna modifica) | service | transform | — (si chiama due volte, non si tocca) | n/a |
| `backend/app/services/pdf_service.py` (mod) | service | transform | `PdfService.render` / `render_pro` | exact |
| `backend/app/templates/pdf_stima.html`, `pdf_stima_pro.html` (mod) | template | transform | blocchi `.bonus-block`, `.totale-block`, `{% if stima.arredo %}` | role-match |
| `backend/tests/test_risultato.py` (nuovo) | test | transform | `tests/test_estimation.py` (funzioni pure, oracolo) | role-match |
| `backend/tests/test_stima_api.py`, `test_stime_salvate.py`, `test_dettaglio_pro*.py`, `test_pdf*.py`, `test_no_leak*.py` (mod) | test | request-response | file stessi | exact |
| `frontend/src/lib/risultato.ts` (nuovo) | utility | transform | `frontend/src/lib/currency.ts` | role-match |
| `frontend/src/lib/currency.ts` (mod: `formatRangeEurMq`) | utility | transform | stesso file | exact |
| `frontend/src/components/RangeBar.tsx` (mod) | component | transform | stesso file | exact |
| `frontend/src/components/TotalCard.tsx` (mod: riepilogo) | component | transform | stesso file + righe extra di `SavedEstimateDetail` | exact |
| `frontend/src/components/CategoryCard.tsx` (mod) | component | transform | stesso file | exact |
| `frontend/src/components/BudgetAlert.tsx` (nuovo) | component | request-response (mutation) | `Alert` shadcn + mutation react-query di `EstimatePage` | role-match |
| `frontend/src/components/ImportoField.tsx` (nuovo) | component | event-driven (input) | `DomandaField.tsx` (label+help+controllo) + `InputGroup` shadcn | role-match |
| `frontend/src/components/EstimateWizard.tsx` (mod: step 3) | component | event-driven | stesso file, blocco `step === 3` (righe 261-274) | exact |
| `frontend/src/api/stima.ts` (mod: `normalizeResponse`, PUT budget) | service (API client) | request-response | `normalizeArredo` / `postSalvaStima` (stesso file) | exact |
| `frontend/src/pages/EstimatePage.tsx`, `components/SavedEstimateDetail.tsx`, `pages/DettaglioProPage.tsx` (mod) | page | request-response | stessi file | exact |
| `frontend/src/routes/AccediPage.tsx`, `RegistratiPage.tsx`, `SoftWallCta.tsx` (mod: budget attraversa il login) | page | event-driven | stessi file (`pendingStima`) | exact |

## Pattern Assignments

### `backend/alembic/versions/0024_budget_eur_su_stima.py` (migration, additiva)

**Analog:** `backend/alembic/versions/0009_stima_tier.py` (intero file, 46 righe). Ultima revisione esistente: `0023`.

**Header e revisione** (0009 righe 1-18, adattare a `0024`/`down_revision '0023'`):
```python
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0024'
down_revision: Union[str, Sequence[str], None] = '0023'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
```

**Core** (0009 righe 35, 44-46): `op.add_column` nullable, nessun backfill (le stime esistenti restano `NULL` = "nessun budget").
```python
def upgrade() -> None:
    op.add_column('stima', sa.Column('budget_eur', sa.Integer(), nullable=True))

def downgrade() -> None:
    op.drop_column('stima', 'budget_eur')
```
Nota: il repo usa `op.drop_column` diretto nel downgrade di 0009 (la variante `batch_alter_table` compare in 0019 solo per ALTER a NOT NULL). Seguire 0009. Verificare `tests/test_migrazioni_sqlite.py`.

---

### `backend/app/models/stima_salvata.py` (model)

**Analog:** stesso file, colonne `livelli_pro_json` e `tier` (righe 253-271). Import già presenti: `Integer`, `Mapped`, `mapped_column` (riga 229-230).

**Pattern da copiare** (commento incluso: e' la regola additiva D-24):
```python
# Livelli di finitura scelti per categoria ... Nullable: NULL significa "l'utente non ha scelto"
livelli_pro_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

tier: Mapped[str | None] = mapped_column(String(16), nullable=True)
```
Nuova colonna, prima di `created_at`:
```python
# Budget dichiarato dall'utente (EUR, IVA inclusa). E' un PARAMETRO, non un
# risultato: sta fuori da risultato_json (snapshot scritto una volta) e non
# entra mai in EstimationService. NULL = nessun budget.
budget_eur: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

---

### `backend/app/schemas/stima.py` (schema, request-response)

**Analog:** `ArredoOut` + `StimaResponse.arredo` (righe ~140-177). Il disclaimer/dati viaggiano DENTRO il payload, campo opzionale a `None`.

**Pattern** (stesso file, `ArredoOut` / `StimaResponse`):
```python
class ArredoOut(BaseModel):
    livello_code: str
    livello_nome: str
    ...
    totale_min: Decimal
    totale_max: Decimal

class StimaResponse(BaseModel):
    ...
    bonus: BonusOut | None = None
    arredo: ArredoOut | None = None
```
Nuovo (10-RESEARCH "Schema"): `ConfrontoFinitureOut(livello_code, livello_nome, totale_min, totale_max)` e `confronto_finiture: ConfrontoFinitureOut | None = None` con default `None` (snapshot e client vecchi). Attenzione anti-leak: `tests/test_no_leak.py` fa match sulla sottostringa `moltiplicatore` (righe 20-27): nessun nome di campo o stringa nuova deve contenerla.

**Validazione input budget** (stesso criterio di `mq`, riga 60): `Field(ge=1, le=2000)`. Per il budget:
```python
class BudgetIn(BaseModel):
    budget_eur: int | None = Field(default=None, ge=1, le=999_999_999)
```

---

### `backend/app/schemas/stima_salvata.py` (schema, CRUD)

**Analog:** stesso file. `StimaSalvataCreate` (righe 66-82) e `PreferenzeProIn` (34-63: parametro che NON entra nello snapshot).

Aggiungere a `StimaSalvataCreate` `budget_eur: int | None = Field(default=None, ge=1, le=999_999_999)` accanto a `preferenze_pro`; `confronto_finiture: ConfrontoFinitureOut | None = None` accanto a `bonus`. A `StimaSalvataOut` (righe 99-112) aggiungere `budget_eur: int | None = None` e `confronto_finiture: ConfrontoFinitureOut | None = None` con lo stesso commento di `bonus` (righe 110-112: "Assente negli snapshot v1... `.get()`, mai `[]`"). Importare `ConfrontoFinitureOut` da `app.schemas.stima` (riga 21).

---

### `backend/app/routers/stima.py` (controller, request-response) - calcolo `confronto_finiture`

**Analog:** stesso file: `crea_stima` (righe 92-230 circa) + helper `_arredo_out` (mappa campo-per-campo, "mai `model_validate`").

**Imports** (righe 20-43): aggiungere `ConfrontoFinitureOut` all'elenco `from app.schemas.stima import (...)` e `from app.services.risultato import livello_inferiore`.

**Core pattern da estendere** (chiamata motore, righe ~97-104):
```python
result = EstimationService.compute(
    session, listino, mq=payload.mq, tipo=payload.tipo.value, risposte=payload.risposte,
)
```
Confronto: subito dopo, seconda `compute` con `{**payload.risposte, "livello_finiture": livello_inferiore}` solo se `payload.risposte is not None` e il livello inferiore esiste. Il livello inferiore si ricava da `OpzioneDomanda` (attive, `ordine` crescente, `is_default`) della domanda `livello_finiture`, mai da una lista `["base","medio","alto"]` (regola 3). Restituire `None` se `confronto.totale_max >= result.totale_max` (Pitfall 3). L'arredo NON entra (D-08): il confronto guarda solo `EstimationService`.

**Mappa campo-per-campo** (copiare la forma di `_arredo_out`, righe ~212-242):
```python
def _confronto_out(...) -> ConfrontoFinitureOut | None:
    if confronto is None:
        return None
    return ConfrontoFinitureOut(livello_code=..., livello_nome=..., totale_min=..., totale_max=...)
```
e passarlo nel `StimaResponse(..., confronto_finiture=...)` in coda (righe ~198-207).

**Rate limit** (riga 92): `@limiter.limit("20/minute")` invariato.

---

### `backend/app/services/effetti.py` (costante)

**Analog:** `DOMANDA_FINITURA` (righe 140-146).
```python
#: Per convenzione (stesso precedente di OPZIONE_VALORE, non regole di
#: business): la domanda del catalogo che rappresenta i livelli di
#: `livello_finitura`. ...
DOMANDA_FINITURA = "finitura"
```
Aggiungere `DOMANDA_LIVELLO_FINITURE = "livello_finiture"` con lo stesso stile di commento ("per convenzione, non regola di business"). Oggi `livello_finiture` compare solo in `seed_data/seed-domande.json`, non nel codice Python.

---

### `backend/app/services/risultato.py` (nuovo, funzioni pure)

**Analog:** `_split_imponibile_iva` (`routers/stima.py` righe 78-90): funzione pura con docstring che spiega l'aritmetica, `Decimal` + `ROUND_HALF_UP`; e `_fmt_eur` (`pdf_service.py` righe 46-57) per l'arrotondamento a intero in stile italiano.

**Forma** (10-RESEARCH "Livello inferiore da dati DB"): `livello_inferiore(opzioni, scelto)`, `scala_barra(min, max, budget)`, `incidenza_eur_mq`, `peso_pct`, `iva_per_aliquota`, `stato_budget`. Duplicano la logica TS (`lib/risultato.ts`) perché i template Jinja non importano TS. Attenzione: lo snapshot passato al PDF è `risultato_json` (JSON, `mode="json"`), quindi i Decimal sono STRINGHE ("11000.00"): convertire con `float()`/`Decimal(str(...))` come fa `_fmt_eur` (`round(float(value))`). Testi di stato in un dict qui, con test di parità con il TS (A5).

Confini di stato (Pitfall 8): `budget < min` -> fuori; `min <= budget <= max` -> limite; `budget > max` -> dentro.

---

### `backend/app/routers/stime_salvate.py` (controller, CRUD)

**Analog:** stesso file.

**Imports** (righe 13-41): `from pydantic import BaseModel` già presente; aggiungere `BudgetIn` (da `schemas/stima_salvata`) e `ConfrontoFinitureOut`.

**Salvataggio - trappola snapshot** (righe 62-67, LEGGERE prima di modificare):
```python
risultato_json = payload.model_dump(mode="json", exclude={"preferenze_pro"})
risultato_json["schema_version"] = SCHEMA_VERSION
```
Deve diventare `exclude={"preferenze_pro", "budget_eur"}`: il budget e' un parametro, altrimenti due verita' dopo un `PUT`. `confronto_finiture` RESTA nello snapshot (e' risultato). Poi nel `StimaSalvata(...)` (righe 107-119) aggiungere `budget_eur=payload.budget_eur`.

**Dettaglio, ricostruzione manuale + `.get()`** (righe 168-183):
```python
bonus=BonusOut(**snapshot["bonus"]) if snapshot.get("bonus") else None,
```
Copiare per `confronto_finiture=ConfrontoFinitureOut(**snapshot["confronto_finiture"]) if snapshot.get("confronto_finiture") else None` e `budget_eur=row.budget_eur`. Mai `snapshot["..."]`: un KeyError romperebbe tutto lo storico (commento righe 179-181).

**Nuovo `PUT /stime/{id}/budget`** - ownership 404 anti-IDOR, copiare da `dettaglio_stima` (righe 152-164):
```python
@router.get("/stime/{stima_id}", response_model=StimaSalvataOut)
def dettaglio_stima(stima_id: int, current_user: User = Depends(get_current_user)) -> StimaSalvataOut:
    with SessionLocal() as session:
        stmt = select(StimaSalvata).where(
            StimaSalvata.id == stima_id,
            StimaSalvata.user_id == current_user.id,
        )
        row = session.execute(stmt).scalar_one_or_none()
        if row is None:
            raise HTTPException(404, "Stima non trovata")
```
Per il PUT: `Depends(get_current_user)` (NON `require_pro`: vale anche per Free e per stime storiche), body `BudgetIn`, `row.budget_eur = payload.budget_eur; session.commit()`, risposta `{budget_eur}` (modello piccolo come `StimaSalvataCreatedOut`, righe 51-53).

---

### `backend/app/routers/dettaglio_pro.py` (controller, request-response) - confronto Pro + IVA

**Analog:** stesso file; `_compute_dettaglio` (righe 198-235) e' l'UNICO punto di calcolo condiviso da GET, POST risposte e PDF Pro (docstring: "Aggiungere qui un secondo punto di calcolo ... e' il modo piu' rapido di far divergere schermata e stampa").

**Chiamata motore Pro** (righe 226-234):
```python
livelli = row.livelli_pro_json or {}
result = DettaglioProService.compute(
    session, listino, row.mq, row.tipo, risposte_motore, livelli
)
return result, risposte_eco, risposte_salvate
```
Estensione: nello stesso punto (non altrove) calcolare (a) totale IVA inclusa Pro = somma `cat.totale * (1 + Categoria.iva_pct)` sulle sole categorie con `Categoria.nel_totale_lavori.is_(True)` (filtro come in `opzioni_pro`, righe 266-273) piu' gli extra attivi come nel Free; (b) un secondo `DettaglioProService.compute(...)` con `livelli` un gradino sotto per categoria (ordine da `LivelloFinitura.ordine`, tabella DB: `_livelli_disponibili`, righe 238-239) e, se il default e' sull'asse `finitura`, `risposte_motore["finitura"]` un gradino sotto. Nessuna categoria con livello inferiore -> `None`. Il valore restituito oggi e' una tripla `(result, risposte_eco, risposte_salvate)`: estenderlo (es. dataclass o quarto elemento) aggiornando i 3 chiamanti (righe 304, 336, 353).

**`_to_out`** (righe 102-164): mappa campo-per-campo nel DTO; aggiungere `totale_ivato_min/max`, `confronto_finiture`, `budget_eur=row.budget_eur` (serve passare `row` o il budget a `_to_out`). Il calcolo `DettaglioProService` gira due volte per richiesta (N+1 note in RESEARCH Pattern 6): accettato.

**Schema** `DettaglioProOut` (`schemas/dettaglio_pro.py` righe 106-136): campi nuovi con default, come `livelli: dict[str, str] = {}` e `risposte_salvate: bool = False`, con commento sul perche' (stile del file).

---

### `backend/app/services/pdf_service.py` (service, transform)

**Analog:** stesso file, `render` (righe 89-105) e `render_pro` (108-128). Contratto: il PDF Free legge SOLO lo snapshot, mai il motore (test statico `test_pdf_service_non_importa_estimation_service`, `tests/test_pdf.py` riga 221); `render_pro` non chiama mai il motore, riceve il risultato dal router.

**Pattern template.render** (righe 99-104):
```python
html_content = template.render(
    stima=stima.risultato_json,
    nome=user.nome,
    data_generazione=datetime.now().strftime("%d/%m/%Y"),
    filename=filename,
)
```
Aggiungere `budget_eur=stima.budget_eur` e i derivati calcolati con `services.risultato` (barra, riepilogo, per-categoria €/m² e peso, stato budget). Non importare `EstimationService`. Filtro Jinja: registrare nuovi filtri accanto a `_env.filters["eur"] = _fmt_eur` (riga 60) se servono (es. formato `€/m²`). Per `render_pro` passare i derivati Pro calcolati nel router (`_compute_dettaglio`) oppure dal risultato esteso.

---

### `backend/app/templates/pdf_stima.html` e `pdf_stima_pro.html` (template)

**Analog:** blocchi esistenti dello stesso template.

**Tabella categorie** (`pdf_stima.html` righe 265-282): aggiungere sotto ogni `categoria.nome` la riga "{min}-{max} €/m² (IVA esclusa)" e "{n}% del totale" con mini-barra statica.
```html
{% for categoria in stima.categorie %}
<tr>
  <td class="nome">{{ categoria.nome }}</td>
  <td class="range">
    {{ categoria.totale_min|eur }} &ndash; {{ categoria.totale_max|eur }} {{ stima.valuta }}
  </td>
</tr>
{% endfor %}
```
**Totale** (righe 284-289, `.totale-block`): qui va la barra statica (div a % passate dal Python) e il riepilogo imponibile/IVA per aliquota/extra.

**Blocchi opzionali** (righe 291, 325): usare lo stesso idioma `{% if stima.bonus %}` / `{% if stima.arredo %}` con commento ("assente su ogni snapshot anteriore") per `{% if budget_eur %}` e per `stima.confronto_finiture`. Riquadro budget: riusare lo stile `.disclaimer-box` (ambra, righe ~98-106) per fuori/limite; niente campo, bottoni o link.

**Stile geometria WeasyPrint** (Pitfall 6): `position:absolute; left:X%` dentro `position:relative`, con `margin-left` negativo in px sulla tacca; niente `transform`/`calc`. Non esiste un analogo con barre in `%` nei template: e' l'unica parte senza precedente (vedi "No Analog Found"). Il template usa `display:flex` (`.header`, `.riepilogo`), quindi il flex semplice e' gia' accettato.

**PDF Pro** (`pdf_stima_pro.html` righe 359-368): `.totale-generale` mostra `dettaglio.totale_min|eur` (IVA esclusa); aggiungere accanto il riquadro budget con la riga "Ora ... IVA inclusa" (A2) e `{% if budget_eur %}`.

---

### `frontend/src/lib/risultato.ts` (nuovo) e `lib/currency.ts` (mod)

**Analog:** `frontend/src/lib/currency.ts` (17 righe, funzioni pure esportate, `Intl.NumberFormat("it-IT")`).

**Pattern** (currency.ts righe 1-17):
```ts
const formatter = new Intl.NumberFormat("it-IT", {
  style: "currency", currency: "EUR", maximumFractionDigits: 0,
  useGrouping: "always",   // sotto 10.000 it-IT non raggruppa senza "always"
});
export function formatEur(value: number): string { return formatter.format(value); }
export function formatEurRange(min: number, max: number): string {
  return `${formatEur(min)} – ${formatEur(max)}`;
}
```
Aggiungere `formatRangeEurMq(min, max)` -> "310–380 €/m²" qui (NON concatenare `formatEurRange`, che produce "min € – max €"). `lib/risultato.ts`: `scalaBarra`, `incidenzaEurMq`, `pesoPct`, `ivaPerAliquota`, `statoBudget`, `parseImporto` come in 10-RESEARCH (Pattern 1, 2, 3 e "Stato dell'avviso"). Imponibile lavori = somma `categorie[].imponibile_*`, NON `totale.imponibile_*` (include gli extra). Nessuna aliquota 10/22 cablata: raggruppare per `iva_pct`. Riga IVA con aliquota piu' alta = `totale.iva - somma(altre)` (riconciliazione).

Non c'e' test runner frontend (solo `dev`, `build`, `lint`): verifica con `npm run build` + `npm run lint` + checklist manuale.

---

### `frontend/src/components/RangeBar.tsx` (component)

**Analog:** stesso file (35 righe). Cambiare solo la geometria, mantenere gradiente `--gold` -> `--primary`, etichette e classi tipografiche.

**Codice attuale da sostituire** (righe 16-25):
```tsx
<div className="relative h-2 w-full rounded-full bg-secondary">
  <div className="absolute inset-y-0 left-[12%] right-[12%] rounded-full"
       style={{ background: "linear-gradient(90deg, var(--gold), var(--primary))" }} />
  <span className="absolute left-[12%] top-1/2 size-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-background bg-gold" />
  <span className="absolute right-[12%] top-1/2 size-3.5 translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-background bg-primary" />
</div>
```
Sostituire `left-[12%]`/`right-[12%]` con `style={{ left: \`${left}%\`, width: ... }}` da `scalaBarra`; aggiungere props `min`, `max`, `budget?`, `role="img"` con `aria-label` ("Stima da X a Y · budget Z"). Tacca: `bg-foreground`, 2px x `h-6`, etichetta "Il tuo budget" sopra solo se `budget` (nessuno spazio riservato altrimenti), allineamento condizionato ai bordi (`<15%` sinistra, `>85%` destra). Unico chiamante: `TotalCard` (righe 53-56).

---

### `frontend/src/components/TotalCard.tsx` (component) - riepilogo

**Analog:** stesso file (33 righe) per la struttura, e le righe extra di `SavedEstimateDetail.tsx` (187-197) per la riga "label a sinistra / cifra a destra".

**Riga label/cifra da riusare** (`SavedEstimateDetail.tsx` 188-196):
```tsx
<div key={extra.code} className="flex items-center justify-between text-sm text-muted-foreground">
  <span>{extra.nome}</span>
  <span className="tabular-nums">{formatEur(extra.importo)}</span>
</div>
```
Struttura target (UI-SPEC §C): fascia eyebrow + `RangeBar` invariata (`border-l-4 border-primary bg-accent/60 px-6 py-5`), poi `Separator` (shadcn, esiste in `components/ui/separator.tsx`) e blocco riepilogo `px-6 py-4`: Imponibile lavori, una riga IVA per aliquota, Costi extra con sotto-elenco, "Totale IVA inclusa". Props nuove: `categorie`, `extra`, `budget?`. La prima nota "Comprende i costi extra..." (righe 60) si puo' accorciare; quella di pre-sopralluogo resta.

---

### `frontend/src/components/CategoryCard.tsx` (component)

**Analog:** stesso file. Oggi riceve solo `categoria` e `isPro` (righe 89-93); aggiungere `mq: number` e `totaleLavoriMedio: number` (o il peso pre-calcolato).

**Punto di inserimento** (righe 109-113, `CardContent className="flex flex-col gap-3 pt-4"`): dopo il `<p className="font-display text-xl font-bold tabular-nums">` con `formatEurRange(categoria.totale_min, categoria.totale_max)` aggiungere (1) riga €/m² con "IVA esclusa" in `text-xs text-muted-foreground`, (2) mini-barra peso: traccia `h-1 rounded-full bg-secondary` + fill `bg-primary`, `aria-hidden`, con "{n}% del totale" (`text-xs font-semibold`; `<1%` con fill 2%). Il teaser Pro (righe 113-126) resta ultimo.

---

### `frontend/src/components/BudgetAlert.tsx` (nuovo)

**Analog:** `Alert` shadcn (`components/ui/alert.tsx`: `Alert`, `AlertTitle`, `AlertDescription`; il `role="alert"` e' cablato nel componente, riga 30) + mutation react-query di `EstimatePage.tsx`.

**Attenzione:** `Alert` imposta `role="alert"`; UI-SPEC vieta l'asserzione ("`role="status"`, `aria-live="polite"`"): sovrascrivere con `role="status"` via props (`{...props}` e' dopo, riga 31-32, quindi il prop del chiamante vince). Varianti disponibili: solo `default` e `destructive`; per l'ambra passare classi `bg-amber-bg border-amber-border text-amber-fg` (token `--amber-bg/border/fg` in `index.css` righe 70-72, 98-100). Nessuna variante `destructive` (rosso solo per l'errore di input).

**Pattern mutation** (`EstimatePage.tsx` righe 80-92):
```tsx
const saveMutation = useMutation({
  mutationFn: (payload: StimaResponse) => postSalvaStima(payload),
});
```
Per il budget: `useMutation({ mutationFn: (b: number | null) => putBudget(stimaId, b) })`, `disabled` + "Aggiorno…" in `isPending`, errore con copy UI-SPEC ("Non siamo riusciti a salvare il budget...") mantenendo il valore digitato. Per Pro invalidare la query `["stima-dettaglio", stimaId]` come in `DettaglioProPage` (riga 259-263). Per la stima anonima (non salvata) "Aggiorna il confronto" cambia solo lo stato locale, nessuna chiamata.

---

### `frontend/src/components/ImportoField.tsx` (nuovo)

**Analog:** `DomandaField.tsx` righe 34-60 per l'ossatura label + help + controllo, e `InputGroup` (`components/ui/input-group.tsx`, esporta `InputGroup`, `InputGroupAddon`, `InputGroupInput`...).

**Ossatura da copiare** (`DomandaField.tsx` 37-60):
```tsx
<div className="flex flex-col gap-2">
  <Label htmlFor={etichettaId} className="text-sm font-medium">{domanda.testo}</Label>
  {domanda.help && (<p id={helpId} className="text-sm text-muted-foreground">{domanda.help}</p>)}
  <Controllo ... id={etichettaId} helpId={helpId} />
</div>
```
Usare `aria-describedby={helpId}` come fa `NumberStepper`. `InputGroup` ha `h-9` di base: passare `className="h-11"` per il target 44px. `inputMode="numeric"`, `type="text"`, suffisso `<InputGroupAddon align="inline-end">€</InputGroupAddon>`. Errore di input con `aria-invalid` (il gruppo gia' gestisce `has-[[data-slot][aria-invalid=true]]:border-destructive`, riga 15).

---

### `frontend/src/components/EstimateWizard.tsx` (mod: step 3)

**Analog:** stesso file, blocco step 3 (righe 261-274) e `invia` (righe 200-220).

**Blocco da estendere** (righe 261-274): dopo `stepCorrente?.domande.map(...)` aggiungere il blocco fisso con label "Qual è il tuo budget per la ristrutturazione?" + help + `ImportoField` (stringa fissa, A1; NON e' una `Domanda` di catalogo, quindi non passa da `DomandaField`/`risposte`, che finirebbero nel limite `ValoreRisposta <= 10_000` e nella pipeline effetti).

**Stato e submit:** aggiungere `const [budget, setBudget] = useState<number | null>(null)` accanto agli altri `useState` (righe 84-106), un campo `budget?: number | null` in `EstimateWizardSubmit` (righe 34-39) e passarlo in `onSubmit({...})` (riga 213). Non toccare `baseValid` / `avantiDisabilitato` (riga 296): il budget vuoto non blocca (Pitfall 10); importo non valido blocca solo l'invio del valore.

---

### `frontend/src/api/stima.ts` (API client)

**Analog:** stesso file, `normalizeArredo` (righe 231-248) e `postSalvaStima` (404-412).

**TRAPPOLA (Pitfall 1)** - commento a righe 250-257: `normalizeResponse` ricostruisce campo per campo e scarta cio' che non elenca; e' successo con `bonus`. Per `confronto_finiture` (Decimal serializzati come stringhe):
```ts
// tipi: aggiungere in StimaResponse (riga 112-127) e RawStimaResponse (riga 172-183)
confronto_finiture: ConfrontoFinitureOut | null;
// normalizzatore, stessa forma di normalizeArredo:
function normalizeConfronto(raw: RawConfrontoFinitureOut | null | undefined): ConfrontoFinitureOut | null {
  if (raw == null) return null;
  return {
    livello_code: raw.livello_code,
    livello_nome: raw.livello_nome,
    totale_min: toNumber(raw.totale_min),
    totale_max: toNumber(raw.totale_max),
  };
}
```
e in `normalizeResponse` (riga 265-289) aggiungere `confronto_finiture: normalizeConfronto(raw.confronto_finiture)`. `budget_eur` sul lato TS: `StimaResponse.budget_eur?: number | null` solo client (il server non lo restituisce da `POST /stima`); `StimaSalvataOut` (righe 387-391) lo riceve dal server e `getStimaDettaglio` (righe 463-467) lo deve copiare a mano (`{ ...normalized, id: raw.id, ... }` non fa spread di raw: aggiungere `budget_eur: raw.budget_eur ?? null`).

**Salvataggio con budget** (`postSalvaStima`, righe 404-412): il budget deve viaggiare DENTRO il payload (`{...payload, budget_eur}`), come `preferenze_pro`. Cosi' attraversa anche `pendingStima` di `SoftWallCta` (`navigate("/registrati?intent=save", { state: { pendingStima: result } })`, righe 39/46/50) e `AccediPage`/`RegistratiPage` (`postSalvaStima(pendingStima)`, AccediPage riga 60): passare `{ ...result, budget_eur }` come `pendingStima`.

**PUT budget** (nuovo): esiste solo `apiPost` in `api/client.ts` (righe 55-70 circa); verificare se c'e' `apiPut` (non letto): se manca, aggiungerlo copiando `apiPost` con `method: "PUT"`, `credentials: "include"`, stessa gestione `leggiDetail`/`ApiError`.

---

### `frontend/src/pages/EstimatePage.tsx`, `SavedEstimateDetail.tsx`, `DettaglioProPage.tsx` (pagine)

**Analog:** stessi file. L'ordine di rendering va RIORDINATO (UI-SPEC §E): `TotalCard` -> `BudgetAlert` -> griglia `CategoryCard` -> blocchi esistenti.

**EstimatePage.tsx** (righe 233-266): oggi l'ordine e' banner fallback -> griglia categorie (238-246) -> lista extra (248-258, DA ELIMINARE) -> `TotalCard` (260) -> bonus -> arredo -> `SoftWallCta`. Spostare `TotalCard` sopra la griglia con `mt-6` verso `BudgetAlert`. L'import `formatEur` (riga 18) diventa inutilizzato se la lista extra sparisce (lint). Lo stato budget vive qui (stato React, anonimo) e va inoltrato a `SoftWallCta` (`result={{...result, budget_eur}}`) e al salvataggio automatico (`saveMutation.mutate(result)`, riga 106) inglobandolo nel payload.

**SavedEstimateDetail.tsx** (righe 181-199): stesso riordino; eliminare le righe 187-197 (extra) e l'import `formatEur` (riga 138, usato solo li'). Il budget viene da `stima.budget_eur` (server) e il "confronto" da `stima.confronto_finiture`. `stima.input.mq` e' gia' disponibile (riga 170) per `CategoryCard`.

**DettaglioProPage.tsx**: `DettaglioProView` (410 righe, condiviso da home Pro, "Le mie stime" e questa pagina) contiene il totale del dettaglio; inserire `BudgetAlert` sotto il totale li' (non in `DettaglioProPage`, che ha solo i pannelli di snapshot righe 296-303). Fonte del confronto: `DettaglioProOut.confronto_finiture` e `totale_ivato_*`, NON lo snapshot Free (A2). Non ho letto `DettaglioProView.tsx`: il planner deve leggerlo per il punto esatto.

---

## Shared Patterns

### Anti-leak: DTO chiusi, mapping campo-per-campo
**Source:** `backend/app/routers/stima.py` righe 1-16 (docstring) e `_arredo_out` (212-242); `schemas/stima.py` righe 1-8.
**Apply to:** ogni schema/endpoint nuovo o toccato (`ConfrontoFinitureOut`, `BudgetIn/Out`, `DettaglioProOut`, `StimaSalvataOut`).
Mai `model_validate` su ORM o dataclass; nessun campo o testo con `base_eur_mq`, `moltiplicatore`, `coefficiente_impresa`, `prezzo_impresa` (`tests/test_no_leak.py` righe 20-33: match sulla SOTTOSTRINGA e anche sui valori `0.65/0.6/0.55/0.5`). Estendere `test_no_leak.py` (test parametrizzato riga 86, `pro_client` riga 200-259) e `test_no_leak_admin.py`.

### Ownership 404 anti-IDOR
**Source:** `backend/app/routers/stime_salvate.py` righe 157-164.
**Apply to:** `PUT /me/stime/{id}/budget`.
```python
stmt = select(StimaSalvata).where(
    StimaSalvata.id == stima_id, StimaSalvata.user_id == current_user.id,
)
row = session.execute(stmt).scalar_one_or_none()
if row is None:
    raise HTTPException(404, "Stima non trovata")
```

### Retrocompatibilita' snapshot: chiavi opzionali con `.get()` e default `None`
**Source:** `stime_salvate.py` righe 179-182; `schemas/stima.py` (`bonus: BonusOut | None = None`).
**Apply to:** `confronto_finiture`, `budget_eur` su stime salvate prima della fase (nessun avviso, nessun errore: Locked). Sezioni opzionali sempre `None`, mai a zero.

### Validazione input al confine (ASVS V5)
**Source:** `schemas/stima.py` riga 60 (`mq: int = Field(ge=1, le=2000)`); `schemas/stima_salvata.py` righe 29-31.
**Apply to:** `budget_eur` (`ge=1, le=999_999_999`, intero).

### Il budget non muove il prezzo
`EstimationService.compute` e `DettaglioProService.compute` non ricevono mai `budget_eur`. Test: `POST /stima` identico con/senza budget; oracolo 85 mq totale RE -> 47.985-70.575 intatto (`tests/test_stima_api.py`, `test_estimation.py`).

### Ordine dei livelli sempre da DB
**Source:** `dettaglio_pro.py` righe 238-239 (`_livelli_disponibili`: `LivelloFinitura.ordine`); `OpzioneDomanda.ordine`/`is_default`/`attiva` (`models/domanda.py`).
**Apply to:** livello inferiore Free (da `opzione_domanda` di `livello_finiture`) e Pro (da `livello_finitura`). Nessuna lista `base/medio/alto` nel codice (regola 3).

### Formattazione cifre frontend
**Source:** `frontend/src/lib/currency.ts` (`formatEur`, `formatEurRange`), tutte le cifre con `font-display tabular-nums`.
**Apply to:** ogni cifra nuova (riepilogo, €/m², avviso).

### Copy e token UI
**Source:** 10-UI-SPEC.md sezione Copywriting Contract e Color; token ambra `index.css` righe 70-72/98-100.
**Apply to:** `BudgetAlert`, `ImportoField`, riepilogo. Destructive solo per errore di importo non valido; mai "coefficiente", "prezzo impresa", "ricarico".

### Test backend
**Source:** `tests/test_stime_salvate.py` righe 1-60 (client `TestClient`, `_stima_payload()` con snapshot v2, registrazione utente reale); `tests/test_pdf.py` (`skip_without_weasyprint`, righe 61-66, guardie statiche attive anche senza WeasyPrint); `tests/test_no_leak.py`.
**Apply to:** nuovi test. Eseguire i soli file toccati con `backend/.venv/Scripts/python.exe -m pytest <file>` (la suite intera ~11 min). Per il PDF, aggiungere un test sull'HTML Jinja renderizzato (larghezze % attese), non solo sui byte del PDF (WeasyPrint puo' mancare su Windows).

## No Analog Found

| File / parte | Role | Data Flow | Reason |
|---|---|---|---|
| Barra proporzionale statica nel PDF (div a `%` con tacca) | template | transform | Nessun template PDF disegna barre a larghezza percentuale. Riferimento: solo il CSS esistente (`.categorie`, `.totale-block`, flex in `.header`). Il planner deve usare la ricetta di RESEARCH Pitfall 6 e verificare col rendering reale |
| `ImportoField` con formattazione migliaia al blur | component | event-driven | Nessun input di importo nell'app (i tipi di controllo sono `stepper`, `toggle`, `scelta_singola`, `scelta_multipla`); si compone da `InputGroup` + `Label` + regole D.1 |
| `PUT` nel client API | utility | request-response | Verificare in `frontend/src/api/client.ts` se esiste `apiPut`; il file letto espone `apiGet`/`apiPost` (righe 42-70) |

## Metadata

**Analog search scope:** `backend/app/{routers,schemas,services,models,templates}`, `backend/alembic/versions`, `backend/tests`, `frontend/src/{components,pages,api,lib,routes}`.
**Files scanned:** ~35 (letti per intero o per range mirato); non letti: `DettaglioProView.tsx`, `SoftWallCta.tsx` (solo grep), `api/client.ts` oltre riga 70, `AccediPage`/`RegistratiPage` (solo grep), `pdf_stima_pro.html` (solo grep).
**Pattern extraction date:** 2026-09-29
