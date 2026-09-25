---
phase: 09
slug: configuratore-pro
status: draft
shadcn_initialized: true
preset: radix-vega (style "radix-vega", baseColor slate, cssVariables true — vedi frontend/components.json)
created: 2026-09-25
---

# Phase 09 — UI Design Contract

> Contratto visivo e di interazione per la chiusura del bug dei cataloghi (CFG-01..04,
> QST-05, WIZ-04). **Unica superficie UI della fase:** il pannello "Qualche dettaglio in
> più" dentro `DettaglioProView` (route `/dettaglio-pro`, riusata da home Pro e "Le mie
> stime"). Nessun linguaggio visivo nuovo — estende un pannello già shippato.
>
> **Fuori da questo contratto, per costruzione (vedi CONTEXT §deferred e Claude's
> Discretion):**
> - La pagina admin `/admin/domande` (08.1-UI-SPEC, invariata: le nuove domande Pro
>   *finitura*/*tipo pavimento*/tre stepper sono **dati** creati con la CRUD già
>   contrattata, zero pixel nuovi).
> - Il file Excel di taratura (D-04): è un deliverable a Riccardo, non uno schermo
>   dell'app — nessun contratto di design si applica a un file scaricato una volta,
>   compilato fuori dal prodotto e ricaricato via `POST /admin/upload-listino/preview`
>   (già contrattato in `08-UI-SPEC.md`).
> - Il wizard (step 1-4, `EstimateWizard`): D-06 lo lascia esplicitamente invariato.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | shadcn (già inizializzato — `frontend/components.json` esiste) |
| Preset | `radix-vega`, baseColor `slate`, cssVariables `true`, prefix vuoto |
| Component library | Radix (via shadcn) |
| Icon library | lucide-react |
| Font | Body/UI: "Inter Variable" (`--font-sans`) · Titoli (`h1`/`h2`/`h3`): "Bricolage Grotesque Variable" (`--font-display`) |

Nessuna nuova dipendenza di design. Palette invariata (arancio `--primary`, sabbia
`--secondary`/`--muted`, oro `--gold*` riservato a Pro, ambra `--amber-*` riservato ad
avviso/default automatico).

Componenti riusati, **tutti già esistenti** (nessun `npx shadcn add`, nessun componente
shadcn nuovo — solo primitivi custom già nel progetto):

| Componente | Percorso | Uso in questa fase |
|---|---|---|
| `NumberStepper` | `frontend/src/components/ui/number-stepper.tsx` | Sostituisce i tre `<Input inputMode="numeric">` grezzi di bagni/porte/condizionatori |
| `OptionCard` | `frontend/src/components/EstimateFormFields.tsx` | Nuovo selettore "tipo di pavimento" (4 opzioni) |
| `DomandaField` | `frontend/src/components/DomandaField.tsx` | Motore di rendering: vedi §A.1 — le tre domande Pro (finitura è già gestita ad-hoc, pavimento + i tre stepper migrano su questo componente) |
| `Accordion`, `Alert`, `Button`, `Label`, `Skeleton` (shadcn) | invariati | nessuna modifica |

---

## Spacing Scale

Scala ereditata, nessuna eccezione:

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Gap icona/testo nei bottoni |
| sm | 8px | Gap tra `Label` e controllo in una singola domanda (`flex flex-col gap-2`) |
| md | 16px | Padding del pannello (`p-6` = 24px, invariato — vedi lg), gap tra i campi di una sezione |
| lg | 24px | Padding del pannello "Qualche dettaglio in più" (`p-6`), gap tra blocchi verticali del pannello (livelli → pavimento → stepper → disclaimer → CTA, `flex flex-col gap-4`) |
| xl | 32px | Non usato in questa fase |
| 2xl | 48px | Non usato in questa fase |
| 3xl | 64px | Non usato in questa fase |

Target di tocco: `NumberStepper` è già 44px (`h-11`, bottoni `w-11`) — invariato.
`OptionCard` è `min-h-11` (44px) — invariato, riusato tale e quale per il pavimento.

Exceptions: nessuna.

---

## Typography

Scala ereditata, invariata:

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Body / input / testo controllo | 14px (`text-sm`) | 400 (default) | 1.5 |
| Label domanda / enfasi minore | 14px (`text-sm`) | 500-600 (`font-medium`/`font-semibold`, come da `DomandaField`/`OptionCard` esistenti) | 1.5 |
| Heading di pannello (`h2`, "Qualche dettaglio in più") | 16px (`text-base`) | 600 (`font-semibold`) | 1.2 |
| Fine print / disclaimer / riepilogo collassato | 14px (`text-sm`) | 400 (default) | 1.5, colore `text-muted-foreground` |

Pesi dichiarati: **400 (regular)** e **600 (semibold)** — nessun peso nuovo introdotto
da questa fase. (Il `font-bold`/20px del "Totale generale stimato" è preesistente,
fuori scope, non toccato da questa fase.)

---

## Color

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `--background` `#fbf8f3` | Sfondo pagina `/dettaglio-pro` |
| Secondary (30%) | `--secondary` (pannello) / `--card` `#ffffff` (righe/OptionCard non selezionate) | Contenitore "Qualche dettaglio in più" (`bg-secondary`), `OptionCard` non selezionata (`bg-card`) |
| Accent (10%) | `--primary` `#e8722a` | `OptionCard` selezionata (bordo+ring+badge check) per pavimento — stesso trattamento già in uso per finitura; bottone "Calcola il dettaglio" |
| Destructive | `--destructive` `#e11d22` | Non usato in questa fase — nessuna azione distruttiva nel pannello. (Il colore appariva solo per `VALIDATION_COPY`, rimosso: vedi §A.3) |

Accent reserved for: `OptionCard` selezionata (pavimento e finitura), bottone primario
"Calcola il dettaglio". **Non** va usato per "Salta, usa la stima automatica" (resta
link testuale `text-muted-foreground`), né per lo stato non-selezionato di
`OptionCard`/`NumberStepper` (`border-border`/`bg-card` neutri).

Ambra (`--amber-bg`/`--amber-border`/`--amber-fg`) resta riservata al banner
"Se salti una domanda, usiamo il default…" (copy estesa, §Copywriting) — nessun uso
nuovo del colore, solo copy aggiornata.

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Primary CTA (calcolo) | "Calcola il dettaglio" (invariato) |
| Secondary action | "Salta, usa la stima automatica" (invariato, link testuale) |
| Panel heading | "Qualche dettaglio in più" (invariato — nessuna rinomina; D-06 lo chiama "tipo 'Affina la stima'" come descrizione funzionale, non come copy letterale) |
| Subheading livelli finitura | "Scegli il livello di finitura: cambia i materiali considerati nel computo, non le lavorazioni." (invariato) |
| Nuovo campo — label | `domanda.testo` dal catalogo (dato, non stringa cablata). Valore consigliato per la curatela (D-08/D-04): **"Che pavimento vuoi per casa?"** |
| Nuovo campo — help | `domanda.help` dal catalogo. Valore consigliato: **"Vale per le zone giorno e notte. Il bagno resta sempre in gres o rivestimento, non cambia con questa scelta."** — visibile sempre sotto la label (stesso trattamento di `DomandaField`), non solo come tooltip, perché è il punto più a rischio di incomprensione della fase (D-02) |
| Subheading stepper | "Rispondi per affinare le quantità stimate (facoltativo: se salti, usiamo una stima prudente in base ai metri quadri)." (invariato, `DOMANDE_SUBHEADING`) |
| Disclaimer default (banner ambra) | Estesa da "Se salti una domanda, usiamo una stima prudente basata sui metri quadri dell'immobile." a: **"Se salti una domanda, usiamo i default: finitura media, pavimento gres, quantità stimate sui metri quadri."** — perché ora ci sono default anche su finitura/pavimento, non solo sulle quantità (D-07) |
| Riepilogo collassato | Estende la riga esistente aggiungendo il pavimento: **"Bagni: {n} · Porte: {n} · Climatizzatori: {n} · Pavimento: {nome opzione scelta}"**, seguita a capo (invariato) dalla riga `riepilogoLivelli` con le finiture per categoria |
| Error state (calcolo) | "Non siamo riusciti a calcolare il dettaglio. Controlla i dati e riprova." (invariato, `CALC_ERROR_COPY`) |
| Error state (PDF) | "Non siamo riusciti a generare il PDF. Riprova tra qualche istante." (invariato, `PDF_ERROR_COPY`) |
| Validazione numerica (`VALIDATION_COPY`) | **Rimossa.** `NumberStepper` rende strutturalmente impossibile un valore non valido (clamp a `min`, mai stato vuoto — vedi la docstring del componente): l'errore "Inserisci un numero valido" non può più verificarsi, quindi non deve più esistere come stato UI. Rimuovere `isValid()`/`validationError` insieme al passaggio da `Input` a `NumberStepper` |
| Destructive confirmation | Nessuna: il pannello non ha azioni distruttive |

---

## Registry Safety

`components.json` ha `"registries": {}` — nessun registry di terze parti, nessun nuovo
componente shadcn installato in questa fase.

| Registry | Blocks Used | Safety Gate |
|----------|-------------|--------------|
| shadcn official | accordion, alert, button, label, skeleton (tutti già installati, invariati) | not required |
| custom (progetto) | `NumberStepper`, `OptionCard`, `DomandaField` (già esistenti, riusati) | not applicable — non è un registry esterno |

---

## §A — Pannello "Qualche dettaglio in più": composizione estesa

### A.1 — Fonte dei campi: dal catalogo, non più cablati (CFG-01, QST-05)

Le domande Pro migrano nello stesso catalogo del Free (D-01/CONTEXT): `finitura`
(scelta_singola, già gestita ad-hoc dal selettore per-categoria esistente — **invariato,
nessun cambio visivo**, si generalizza da solo quando il backend attiva più livelli per
categoria), `tipo_pavimento` (scelta_singola, **nuova**) e i tre stepper `bagni` /
`porte` / `condizionatori` (**migrano da `RisposteInput`/`FIELD_LABELS` cablati a
`DomandaField`**, come già avviene nel wizard).

Questo non è solo refactor interno: cambia il contratto visivo in un punto preciso —
**la label del campo non è più la stringa `FIELD_LABELS[field]` cablata in
`DettaglioProView.tsx`, ma `domanda.testo`** servito da `GET /api/v1/domande?tier=pro`
(o equivalente scoped al dettaglio Pro). Il componente che disegna questi tre campi
diventa `DomandaField`, esattamente come nello step 3/4 del wizard — stesso controllo
(`isNumerico` → `NumberStepper`), stessa forma visiva, stesso `aria-label`.

Il selettore pavimento usa lo stesso `DomandaField` con `tipo_controllo="scelta_singola"`
→ renderizza `OptionCard` in griglia.

### A.2 — Selettore "tipo di pavimento": griglia a 2 colonne fissa

**Eccezione dichiarata** alla regola generica di `DomandaField`
(`opzioni.length === 2 ? "sm:grid-cols-2" : "sm:grid-cols-3"`): con **4** opzioni
(gres / parquet / maxi lastra / mosaico) e il pannello contenuto in un layout largo al
massimo 640px (`sm:max-w-[640px]` di `DettaglioProPage`), `sm:grid-cols-3` produrrebbe
una quarta card isolata su una riga propria, sbilanciata. Usare invece:

```
grid grid-cols-2 gap-3
```

2×2 fissa a ogni breakpoint (non solo `sm:`) — le etichette sono brevi ("Gres", "Parquet",
"Maxi lastra", "Mosaico"), quindi 2 colonne restano leggibili anche su schermi stretti.
Ogni `OptionCard` mostra `nome` (etichetta opzione) + `descrizione` se presente
(es. "Piastrelle in gres porcellanato" sotto "Gres") — stessa forma di `OptionCard`
esistente, **nessuna immagine**: `opzione.immagine_url` esiste nello schema (08.1) ma
questa fase non la consuma — variante testo-solo, coerente con l'uso attuale di
`OptionCard` nel wizard (nessun campo del wizard mostra immagini oggi). Se in futuro le
foto aiutano a distinguere le pose, è un'estensione separata, non un requisito di questa
fase.

### A.3 — Stepper: da `Input` grezzo a `NumberStepper`

Sostituzione diretta, stessa posizione nel layout (uno per riga, `Label` sopra,
controllo sotto, `flex flex-col gap-1` per riga → invariato). Cambia:

- Il controllo: `<Input inputMode="numeric" min={0} ...>` → `<NumberStepper min={0}
  max={99} value={...} onChange={...} aria-label={domanda.testo}>`. `max={99}` è un
  default ragionevole per conteggi di bagni/porte/climatizzatori (nessun limite di
  dominio noto più stringente dal backend); se il catalogo porta un vincolo esplicito
  per queste tre domande, quello vince.
- Lo stato di errore: **eliminato** (vedi Copywriting Contract). Il bottone "Calcola il
  dettaglio" perde la condizione `disabled={... || validationError}` legata alla
  validazione testuale — resta `disabled={risposteMutation.isPending}`.

### A.4 — Ordine verticale del pannello (quando espanso)

1. Selettori finitura per categoria (esistenti, invariati — `OptionCard`-equivalenti
   inline già presenti in `DettaglioProView`)
2. **Nuovo:** selettore "tipo di pavimento" (§A.2)
3. I tre `NumberStepper` bagni/porte/condizionatori (§A.3), in quest'ordine — invariato
   rispetto a oggi
4. Banner ambra con la copy estesa (§Copywriting)
5. Riga CTA: "Calcola il dettaglio" (primario) + "Salta, usa la stima automatica" (link)

Gap verticale tra i cinque blocchi: `gap-4` (16px), invariato dal contenitore esistente.

### A.5 — Stato collassato

Dopo il calcolo, il riepilogo (§Copywriting → "Riepilogo collassato") aggiunge il
pavimento scelto sulla stessa riga di bagni/porte/climatizzatori, mantenendo
`riepilogoLivelli` (finiture per categoria) come seconda riga sottostante, esattamente
come oggi. Il bottone "Modifica" (link testuale, invariato) riapre tutti i campi,
pavimento incluso.

### A.6 — Cosa NON cambia in questa fase

- `SottocategoriaAccordion` e il rendering delle voci/quantità/range: nessuna modifica
  visiva. CFG-02 (una sola famiglia di alternative per sottocategoria) è un vincolo sul
  *conteggio* delle voci che il motore restituisce, non sulla presentazione — meno voci
  alternative nello stesso accordion, stesso componente.
- Il blocco "Totale generale stimato" e il bottone "Scarica PDF dettagliato": invariati.
- `BonusPanel`/`ArredoCard` sotto il pannello: invariati, fuori scope.

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending
