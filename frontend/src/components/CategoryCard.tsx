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
}

/** Neutral category card — never accent-styled; range is IVA-inclusive. */
export function CategoryCard({ categoria }: CategoryCardProps) {
  const nota = COVERAGE_NOTES[categoria.code];

  return (
    <Card className="border-border bg-card">
      <CardHeader>
        <CardTitle className="text-sm font-semibold">{categoria.nome}</CardTitle>
        {nota && <p className="text-sm text-muted-foreground">{nota}</p>}
      </CardHeader>
      <CardContent>
        <p className="text-xl font-semibold tabular-nums">
          {formatEurRange(categoria.totale_min, categoria.totale_max)}
        </p>
      </CardContent>
    </Card>
  );
}
