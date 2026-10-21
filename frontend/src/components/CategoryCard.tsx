import { AirVent, DoorOpen, Hammer, Lock, Paintbrush, type LucideIcon } from "lucide-react";
import { Link } from "react-router";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LetturaCategoria } from "@/components/LetturaCategoria";
import { formatEurRange } from "@/lib/currency";
import { incidenzaEurMq, pesoCategoria } from "@/lib/risultato";
import type { CategoriaOut } from "@/api/stima";

const COVERAGE_NOTES: Record<string, string> = {
  "A-EDILE": "Demolizioni, massetti, murature, impianti, posa e tinteggiature.",
  "B-FINITURE": "Pavimenti, rivestimenti, sanitari, rubinetteria e radiatori.",
  "C-SERRAMENTI": "Porte interne, porta blindata, finestre, tapparelle e cassonetti.",
  "D-PRODOTTI": "Climatizzatori, caldaia e scaldasalviette.",
};

const CATEGORY_ICONS: Record<string, LucideIcon> = {
  "A-EDILE": Hammer,
  "B-FINITURE": Paintbrush,
  "C-SERRAMENTI": DoorOpen,
  "D-PRODOTTI": AirVent,
};

interface CategoryCardProps {
  categoria: CategoriaOut;
  /** Utente Free (non Pro): mostra la striscia teaser bloccata. Nessun teaser per Pro. */
  isPro?: boolean;
  /**
   * G14(f): stima Free aperta da un utente gia' Pro. Il lucchetto resta (la stima
   * non ha il dettaglio), ma il link porta a rifarla in Pro invece che a "Passa a Pro".
   */
  rifaiProHref?: string;
  /** Superficie della stima, per l'incidenza €/m². */
  mq: number;
  /** Somma dei valori medi delle categorie, denominatore del peso. */
  sommaMedi: number;
}

/** Card categoria — neutra; il range è IVA esclusa (stessa base di €/m² e peso). */
export function CategoryCard({ categoria, isPro = false, rifaiProHref, mq, sommaMedi }: CategoryCardProps) {
  const nota = COVERAGE_NOTES[categoria.code];
  const Icon = CATEGORY_ICONS[categoria.code] ?? Hammer;
  const inc = incidenzaEurMq(categoria.imponibile_min, categoria.imponibile_max, mq);
  const peso = pesoCategoria(categoria, sommaMedi);

  return (
    <Card className="gap-0 border-border bg-card shadow-sm transition-shadow hover:shadow-md">
      <CardHeader className="gap-2">
        <span className="flex size-9 items-center justify-center rounded-lg bg-accent text-accent-foreground">
          <Icon className="size-4.5" aria-hidden />
        </span>
        <CardTitle className="text-sm font-semibold">{categoria.nome}</CardTitle>
        {nota && <p className="text-sm text-muted-foreground">{nota}</p>}
      </CardHeader>
      <CardContent className="flex flex-col gap-3 pt-4">
        <p className="font-display text-xl font-bold tabular-nums">
          {formatEurRange(categoria.imponibile_min, categoria.imponibile_max)}{" "}
          <span className="text-xs font-normal text-muted-foreground">IVA esclusa</span>
        </p>
        <LetturaCategoria incidenza={inc} peso={{ etichetta: peso.etichetta, fillPct: peso.fillPct }} />
        {!isPro && (
          <div className="flex items-center gap-2 rounded-md border border-border bg-muted px-3 py-2">
            <Lock className="size-4 shrink-0 text-muted-foreground" aria-hidden />
            <p className="text-sm text-muted-foreground">
              Dettaglio con Pro ·{" "}
              <Link
                to={rifaiProHref ?? "/passa-a-pro"}
                className="font-medium text-primary underline-offset-4 hover:underline"
              >
                {rifaiProHref ? "Rifai in versione Pro" : "Passa a Pro"}
              </Link>
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
