import { RangeBar } from "@/components/RangeBar";
import { Separator } from "@/components/ui/separator";
import { formatEur, formatEurRange } from "@/lib/currency";
import { riepilogoIva } from "@/lib/risultato";
import type { CategoriaOut, ExtraOut, TotaleOut } from "@/api/stima";

interface TotalCardProps {
  totale: TotaleOut;
  categorie: CategoriaOut[];
  extra: ExtraOut[];
}

function Riga({
  label,
  value,
  strong = false,
  muted = false,
}: {
  label: string;
  value: string;
  strong?: boolean;
  muted?: boolean;
}) {
  return (
    <div
      className={`flex justify-between gap-2 text-sm ${strong ? "font-semibold" : ""} ${
        muted ? "text-muted-foreground" : ""
      }`}
    >
      <span className="min-w-0">{label}</span>
      <span className="shrink-0 tabular-nums">{value}</span>
    </div>
  );
}

/** Pannello di enfasi: la cifra più importante della schermata risultati, a range. */
export function TotalCard({ totale, categorie, extra }: TotalCardProps) {
  const riepilogo = riepilogoIva(categorie, extra, totale);
  const sommaExtra = extra.reduce((acc, e) => acc + e.importo, 0);

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
          />
        </div>
      </div>
      <Separator />
      <div className="flex flex-col gap-2 px-6 py-4">
        <Riga
          label="Imponibile lavori"
          value={formatEurRange(riepilogo.imponibileLavoriMin, riepilogo.imponibileLavoriMax)}
        />
        {riepilogo.righeIva.map((r) => (
          <Riga
            key={r.ivaPct}
            label={`IVA ${Math.round(r.ivaPct * 100)}%`}
            value={formatEurRange(r.min, r.max)}
          />
        ))}
        {extra.length > 0 && (
          <>
            <Riga label="Costi extra" value={formatEur(sommaExtra)} />
            {extra.map((e) => (
              <Riga key={e.code} label={e.nome} value={formatEur(e.importo)} muted />
            ))}
          </>
        )}
        <Separator />
        <Riga
          label="Totale IVA inclusa"
          value={formatEurRange(riepilogo.totaleMin, riepilogo.totaleMax)}
          strong
        />
      </div>
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
