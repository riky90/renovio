import { Separator } from "@/components/ui/separator";
import { formatEur, formatEurRange } from "@/lib/currency";
import type { RiepilogoIva } from "@/lib/risultato";

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

interface RiepilogoIvaRigheProps {
  riepilogo: RiepilogoIva;
  className?: string;
}

/**
 * Righe del riepilogo imponibile / IVA per aliquota / extra / totale IVA
 * inclusa. Condivise da TotalCard (Free) e dalla vista Pro: solo
 * presentazione, i numeri arrivano già calcolati.
 */
export function RiepilogoIvaRighe({ riepilogo, className }: RiepilogoIvaRigheProps) {
  const sommaExtra = riepilogo.extra.reduce((acc, e) => acc + e.importo, 0);

  return (
    <div className={`flex flex-col gap-2 ${className ?? ""}`}>
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
      {riepilogo.extra.length > 0 && (
        <>
          <Riga label="Costi extra" value={formatEur(sommaExtra)} />
          {riepilogo.extra.map((e) => (
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
  );
}
