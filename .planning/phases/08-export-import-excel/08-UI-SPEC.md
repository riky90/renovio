---
phase: 08
slug: export-import-excel
status: draft
shadcn_initialized: true
preset: radix-vega (style "radix-vega", baseColor slate, cssVariables true — vedi frontend/components.json)
created: 2026-09-22
---

# Phase 08 — UI Design Contract

> Contratto visivo e di interazione per l'export/import Excel dal pannello admin, la tab
> Anteprima e la pagina CRUD del catalogo domande. Nessun linguaggio visivo nuovo: questa
> fase estende un pannello admin già completo (otto pagine). Fonte primaria: `08-CONTEXT.md`
> (26 decisioni locked, D-01..D-26).

---

## Design System

| Property | Value |
|----------|-------|
| Tool | shadcn (già inizializzato — `frontend/components.json` esiste) |
| Preset | `radix-vega`, baseColor `slate`, cssVariables `true`, prefix vuoto |
| Component library | Radix (via shadcn) |
| Icon library | lucide-react |
| Font | Body/UI: "Inter Variable" (`--font-sans`) · Titoli (`h1`/`h2`/`h3`): "Bricolage Grotesque Variable" (`--font-display`), applicato automaticamente dal layer base — nessuna classe da aggiungere sui tag heading |

Nessuna nuova dipendenza di design: si riusa il token set di `frontend/src/index.css`
("palette calda da cantiere" — arancio `--primary`, sabbia `--secondary`/`--muted`, oro
`--gold*` riservato a Pro, ambra `--amber-*` riservato ad avviso/fallback).

---

## Spacing Scale

Scala ereditata dal pannello admin esistente, nessuna eccezione per questa fase:

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Gap tra icona e testo nei bottoni/badge |
| sm | 8px | Gap tra elementi compatti (badge in fila, azioni in una cella) |
| md | 16px | Padding di card/dialog, gap tra campi form |
| lg | 24px | Gap tra blocchi di una pagina (`flex flex-col gap-6`) |
| xl | 32px | Non usato in questa fase |
| 2xl | 48px | Non usato in questa fase |
| 3xl | 64px | Non usato in questa fase |

Target di tocco: bottoni icona `size="icon-sm"` (già in uso per Modifica/Elimina) restano lo
standard per le azioni di riga; nessun target sotto 40px introdotto da questa fase.

Exceptions: nessuna.

---

## Typography

Scala ereditata, invariata (nessuna dimensione o peso nuovo introdotto):

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Body / celle tabella / input | 14px (`text-sm`) | 400 (default) | 1.5 |
| Label / enfasi minore | 14px (`text-sm`) | 600 (`font-semibold`) | 1.5 |
| Heading di sezione (`h2`/`h3`, es. "Anteprima", "Opzioni — {domanda}") | 16px (`text-base`) | 600 (`font-semibold`) | 1.2 |
| Heading di pagina (`h1`, es. "Domande", "Lead") | 18px (`text-lg`) | 600 (`font-semibold`) | 1.2 |
| Fine print / istruzioni / timestamp export | 12px (`text-xs`) | 400 (default) | 1.5 |

Pesi dichiarati: **400 (regular)** e **600 (semibold)** — nessun altro peso in nessun
componente di questa fase.

---

## Color

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `--background` `#fbf8f3` | Sfondo pagina, sfondo dialog |
| Secondary (30%) | `--card` `#ffffff` / `--secondary` `#f3eee5` | Container tabella (`AdminTable`), sidebar nav, sfondo blocchi informativi (es. riepilogo lead) |
| Accent (10%) | `--primary` `#e8722a` | Riservato a: bottone primario di ogni dialog/form ("Salva", "Conferma import", "Calcola anteprima"), bottone "Scarica" quando è l'azione consigliata, badge di stato positivo ("Nuova"/"Attiva"/"Applicato"), voce di navigazione attiva nella sidebar admin |
| Destructive | `--destructive` `#e11d22` | Riservato a: badge "N scartate" nell'import, messaggi di errore inline, eventuali azioni di eliminazione fisica già esistenti (categoria/voce/extra — non nuove in questa fase) |

Accent reserved for: bottone primario di submit nei tre dialog (Aggiungi/Modifica
domanda-opzione-effetto, conferma import), CTA "Scarica {risorsa}", badge "Nuova" (righe
import), badge "Attiva" (domande/opzioni/effetti), badge "Applicato" (tabella effetti
anteprima), indicatore di tab/nav attiva. **Non** va usato per bottoni secondari, per il
bottone "Carica" quando è azione paritaria a "Scarica" (resta `variant="outline"`, coerente
con "Carica listino da Excel" già in `ListiniPage`), né per l'evidenziazione delle righe
stale nel diff (quella usa ambra, non arancio — sono semantiche diverse: primary = azione
consigliata, ambra = attenzione).

Colori semantici aggiuntivi già nel token set, riusati (non nuovi):
- **Ambra** (`--amber-bg #fdf6e3` / `--amber-border #f2ce5b` / `--amber-fg #8a5a12`): righe
  "modificate" nel diff import e nuovo stato "cambiata dopo l'export" (D-11). Preferire le
  classi token (`bg-amber-bg border-amber-border text-amber-fg`) invece dei valori hex
  cablati che oggi compaiono in `ExcelUploadDialog.tsx` (`#FCD34D`/`#FFFBEB`/`#B45309`) — la
  stessa famiglia visiva, ma senza duplicare il colore fuori dal token.
- **Oro** (`--gold*`): non toccato da questa fase, resta riservato a Pro.

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Primary CTA (archetipo) | "Scarica {risorsa}" (verbo+nome, es. "Scarica listino", "Scarica catalogo domande", "Scarica parametri", "Scarica lead") |
| Empty state heading (liste nuove di questa fase) | "Nessun elemento presente" (riuso letterale della costante `EMPTY_HEADING` già in `CoefficientiPage.tsx`) |
| Empty state body | "Aggiungi il primo elemento con il pulsante qui sopra, oppure carica un file." (riuso letterale `EMPTY_BODY`) |
| Error state (salvataggio) | "Non siamo riusciti a salvare la modifica. Riprova." (riuso letterale `SAVE_ERROR`) |
| Error state (import) | "Import non riuscito. Riprova o contatta l'assistenza tecnica." (riuso letterale `IMPORT_ERROR`) |
| Destructive confirmation (nessuna nuova in questa fase) | Le entità nuove (domanda/opzione/effetto) non si eliminano: si disattivano senza dialog di conferma (D-25) — vedi §F |

Copy specifica per ciascuna delle sei superfici nuove è nelle sezioni §A–§F sotto: non
esiste un solo "primary CTA" per l'intera fase, ne esistono sei, uno per superficie.

---

## Registry Safety

`components.json` ha `"registries": {}` — nessun registry di terze parti dichiarato o
necessario per questa fase. Nessun nuovo componente shadcn da installare: tutti i blocchi
usati (`table`, `dialog`, `alert-dialog`, `tabs`, `badge`, `select`, `switch`, `accordion`,
`radio-group`) sono già presenti nel progetto (vedi `ExcelUploadDialog.tsx`,
`CoefficientiPage.tsx`).

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | table, dialog, alert-dialog, tabs, badge, select, switch, accordion, radio-group, skeleton, input, label, textarea (tutti già installati) | not required |

---

## §A — Toolbar Scarica/Carica su quattro pagine (D-26)

Contratto unico riusato identico su `/admin/listini`, `/admin/domande`,
`/admin/coefficienti`, `/admin/lead`.

**Collocazione:** riga header della pagina, a destra del titolo `h1`, stesso pattern già in
uso in `ListiniPage.tsx` (`<div className="flex flex-wrap items-center justify-between
gap-3">`). Ordine dei bottoni, da sinistra a destra: **[Scarica {risorsa}]** (outline) ·
**[Carica file]** (outline) · bottoni esistenti della pagina (es. "Aggiungi listino") che
restano primary/accent più a destra, invariati.

- **Scarica {risorsa}** — `variant="outline"`, icona `Download` (lucide) a sinistra del
  testo. Per `/admin/coefficienti` (unico export multi-tabella con variante sensibile)
  diventa un `DropdownMenu`/split-button con due voci: "Scarica" (default, senza margine) e
  "Scarica con margine (riservato)" — vedi §B. Sulle altre tre pagine resta un bottone
  singolo, nessun margine da opzionare.
- **Carica file** — `variant="outline"`, icona `UploadCloud`, apre un dialog di
  upload+preview che riusa la shell di `ExcelUploadDialog.tsx` (§C).
- Stato di caricamento: durante la generazione del file lato server, il bottone Scarica
  passa a `disabled` con testo "Generazione…" (stesso pattern di `confirmMutation.isPending
  ? "Import in corso…" : "Conferma import"` già in uso).
- Errore di generazione export: toast di errore (pattern `sonner` esistente, non un banner
  in pagina) con testo "Non siamo riusciti a generare il file. Riprova."

---

## §B — Export con margine, opt-in (D-13)

Il default **non è mai sensibile**: nessuna colonna di margine, nessun avviso necessario.
La variante marcata è un'azione distinta, mai il default di un checkbox lasciato acceso.

- Voce di menu "Scarica con margine (riservato)" marcata con icona `Lock` (lucide, 14px)
  accanto al testo, colore `text-muted-foreground` nel menu (non urla, ma si distingue).
- Click apre un `AlertDialog` di conferma — **non** distruttivo quindi **non** in rosso
  destructive, ma in tono ambra (stessa famiglia semantica di "attenzione" di §C):
  - Titolo: "Scaricare il file con il margine?"
  - Corpo: "Questo file contiene il coefficiente impresa: non condividerlo con clienti o
    consulenti esterni. Il download viene registrato con il tuo nome."
  - Bottoni: "Annulla" (`AlertDialogCancel`, bare) · "Scarica con margine" (bottone con
    `className="border border-amber-border bg-amber-bg text-amber-fg hover:bg-amber-border/40"`,
    icona `Lock`).
- Nome file marcato per riconoscibilità anche fuori dall'app: aggiunge il segmento
  `con-margine` prima della data, es. `parametri-motore_con-margine_2026-09-22.xlsx` contro
  `parametri-motore_2026-09-22.xlsx` per il default.
- Foglio di avviso in testa al workbook (prima tab, nome foglio `AVVISO`): testo minimo
  "Questo file contiene il coefficiente impresa (margine). Uso riservato al ruolo admin. Non
  inoltrare." — fuori dall'ambito frontend puro ma parte del contratto di copy di questa
  fase.

---

## §C — Import: preview estesa con avviso file superato (D-11, D-18 esteso)

Si estende `ExcelUploadDialog.tsx` esistente, non se ne crea uno nuovo. Il flusso a passi
(destinazione → dropzone → preview diff → conferma) resta identico; cambiano due cose nella
tabella di preview:

1. **Colonna/badge aggiuntivo per riga stale.** Una riga il cui record è stato modificato nel
   database *dopo* il timestamp di generazione del file esportato riceve, oltre al badge di
   stato esistente ("Nuova"/"Modificata"), un secondo badge ambra: "Cambiata dopo l'export"
   (`className="border-amber-border bg-amber-bg text-amber-fg"`). I due badge convivono nella
   stessa cella "Stato", separati da `gap-1`.
2. **Banner riassuntivo sopra la tabella**, visibile solo se almeno una riga è stale:
   `<div className="rounded-lg border border-amber-border bg-amber-bg px-4 py-3 text-sm text-amber-fg">`
   con testo: "{N} righe sono cambiate nel database dopo che hai scaricato questo file
   (generato il {data export}). Controllale prima di confermare." — **nessun blocco duro**
   (D-11): il bottone "Conferma import" resta abilitato e visivamente invariato (primary),
   perché la decisione resta dell'admin, l'avviso è informativo non ostativo.

Il resto del contratto di `ExcelUploadDialog` (badge nuove/modificate/scartate, accordion
scarti oltre 10 righe, dialog di conferma annullamento) resta **invariato** — non
duplicare la logica, estendere lo stesso componente con le due aggiunte sopra.

**Regola D-09 (cella vuota = non toccato) nel foglio di istruzioni:** ogni export porta un
foglio `ISTRUZIONI` (o le prime righe del foglio dati, a discrezione dell'esecutore) con il
testo: "Cella vuota = campo non modificato. Per cancellare un valore esistente scrivi
`#CANCELLA#` nella cella." Il token `#CANCELLA#` è la stringa di cancellazione esplicita
richiesta da D-09, usata identica in ogni file esportato da questa fase.

---

## §D — Log dei download, in fondo alla dashboard lead (D-15, D-16)

Nuova sezione in coda a `LeadDashboardPage.tsx`, sotto la tabella lead esistente, separata da
un `gap-6` (stesso ritmo verticale della pagina). Copre **tutti e quattro** gli export
(D-15), visibile qui perché D-16 non lo restringe alla sola risorsa lead — un admin che
guarda i download vuole vedere chi ha preso cosa, non solo i lead.

- Heading `h2` (16px/600): "Download registrati".
- `AdminTable` con colonne: **Data · Utente · Risorsa · Righe · Margine**.
  - Data: `formatData()` esistente (`toLocaleDateString("it-IT")`), stesso formato della
    tabella lead.
  - Utente: nome o email di chi ha scaricato.
  - Risorsa: etichetta leggibile (`Listino`, `Catalogo domande`, `Parametri`, `Lead`) — mai
    il nome tecnico della tabella.
  - Righe: numero, `tabular-nums`, allineato a destra.
  - Margine: `Badge` — "Sì" con lo stile ambra (`bg-amber-bg text-amber-fg`, coerente con
    §B: è la stessa semantica di attenzione) quando `include_margine=true`, altrimenti "—"
    in `text-muted-foreground` (non un badge: l'assenza di margine è la norma, non va
    enfatizzata quanto la presenza).
- Empty state: heading "Nessun download registrato", body "I download di questa pagina
  compariranno qui." (stesso pattern `emptyHeading`/`emptyBody` di `AdminTable`).
- Nessuna paginazione: mostra gli ultimi 50, ordine dal più recente (coerente con l'assenza
  di paginazione nel resto del pannello admin).
- Visibilità: la sezione compare per **admin e consulente** (`allow={["admin","consulente"]}`
  già impostato su questa pagina) — il consulente vede anche le proprie righe di download dei
  lead, non solo quelle altrui: nessun filtro di riga per ruolo, la trasparenza è reciproca.

---

## §E — Tab Anteprima, sesta tab di /admin/coefficienti (D-17..D-20, PAR-04)

Backend già completo (`POST /admin/domande/anteprima`) — questa sezione è puro frontend.

**Collocazione:** nuova `TabsTrigger value="anteprima"` in coda alla `TabsList` esistente di
`CoefficientiPage.tsx` (dopo "Coefficienti Pro"), stesso pattern di composizione (`<TabsContent
value="anteprima"><AnteprimaTab /></TabsContent>`).

### E.1 — Form input sintetici (D-19)

Riusa i componenti del wizard pubblico invece di inventarne di nuovi — stessa forma esatta
di `AnteprimaIn`:

| Campo | Componente | Note |
|-------|-----------|------|
| Città | `CityAutocomplete` (riuso diretto) | stesso comportamento del wizard pubblico |
| M² | `NumberStepper` (riuso diretto, WIZ-02) | min 1, max 2000 come `AnteprimaIn.mq` |
| Tipo | `Select` con le tre opzioni `leggera`/`moderata`/`totale`, etichette da `TIPO_LABELS` (già definite in `LeadDashboardPage.tsx`, da estrarre in un modulo condiviso se non lo è già) | |
| Risposte | Una `DomandaField` per ogni domanda del catalogo (`GET /api/v1/domande`), riuso diretto dal wizard | Nessun campo hardcoded: una domanda nuova nel catalogo appare qui senza modifiche, stessa proprietà del wizard |

Bottone di submit: **"Calcola anteprima"** (primary, `variant` default), disabilitato finché
città e mq non sono validi. Stato di caricamento: testo diventa "Calcolo…", disabilitato.
Errore: messaggio inline sotto il bottone, "Non siamo riusciti a calcolare l'anteprima.
Controlla i valori e riprova."

Il form resta visibile e compilato dopo il calcolo (non collassa): l'admin deve poter
cambiare un valore e ricalcolare senza ricompilare da zero — è uno strumento di esplorazione
iterativa (D-19), non un wizard a passi.

### E.2 — Breakdown per categoria (`AnteprimaCategoriaOut[]`)

Griglia di card compatte (una per categoria, stesso `border border-border bg-card
rounded-xl` delle altre superfici admin), sotto il form. Per ciascuna:

- Nome categoria (`text-sm font-semibold`).
- Range base (senza risposte): "{base_min}–{base_max} €", `text-sm tabular-nums
  text-muted-foreground`.
- Range con risposte: "{totale_min}–{totale_max} €", `text-sm tabular-nums font-semibold
  text-foreground` — è il numero che conta di più nella card, quindi il peso visivo maggiore.
- Delta: "Δ {delta_min}–{delta_max} €" con icona `TrendingUp`/`TrendingDown` (lucide, 14px)
  a seconda del segno, **colore neutro** (`text-foreground`, non rosso/verde): questa fase
  non introduce una semantica positivo/negativo a colori — quella è nel backlog RIS-01..04
  della Fase 10, non qui.

Layout: `grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4` (una card per le quattro
categorie A/B/C/D, coerente con la griglia a card già vista altrove nel prodotto).

### E.3 — Tabella effetti, tutti visibili (D-20)

Vincolo esplicito, non negoziabile per questa fase: **l'effetto che non ha sparato non è
mai nascosto, filtrato, paginato fuori vista, né visivamente attenuato.** Nessun
`opacity-*`, nessun `text-muted-foreground` sull'intera riga per gli effetti non applicati:
solo il badge di stato cambia, il resto della riga (testo domanda/opzione, valore,
contributo) ha lo stesso peso visivo di una riga applicata.

`AdminTable` con colonne: **Domanda · Opzione · Tipo effetto · Categoria · Valore ·
Contributo · Stato**.

- Stato: `Badge` — "Applicato" con `bg-primary/10 text-primary` (stessa semantica di
  "Nuova"/"Attiva" — è lo stato "buono/atteso" del sistema), "Non applicato" con
  `variant="outline"` (bordo neutro, testo `text-foreground`, **non** `text-muted-foreground`
  — deve leggersi con la stessa facilità di "Applicato").
- Ordine righe: **quello del catalogo** (per domanda, poi per opzione), non un riordino che
  porti gli applicati in cima o i non applicati in fondo — la tabella deve restare
  prevedibile e ripercorribile con lo stesso ordine ogni volta, indipendentemente da cosa ha
  sparato in questa singola simulazione.
- `nota` (quando presente): riga secondaria sotto il valore, `text-xs text-muted-foreground`
  — es. motivo per cui un effetto non si applica ("condizione non soddisfatta: …").
- `avvisi` (array top-level di `AnteprimaOut`): banner sopra la tabella, stesso stile ambra
  di §C quando non vuoto (es. fallback città).

---

## §F — Pagina CRUD Catalogo domande (D-21..D-25)

Nuova pagina `/admin/domande`, voce di navigazione aggiuntiva in `AdminLayout.tsx`
(`NAV_ITEMS`), icona `HelpCircle` o `ListChecks` (lucide), `roles: ["admin"]`.

### F.1 — Master-detail annidato senza cambio pagina (D-24)

Stesso pattern di rivelazione progressiva già in `ListiniPage.tsx` (listino → categorie →
voci): un click su una riga della tabella superiore rivela la tabella del livello
sottostante *sotto*, sulla stessa pagina — nessuna navigazione a route separata, nessun
dialog per il drill-down (i dialog restano riservati a crea/modifica).

1. **Tabella Domande** (sempre visibile in cima): colonne **Codice · Testo · Attributo ·
   Tipo controllo · Attiva · Azioni**. Bottone "Aggiungi domanda" in alto a destra
   (`variant="outline"`, stesso posto di "Aggiungi extra"/"Aggiungi listino").
2. Click su una riga → sotto compare **"Opzioni — {domanda.testo}"** con la tabella Opzioni
   di quella domanda: colonne **Codice · Etichetta · Attiva · Azioni**. Bottone "Aggiungi
   opzione" sopra la tabella.
3. Click su una riga opzione → sotto compare **"Effetti — {opzione.etichetta}"** con la
   tabella Effetti: colonne **Tipo effetto · Categoria · Valore · Attivo · Azioni**. Bottone
   "Aggiungi effetto" sopra la tabella.

Deselezionare (click sulla stessa riga già selezionata, o un bottone testuale "Chiudi") fa
collassare il livello e quelli sotto di esso — stesso comportamento implicito già presente
in `ListiniPage` quando si cambia listino (`setSelectedCategoriaId(null)`).

### F.2 — Form crea/modifica (D-22)

Riuso letterale di `AdminCrudDialog` per le tre entità, un dialog per tipo:

- **Domanda:** campi `code` (Input, sola creazione, disabled in modifica — stesso pattern di
  `extra-code`), `testo` (Input), `help` (Textarea, opzionale), `attributo_code` (Input),
  `tipo_controllo` (Select tra i cinque valori chiusi noti a `DomandaField`), `attiva`
  (Switch, default `true`).
- **Opzione:** campi `code` (Input, sola creazione), `etichetta` (Input), `attiva` (Switch).
  Contesto (`domanda_code`) mostrato come testo statico non editabile, stesso pattern di
  "Tipo × categoria" in `CoefficientiPage`.
- **Effetto:** campi `tipo_effetto` (Select tra i sette valori chiusi di `effetti.py`),
  `categoria_code` (Select tra le categorie A/B/C/D, quando il tipo di effetto lo richiede),
  `valore` (Input number), `attivo` (Switch). Contesto (opzione) mostrato come testo statico.

Titoli dialog: "Aggiungi {entità}" / "Modifica {entità}", identico al pattern esistente.
Bottone submit: "Salva {entità}" (ereditato da `AdminCrudDialog`, nessuna copy nuova da
scrivere).

### F.3 — Nessun delete fisico, disattivazione inline (D-25)

Questa è l'unica pagina CRUD del pannello che **non** usa `AdminDeleteConfirm`. L'azione
"Elimina" è sostituita da un toggle di attivazione:

- Colonna "Attiva"/"Attivo" mostra un `Badge` di stato (pattern identico a "Attivo"/"Non
  attivo" già in `ExtraTab`): `bg-primary/10 text-primary` se attivo, `bg-muted
  text-muted-foreground` se disattivato — qui, a differenza di §E.3, l'attenuazione è
  corretta perché "disattivato" *è* uno stato secondario voluto, non un dato da non
  nascondere.
- Azione di riga: **un solo bottone icona** (`Power` o `EyeOff`/`Eye` da lucide a seconda
  dello stato corrente), `variant="ghost" size="icon-sm"`, che alterna `attiva`
  direttamente — **nessun `AlertDialog` di conferma**: è un'azione reversibile (si
  riattiva con lo stesso bottone), coerente con D-25 e con il fatto che le stime salvate che
  citano la domanda restano leggibili comunque. Al successo: toast "Modifica salvata"
  (pattern esistente), nessuna copy di conferma distruttiva da scrivere perché non è
  un'azione distruttiva.
- Il bottone "Modifica" (`Pencil`, icon-sm) resta accanto, invariato.

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending
