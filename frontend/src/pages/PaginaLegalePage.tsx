import { Fragment, type ReactNode } from "react";
import { Link } from "react-router";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { AGGIORNAMENTO_LEGALE, DATI_LEGALI, type DatiLegali } from "@/content/datiLegali";
import type { Blocco, DocumentoLegale } from "@/content/legale";
import { ORGANIZATION_LD, Seo, breadcrumbLd } from "@/lib/seo";

const ETICHETTE: Record<keyof DatiLegali, string> = {
  titolare: "ragione sociale",
  sede: "sede",
  partitaIva: "partita IVA",
  codiceFiscale: "codice fiscale",
  email: "email",
  pec: "PEC",
  regioneHosting: "regione dei server",
  fornitoreEmail: "fornitore email",
};

/** Un campo di `DATI_LEGALI`, o un segnaposto evidenziato se manca. */
function campo(nome: string, chiave: string): ReactNode {
  const valore = DATI_LEGALI[nome as keyof DatiLegali];
  if (valore) return <Fragment key={chiave}>{valore}</Fragment>;
  return (
    <mark key={chiave} className="rounded bg-amber-200 px-1 text-amber-950">
      [da completare: {ETICHETTE[nome as keyof DatiLegali] ?? nome}]
    </mark>
  );
}

/** `{{campo}}`, `[testo](url)` e `**grassetto**` in un testo legale. */
function inline(testo: string): ReactNode[] {
  const parti = testo.split(/(\{\{\w+\}\}|\[[^\]]+\]\([^)]+\)|\*\*[^*]+\*\*)/g);
  return parti.map((parte, i) => {
    const chiave = `${i}`;
    const segnaposto = parte.match(/^\{\{(\w+)\}\}$/);
    if (segnaposto) return campo(segnaposto[1], chiave);
    const link = parte.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (link) {
      const [, etichetta, href] = link;
      const classe = "font-medium text-primary underline underline-offset-4";
      return href.startsWith("/") ? (
        <Link key={chiave} to={href} className={classe}>
          {inline(etichetta)}
        </Link>
      ) : (
        <a key={chiave} href={href} className={classe} target="_blank" rel="noreferrer">
          {etichetta}
        </a>
      );
    }
    const grassetto = parte.match(/^\*\*([^*]+)\*\*$/);
    if (grassetto) {
      return (
        <strong key={chiave} className="font-semibold text-foreground">
          {inline(grassetto[1])}
        </strong>
      );
    }
    return <Fragment key={chiave}>{parte}</Fragment>;
  });
}

function BloccoLegale({ blocco }: { blocco: Blocco }) {
  switch (blocco.tipo) {
    case "p":
      return <p className="leading-relaxed text-muted-foreground">{inline(blocco.testo)}</p>;
    case "lista":
      return (
        <ul className="flex list-disc flex-col gap-2 pl-5 leading-relaxed text-muted-foreground marker:text-primary">
          {blocco.voci.map((voce) => (
            <li key={voce}>{inline(voce)}</li>
          ))}
        </ul>
      );
    case "box":
      return (
        <div className="rounded-xl border border-border bg-secondary/40 px-5 py-4 leading-relaxed text-muted-foreground">
          {inline(blocco.testo)}
        </div>
      );
    case "tabella":
      return (
        <div className="overflow-x-auto rounded-xl border border-border">
          <table className="w-full min-w-[560px] border-collapse text-left text-sm">
            <thead className="bg-secondary/60">
              <tr>
                {blocco.colonne.map((c) => (
                  <th key={c} scope="col" className="px-4 py-3 font-semibold text-foreground">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {blocco.righe.map((riga) => (
                <tr key={riga.join("|")} className="border-t border-border align-top">
                  {riga.map((cella, j) => (
                    <td key={j} className="px-4 py-3 text-muted-foreground">
                      {inline(cella)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
  }
}

/** Pagina pubblica di un documento legale (privacy, cookie, condizioni di vendita). */
export function PaginaLegalePage({ documento }: { documento: DocumentoLegale }) {
  return (
    <div className="flex min-h-svh flex-col bg-background">
      <Seo
        title={documento.titolo}
        description={documento.descrizione}
        path={documento.path}
        jsonLd={[
          ORGANIZATION_LD,
          breadcrumbLd([
            { nome: "Home", path: "/" },
            { nome: documento.titolo, path: documento.path },
          ]),
        ]}
      />
      <SiteHeader />
      <main id="contenuto" className="flex-1">
        <article className="mx-auto flex w-full max-w-3xl flex-col gap-10 px-4 py-12 sm:px-6 sm:py-16">
          <header className="flex flex-col gap-3">
            <h1 className="text-3xl font-bold text-foreground sm:text-4xl">{documento.titolo}</h1>
            <p className="text-sm text-muted-foreground">Ultimo aggiornamento: {AGGIORNAMENTO_LEGALE}</p>
            <p className="leading-relaxed text-muted-foreground">{inline(documento.introduzione)}</p>
          </header>
          {documento.sezioni.map((sezione) => (
            <section key={sezione.titolo} className="flex flex-col gap-4">
              <h2 className="text-xl font-bold text-foreground">{sezione.titolo}</h2>
              {sezione.blocchi.map((blocco, i) => (
                <BloccoLegale key={i} blocco={blocco} />
              ))}
            </section>
          ))}
        </article>
      </main>
      <SiteFooter />
    </div>
  );
}
