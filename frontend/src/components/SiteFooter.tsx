import { Link } from "react-router";
import { BrandMark } from "@/components/BrandMark";
import { GUIDA_GENERALE, GUIDE, pathGuida } from "@/content/guide";
import { DATI_LEGALI } from "@/content/datiLegali";
import { PATH_CONDIZIONI, PATH_COOKIE, PATH_PRIVACY } from "@/content/legale";

interface FooterLink {
  label: string;
  to: string;
}

const COLUMNS: { title: string; links: FooterLink[] }[] = [
  {
    title: "Prodotto",
    links: [
      { label: "Calcola una stima", to: "/#stima" },
      { label: "Passa a Pro", to: "/passa-a-pro" },
      { label: "I miei progetti", to: "/le-mie-stime" },
    ],
  },
  {
    title: "Account",
    links: [
      { label: "Accedi", to: "/accedi" },
      { label: "Registrati", to: "/registrati" },
    ],
  },
  {
    title: "Guide ai costi",
    links: [GUIDA_GENERALE, ...GUIDE].map((g) => ({ label: g.nome, to: pathGuida(g) })),
  },
  {
    title: "Risorse",
    links: [
      { label: "Domande frequenti", to: "/supporto" },
      { label: "Privacy", to: PATH_PRIVACY },
      { label: "Cookie", to: PATH_COOKIE },
      { label: "Condizioni di vendita", to: PATH_CONDIZIONI },
      { label: "Recesso dal contratto", to: "/impostazioni/abbonamento" },
    ],
  },
];

const YEAR = new Date().getFullYear();

/** Footer di sito: brand + colonne di link + riga legale. */
export function SiteFooter() {
  return (
    <footer className="mt-auto border-t border-border bg-secondary/40">
      <div className="mx-auto w-full max-w-5xl px-4 py-12 sm:px-6">
        <div className="flex flex-col gap-10 md:flex-row md:justify-between">
          <div className="max-w-xs">
            <BrandMark />
            <p className="mt-1 text-sm font-medium text-foreground">
              La stima trasparente per la tua casa.
            </p>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              Stime di ristrutturazione oneste, a range, calcolate voce per voce sul listino della
              tua città. Prima del sopralluogo, in un paio di minuti.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-10 sm:grid-cols-4 sm:gap-10">
            {COLUMNS.map((col) => (
              <div key={col.title} className="flex flex-col gap-3">
                <h2 className="font-sans text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  {col.title}
                </h2>
                <ul className="flex flex-col gap-2.5">
                  {col.links.map((link) => (
                    <li key={link.label}>
                      <Link
                        to={link.to}
                        className="text-sm text-foreground underline-offset-4 transition-colors hover:text-primary hover:underline"
                      >
                        {link.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-10 flex flex-col gap-1 border-t border-border/70 pt-6 text-xs text-muted-foreground">
          <p>
            © {YEAR} Renovio. Tutti i diritti riservati.
            {DATI_LEGALI.titolare && DATI_LEGALI.partitaIva && (
              <>
                {" "}
                {DATI_LEGALI.titolare} · {DATI_LEGALI.sede} · P. IVA {DATI_LEGALI.partitaIva}
              </>
            )}
          </p>
          <p>
            Le stime sono indicative e pre-sopralluogo. L'importo definitivo dipende dallo stato
            dell'immobile e dai materiali scelti.
          </p>
        </div>
      </div>
    </footer>
  );
}
