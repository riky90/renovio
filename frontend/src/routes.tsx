import type { ComponentType } from "react";
import { Navigate, type RouteObject } from "react-router";
import { EstimatePage } from "@/pages/EstimatePage";
import { GuidaCostiPage } from "@/pages/GuidaCostiPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { SupportoPage } from "@/routes/SupportoPage";
import { PATH_GUIDE, GUIDE } from "@/content/guide";
import { Seo } from "@/lib/seo";

/**
 * Le rotte del sito, condivise fra il browser (`App.tsx`) e il prerender
 * (`entry-server.tsx`).
 *
 * Le pagine PUBBLICHE (home, guide, supporto) sono nel pacchetto
 * iniziale e vengono prerenderizzate in HTML statico. Account e admin si
 * caricano solo quando servono (`lazy`): chi arriva dalla ricerca non scarica
 * il pannello admin, e queste pagine sono comunque fuori dall'indice.
 */

/** Pagina privata o di servizio: caricata al bisogno e marcata `noindex`. */
function privata(path: string, title: string, carica: () => Promise<ComponentType>): RouteObject {
  return {
    path,
    lazy: async () => {
      const Pagina = await carica();
      return {
        Component: () => (
          <>
            <Seo title={title} path={path} noindex />
            <Pagina />
          </>
        ),
      };
    },
  };
}

export const routes: RouteObject[] = [
  { path: "/", element: <EstimatePage /> },
  { path: PATH_GUIDE, element: <GuidaCostiPage /> },
  { path: `${PATH_GUIDE}/:slug`, element: <GuidaCostiPage /> },
  { path: "/supporto", element: <SupportoPage /> },

  privata("/registrati", "Registrati", async () => (await import("@/routes/RegistratiPage")).RegistratiPage),
  privata("/accedi", "Accedi", async () => (await import("@/routes/AccediPage")).AccediPage),
  privata("/password-dimenticata", "Password dimenticata", async () => (await import("@/routes/PasswordDimenticataPage")).PasswordDimenticataPage),
  privata("/reimposta-password", "Reimposta la password", async () => (await import("@/routes/ReimpostaPasswordPage")).ReimpostaPasswordPage),
  privata("/passa-a-pro", "Passa a Pro", async () => (await import("@/routes/PassaAProPage")).PassaAProPage),
  privata("/le-mie-stime", "I miei progetti", async () => (await import("@/routes/LeMieStimePage")).LeMieStimePage),
  // La tab sta nel path, non in query string. La rotta senza tab esiste solo
  // per reggere i vecchi link `/impostazioni?tab=...` e rimandarli al posto giusto.
  privata("/impostazioni", "Impostazioni", async () => (await import("@/routes/ImpostazioniPage")).ImpostazioniRedirect),
  privata("/impostazioni/:tab", "Impostazioni", async () => (await import("@/routes/ImpostazioniPage")).ImpostazioniPage),
  privata("/nuova-stima", "Nuova stima", async () => (await import("@/pages/NuovaStimaProPage")).NuovaStimaProPage),
  privata("/dettaglio-pro", "Dettaglio Pro", async () => (await import("@/pages/DettaglioProPage")).DettaglioProPage),

  { path: "/admin", element: <Navigate to="/admin/lead" replace /> },
  privata("/admin/lead", "Admin · Lead", async () => (await import("@/pages/admin/LeadDashboardPage")).LeadDashboardPage),
  privata("/admin/listini", "Admin · Listini", async () => (await import("@/pages/admin/ListiniPage")).ListiniPage),
  privata("/admin/dettaglio-pro", "Admin · Dettaglio Pro", async () => (await import("@/pages/admin/DettaglioProPage")).DettaglioProAdminPage),
  privata("/admin/domande", "Admin · Domande", async () => (await import("@/pages/admin/DomandePage")).DomandePage),
  privata("/admin/coefficienti", "Admin · Coefficienti", async () => (await import("@/pages/admin/CoefficientiPage")).CoefficientiPage),
  privata("/admin/bonus", "Admin · Bonus", async () => (await import("@/pages/admin/BonusPage")).BonusPage),
  privata("/admin/citta-testi", "Admin · Città e testi", async () => (await import("@/pages/admin/CittaTestiPage")).CittaTestiPage),
  privata("/admin/referenti", "Admin · Referenti", async () => (await import("@/pages/admin/ReferentiPage")).ReferentiPage),
  privata("/admin/utenti", "Admin · Utenti", async () => (await import("@/pages/admin/UtentiPage")).UtentiPage),
  privata("/admin/documentazione", "Admin · Documentazione", async () => (await import("@/pages/admin/DocumentazionePage")).DocumentazionePage),

  { path: "*", element: <NotFoundPage /> },
];

/** Le pagine indicizzabili: prerender, sitemap e llms.txt partono da qui. */
export const PAGINE_PUBBLICHE: string[] = [
  "/",
  PATH_GUIDE,
  ...GUIDE.map((g) => `${PATH_GUIDE}/${g.slug}`),
  "/supporto",
];
