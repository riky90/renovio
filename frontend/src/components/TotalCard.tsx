import { RangeBar } from "@/components/RangeBar";
import { formatEur } from "@/lib/currency";
import type { TotaleOut } from "@/api/stima";

interface TotalCardProps {
  totale: TotaleOut;
}

/** Pannello di enfasi: la cifra più importante della schermata risultati, a range. */
export function TotalCard({ totale }: TotalCardProps) {
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
      <div className="border-l-4 border-primary bg-accent/60 px-6 py-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-accent-foreground">
          Totale stimato · IVA inclusa
        </p>
        <div className="mt-4">
          <RangeBar
            minLabel={formatEur(totale.totale_min)}
            maxLabel={formatEur(totale.totale_max)}
          />
        </div>
      </div>
      <div className="space-y-1.5 px-6 py-4 text-sm text-muted-foreground">
        <p>Comprende i costi extra (sicurezza e pratiche amministrative).</p>
        <p>
          Stima pre-sopralluogo: l'importo definitivo dipende dallo stato dell'immobile e dai
          materiali scelti.
        </p>
      </div>
    </div>
  );
}
