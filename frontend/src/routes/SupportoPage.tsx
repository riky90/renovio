import { Link } from "react-router";
import { ChevronDown } from "lucide-react";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { GuideCards } from "@/components/GuideCards";
import { Button } from "@/components/ui/button";
import { GUIDA_GENERALE, GUIDE } from "@/content/guide";
import { ORGANIZATION_LD, Seo, breadcrumbLd, faqLd } from "@/lib/seo";

interface Faq {
  domanda: string;
  risposta: string;
  link?: { to: string; testo: string };
}

const FAQS: Faq[] = [
  {
    domanda: "Come funziona la stima?",
    risposta:
      "Inserisci città e superficie in m² e scegli il tipo di lavori. Il tipo precompila le risposte sugli interventi (pavimenti, bagni, impianti, serramenti), che puoi cambiare. Il motore calcola le quantità voce per voce e le moltiplica per i prezzi del listino locale: ottieni un costo per categoria di lavori, IVA inclusa.",
  },
  {
    domanda: "Perché ricevo un range e non un prezzo preciso?",
    risposta:
      "Perché è una stima prima del sopralluogo. Un numero secco darebbe una falsa certezza: il costo reale dipende dallo stato dell'immobile e dai materiali scelti. Un minimo e un massimo onesti sono più utili di un prezzo finto-preciso.",
  },
  {
    domanda: "È gratis? Devo registrarmi?",
    risposta:
      "Il calcolo è gratuito e non richiede registrazione. Se crei un account, la stima resta salvata e puoi ritrovarla in «I miei progetti».",
  },
  {
    domanda: "Cosa include il totale?",
    risposta:
      "Le categorie di lavori (edile, finiture, serramenti e porte, prodotti), l'IVA di ciascuna, il cantiere, gli oneri della sicurezza e i costi extra come CSE/CSP e pratiche amministrative. Il finanziamento a rate e l'arredo non sono nel totale lavori: l'arredo, se lo chiedi, compare a parte.",
  },
  {
    domanda: "I prezzi valgono per la mia città?",
    risposta:
      "I prezzi vengono dal listino locale. Per una città senza un listino proprio usiamo il più vicino disponibile e te lo segnaliamo con un avviso esplicito, così sai sempre su cosa si basa il numero.",
  },
  {
    domanda: "Cosa aggiunge il piano Pro?",
    risposta:
      "Con Pro vedi il computo voce per voce di ogni categoria, con quantità e prezzi, scegli finiture e pavimenti e scarichi il preventivo in PDF da tenere o condividere.",
    link: { to: "/passa-a-pro", testo: "Scopri Pro" },
  },
  {
    domanda: "Come parlo con un professionista?",
    risposta:
      "Dal risultato della stima puoi chiedere di essere ricontattato: giriamo i tuoi dati a un referente della zona, senza impegno.",
  },
];

export function SupportoPage() {
  return (
    <div className="flex min-h-svh flex-col bg-background">
      <Seo
        title="Domande frequenti sulla stima dei costi di ristrutturazione"
        description="Come funziona la stima di Renovio, perché è un intervallo, cosa include il totale e da dove vengono i prezzi."
        path="/supporto"
        jsonLd={[
          ORGANIZATION_LD,
          faqLd(FAQS.map(({ domanda, risposta }) => ({ domanda, risposta }))),
          breadcrumbLd([
            { nome: "Home", path: "/" },
            { nome: "Domande frequenti", path: "/supporto" },
          ]),
        ]}
      />
      <SiteHeader />
      <main id="contenuto" className="flex-1">
        <div className="mx-auto w-full max-w-3xl px-4 py-12 sm:px-6 sm:py-16">
          <header className="flex flex-col gap-2 text-center">
            <span className="text-xs font-semibold uppercase tracking-wide text-primary">
              Guide & supporto
            </span>
            <h1 className="text-3xl font-bold text-foreground sm:text-4xl">Domande frequenti</h1>
            <p className="mx-auto max-w-xl text-muted-foreground">
              Tutto quello che serve sapere sulla stima, in parole semplici.
            </p>
          </header>

          {/* `details` nativo: le risposte restano nell'HTML anche chiuse, quindi le
              leggono i crawler e funzionano senza JavaScript. */}
          <div className="mt-10 divide-y divide-border rounded-2xl border border-border bg-card px-5 shadow-sm sm:px-8">
            {FAQS.map((faq) => (
              <details key={faq.domanda} className="group py-1">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 rounded-md py-4 text-base font-semibold text-foreground outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 [&::-webkit-details-marker]:hidden">
                  <h2 className="font-sans text-base font-semibold">{faq.domanda}</h2>
                  <ChevronDown
                    className="size-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-180"
                    aria-hidden
                  />
                </summary>
                <p className="pb-4 leading-relaxed text-muted-foreground">
                  {faq.risposta}
                  {faq.link && (
                    <>
                      {" "}
                      <Link to={faq.link.to} className="font-medium text-primary underline-offset-4 hover:underline">
                        {faq.link.testo}
                      </Link>
                      .
                    </>
                  )}
                </p>
              </details>
            ))}
          </div>

          <section aria-labelledby="guide-supporto" className="mt-12">
            <h2 id="guide-supporto" className="text-xl font-bold text-foreground">
              Le guide ai costi
            </h2>
            <GuideCards guide={[GUIDA_GENERALE, ...GUIDE]} />
          </section>

          <div className="mt-10 flex flex-col items-center gap-4 rounded-2xl border border-border bg-secondary/40 px-6 py-10 text-center">
            <h2 className="text-xl font-bold text-foreground">Non hai trovato la risposta?</h2>
            <p className="max-w-md text-sm text-muted-foreground">
              Fai una stima e chiedi di essere ricontattato: un referente della tua zona ti
              risponde senza impegno.
            </p>
            <Button asChild className="h-11 px-6">
              <Link to="/#stima">Calcola una stima</Link>
            </Button>
          </div>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
