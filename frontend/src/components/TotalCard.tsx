import { formatEurRange } from "@/lib/currency";
import type { TotaleOut } from "@/api/stima";

interface TotalCardProps {
  totale: TotaleOut;
}

/** Accent-tinted emphasis panel — the single most prominent figure on the result screen. */
export function TotalCard({ totale }: TotalCardProps) {
  return (
    <div className="rounded-lg border-l-4 border-primary bg-accent px-6 py-5">
      <p className="text-sm font-semibold text-foreground">Totale stimato (IVA inclusa)</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums text-primary sm:text-3xl">
        {formatEurRange(totale.totale_min, totale.totale_max)}
      </p>
      <p className="mt-3 text-sm text-muted-foreground">
        Totale IVA inclusa. Comprende i costi extra (sicurezza e pratiche amministrative).
      </p>
      <p className="mt-1 text-sm text-muted-foreground">
        Stima pre-sopralluogo. L'importo definitivo dipende dallo stato dell'immobile e dai
        materiali scelti.
      </p>
    </div>
  );
}
