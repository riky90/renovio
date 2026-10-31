/**
 * Statistiche e pubblicità: Google Analytics 4, Google Ads, Meta Pixel, con il
 * banner dei cookie (CookieConsent, MIT, ospitato nel sito: niente account
 * esterni né limiti di visite).
 *
 * REGOLE
 * - Niente parte prima del consenso: gli script di Google e Meta si caricano
 *   solo dopo che l'utente ha accettato la categoria che li riguarda
 *   ("statistiche" per GA4, "marketing" per Ads e Meta). È il modo più
 *   prudente rispetto alle linee guida del Garante (10 giugno 2021).
 * - Banner conforme: "Accetta tutto" e "Rifiuta" con lo stesso peso, la X
 *   chiude rifiutando, preferenze per categoria, nuova richiesta dopo 6 mesi.
 *   Le preferenze si riaprono dal footer ("Preferenze cookie").
 * - Gli ID arrivano dalle variabili d'ambiente di Vercel. Se mancano tutti,
 *   il banner non compare e non si carica nulla: il sito resta come prima,
 *   con i soli cookie tecnici.
 * - Revocare un consenso cancella i cookie della categoria e ricarica la
 *   pagina, così lo script già caricato non resta attivo.
 *
 * Tutto è lato browser: niente qui gira nel prerender.
 */

const GA4_ID = (import.meta.env.VITE_GA4_ID as string | undefined)?.trim() || null;
const ADS_ID = (import.meta.env.VITE_GOOGLE_ADS_ID as string | undefined)?.trim() || null;
const ADS_LABEL_CONTATTO = (import.meta.env.VITE_GOOGLE_ADS_LABEL_CONTATTO as string | undefined)?.trim() || null;
const ADS_LABEL_ACQUISTO = (import.meta.env.VITE_GOOGLE_ADS_LABEL_ACQUISTO as string | undefined)?.trim() || null;
const META_PIXEL_ID = (import.meta.env.VITE_META_PIXEL_ID as string | undefined)?.trim() || null;

const CAT_STATISTICHE = "statistiche";
const CAT_MARKETING = "marketing";

type Gtag = (...args: unknown[]) => void;
type Fbq = ((...args: unknown[]) => void) & { callMethod?: unknown; queue?: unknown[]; loaded?: boolean; version?: string; push?: unknown };

declare global {
  interface Window {
    dataLayer?: unknown[];
    gtag?: Gtag;
    fbq?: Fbq;
    _fbq?: Fbq;
  }
}

let statisticheAttive = false;
let marketingAttivo = false;

export function tracciamentoConfigurato(): boolean {
  return Boolean(GA4_ID || ADS_ID || META_PIXEL_ID);
}

function caricaScript(src: string): void {
  if (document.querySelector(`script[src="${src}"]`)) return;
  const s = document.createElement("script");
  s.async = true;
  s.src = src;
  document.head.appendChild(s);
}

function preparaGtag(): Gtag {
  if (!window.gtag) {
    window.dataLayer = window.dataLayer || [];
    window.gtag = function gtag() {
      // gtag vuole proprio l'oggetto `arguments`.
      // eslint-disable-next-line prefer-rest-params
      window.dataLayer!.push(arguments);
    };
    window.gtag("consent", "default", {
      analytics_storage: "denied",
      ad_storage: "denied",
      ad_user_data: "denied",
      ad_personalization: "denied",
    });
    window.gtag("js", new Date());
  }
  return window.gtag;
}

function avviaGoogle(): void {
  const idPrincipale = (statisticheAttive && GA4_ID) || (marketingAttivo && ADS_ID) || null;
  if (!idPrincipale) return;
  const gtag = preparaGtag();
  gtag("consent", "update", {
    analytics_storage: statisticheAttive ? "granted" : "denied",
    ad_storage: marketingAttivo ? "granted" : "denied",
    ad_user_data: marketingAttivo ? "granted" : "denied",
    ad_personalization: marketingAttivo ? "granted" : "denied",
  });
  caricaScript(`https://www.googletagmanager.com/gtag/js?id=${idPrincipale}`);
  // Le pagine viste le mandiamo noi a ogni cambio di rotta (sito a pagina unica).
  if (statisticheAttive && GA4_ID) gtag("config", GA4_ID, { send_page_view: false });
  if (marketingAttivo && ADS_ID) gtag("config", ADS_ID);
}

function avviaMeta(): void {
  if (!marketingAttivo || !META_PIXEL_ID || window.fbq) return;
  // Snippet ufficiale di Meta, riscritto senza `eval`.
  const fbq = ((...args: unknown[]) => {
    const f = window.fbq!;
    if (typeof f.callMethod === "function") (f.callMethod as (...a: unknown[]) => void)(...args);
    else f.queue!.push(args);
  }) as Fbq;
  fbq.push = fbq;
  fbq.loaded = true;
  fbq.version = "2.0";
  fbq.queue = [];
  window.fbq = fbq;
  window._fbq = fbq;
  caricaScript("https://connect.facebook.net/en_US/fbevents.js");
  fbq("init", META_PIXEL_ID);
}

function applicaConsenso(accettate: string[]): void {
  statisticheAttive = accettate.includes(CAT_STATISTICHE) && Boolean(GA4_ID);
  marketingAttivo = accettate.includes(CAT_MARKETING) && Boolean(ADS_ID || META_PIXEL_ID);
  avviaGoogle();
  avviaMeta();
  tracciaPagina(window.location.pathname + window.location.search);
}

/** Banner e preferenze. Da chiamare una volta, all'avvio dell'app nel browser. */
export async function avviaConsenso(): Promise<void> {
  if (!tracciamentoConfigurato() || typeof window === "undefined") return;
  const [CookieConsent] = await Promise.all([
    import("vanilla-cookieconsent"),
    import("vanilla-cookieconsent/dist/cookieconsent.css"),
  ]);

  const categorie: Record<string, object> = { necessari: { enabled: true, readOnly: true } };
  const sezioni: object[] = [
    {
      title: "Cookie tecnici",
      description: "Necessari per accedere al tuo account. Sempre attivi.",
      linkedCategory: "necessari",
    },
  ];
  if (GA4_ID) {
    categorie[CAT_STATISTICHE] = {
      autoClear: { cookies: [{ name: /^_ga/ }], reloadPage: true },
    };
    sezioni.push({
      title: "Statistiche",
      description:
        "Google Analytics 4: quante persone usano Renovio, da dove arrivano, quali pagine e passaggi del wizard usano. Ci aiuta a migliorare il sito.",
      linkedCategory: CAT_STATISTICHE,
    });
  }
  if (ADS_ID || META_PIXEL_ID) {
    categorie[CAT_MARKETING] = {
      autoClear: { cookies: [{ name: /^_gcl/ }, { name: "_fbp" }, { name: "_fbc" }], reloadPage: true },
    };
    sezioni.push({
      title: "Marketing",
      description:
        "Google Ads e Meta (Facebook, Instagram): misurano se le nostre pubblicità portano a una stima, un contatto o un acquisto, e permettono di mostrarti i nostri annunci su altri siti.",
      linkedCategory: CAT_MARKETING,
    });
  }
  sezioni.push({
    title: "Più informazioni",
    description: 'Tutti i dettagli nella <a href="/cookie">cookie policy</a> e nell\'<a href="/privacy">informativa privacy</a>.',
  });

  await CookieConsent.run({
    cookie: { name: "cc_renovio", expiresAfterDays: 182 },
    guiOptions: {
      consentModal: { layout: "box", position: "bottom left", equalWeightButtons: true, flipButtons: false },
      preferencesModal: { layout: "box", equalWeightButtons: true, flipButtons: false },
    },
    categories: categorie,
    onConsent: ({ cookie }) => applicaConsenso(cookie.categories),
    onChange: ({ cookie }) => applicaConsenso(cookie.categories),
    language: {
      default: "it",
      translations: {
        it: {
          consentModal: {
            title: "Usiamo i cookie, solo se vuoi",
            description:
              'Oltre ai cookie tecnici, con il tuo consenso usiamo cookie di statistica e di marketing (Google e Meta) per capire come viene usato il sito e misurare le nostre pubblicità. Puoi cambiare idea quando vuoi da «Preferenze cookie» in fondo alla pagina. <a href="/cookie">Cookie policy</a>',
            acceptAllBtn: "Accetta tutto",
            acceptNecessaryBtn: "Rifiuta",
            showPreferencesBtn: "Scegli",
            closeIconLabel: "Rifiuta e chiudi",
          },
          preferencesModal: {
            title: "Preferenze cookie",
            acceptAllBtn: "Accetta tutto",
            acceptNecessaryBtn: "Rifiuta tutto",
            savePreferencesBtn: "Salva le scelte",
            closeIconLabel: "Chiudi",
            sections: sezioni,
          },
        },
      },
    },
  } as Parameters<typeof CookieConsent.run>[0]);
}

/** Riapre le preferenze (link "Preferenze cookie" nel footer). */
export async function apriPreferenzeCookie(): Promise<void> {
  if (!tracciamentoConfigurato()) return;
  const CookieConsent = await import("vanilla-cookieconsent");
  CookieConsent.showPreferences();
}

/** Pagina vista, a ogni cambio di rotta. */
export function tracciaPagina(percorso: string): void {
  if (statisticheAttive && GA4_ID && window.gtag) {
    window.gtag("event", "page_view", {
      page_path: percorso,
      page_location: window.location.origin + percorso,
      page_title: document.title,
    });
  }
  if (marketingAttivo && window.fbq) window.fbq("track", "PageView");
}

export type EventoConversione =
  | { tipo: "stima_completata" }
  | { tipo: "registrazione" }
  | { tipo: "richiesta_contatto" }
  | { tipo: "acquisto_pro"; valore: number; valuta: string; piano: string; idTransazione: string };

/** Le quattro conversioni del sito, verso GA4, Google Ads e Meta. */
export function tracciaEvento(evento: EventoConversione): void {
  const gtag = window.gtag;
  const fbq = window.fbq;
  switch (evento.tipo) {
    case "stima_completata":
      if (statisticheAttive && gtag) gtag("event", "stima_completata");
      if (marketingAttivo && fbq) fbq("trackCustom", "StimaCompletata");
      break;
    case "registrazione":
      if (statisticheAttive && gtag) gtag("event", "sign_up", { method: "email" });
      if (marketingAttivo && fbq) fbq("track", "CompleteRegistration");
      break;
    case "richiesta_contatto":
      if (statisticheAttive && gtag) gtag("event", "generate_lead");
      if (marketingAttivo && gtag && ADS_ID && ADS_LABEL_CONTATTO) {
        gtag("event", "conversion", { send_to: `${ADS_ID}/${ADS_LABEL_CONTATTO}` });
      }
      if (marketingAttivo && fbq) fbq("track", "Lead");
      break;
    case "acquisto_pro": {
      const dati = { value: evento.valore, currency: evento.valuta };
      if (statisticheAttive && gtag) {
        gtag("event", "purchase", {
          ...dati,
          transaction_id: evento.idTransazione,
          items: [{ item_id: `pro_${evento.piano}`, item_name: `Renovio Pro ${evento.piano}`, price: evento.valore }],
        });
      }
      if (marketingAttivo && gtag && ADS_ID && ADS_LABEL_ACQUISTO) {
        gtag("event", "conversion", { send_to: `${ADS_ID}/${ADS_LABEL_ACQUISTO}`, ...dati, transaction_id: evento.idTransazione });
      }
      if (marketingAttivo && fbq) fbq("track", "Subscribe", { ...dati, predicted_ltv: evento.valore });
      break;
    }
  }
}
