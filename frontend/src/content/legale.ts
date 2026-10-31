/**
 * Testi legali del sito: informativa privacy, cookie policy, condizioni di
 * vendita del Pro. Li mostra `pages/PaginaLegalePage.tsx`.
 *
 * Mini-sintassi dei testi:
 *   {{campo}}          un campo di `DATI_LEGALI` (es. {{titolare}}); se manca,
 *                      la pagina mostra "[da completare]" evidenziato;
 *   [testo](/percorso) un link;
 *   **testo**          grassetto.
 *
 * I testi descrivono i trattamenti che il codice fa DAVVERO (account, stime,
 * richieste di contatto, pagamenti Stripe, cookie tecnici). Se il sito
 * aggiunge un trattamento (analytics, newsletter, pubblicita'), questi testi
 * vanno aggiornati nello stesso cambio. Bozza da far verificare a un legale.
 */

export type Blocco =
  | { tipo: "p"; testo: string }
  | { tipo: "lista"; voci: string[] }
  | { tipo: "tabella"; colonne: string[]; righe: string[][] }
  | { tipo: "box"; testo: string };

export interface Sezione {
  titolo: string;
  blocchi: Blocco[];
}

export interface DocumentoLegale {
  path: string;
  titolo: string;
  descrizione: string;
  introduzione: string;
  sezioni: Sezione[];
}

const p = (testo: string): Blocco => ({ tipo: "p", testo });
const lista = (...voci: string[]): Blocco => ({ tipo: "lista", voci });
const box = (testo: string): Blocco => ({ tipo: "box", testo });
const tabella = (colonne: string[], ...righe: string[][]): Blocco => ({ tipo: "tabella", colonne, righe });

export const PATH_PRIVACY = "/privacy";
export const PATH_COOKIE = "/cookie";
export const PATH_CONDIZIONI = "/condizioni-di-vendita";

// --- Informativa privacy -------------------------------------------------------

export const PRIVACY: DocumentoLegale = {
  path: PATH_PRIVACY,
  titolo: "Informativa privacy",
  descrizione:
    "Come Renovio tratta i dati personali di chi usa il sito: quali dati, perché, per quanto tempo, con chi li condivide e quali diritti hai.",
  introduzione:
    "Questa informativa spiega come trattiamo i tuoi dati personali quando usi Renovio: il sito, la stima gratuita, l'account, la richiesta di contatto con un professionista e l'abbonamento Pro. È scritta ai sensi del Regolamento (UE) 2016/679 (GDPR) e del D.lgs. 196/2003.",
  sezioni: [
    {
      titolo: "1. Chi è il titolare del trattamento",
      blocchi: [
        p("Il titolare del trattamento è **{{titolare}}**, con sede in {{sede}}, P. IVA {{partitaIva}}."),
        p("Per qualsiasi domanda sui tuoi dati scrivi a **{{email}}**."),
        p(
          "Non abbiamo nominato un Responsabile della protezione dei dati (DPO): non ricorrono i presupposti dell'art. 37 GDPR, perché non trattiamo su larga scala categorie particolari di dati né monitoriamo le persone in modo sistematico.",
        ),
      ],
    },
    {
      titolo: "2. Quali dati trattiamo",
      blocchi: [
        p("Trattiamo solo i dati che servono a farti usare il servizio:"),
        lista(
          "**Dati dell'account**: nome, email, password (conservata solo in forma cifrata e non reversibile) oppure, se accedi con Google, nome, email e foto del profilo che Google ci condivide. Facoltativi: cognome, telefono, città, foto del profilo.",
          "**Dati delle stime**: città, metri quadri, tipo di ristrutturazione, risposte alle domande sulla casa e sui lavori, budget indicato, risultati della stima. Non chiediamo indirizzi, planimetrie né documenti dell'immobile.",
          "**Dati della richiesta di contatto** con un professionista: nome, email, telefono (facoltativo), come e quando preferisci essere contattato, eventuale messaggio, e il riepilogo della stima a cui si riferisce la richiesta.",
          "**Dati dell'abbonamento Pro**: piano scelto, stato e scadenza dell'abbonamento, identificativi del cliente e dell'abbonamento presso Stripe. **I dati della carta li tratta solo Stripe**: noi non li vediamo e non li conserviamo.",
          "**Dati tecnici**: indirizzo IP, browser e orari di accesso nei log dei server, il cookie di sessione che ti tiene connesso.",
        ),
        p(
          "Non usiamo strumenti di analisi del traffico, pubblicità mirata o profilazione, e non vendiamo i tuoi dati a nessuno.",
        ),
      ],
    },
    {
      titolo: "3. Perché li trattiamo, su quale base e per quanto tempo",
      blocchi: [
        tabella(
          ["Finalità", "Dati", "Base giuridica", "Conservazione"],
          [
            "Creare e gestire il tuo account",
            "Dati dell'account",
            "Esecuzione del contratto (art. 6.1.b GDPR)",
            "Finché hai l'account; poi cancellati entro 30 giorni",
          ],
          [
            "Calcolare, salvare e scaricare in PDF le stime",
            "Dati delle stime",
            "Esecuzione del contratto (art. 6.1.b)",
            "Finché hai l'account o finché non elimini la stima",
          ],
          [
            "Metterti in contatto con un professionista della tua zona, su tua richiesta",
            "Dati della richiesta di contatto",
            "Misure precontrattuali richieste da te (art. 6.1.b)",
            "24 mesi dalla richiesta",
          ],
          [
            "Vendere e gestire l'abbonamento Pro",
            "Dati dell'account e dell'abbonamento",
            "Esecuzione del contratto (art. 6.1.b)",
            "Per la durata dell'abbonamento",
          ],
          [
            "Adempimenti fiscali e contabili sui pagamenti",
            "Dati dell'abbonamento, importi, date",
            "Obbligo di legge (art. 6.1.c)",
            "10 anni",
          ],
          [
            "Email di servizio (conferme, reset della password, ricevute)",
            "Email, nome",
            "Esecuzione del contratto (art. 6.1.b)",
            "Come i dati dell'account",
          ],
          [
            "Sicurezza del servizio e prevenzione degli abusi",
            "Dati tecnici",
            "Legittimo interesse (art. 6.1.f) a proteggere il servizio e gli utenti",
            "Log dei server: al massimo 12 mesi",
          ],
          [
            "Difendere i nostri diritti in caso di contestazioni",
            "I dati pertinenti alla contestazione",
            "Legittimo interesse (art. 6.1.f)",
            "Fino alla prescrizione dei diritti",
          ],
        ),
        box(
          "**Conferire i dati è necessario** per creare l'account, salvare le stime, ricevere il contatto e acquistare il Pro: senza questi dati non possiamo fornirti il servizio. La stima gratuita senza account non richiede dati personali, a parte i dati tecnici.",
        ),
      ],
    },
    {
      titolo: "4. Con chi condividiamo i dati",
      blocchi: [
        p(
          "**Professionisti della tua zona.** Solo se chiedi tu di essere contattato, inviamo la tua richiesta (nome, email, telefono se indicato, preferenze di contatto, messaggio e riepilogo della stima) al professionista che segue la tua città. Il professionista tratta questi dati come titolare autonomo, per risponderti e prepararti un preventivo. Il suo nominativo è disponibile su richiesta a {{email}}.",
        ),
        p("**Fornitori che lavorano per nostro conto**, nominati responsabili del trattamento (art. 28 GDPR):"),
        lista(
          "Render Services, Inc.: hosting del backend e del database ({{regioneHosting}});",
          "Vercel Inc.: pubblicazione del sito web;",
          "{{fornitoreEmail}}: invio delle email di servizio;",
          "Google Ireland Limited / Google LLC: accesso con Google, solo se lo scegli.",
        ),
        p(
          "**Stripe Payments Europe, Ltd.** (Irlanda) gestisce i pagamenti del Pro come titolare autonomo, secondo la [sua informativa](https://stripe.com/it/privacy).",
        ),
        p(
          "Possiamo comunicare dati alle autorità solo quando la legge lo impone (per esempio alle autorità fiscali o giudiziarie).",
        ),
        box(
          "**Trasferimenti fuori dallo Spazio economico europeo.** Alcuni fornitori (Render, Vercel, Google) hanno sede negli Stati Uniti. I trasferimenti avvengono sulla base del Data Privacy Framework UE-USA, per i fornitori aderenti, o delle Clausole contrattuali standard approvate dalla Commissione europea (artt. 45-46 GDPR).",
        ),
      ],
    },
    {
      titolo: "5. Cookie",
      blocchi: [
        p(
          "Usiamo solo cookie tecnici, necessari a farti restare connesso: per questo non ti chiediamo il consenso e non vedi un banner. I dettagli sono nella [cookie policy](/cookie).",
        ),
      ],
    },
    {
      titolo: "6. Minori",
      blocchi: [
        p(
          "Il servizio non è pensato per chi ha meno di 18 anni e non raccogliamo consapevolmente dati di minori. Se pensi che un minore ci abbia dato i suoi dati, scrivici e li cancelliamo.",
        ),
      ],
    },
    {
      titolo: "7. Sicurezza",
      blocchi: [
        p(
          "Proteggiamo i dati con misure tecniche e organizzative adeguate: connessioni cifrate (HTTPS), password conservate solo in forma cifrata e non reversibile, accessi riservati al personale autorizzato. Nessuna trasmissione via Internet è sicura al cento per cento, ma facciamo il possibile per proteggere i tuoi dati.",
        ),
      ],
    },
    {
      titolo: "8. I tuoi diritti",
      blocchi: [
        p("In qualsiasi momento puoi chiederci di:"),
        lista(
          "**accedere** ai tuoi dati e averne una copia (art. 15 GDPR);",
          "**correggerli** se sono inesatti (art. 16); i dati del profilo li puoi modificare anche da Impostazioni → Profilo;",
          "**cancellarli** (art. 17), salvo i dati che la legge ci obbliga a conservare;",
          "**limitarne** il trattamento (art. 18);",
          "**riceverli** in un formato strutturato per trasferirli ad altri (art. 20);",
          "**opporti** al trattamento basato sul nostro legittimo interesse (art. 21).",
        ),
        p(
          "Per esercitare i tuoi diritti scrivi a **{{email}}**. Rispondiamo entro un mese. Potremmo chiederti qualche informazione per verificare la tua identità.",
        ),
        p(
          "Non prendiamo decisioni basate unicamente su trattamenti automatizzati che producano effetti giuridici su di te (art. 22 GDPR): la stima è un calcolo indicativo, non una decisione che ti riguarda.",
        ),
      ],
    },
    {
      titolo: "9. Reclamo al Garante",
      blocchi: [
        p(
          "Se ritieni che il trattamento dei tuoi dati violi la normativa, puoi proporre reclamo al Garante per la protezione dei dati personali, Piazza Venezia 11, 00187 Roma, [www.garanteprivacy.it](https://www.garanteprivacy.it).",
        ),
      ],
    },
    {
      titolo: "10. Modifiche",
      blocchi: [
        p(
          "Possiamo aggiornare questa informativa, per esempio se aggiungiamo funzioni o fornitori. La data dell'ultimo aggiornamento è in cima alla pagina; se le modifiche sono importanti te lo diciamo via email.",
        ),
      ],
    },
  ],
};

// --- Cookie policy ---------------------------------------------------------------

export const COOKIE: DocumentoLegale = {
  path: PATH_COOKIE,
  titolo: "Cookie policy",
  descrizione: "Quali cookie usa Renovio: solo cookie tecnici, necessari a tenerti connesso.",
  introduzione:
    "I cookie sono piccoli file di testo che un sito salva nel tuo browser. Renovio usa solo cookie tecnici, indispensabili per farti accedere al tuo account: per questi la legge non richiede il consenso (art. 122 del Codice privacy e Linee guida del Garante del 10 giugno 2021).",
  sezioni: [
    {
      titolo: "Cookie che usiamo",
      blocchi: [
        tabella(
          ["Nome", "A cosa serve", "Tipo", "Durata"],
          ["session_id", "Ti tiene connesso al tuo account dopo l'accesso.", "Tecnico, nostro", "30 giorni o fino all'uscita"],
          ["session", "Solo durante l'accesso con Google: protegge il passaggio da Google al nostro sito.", "Tecnico, nostro", "Fine della sessione del browser"],
        ),
        p("Non usiamo cookie di analisi, di profilazione o pubblicitari, né nostri né di terze parti."),
      ],
    },
    {
      titolo: "Pagamenti",
      blocchi: [
        p(
          "Quando acquisti il Pro vai sulla pagina di pagamento di Stripe, che è su un dominio di Stripe e usa i propri cookie, anche per prevenire le frodi. Sono regolati dalla [cookie policy di Stripe](https://stripe.com/it/legal/cookies-policy).",
        ),
      ],
    },
    {
      titolo: "Come gestire i cookie",
      blocchi: [
        p(
          "Puoi cancellare o bloccare i cookie dalle impostazioni del browser. Se blocchi il cookie di sessione non potrai accedere al tuo account; la stima gratuita continua a funzionare.",
        ),
        p("Per tutto il resto vale l'[informativa privacy](/privacy)."),
      ],
    },
  ],
};

// --- Condizioni di vendita ---------------------------------------------------------

export const CONDIZIONI: DocumentoLegale = {
  path: PATH_CONDIZIONI,
  titolo: "Condizioni di vendita di Renovio Pro",
  descrizione:
    "Prezzi, rinnovo, disdetta e diritto di recesso dell'abbonamento Renovio Pro, mensile o annuale.",
  introduzione:
    "Queste condizioni regolano l'acquisto dell'abbonamento Renovio Pro da parte dei consumatori. Valgono insieme al Codice del Consumo (D.lgs. 206/2005), che resta applicabile per tutto quanto non è scritto qui.",
  sezioni: [
    {
      titolo: "1. Chi vende",
      blocchi: [
        p(
          "Renovio Pro è venduto da **{{titolare}}**, con sede in {{sede}}, P. IVA {{partitaIva}}, email {{email}}, PEC {{pec}}.",
        ),
      ],
    },
    {
      titolo: "2. Cosa compri",
      blocchi: [
        p("Renovio Pro è un servizio digitale in abbonamento. Aggiunge alla stima gratuita:"),
        lista(
          "il dettaglio del computo voce per voce, con quantità e importi stimati;",
          "la configurazione di finiture, pavimenti e lavori particolari della tua casa;",
          "il PDF dettagliato di ogni stima.",
        ),
        box(
          "Le stime di Renovio, gratuite e Pro, sono **indicative e pre-sopralluogo**: sono calcolate su listini di riferimento e sui dati che inserisci tu. **Non sono un preventivo**, non sono un'offerta di esecuzione dei lavori e non sostituiscono il sopralluogo né il computo di un tecnico. Il costo reale dipende dallo stato dell'immobile, dai materiali e dall'impresa.",
        ),
      ],
    },
    {
      titolo: "3. Prezzi",
      blocchi: [
        tabella(
          ["Piano", "Prezzo", "Rinnovo"],
          ["Mensile", "3 € al mese", "Ogni mese"],
          ["Annuale", "29 € all'anno", "Ogni anno"],
        ),
        p(
          "I prezzi sono in euro e **comprendono l'IVA**. Vale il prezzo mostrato nella pagina [Passa a Pro](/passa-a-pro) al momento dell'acquisto. Se cambiamo il prezzo per i rinnovi, ti avvisiamo via email almeno 30 giorni prima: puoi disdire prima che si applichi.",
        ),
      ],
    },
    {
      titolo: "4. Come si acquista",
      blocchi: [
        lista(
          "Accedi al tuo account, scegli il piano e accetta queste condizioni.",
          "Paghi sulla pagina di **Stripe**, il nostro fornitore di pagamenti, con carta, Apple Pay o Google Pay. Noi non vediamo i dati della tua carta.",
          "Il contratto è concluso quando il pagamento va a buon fine. Il Pro si attiva subito e ricevi una email di conferma con il riepilogo dell'acquisto e queste condizioni.",
        ),
      ],
    },
    {
      titolo: "5. Rinnovo automatico e disdetta",
      blocchi: [
        lista(
          "L'abbonamento **si rinnova automaticamente** alla fine di ogni periodo, con addebito sullo stesso metodo di pagamento.",
          "Puoi **disdire in qualsiasi momento**, senza penali, da Impostazioni → Abbonamento → «Gestisci abbonamento». Il Pro resta attivo fino alla fine del periodo già pagato e poi non si rinnova.",
          "Prima del rinnovo dell'abbonamento annuale ti mandiamo un promemoria via email.",
          "Se un pagamento di rinnovo non va a buon fine riproviamo per alcuni giorni; se non riesce, l'abbonamento si chiude e l'account torna gratuito, senza perdere le stime salvate.",
        ),
      ],
    },
    {
      titolo: "6. Diritto di recesso: 14 giorni",
      blocchi: [
        p(
          "Puoi **recedere entro 14 giorni** dall'acquisto, senza dare spiegazioni, con il pulsante «Recedi dal contratto qui» in Impostazioni → Abbonamento, oppure scrivendo a {{email}} o alla PEC {{pec}}.",
        ),
        p(
          "Se recedi, ti **rimborsiamo l'intero importo pagato** entro 14 giorni dalla tua richiesta, sullo stesso metodo di pagamento, e il Pro si disattiva subito. Ti confermiamo il recesso via email.",
        ),
        p(
          "Il diritto di recesso vale per il primo acquisto; per i rinnovi successivi puoi sempre disdire come al punto 5.",
        ),
      ],
    },
    {
      titolo: "7. Garanzia di conformità",
      blocchi: [
        p(
          "Il servizio è coperto dalla garanzia legale di conformità dei servizi digitali (Codice del Consumo, artt. 135-octies e seguenti). Se il Pro non funziona come descritto, scrivici a {{email}}: lo ripristiniamo e, se non è possibile, hai diritto a una riduzione del prezzo o alla risoluzione del contratto con rimborso.",
        ),
      ],
    },
    {
      titolo: "8. Uso del servizio e responsabilità",
      blocchi: [
        lista(
          "L'account è personale. Puoi condividere stime e PDF con i tuoi tecnici e le imprese, ma non rivendere i contenuti del servizio né estrarli in modo automatico.",
          "Le stime dipendono dai dati inseriti e dai listini di riferimento: non garantiamo che coincidano con i preventivi delle imprese.",
          "Nei limiti consentiti dalla legge non rispondiamo delle decisioni prese soltanto sulla base delle stime. Restano ferme la responsabilità per dolo o colpa grave e quelle che la legge non permette di escludere verso il consumatore.",
        ),
      ],
    },
    {
      titolo: "9. Dati personali",
      blocchi: [
        p(
          "Trattiamo i tuoi dati secondo l'[informativa privacy](/privacy). I pagamenti li gestisce Stripe come titolare autonomo.",
        ),
      ],
    },
    {
      titolo: "10. Modifiche",
      blocchi: [
        p(
          "Possiamo aggiornare queste condizioni. Le modifiche che ti riguardano te le comunichiamo via email almeno 30 giorni prima e valgono dal rinnovo successivo: se non le accetti, puoi disdire prima.",
        ),
      ],
    },
    {
      titolo: "11. Reclami e controversie",
      blocchi: [
        lista(
          "Assistenza e reclami: {{email}}. Rispondiamo entro 7 giorni lavorativi.",
          "Il contratto è regolato dalla legge italiana. Per le controversie è competente il giudice del luogo di residenza o di domicilio del consumatore.",
          "Puoi anche rivolgerti a un organismo di risoluzione alternativa delle controversie (ADR) iscritto negli elenchi previsti dal Codice del Consumo.",
        ),
      ],
    },
  ],
};

export const DOCUMENTI_LEGALI: DocumentoLegale[] = [PRIVACY, COOKIE, CONDIZIONI];
