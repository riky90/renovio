---
phase: 10
slug: risultato-leggibile
status: approved
reviewed_at: 2026-09-29
shadcn_initialized: true
preset: radix-vega (style "radix-vega", baseColor slate, cssVariables true — vedi frontend/components.json)
created: 2026-09-29
---

# Phase 10 — UI Design Contract

> Contratto visivo e di interazione per RIS-01..04. Nessun linguaggio visivo nuovo: la fase
> cambia la **geometria** della `RangeBar`, arricchisce `CategoryCard` e `TotalCard`, aggiunge
> un box avviso budget e una domanda budget nel wizard. Fonte delle decisioni: 10-CONTEXT.md
> (D-01..D-17, bloccate). Token e convenzioni ereditati da 09-UI-SPEC.md e da
> `frontend/src/index.css`.
>
> **Superfici toccate:** `RangeBar`, `TotalCard`, `CategoryCard`, nuovo `BudgetAlert`,
> `EstimatePage`, `SavedEstimateDetail`, `DettaglioProPage` (Pro), step 3 di `EstimateWizard`,
> template PDF `pdf_stima.html` e `pdf_stima_pro.html` (versione statica, §F).
>
> **Regole di dominio che vincolano il design:** cifre sempre a range (unica eccezione
> dichiarata: la percentuale di peso, D-15); mai prezzo impresa o coefficiente; il budget non
> muove il prezzo; l'arredo resta fuori da barra, peso, riepilogo e confronto budget (D-08).

---

## Design System

| Property | Value |
|----------|-------|
| Tool | shadcn (già inizializzato, `frontend/components.json`) |
| Preset | `radix-vega`, baseColor `slate`, cssVariables `true`, prefix vuoto |
| Component library | Radix (via shadcn) |
| Icon library | lucide-react |
| Font | Body/UI: "Inter Variable" (`--font-sans`) · Titoli e cifre (`font-display`): "Bricolage Grotesque Variable" |

Nessuna nuova dipendenza, nessun `npx shadcn add`. Componenti riusati (tutti già presenti):
`Alert`, `Button`, `Card`, `Input`, `InputGroup`, `Label`, `Separator`, `Badge`,
`NumberStepper` (non per il budget), `formatEur` / `formatEurRange` (`@/lib/currency`).

Componente custom nuovo: **`BudgetAlert`** (`frontend/src/components/BudgetAlert.tsx`) e il
campo importo (`ImportoField`, §D.1). Nessun registry esterno.

---

## Spacing Scale

Scala ereditata, multipli di 4:

| Token | Value | Usage in questa fase |
|-------|-------|-------|
| xs | 4px | Gap tra barra peso e etichetta %, gap icona/testo nell'avviso |
| sm | 8px | Gap barra → etichette min/max (`gap-2`), gap righe del riepilogo (`gap-2`) |
| md | 16px | Gap tra blocchi dentro `BudgetAlert` (`gap-4`), padding orizzontale card avviso (`px-4`) |
| lg | 24px | Padding `TotalCard` (`px-6`), gap tra `TotalCard` e `BudgetAlert` (`mt-6`) |
| xl | 32px | Non usato |
| 2xl | 48px | Non usato |
| 3xl | 64px | Non usato |

Dimensioni specifiche (multipli di 4):
- Barra `RangeBar`: altezza traccia 8px (`h-2`, invariata); pallini 14px (`size-3.5`, invariati).
- Tacca budget: larghezza 2px, altezza 24px (`h-6`), centrata sulla traccia; l'etichetta "Il tuo budget" sta **sopra** la barra (vedi §A.3).
- Mini-barra peso categoria: altezza 4px (`h-1`), larghezza piena della card.
- Campo importo budget: altezza 44px (`h-11`), stesso target di tocco di `NumberStepper`.

Exceptions: la tacca da 2px e la traccia peso da 4px sono spessori di linea, non spaziature.

---

## Typography

Esattamente 4 dimensioni e 2 pesi, tutti già in uso nell'app:

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Body / testo avviso / righe riepilogo | 14px (`text-sm`) | 400 | 1.5 |
| Label / micro-label (eyebrow, "fino a", etichetta tacca, % peso, €/m²) | 12px (`text-xs`) | 600 (eyebrow, % peso) o 400 (€/m², "fino a") | 1.5 |
| Cifra card / titolo avviso (`font-display`) | 20px (`text-xl`) | 600 | 1.2 |
| Cifra totale sulla barra (`font-display`, `text-lg sm:text-xl`) | 18px mobile / 20px desktop | 600 | 1.2 |

Note:
- Il 18px mobile della cifra totale è preesistente in `RangeBar` (`text-lg`); è il solo caso fuori dalla scala 12/14/20 e resta com'è. Nessun'altra dimensione nuova.
- Peso **bold (700)** oggi usato in `RangeBar` e `CategoryCard` (`font-bold`) **non si estende** a elementi nuovi: gli elementi nuovi usano 400 o 600. Il cambio di `font-bold` esistenti a 600 è raccomandato ma fuori scope se rischia regressioni visive; gli elementi nuovi non introducono un terzo peso.
- Tutte le cifre: `tabular-nums`.

---

## Color

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `--background` `#fbf8f3` | Sfondo pagina risultato |
| Secondary (30%) | `--card` `#ffffff`, `--secondary` `#f3eee5`, `--muted` | Card categoria, `TotalCard`, traccia barra e traccia peso (`bg-secondary`) |
| Accent (10%) | `--primary` `#e8722a` (+ `--gold` `#f4b60e` nel gradiente) | vedi lista sotto |
| Destructive | `--destructive` `#e11d22` | **Non usato in questa fase.** Sforare il budget non è un errore: usa l'ambra |

Accent reserved for:
1. Segmento del range sulla `RangeBar` (gradiente `--gold` → `--primary`, motivo-firma invariato) e pallino max.
2. Fill della mini-barra peso nelle card di categoria (`bg-primary`, opacità piena).
3. Cifra massima sulla barra (`text-primary`, invariato).
4. Bottone primario del campo budget ("Aggiorna il confronto").

Colori semantici dell'avviso (nessun colore nuovo, solo token esistenti):

| Stato (D-06) | Superficie | Testo/icona | Icona lucide |
|---|---|---|---|
| Fuori budget (budget < min) | `bg-amber-bg` + `border-amber-border` | `text-amber-fg` | `AlertTriangle` |
| Al limite (min ≤ budget ≤ max) | `bg-amber-bg` + `border-amber-border` | `text-amber-fg` | `Info` |
| Nei limiti (budget > max) | `bg-accent/60` + `border-border` | `text-accent-foreground` | `CheckCircle2` |

- Fuori budget e al limite condividono la superficie ambra; li distingue titolo, icona e testo, non il colore (accessibilità: mai solo colore).
- Tacca budget sulla barra: `bg-foreground` (inchiostro `#22201c`), volutamente **non** arancio né oro, per non confondersi con gli estremi del range. Etichetta "Il tuo budget" in `text-foreground`, 12px/600.
- Il verde non esiste nella palette: la conferma positiva usa `--accent` (arancio tenue) + icona check, non un verde nuovo.
- Riepilogo IVA (§C): nessun colore semantico; righe neutre, totale in `text-foreground` 600.

---

## Copywriting Contract

Lingua italiana, tono diretto, dà del "tu" (coerente con "il tuo budget"). Niente gergo per professionisti.

| Element | Copy |
|---------|------|
| Domanda wizard (step 3), label | "Qual è il tuo budget per la ristrutturazione?" (dato di catalogo se la forma tecnica lo permette; altrimenti stringa fissa) |
| Help sotto la label | "Facoltativo. Scrivi la cifra che hai in mente, IVA inclusa: non cambia la stima, ci serve per dirti se ci rientri." |
| Placeholder campo importo | "Es. 40.000" (suffisso fisso "€" nel campo, `InputGroup`) |
| Azione "salta" budget | Nessun bottone: il campo vuoto = nessun budget. Cancellare il valore lo rimuove |
| Titolo avviso, fuori budget | "La stima supera il tuo budget" |
| Corpo avviso, fuori budget, con confronto | "Con finiture {livello_inferiore} la stessa ristrutturazione costerebbe {min}–{max} (IVA inclusa), circa {delta_min}–{delta_max} in meno." |
| Corpo avviso, fuori budget, finiture già economiche (D-07) | "Hai già scelto finiture economiche. Per stare nel tuo budget servono meno lavori: prova a togliere qualche intervento." |
| Titolo avviso, al limite | "Il tuo budget è al limite" |
| Corpo avviso, al limite | "Rientra nel range della stima, ma dipende dalle scelte che farai. Le finiture sono la leva più semplice." |
| Titolo avviso, nei limiti | "Rientri nel tuo budget" |
| Corpo avviso, nei limiti | "Anche nel caso più alto della stima resti sotto {budget}." |
| Etichetta livelli | `base` → "economiche", `medio` → "medie", `alto` → "alte" (stessi nomi delle opzioni del catalogo) |
| Etichetta tacca | "Il tuo budget" |
| Campo budget nell'avviso, label | "Il tuo budget (IVA inclusa)" |
| CTA campo budget nell'avviso | "Aggiorna il confronto" |
| CTA aggiungi budget (nessun budget dichiarato, pagina risultato) | "Aggiungi il tuo budget" (link testuale `text-primary`, apre il campo; non compare nessun avviso finché il valore non c'è, D-02) |
| CTA rimuovi budget | "Togli il budget" (link testuale `text-muted-foreground`, non distruttivo: nessuna conferma) |
| Nota permanente sotto avviso | "Il budget non cambia il prezzo della stima." |
| Etichetta €/m² card | "{min}–{max} €/m²" seguito da "IVA esclusa" in `text-muted-foreground` |
| Etichetta peso card | "{n}% del totale" |
| Primary CTA della pagina | invariata (nessun CTA primario nuovo: la fase non aggiunge un'azione principale) |
| Empty state | Nessuno: budget assente = nessun avviso, nessuna tacca, nessuna riga. Stime salvate prima della fase idem, senza errore |
| Error state, salvataggio budget | "Non siamo riusciti a salvare il budget. Riprova tra qualche istante." Il campo resta con il valore digitato; l'avviso non si ricalcola |
| Error state, importo non valido | "Scrivi un importo in euro maggiore di zero." (sotto il campo, `text-sm text-destructive` solo per errore di input; l'unico uso del rosso in questa fase) |
| Destructive confirmation | Nessuna. "Togli il budget" è reversibile e non tocca il prezzo |

Regole di copy:
- Nessuna cifra secca di prezzo: il budget dichiarato dall'utente è un dato suo, non una stima, e può comparire come numero singolo. Il **peso %** è un solo numero (D-15).
- Il delta si scrive sempre come range ("circa 8.000–12.000 € in meno").
- Mai le parole "coefficiente", "prezzo impresa", "ricarico".

---

## Registry Safety

`components.json` ha `"registries": {}`.

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | alert, button, card, input, input-group, label, separator, badge (tutti già installati) | not required |
| custom (progetto) | `RangeBar`, `TotalCard`, `CategoryCard`, `BudgetAlert` (nuovo), `ImportoField` (nuovo) | not applicable — non è un registry esterno |

---

## §A — RangeBar proporzionale (RIS-01, D-11, D-12)

### A.1 — Geometria

La traccia (`bg-secondary`, `h-2`, `rounded-full`) rappresenta un asse **0 → tetto**.
Il segmento colorato va da `min/tetto` a `max/tetto` (percentuali di larghezza), i due pallini
stanno agli estremi del segmento. Sostituisce gli offset fissi `left-[12%]` / `right-[12%]`.

- `tetto = max(1.2 × totale_max, budget)`, arrotondato per eccesso a un numero tondo (es. al migliaio superiore sotto i 100.000 €, alle 5.000 € sopra). L'arrotondamento esatto è a discrezione dell'implementazione; il contratto è: tetto ≥ max, segmento mai a filo del bordo destro senza budget.
- Larghezza minima del segmento: 4% (perché un range molto stretto resti visibile e i due pallini non si sovrappongano). Se `min/tetto` e `max/tetto` distano meno di 4%, allarga simmetricamente attorno al centro.
- Effetto atteso: ±10% e ±20% producono segmenti di larghezza visibilmente diversa (criterio di RIS-01).

### A.2 — Props

`RangeBar` mantiene `minLabel`, `maxLabel`, `className` e aggiunge `min`, `max` (numeri, obbligatori per la geometria) e `budget?: number | null`. Con `min`/`max` assenti (uso legacy) ricade sulla geometria vecchia solo se un chiamante non è ancora migrato; a fine fase nessun chiamante la usa.

### A.3 — Tacca budget

Se `budget` è valorizzato: linea verticale 2px × 24px (`bg-foreground`), posizionata a `budget/tetto`, centrata sulla traccia; etichetta "Il tuo budget" (12px/600) **sopra** la barra, allineata alla tacca e vincolata ai bordi del contenitore (`translate` con clamp per non uscire a sinistra/destra su mobile). Il valore in euro sta nell'`aria-label` e nell'avviso, non ripetuto sulla barra. Nessun budget: nessuna tacca, nessuno spazio riservato sopra la barra.

### A.4 — Etichette sotto la barra

Invariate: cifra min a sinistra (`text-foreground`), "fino a" al centro, cifra max a destra (`text-primary`), `font-display tabular-nums`. Tra traccia ed etichette `gap-2`.

### A.5 — Accessibilità

La barra è `role="img"` con `aria-label` "Stima da {min} a {max}" più " · budget {budget}" se presente. La tacca non è l'unico segnale: l'esito è nell'avviso testuale.

---

## §B — CategoryCard (RIS-02, D-13, D-14, D-15)

Ordine verticale nel `CardContent`, `gap-3`:

1. Range totale categoria IVA inclusa (invariato): `font-display text-xl` `formatEurRange`.
2. **Riga incidenza**: "{min}–{max} €/m²" (`text-sm`, 400, `tabular-nums`) + "IVA esclusa" in `text-xs text-muted-foreground`. Calcolo su `imponibile_min/max ÷ mq calpestabili`; valori arrotondati all'euro, formattati con `formatEurRange` adattato al suffisso "€/m²".
3. **Mini-barra peso**: traccia `h-1 rounded-full bg-secondary`, fill `bg-primary` largo quanto il peso %. Sopra o a destra della traccia (stessa riga, `justify-between`, `gap-1`): "{n}% del totale" in `text-xs font-semibold`. Il peso è calcolato sul valore medio ((min+max)/2) della categoria sul totale lavori (senza arredo), arrotondato a intero; le percentuali possono non sommare a 100 esattamente, nessuna correzione visibile.
4. Strip teaser Pro (invariata, solo Free).

Categorie con peso < 1%: mostra "<1%" e fill di larghezza minima 2%.
`role="progressbar"`-equivalente non serve: la mini-barra è decorativa (`aria-hidden`), il numero % è il dato accessibile.

Non esiste una `RangeBar` nella card (D-13).

---

## §C — TotalCard e riepilogo (RIS-03, D-16)

Struttura della `TotalCard`, dall'alto:

1. Fascia eyebrow + `RangeBar` (invariata nel layout: `border-l-4 border-primary bg-accent/60 px-6 py-5`), ora proporzionale (§A).
2. **Riepilogo** (nuovo), sotto la fascia, `px-6 py-4`, righe `flex justify-between gap-2 text-sm`, cifre a destra `tabular-nums`, separate dalla fascia da un `Separator`:
   - "Imponibile lavori" → range imponibile totale lavori
   - "IVA 10%" → range (una riga per ogni aliquota presente; raggruppa per `iva_pct` delle categorie). Se esiste una sola aliquota, una sola riga.
   - "IVA 22%" → idem
   - "Costi extra" con sotto-elenco: una riga per extra ("Sicurezza (CSE/CSP)", "Pratiche"…) con `nome` e importo, in `text-muted-foreground`. L'importo degli extra è un dato fisso già presente in `ExtraOut`: si mostra com'è (non è un prezzo stimato a range).
   - Separatore, poi "Totale IVA inclusa" (`font-semibold`, range).
   - Le righe con aliquota mostrano solo la percentuale di legge (10% / 22%), mai altro.
3. Note esistenti ("Comprende i costi extra…" e "Stima pre-sopralluogo…") restano in coda, `text-sm text-muted-foreground`. La prima frase può accorciarsi perché il riepilogo ora dettaglia gli extra; il disclaimer pre-sopralluogo non si rimuove.

La lista extra separata oggi in `EstimatePage` (riga ~249) e in `SavedEstimateDetail` viene **eliminata**: gli extra vivono solo nel riepilogo.

Sezioni assenti (`None`): se non ci sono extra, la riga "Costi extra" non compare. Arredo e bonus non entrano nel riepilogo.

Mobile: le righe restano su una riga fino a 360px (label a sinistra `min-w-0`, cifra a destra `shrink-0`); se il range non entra, la cifra va a capo sotto la label, allineata a destra.

---

## §D — Budget: raccolta e modifica (RIS-04, D-01..D-05)

### D.1 — `ImportoField` (nuovo controllo, tipo "importo")

Input numerico in euro, tap target 44px:
- `InputGroup` con suffisso fisso "€" a destra, `h-11`, `inputMode="numeric"`, `type="text"` con formattazione a migliaia in italiano (punto come separatore) al blur, valore grezzo intero mentre si digita.
- Accetta solo cifre; separatori incollati vengono ripuliti. Intero positivo, massimo 9 cifre.
- Vuoto = nessun budget (valido). 0 o non numerico = errore di input ("Scrivi un importo in euro maggiore di zero."), il valore non viene inviato.
- Focus: anello `--ring` come gli altri `Input`.
- Nessuno stepper: non è un contatore.

### D.2 — Nel wizard (step 3 "La ristrutturazione")

Posizione: **ultima domanda dello step 3**, dopo le domande sulla ristrutturazione, prima del pulsante di avanzamento. Struttura come `DomandaField`: `Label` (14px/600), help `text-sm text-muted-foreground` sempre visibile sotto la label, poi `ImportoField`, `gap-2` tra label e controllo. Facoltativo: lo step non si blocca con il campo vuoto. Nessun asterisco.

### D.3 — Nella pagina risultato

`BudgetAlert` sta **subito sotto la `TotalCard`**, `mt-6`, prima delle card di categoria. Vale per Free (`EstimatePage`), stima salvata (`SavedEstimateDetail`) e Pro (`DettaglioProPage`, sotto il totale del dettaglio), stesso componente.

- Con budget dichiarato: mostra l'avviso nello stato corrispondente (§Color) con titolo, corpo, nota permanente e il campo di modifica.
- Senza budget: nessun avviso; sotto la `TotalCard` compare solo il link "Aggiungi il tuo budget". Cliccandolo, si apre il box con `ImportoField` + "Aggiorna il confronto" (senza titolo di esito finché non c'è un valore).

### D.4 — Anatomia di `BudgetAlert`

`Alert` shadcn con classi di superficie per stato (§Color), `px-4 py-4`, `flex flex-col gap-4`:

1. Riga icona + titolo (`font-display text-xl font-semibold`... in mobile il titolo può andare a `text-sm font-semibold` se il testo supera due righe; la scala resta 14/20).
2. Corpo (`text-sm`).
3. Solo se stato = fuori budget con confronto: mini riepilogo a due righe — "Ora: {min}–{max}" e "Con finiture {livello}: {min}–{max}" — cifre `tabular-nums font-display`, con il delta a range in `text-xs text-muted-foreground`. Dati dal ricalcolo server (D-09); il client non stima nulla.
4. Riga di modifica: `Label` "Il tuo budget (IVA inclusa)" + `ImportoField` + `Button` "Aggiorna il confronto" (variante default = accento). Su `sm:` in riga (`flex-row items-end gap-2`), su mobile in colonna, bottone a tutta larghezza.
5. Link "Togli il budget" (`text-xs`/`text-sm`, `text-muted-foreground`, sottolineato al hover).
6. Nota "Il budget non cambia il prezzo della stima." (`text-xs text-muted-foreground`).

### D.5 — Interazione (D-05)

- "Aggiorna il confronto" invia il nuovo budget al server e ricalcola. Durante l'attesa: bottone `disabled` con testo "Aggiorno…", il resto dell'avviso resta visibile (nessuno skeleton a schermo intero). A successo: l'avviso cambia stato con transizione di opacità 150ms (`prefers-reduced-motion`: nessuna transizione); il valore si salva sulla stima. In errore: messaggio di errore salvataggio (§Copywriting), valore digitato conservato.
- Il prezzo (totale, categorie, barra) **non cambia** in nessun caso; cambia solo la posizione della tacca e l'avviso.
- Su una stima salvata prima della fase, senza budget: nessun avviso, solo "Aggiungi il tuo budget".
- Pro (D-10): stesso comportamento; il confronto nasce da un ricalcolo sull'asse `finitura` un livello sotto quello scelto in "Affina la stima". Stesso `BudgetAlert`, stessa copy.
- Focus: aprendo il box "Aggiungi il tuo budget" il focus va su `ImportoField`. L'esito dopo l'aggiornamento è annunciato via `role="status"` (`aria-live="polite"`); l'avviso "fuori budget" non usa `role="alert"` assertivo (non è un errore bloccante).

---

## §E — Ordine e layout della schermata risultato

1. `TotalCard` (barra proporzionale + tacca budget + riepilogo)
2. `BudgetAlert` (o link "Aggiungi il tuo budget")
3. Griglia `CategoryCard` (invariata: 1 colonna mobile, 2 colonne `sm:`)
4. Blocchi esistenti a seguire (arredo, bonus, disclaimer, CTA PDF), invariati

Larghezza contenuto invariata dai layout attuali. Il box avviso non è sticky.

---

## §F — PDF (D-17)

`pdf_stima.html` e `pdf_stima_pro.html`, versione statica (nessuna interazione):

- **Barra**: stessa geometria proporzionale, disegnata con `div` a larghezza percentuale calcolati lato server (nessun JS). Tacca budget e etichetta "Il tuo budget" se presente. Colori e gradiente come web. Niente ombre; bordi 1px `--border`.
- **Riepilogo** imponibile / IVA per aliquota / extra / totale come tabella a due colonne con la stessa gerarchia tipografica del web (sezione §C).
- **Per categoria**: range IVA inclusa, riga "{min}–{max} €/m² (IVA esclusa)" e "{n}% del totale" con mini-barra statica.
- **Budget e avviso**: riquadro con il titolo e il corpo dello stato, ma **senza** campo, bottoni o link di modifica. Nota "Il budget non cambia il prezzo della stima." inclusa. Con confronto: le due righe "Ora" / "Con finiture {livello}".
- Nessun budget nello snapshot: la sezione non viene emessa.
- I dati vengono da `risultato_json` congelato: il PDF non ricalcola.
- Il disclaimer pre-sopralluogo e quello di fallback listino restano dove sono. Nessun coefficiente, nessun prezzo impresa.

---

## §G — Stati e casi limite

| Caso | Comportamento |
|------|---------------|
| Nessun budget | Nessun avviso, nessuna tacca; solo link "Aggiungi il tuo budget" |
| Budget < min | Avviso ambra "La stima supera il tuo budget" + confronto |
| min ≤ budget ≤ max | Avviso ambra morbido "Il tuo budget è al limite" |
| Budget > max | Conferma "Rientri nel tuo budget" (tono accento) |
| Finiture già economiche + budget < min | Testo "meno lavori", nessun confronto numerico |
| Budget > tetto della scala | Il tetto sale a `budget`; il segmento si restringe visivamente, comportamento voluto |
| Stima salvata pre-fase | Come "nessun budget", nessun errore |
| Confronto non calcolabile (errore server) | L'avviso mostra titolo e corpo senza la parte del confronto; nessun messaggio tecnico |
| Categoria con peso <1% | "<1%", fill minimo 2% |
| Extra assenti | Riga "Costi extra" omessa dal riepilogo |
| Solo un'aliquota IVA presente | Una sola riga IVA |
| Arredo presente | Fuori da barra, pesi, riepilogo, confronto (D-08); `ArredoCard` invariata |

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending
