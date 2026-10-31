# Statistiche e pubblicità: Google Analytics 4, Google Ads, Meta Pixel

Il codice è pronto (`frontend/src/lib/tracciamento.ts`). Finché su Vercel non ci sono gli ID,
il sito non carica niente e il banner dei cookie non compare.

## Come funziona

- **Banner dei cookie**: CookieConsent (MIT), ospitato nel sito, gratuito e senza limiti.
  - "Accetta tutto" e "Rifiuta" hanno lo stesso peso; la X chiude rifiutando.
  - Con "Scegli" si decide per categoria: **Statistiche** (GA4) e **Marketing** (Google Ads e
    Meta).
  - Il consenso si richiede dopo 6 mesi.
  - "Preferenze cookie" nel footer riapre le scelte; una revoca cancella i cookie e ricarica la
    pagina.
- **Niente prima del consenso**: gli script di Google e Meta si caricano solo dopo "Accetta".
  Google riceve il Consent Mode v2 (tutto negato di default, poi aggiornato).
- **Eventi misurati**:

  | Evento | GA4 | Google Ads | Meta |
  |---|---|---|---|
  | Pagina vista (a ogni cambio di pagina) | `page_view` | — | `PageView` |
  | Stima completata | `stima_completata` | — | `StimaCompletata` (personalizzato) |
  | Registrazione con email | `sign_up` | — | `CompleteRegistration` |
  | Richiesta di contatto a un professionista | `generate_lead` | conversione "contatto" | `Lead` |
  | Acquisto del Pro | `purchase` (valore, valuta, piano) | conversione "acquisto" | `Subscribe` |

## Passi

### Google Analytics 4
1. In [analytics.google.com](https://analytics.google.com) crea una proprietà "Renovio", con lo
   stream web sul dominio del sito.
2. Copia l'**ID di misurazione** (`G-XXXXXXX`).
3. In Amministrazione → Raccolta e conservazione dei dati imposta la **conservazione a 14 mesi**,
   come dice la cookie policy.
4. In Eventi segna come **eventi chiave** `generate_lead` e `purchase`, e se vuoi anche
   `sign_up` e `stima_completata`.

### Google Ads (quando parte la prima campagna)
1. In Obiettivi → Conversioni crea due azioni di conversione "Sito web", con il tag configurato
   manualmente:
   - "Contatto professionista";
   - "Acquisto Pro", con valore.
2. Dal tag copia l'**ID** (`AW-XXXXXXXXX`) e le due **etichette** (la parte dopo `/`).

### Meta Pixel (quando parte la prima campagna)
1. In Meta Business Suite → Gestione eventi crea un **pixel** e copia l'ID numerico.
2. Non serve installare nient'altro: gli eventi li manda il sito.

### Variabili su Vercel (progetto frontend, Production)

| Variabile | Valore |
|---|---|
| `VITE_GA4_ID` | `G-XXXXXXX` |
| `VITE_GOOGLE_ADS_ID` | `AW-XXXXXXXXX` |
| `VITE_GOOGLE_ADS_LABEL_CONTATTO` | etichetta della conversione "contatto" |
| `VITE_GOOGLE_ADS_LABEL_ACQUISTO` | etichetta della conversione "acquisto" |
| `VITE_META_PIXEL_ID` | ID del pixel |

Le variabili entrano nella build: dopo averle impostate serve un nuovo deploy (Redeploy).
Puoi accendere solo GA4 adesso e aggiungere Ads e Meta più avanti. Il banner mostra solo le
categorie con almeno uno strumento configurato.

## Verifica
1. Apri il sito in una finestra anonima: deve comparire il banner. In Strumenti per sviluppatori
   → Rete non deve esserci nessuna richiesta a `googletagmanager.com` o `facebook.net`.
2. Premi "Accetta tutto": partono le richieste.
   - In GA4, Rapporti → Tempo reale mostra la visita.
   - L'estensione "Meta Pixel Helper" vede il pixel.
3. Footer → "Preferenze cookie" → "Rifiuta tutto": la pagina si ricarica e i cookie `_ga`,
   `_gcl_au` e `_fbp` spariscono.
