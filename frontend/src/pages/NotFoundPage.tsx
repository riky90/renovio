import { Link } from "react-router";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { Button } from "@/components/ui/button";
import { GuideCards } from "@/components/GuideCards";
import { GUIDA_GENERALE, GUIDE } from "@/content/guide";
import { Seo } from "@/lib/seo";

/** Pagina inesistente: fuori dall'indice, con le strade per ripartire. */
export function NotFoundPage() {
  return (
    <div className="flex min-h-svh flex-col bg-background">
      <Seo title="Pagina non trovata" path="/404" noindex />
      <SiteHeader />
      <main id="contenuto" className="mx-auto w-full max-w-3xl flex-1 px-4 py-16 sm:px-6">
        <p className="text-sm font-semibold text-primary">Errore 404</p>
        <h1 className="mt-2 font-display text-3xl font-bold text-foreground">Questa pagina non esiste</h1>
        <p className="mt-3 text-muted-foreground">
          Il link potrebbe essere vecchio o scritto male. Puoi calcolare una stima o leggere le guide ai costi.
        </p>
        <Button asChild className="mt-6">
          <Link to="/">Calcola una stima</Link>
        </Button>
        <GuideCards guide={[GUIDA_GENERALE, ...GUIDE.slice(0, 3)]} />
      </main>
      <SiteFooter />
    </div>
  );
}
