/**
 * Prerender delle pagine pubbliche (build, non runtime).
 *
 * `scripts/prerender.mjs` chiama `render(url)` per ogni pagina di
 * `PAGINE_PUBBLICHE` e scrive l'HTML in `dist/<path>/index.html`, con i tag
 * raccolti da `<Seo>`. Chi non esegue JavaScript (crawler, assistenti AI,
 * anteprime social) legge cosi' contenuto e cifre vere; nel browser React
 * riparte da `main.tsx` e sostituisce il markup.
 */

import { renderToString } from "react-dom/server";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createStaticHandler, createStaticRouter, StaticRouterProvider } from "react-router";
import { routes, PAGINE_PUBBLICHE } from "@/routes";
import { HeadContext, type HeadRaccolto } from "@/lib/seo";
import { GUIDA_GENERALE, GUIDE, pathGuida } from "@/content/guide";
import { DATI_ISTANTANEA } from "@/lib/guideCosti";

export { PAGINE_PUBBLICHE };

export async function render(url: string): Promise<{ html: string; head: HeadRaccolto | null }> {
  const handler = createStaticHandler(routes);
  const context = await handler.query(new Request(`http://prerender${url}`));
  if (context instanceof Response) {
    throw new Error(`Prerender di ${url}: risposta inattesa ${context.status}`);
  }
  const router = createStaticRouter(handler.dataRoutes, context);
  const raccolto: { head: HeadRaccolto | null } = { head: null };
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, enabled: false } } });
  const html = renderToString(
    <HeadContext.Provider value={raccolto}>
      <QueryClientProvider client={queryClient}>
        <StaticRouterProvider router={router} context={context} hydrate={false} />
      </QueryClientProvider>
    </HeadContext.Provider>,
  );
  return { html, head: raccolto.head };
}

/** Il testo di `llms.txt`: cosa e' il sito e dove sono le cifre, in Markdown. */
export function llmsTxt(siteUrl: string): string {
  const d = DATI_ISTANTANEA;
  const guide = [GUIDA_GENERALE, ...GUIDE]
    .map((g) => `- [${g.titolo(d)}](${siteUrl}${pathGuida(g)}): ${g.sintesi(d)}`)
    .join("\n");
  return `# Renovio

> Renovio stima quanto costa ristrutturare casa in Italia: una fascia di prezzo minimo–massimo, IVA inclusa, calcolata voce per voce (demolizioni, massetti, impianti, posa, forniture) sul listino reale della città. Gratuita e senza registrazione. I prezzi attuali vengono dal listino di ${d.citta_listino}, aggiornato al ${d.aggiornato_il}.

Le cifre sono stime pre-sopralluogo, arrotondate alle centinaia di euro, IVA inclusa, con cantiere e oneri di sicurezza compresi ed esclusi CSE/CSP e pratiche amministrative. Per citare un numero, cita la guida e la sua data di aggiornamento.

## Guide ai costi

${guide}

## Strumenti

- [Stima gratuita](${siteUrl}/): città, superficie e tipo di lavori; il risultato è diviso per categoria (edile, finiture, serramenti e porte, prodotti) con le detrazioni fiscali stimate.
- [Domande frequenti](${siteUrl}/supporto): come funziona la stima e cosa include.
`;
}
