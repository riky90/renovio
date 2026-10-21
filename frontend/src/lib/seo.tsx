/**
 * Metadati di pagina: title, description, canonical, robots, Open Graph,
 * Twitter e dati strutturati JSON-LD.
 *
 * Due ambienti, un solo componente:
 *  - nel BROWSER `<Seo>` aggiorna `document.head` a ogni cambio di pagina;
 *  - al PRERENDER (`entry-server.tsx`) scrive i tag in un raccoglitore che lo
 *    script di build inietta nell'HTML statico. E' cio' che leggono i crawler
 *    e gli assistenti AI che non eseguono JavaScript.
 *
 * Il dominio pubblico viene da `VITE_SITE_URL`: e' provvisorio, e cambiarlo
 * non deve richiedere modifiche al codice.
 */

import { createContext, useContext, useEffect } from "react";

export const SITE_URL = (import.meta.env.VITE_SITE_URL || "https://stima-lovat.vercel.app").replace(/\/$/, "");
export const SITE_NAME = "Renovio";
export const DEFAULT_DESCRIPTION =
  "Quanto costa ristrutturare casa? Stima gratuita a range, IVA inclusa, calcolata voce per voce sul listino reale della tua città. Senza registrazione.";
export const OG_IMAGE = `${SITE_URL}/og-image.png`;

export type JsonLd = Record<string, unknown>;

export interface SeoProps {
  /** Titolo della pagina, senza il nome del sito (lo aggiunge il componente). */
  title: string;
  description?: string;
  /** Path canonico, es. `/costi-ristrutturazione`. */
  path: string;
  /** Pagine private o di servizio: fuori dall'indice. */
  noindex?: boolean;
  ogType?: "website" | "article";
  jsonLd?: JsonLd[];
}

export interface HeadRaccolto {
  titolo: string;
  tags: string;
}

/** Al prerender: dove `<Seo>` deposita i tag. Assente nel browser. */
export const HeadContext = createContext<{ head: HeadRaccolto | null } | null>(null);

function titoloCompleto(title: string): string {
  return title.includes(SITE_NAME) ? title : `${title} | ${SITE_NAME}`;
}

function escapeAttr(valore: string): string {
  return valore.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
}

/** JSON dentro `<script>`: `<` escapato perche' non chiuda mai il tag. */
function jsonPerScript(dati: JsonLd): string {
  return JSON.stringify(dati).replace(/</g, "\\u003c");
}

interface Meta {
  attr: "name" | "property";
  key: string;
  content: string;
}

function metaDi(props: SeoProps): { titolo: string; canonical: string; metas: Meta[] } {
  const titolo = titoloCompleto(props.title);
  const description = props.description ?? DEFAULT_DESCRIPTION;
  const canonical = `${SITE_URL}${props.path === "/" ? "/" : props.path}`;
  const metas: Meta[] = [
    { attr: "name", key: "description", content: description },
    {
      attr: "name",
      key: "robots",
      content: props.noindex ? "noindex, nofollow" : "index, follow, max-image-preview:large, max-snippet:-1",
    },
    { attr: "property", key: "og:site_name", content: SITE_NAME },
    { attr: "property", key: "og:locale", content: "it_IT" },
    { attr: "property", key: "og:type", content: props.ogType ?? "website" },
    { attr: "property", key: "og:title", content: titolo },
    { attr: "property", key: "og:description", content: description },
    { attr: "property", key: "og:url", content: canonical },
    { attr: "property", key: "og:image", content: OG_IMAGE },
    { attr: "property", key: "og:image:width", content: "1200" },
    { attr: "property", key: "og:image:height", content: "630" },
    { attr: "name", key: "twitter:card", content: "summary_large_image" },
    { attr: "name", key: "twitter:title", content: titolo },
    { attr: "name", key: "twitter:description", content: description },
    { attr: "name", key: "twitter:image", content: OG_IMAGE },
  ];
  return { titolo, canonical, metas };
}

/** I tag come HTML statico: usato solo dal prerender. */
export function headComeHtml(props: SeoProps): HeadRaccolto {
  const { titolo, canonical, metas } = metaDi(props);
  const righe = [
    ...metas.map((m) => `<meta ${m.attr}="${m.key}" content="${escapeAttr(m.content)}" data-seo />`),
    `<link rel="canonical" href="${escapeAttr(canonical)}" data-seo />`,
    ...(props.jsonLd ?? []).map(
      (dati) => `<script type="application/ld+json" data-seo>${jsonPerScript(dati)}</script>`,
    ),
  ];
  return { titolo, tags: righe.join("\n    ") };
}

function applicaAlDocumento(props: SeoProps): void {
  const { titolo, canonical, metas } = metaDi(props);
  document.title = titolo;
  document.head.querySelectorAll("[data-seo]").forEach((el) => el.remove());
  for (const m of metas) {
    document.head.querySelectorAll(`meta[${m.attr}="${m.key}"]`).forEach((el) => el.remove());
    const el = document.createElement("meta");
    el.setAttribute(m.attr, m.key);
    el.setAttribute("content", m.content);
    el.setAttribute("data-seo", "");
    document.head.appendChild(el);
  }
  const link = document.createElement("link");
  link.rel = "canonical";
  link.href = canonical;
  link.setAttribute("data-seo", "");
  document.head.appendChild(link);
  for (const dati of props.jsonLd ?? []) {
    const script = document.createElement("script");
    script.type = "application/ld+json";
    script.setAttribute("data-seo", "");
    script.textContent = jsonPerScript(dati);
    document.head.appendChild(script);
  }
}

export function Seo(props: SeoProps) {
  const raccoglitore = useContext(HeadContext);
  if (raccoglitore) {
    // Prerender: nessun effetto gira lato server, si raccoglie durante il render.
    raccoglitore.head = headComeHtml(props);
  }
  const chiave = JSON.stringify(props);
  useEffect(() => {
    applicaAlDocumento(JSON.parse(chiave) as SeoProps);
  }, [chiave]);
  return null;
}

// --- dati strutturati condivisi ---------------------------------------------

export const ORGANIZATION_LD: JsonLd = {
  "@context": "https://schema.org",
  "@type": "Organization",
  "@id": `${SITE_URL}/#organization`,
  name: SITE_NAME,
  url: `${SITE_URL}/`,
  logo: `${SITE_URL}/favicon.svg`,
};

export const WEBSITE_LD: JsonLd = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  "@id": `${SITE_URL}/#website`,
  name: SITE_NAME,
  url: `${SITE_URL}/`,
  inLanguage: "it-IT",
  publisher: { "@id": `${SITE_URL}/#organization` },
};

export function breadcrumbLd(voci: { nome: string; path: string }[]): JsonLd {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: voci.map((v, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: v.nome,
      item: `${SITE_URL}${v.path}`,
    })),
  };
}

export function faqLd(faq: { domanda: string; risposta: string }[]): JsonLd {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faq.map((f) => ({
      "@type": "Question",
      name: f.domanda,
      acceptedAnswer: { "@type": "Answer", text: f.risposta },
    })),
  };
}
