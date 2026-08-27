import { Lock } from "lucide-react";
import { Link } from "react-router";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatEurRange } from "@/lib/currency";
import type { CategoriaOut } from "@/api/stima";

const COVERAGE_NOTES: Record<string, string> = {
  "A-EDILE": "Demolizioni, murature, tracce e opere edili di base.",
  "B-FINITURE": "Pavimenti, rivestimenti, tinteggiature, cartongesso.",
  "C-SERRAMENTI": "Porte interne, infissi esterni, serramenti.",
  "D-PRODOTTI": "Sanitari, rubinetteria, apparecchi e prodotti finiti.",
};

interface CategoryCardProps {
  categoria: CategoriaOut;
  /** Utente Free (non Pro): mostra la striscia teaser bloccata. Nessun teaser per Pro. */
  isPro?: boolean;
}

/** Neutral category card — never accent-styled; range is IVA-inclusive. */
export function CategoryCard({ categoria, isPro = false }: CategoryCardProps) {
  const nota = COVERAGE_NOTES[categoria.code];

  return (
    <Card className="border-border bg-card">
      <CardHeader>
        <CardTitle className="text-sm font-semibold">{categoria.nome}</CardTitle>
        {nota && <p className="text-sm text-muted-foreground">{nota}</p>}
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <p className="text-xl font-semibold tabular-nums">
          {formatEurRange(categoria.totale_min, categoria.totale_max)}
        </p>
        {!isPro && (
          <div className="flex items-center gap-2 rounded-md border border-border bg-muted px-3 py-2">
            <Lock className="size-4 shrink-0 text-muted-foreground" aria-hidden />
            <p className="text-sm text-muted-foreground">
              Dettaglio disponibile con Pro ·{" "}
              <Link
                to="/passa-a-pro"
                className="font-medium text-primary underline-offset-4 hover:underline"
              >
                Passa a Pro
              </Link>
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
