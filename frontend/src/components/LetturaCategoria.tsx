import { formatRangeEurMq } from "@/lib/currency";

interface LetturaCategoriaProps {
  incidenza: { min: number; max: number } | null;
  peso: { etichetta: string; fillPct: number };
  className?: string;
}

/**
 * Riga di lettura di una categoria: €/m² (IVA esclusa) e mini-barra del peso.
 * Condivisa da CategoryCard (Free) e dalla vista Pro: solo presentazione.
 */
export function LetturaCategoria({ incidenza, peso, className }: LetturaCategoriaProps) {
  return (
    <div className={`flex flex-col gap-3 ${className ?? ""}`}>
      {incidenza && (
        <p className="text-sm tabular-nums">
          {formatRangeEurMq(incidenza.min, incidenza.max)}{" "}
          <span className="text-xs text-muted-foreground">IVA esclusa</span>
        </p>
      )}
      <div className="flex items-center justify-between gap-1">
        <div aria-hidden className="h-1 w-full rounded-full bg-secondary">
          <div className="h-1 rounded-full bg-primary" style={{ width: `${peso.fillPct}%` }} />
        </div>
        <span className="shrink-0 whitespace-nowrap pl-2 text-xs font-semibold tabular-nums">
          {peso.etichetta} del totale
        </span>
      </div>
    </div>
  );
}
