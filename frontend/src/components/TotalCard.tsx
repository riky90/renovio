import { RangeBar } from "@/components/RangeBar";
import { RiepilogoIvaRighe } from "@/components/RiepilogoIvaRighe";
import { Separator } from "@/components/ui/separator";
import { formatEur } from "@/lib/currency";
import { riepilogoIva } from "@/lib/risultato";
import type { CategoriaOut, ExtraOut, TotaleOut } from "@/api/stima";

interface TotalCardProps {
  totale: TotaleOut;
  categorie: CategoriaOut[];
  extra: ExtraOut[];
  budget?: number | null;
}

/** Pannello di enfasi: la cifra più importante della schermata risultati, a range. */
export function TotalCard({ totale, categorie, extra, budget }: TotalCardProps) {
  const riepilogo = riepilogoIva(categorie, extra, totale);

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
      <div className="border-l-4 border-primary bg-accent/60 px-6 py-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-accent-foreground">
          Totale stimato · IVA inclusa
        </p>
        <div className="mt-4">
          <RangeBar
            min={totale.totale_min}
            max={totale.totale_max}
            minLabel={formatEur(totale.totale_min)}
            maxLabel={formatEur(totale.totale_max)}
            budget={budget}
          />
        </div>
      </div>
      <Separator />
      <RiepilogoIvaRighe riepilogo={riepilogo} className="px-6 py-4" />
      <div className="space-y-1.5 px-6 pb-4 text-sm text-muted-foreground">
        <p>Il dettaglio degli extra è nel riepilogo qui sopra.</p>
        <p>
          Stima pre-sopralluogo: l'importo definitivo dipende dallo stato dell'immobile e dai
          materiali scelti.
        </p>
      </div>
    </div>
  );
}
