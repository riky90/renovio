# Brief di discussione — App stima ristrutturazioni

_Data: 2026-08-24 · Fonte: `2025_Computo Base_ER_PREZZI IMPRESE DEFINITI (2).xlsx`_

## Visione
App web dove l'utente (registrandosi con email o Google) inserisce **città + mq appartamento + tipo di ristrutturazione (leggera / moderata / totale)** e riceve una **stima dei costi** divisa per le 4 categorie **Edile, Finiture, Serramenti/Porte, Prodotti**. Con abbonamento **Pro** ottiene il dettaglio per sottocategorie (a.1/a.2…). In ogni caso può **contattare un professionista** per il preventivo dettagliato. Il risultato è **scaricabile in PDF a ogni livello**.

## Come è fatto il file sorgente (analisi)
- `Analisi preliminareTOTALI` = preventivo cliente: dati cliente + 4 totali categoria con **IVA differenziata** (Edile 10%, Finiture 22%, Serramenti, Prodotti 10%), costi extra (CSE/CSP, pratiche), finanziamento a rate.
- `A-EDILE` = **105 codici** (A.1.1 … A.6.11), ~116 voci → è il livello "Pro / sottocategorie".
- `B-FINITURE` (~57 voci), `C-SERRAMENTI PORTE` (~16), `D-PRODOTTI` (~11).
- `listini` = coefficienti impresa **0.65 / 0.6 / 0.55 / 0.5**.
- Motore prezzo per riga: `Prezzo Unitario (F) × Quantità (E)`.
  - **Prezzo cliente** (col G) = prezzo pieno → mostrato all'utente.
  - **Prezzo impresa** (col L) = prezzo × coeff. (0.65…) → costo interno, MAI mostrato.
- Le **quantità** oggi sono inserite a mano da un tecnico dopo sopralluogo. I prezzi del file sono di **Reggio Emilia**.

## Nodo centrale del prodotto
Il file è **bottom-up** (quantità esatte inserite dal tecnico); l'app è **top-down** (solo mq + tipo). Serve un **modello parametrico** che da `(mq, tipo)` stimi le quantità/costi. Questo motore di coefficienti è l'IP dell'app.

## Decisioni prese

### 1. Motore di stima — Ibrido C
- **Free**: costo €/m² sulle 4 categorie.
- **Pro**: quantità parametriche vere sulle **voci-chiave** (l'80% del costo sta in ~20% delle voci).
- **Output sempre a range** (es. €28k–34k) — protezione legale pre-sopralluogo.
- L'utente vede **solo il prezzo cliente**; il coeff. impresa resta interno.
- I coefficienti vengono estratti dal file come bozza, poi tarati dall'utente.

### 2. Città e dati
- La **città seleziona il listino** (prezzi in DB, non nel codice). RE è il primo listino.
- Città senza listino → **fallback con disclaimer** esplicito ("stima su listino RE, non ancora tarata su <città>").
- Roadmap: moltiplicatori prezzo per zona = **fase 2**.

### 3. Backend admin (pilastro fondante)
Pannello dove l'admin gestisce **senza toccare codice**: listini/prezzi per città, coefficiente impresa, coefficienti parametrici del modello (€/m² e quantità-per-m² per tipo), mappatura città→listino, tipi ristrutturazione, referenti, testi/disclaimer.

### 4. Free vs Pro
| | Free | Pro (prezzo da definire) |
|---|---|---|
| Output | 4 totali categoria + IVA, a range | + sottocategorie a.1/a.2 + voci + quantità stimate |
| PDF | sintetico | dettagliato |
| Contatto pro | **aperto a tutti** | aperto a tutti |

### 5. Lead & professionisti
- Lead → **email + dashboard admin**.
- Modello dati **multi-referente per città dal giorno 1**; v1 parte con l'utente come **unico referente**. La rete completa di professionisti (portale partner, assegnazione) è visione futura.
- Meccanica esatta "referenti per città" (a chi arriva la mail / cosa vede l'utente) = da definire.

### 6. Costi & IVA
- Includere i **4 lavori + IVA differenziata** come nel file.
- **Extra sì** (CSE/CSP, pratiche) nel totale.
- **Finanziamento a rate: no** in v1.

### 7. Piattaforma
- Auth: email + Google (provider gestito).
- PDF: generato server-side, con brand, scaricabile a ogni livello.

## Da definire più avanti (non perse)
- Prezzo abbonamento Pro.
- Moltiplicatori prezzo per zona (fase 2).
- Meccanica referenti per città.
- Portale rete professionisti (visione futura).
- Quali voci esatte sono le "voci-chiave" del Pro.
