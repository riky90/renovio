import { Link } from "react-router";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { Button } from "@/components/ui/button";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

interface Faq {
  q: string;
  a: React.ReactNode;
}

const FAQS: Faq[] = [
  {
    q: "Come funziona la stima?",
    a: "Bastano tre informazioni — città, superficie in m² e tipo di lavori. Il motore le incrocia con il listino locale e ti restituisce un costo per categoria di lavori, IVA inclusa. Tutto in una trentina di secondi.",
  },
  {
    q: "Perché ricevo un range e non un prezzo preciso?",
    a: "Perché è una stima prima del sopralluogo. Un numero secco darebbe una falsa certezza: il costo reale dipende dallo stato dell'immobile e dai materiali scelti. Un minimo e un massimo onesti sono più utili di un prezzo finto-preciso.",
  },
  {
    q: "È gratis? Devo registrarmi?",
    a: "Il calcolo è gratuito e non richiede registrazione. Se crei un account, la stima resta salvata e puoi ritrovarla in «I miei progetti».",
  },
  {
    q: "Cosa include il totale?",
    a: "Le categorie di lavori (edile, finiture, serramenti, prodotti), l'IVA per ciascuna e i costi extra come sicurezza e pratiche amministrative. Il finanziamento a rate non è incluso.",
  },
  {
    q: "I prezzi valgono per la mia città?",
    a: "I prezzi sono calibrati sul listino locale. Per una città senza un listino proprio usiamo il più vicino disponibile e te lo segnaliamo con un avviso esplicito, così sai sempre su cosa si basa il numero.",
  },
  {
    q: "Cosa aggiunge il piano Pro?",
    a: (
      <>
        Con Pro vedi il dettaglio voce per voce di ogni categoria e ottieni il preventivo in PDF
        da tenere o condividere.{" "}
        <Link to="/passa-a-pro">Scopri Pro</Link>.
      </>
    ),
  },
  {
    q: "Come parlo con un professionista?",
    a: "Da una stima salvata puoi chiedere di essere ricontattato: giriamo i tuoi dati a un referente della zona, senza impegno.",
  },
];

export function SupportoPage() {
  return (
    <div className="flex min-h-svh flex-col bg-background">
      <SiteHeader />
      <main className="flex-1">
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

          <div className="mt-10 rounded-2xl border border-border bg-card px-5 shadow-sm sm:px-8">
            <Accordion type="single" collapsible>
              {FAQS.map((faq, i) => (
                <AccordionItem key={i} value={`faq-${i}`}>
                  <AccordionTrigger className="text-base font-semibold">{faq.q}</AccordionTrigger>
                  <AccordionContent className="text-muted-foreground">{faq.a}</AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </div>

          <div className="mt-10 flex flex-col items-center gap-4 rounded-2xl border border-border bg-secondary/40 px-6 py-10 text-center">
            <h2 className="text-xl font-bold text-foreground">Non hai trovato la risposta?</h2>
            <p className="max-w-md text-sm text-muted-foreground">
              Fai una stima e chiedi di essere ricontattato: un referente della tua zona ti
              risponde senza impegno.
            </p>
            <Button asChild className="h-11 px-6">
              <Link to="/">Calcola una stima</Link>
            </Button>
          </div>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
