import { Link, useParams } from "react-router";
import { ArrowRight, Calculator, ChevronRight } from "lucide-react";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { Button } from "@/components/ui/button";
import {
  GUIDA_GENERALE,
  GUIDE,
  PATH_GUIDE,
  guidaPerSlug,
  pathGuida,
  type Blocco,
} from "@/content/guide";
import { meseAnno, useDatiGuide } from "@/lib/guideCosti";
import { ORGANIZATION_LD, SITE_URL, Seo, breadcrumbLd, faqLd } from "@/lib/seo";
import { GuideCards } from "@/components/GuideCards";
import { NotFoundPage } from "@/pages/NotFoundPage";

/**
 * Le guide ai costi: `/costi-ristrutturazione` (hub) e
 * `/costi-ristrutturazione/:slug`. Contenuto e cifre vengono da
 * `content/guide.ts`, che li ricava dai dati del motore.
 */
export function GuidaCostiPage() {
  const { slug } = useParams();
  const guida = guidaPerSlug(slug);
  const dati = useDatiGuide();
  if (!guida) return <NotFoundPage />;

  const path = pathGuida(guida);
  const blocchi = guida.blocchi(dati);
  const faq = guida.faq(dati);
  const indice = blocchi.filter((b): b is Extract<Blocco, { tipo: "h2" }> => b.tipo === "h2" && !!b.id);
  const briciole = [
    { nome: "Home", path: "/" },
    { nome: "Costi di ristrutturazione", path: PATH_GUIDE },
    ...(guida.slug ? [{ nome: guida.nome, path }] : []),
  ];
  const isHub = !guida.slug;
  const altre = isHub ? GUIDE : [GUIDA_GENERALE, ...GUIDE.filter((g) => g.slug !== guida.slug)];

  return (
    <div className="flex min-h-svh flex-col bg-background">
      <Seo
        title={guida.titolo(dati)}
        description={guida.descrizione(dati)}
        path={path}
        ogType="article"
        jsonLd={[
          ORGANIZATION_LD,
          {
            "@context": "https://schema.org",
            "@type": "Article",
            headline: guida.h1(dati),
            description: guida.descrizione(dati),
            inLanguage: "it-IT",
            dateModified: dati.aggiornato_il,
            mainEntityOfPage: `${SITE_URL}${path}`,
            author: { "@id": `${SITE_URL}/#organization` },
            publisher: { "@id": `${SITE_URL}/#organization` },
            image: `${SITE_URL}/og-image.png`,
          },
          breadcrumbLd(briciole),
          ...(faq.length ? [faqLd(faq)] : []),
        ]}
      />
      <SiteHeader />
      <main id="contenuto" className="flex-1">
        <article className="mx-auto w-full max-w-3xl px-4 pb-16 pt-8 sm:px-6 sm:pt-12">
          <nav aria-label="Percorso" className="mb-6">
            <ol className="flex flex-wrap items-center gap-1 text-sm text-muted-foreground">
              {briciole.map((b, i) => (
                <li key={b.path} className="flex items-center gap-1">
                  {i > 0 && <ChevronRight className="size-3.5" aria-hidden />}
                  {i === briciole.length - 1 ? (
                    <span aria-current="page" className="text-foreground">
                      {b.nome}
                    </span>
                  ) : (
                    <Link to={b.path} className="underline-offset-4 hover:text-primary hover:underline">
                      {b.nome}
                    </Link>
                  )}
                </li>
              ))}
            </ol>
          </nav>

          <p className="text-xs font-semibold uppercase tracking-wide text-primary">
            Guida ai costi · aggiornata a{" "}
            <time dateTime={dati.aggiornato_il}>{meseAnno(dati.aggiornato_il)}</time>
          </p>
          <h1 className="mt-2 text-balance font-display text-3xl font-bold leading-tight tracking-tight text-foreground sm:text-4xl">
            {guida.h1(dati)}
          </h1>

          <section aria-labelledby="in-breve" className="mt-6 rounded-xl border border-primary/25 bg-primary/5 p-5">
            <h2 id="in-breve" className="font-sans text-xs font-semibold uppercase tracking-wide text-primary">
              In breve
            </h2>
            <p className="mt-2 text-base leading-relaxed text-foreground sm:text-lg">{guida.sintesi(dati)}</p>
          </section>

          {indice.length > 2 && (
            <nav aria-label="In questa guida" className="mt-8">
              <h2 className="font-sans text-sm font-semibold text-foreground">In questa guida</h2>
              <ul className="mt-2 grid gap-1.5 text-sm sm:grid-cols-2">
                {indice.map((h) => (
                  <li key={h.id}>
                    <a href={`#${h.id}`} className="text-muted-foreground underline-offset-4 hover:text-primary hover:underline">
                      {h.testo}
                    </a>
                  </li>
                ))}
                {faq.length > 0 && (
                  <li>
                    <a href="#domande" className="text-muted-foreground underline-offset-4 hover:text-primary hover:underline">
                      Domande frequenti
                    </a>
                  </li>
                )}
              </ul>
            </nav>
          )}

          <div className="mt-4">
            {blocchi.map((b, i) => (
              <BloccoGuida key={i} blocco={b} />
            ))}
          </div>

          <CtaStima />

          {faq.length > 0 && (
            <section aria-labelledby="domande" className="mt-12">
              <h2 id="domande" className="scroll-mt-24 font-display text-2xl font-bold text-foreground">
                Domande frequenti
              </h2>
              <dl className="mt-4 divide-y divide-border rounded-xl border border-border bg-card">
                {faq.map((f) => (
                  <div key={f.domanda} className="p-5">
                    <dt className="font-semibold text-foreground">{f.domanda}</dt>
                    <dd className="mt-2 leading-relaxed text-muted-foreground">{f.risposta}</dd>
                  </div>
                ))}
              </dl>
            </section>
          )}

          <section aria-labelledby="altre-guide" className="mt-12">
            <h2 id="altre-guide" className="font-display text-2xl font-bold text-foreground">
              {isHub ? "Le guide per intervento" : "Altre guide ai costi"}
            </h2>
            <GuideCards guide={altre} />
          </section>
        </article>
      </main>
      <SiteFooter />
    </div>
  );
}

function BloccoGuida({ blocco }: { blocco: Blocco }) {
  switch (blocco.tipo) {
    case "h2":
      return (
        <h2 id={blocco.id} className="mt-10 scroll-mt-24 font-display text-2xl font-bold text-foreground">
          {blocco.testo}
        </h2>
      );
    case "p":
      return <p className="mt-4 leading-relaxed text-foreground/85">{blocco.testo}</p>;
    case "elenco":
      return (
        <ul className="mt-4 list-disc space-y-2 pl-5 leading-relaxed text-foreground/85 marker:text-primary">
          {blocco.voci.map((v) => (
            <li key={v}>{v}</li>
          ))}
        </ul>
      );
    case "tabella":
      return (
        <figure className="mt-5">
          <div className="overflow-x-auto rounded-xl border border-border bg-card">
            <table className="w-full min-w-[32rem] text-left text-sm">
              <caption className="sr-only">{blocco.didascalia}</caption>
              <thead className="bg-secondary/60">
                <tr>
                  {blocco.colonne.map((c) => (
                    <th key={c} scope="col" className="px-4 py-3 font-semibold text-foreground">
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {blocco.righe.map((riga) => (
                  <tr key={riga.join("|")}>
                    {riga.map((cella, j) =>
                      j === 0 ? (
                        <th key={j} scope="row" className="px-4 py-3 font-medium text-foreground">
                          {cella}
                        </th>
                      ) : (
                        <td key={j} className="px-4 py-3 tabular-nums text-foreground/85">
                          {cella}
                        </td>
                      ),
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <figcaption className="mt-2 text-xs text-muted-foreground">{blocco.didascalia}</figcaption>
        </figure>
      );
  }
}

function CtaStima() {
  return (
    <aside className="mt-12 flex flex-col items-start gap-4 rounded-2xl border border-border bg-card p-6 shadow-sm sm:flex-row sm:items-center sm:justify-between">
      <div className="flex gap-3">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <Calculator className="size-5" aria-hidden />
        </span>
        <div>
          <p className="font-semibold text-foreground">Quanto costa la tua casa?</p>
          <p className="text-sm text-muted-foreground">
            Stima gratuita a range, IVA inclusa, divisa per categoria di lavori. Senza registrazione.
          </p>
        </div>
      </div>
      <Button asChild className="shrink-0">
        <Link to="/#stima">
          Calcola la stima <ArrowRight className="size-4" aria-hidden />
        </Link>
      </Button>
    </aside>
  );
}
