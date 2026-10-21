import { Link } from "react-router";
import { ArrowRight } from "lucide-react";
import { pathGuida, type Guida } from "@/content/guide";

/** Card di collegamento alle guide ai costi. */
export function GuideCards({ guide }: { guide: Guida[] }) {
  return (
    <ul className="mt-4 grid gap-3 sm:grid-cols-2">
      {guide.map((g) => (
        <li key={g.slug || "hub"}>
          <Link
            to={pathGuida(g)}
            className="group flex h-full items-start justify-between gap-3 rounded-xl border border-border bg-card p-4 transition-colors hover:border-primary/40 hover:bg-primary/5"
          >
            <span>
              <span className="block font-semibold text-foreground">{g.nome}</span>
              <span className="mt-1 block text-sm text-muted-foreground">{g.sottotitolo}</span>
            </span>
            <ArrowRight className="mt-1 size-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary" aria-hidden />
          </Link>
        </li>
      ))}
    </ul>
  );
}
