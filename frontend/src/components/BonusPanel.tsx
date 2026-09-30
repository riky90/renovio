import { useState } from "react";
import { ChevronDown, Info } from "lucide-react";
import { RangeBar } from "@/components/RangeBar";
import { formatEur } from "@/lib/currency";
import { cn } from "@/lib/utils";
import type { BonusOut } from "@/api/stima";

interface BonusPanelProps {
  bonus: BonusOut;
}

function RigaLegenda({ label, min, max }: { label: string; min: number; max: number }) {
  return (
    <div className="flex justify-between gap-2 text-sm">
      <span className="flex min-w-0 items-center gap-2">{label}</span>
      <span className="shrink-0 tabular-nums">
        {formatEur(min)} – {formatEur(max)}
      </span>
    </div>
  );
}

/** 0.5 -> "50%". Le aliquote arrivano come frazione, mai come percentuale. */
function formatAliquota(pct: number): string {
  return `${Math.round(pct * 100)}%`;
}

/**
 * "Quanto recuperi con le detrazioni". Una sola barra: il range della detrazione
 * (`detrazione_min` – `detrazione_max`, Bonus Mobili incluso quando c'e' arredo).
 * Il netto non si mostra piu' (G7, ri-collaudo 2026-09-30) anche se il server lo
 * manda ancora: il client non disegna ne' calcola valori fiscali.
 *
 * Due scelte non estetiche:
 *
 * 1. **Il disclaimer si legge dal payload**, mai da una costante locale. E'
 *    materia fiscale: il testo deve poter cambiare dal pannello admin e deve
 *    essere lo stesso che finisce nello snapshot congelato e nel PDF.
 * 2. **Sempre a range**, come il resto della stima. Un numero secco qui
 *    sarebbe una promessa, e la detrazione dipende dalla spesa effettiva.
 */
export function BonusPanel({ bonus }: BonusPanelProps) {
  const [dettaglioAperto, setDettaglioAperto] = useState(false);

  const lavoriMin = bonus.detrazione_lavori_min;
  const lavoriMax = bonus.detrazione_lavori_max;
  const haLavori = lavoriMin !== null && lavoriMax !== null;
  // Detrazione che comprende anche un bonus non sui lavori (es. Bonus Mobili).
  const detrazioneEsclusa = haLavori && bonus.detrazione_max > lavoriMax;

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
      <div className="border-l-4 border-gold bg-secondary/60 px-6 py-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Quanto recuperi con le detrazioni
        </p>
        <div className="mt-4">
          <RangeBar
            min={bonus.detrazione_min}
            max={bonus.detrazione_max}
            minLabel={formatEur(bonus.detrazione_min)}
            maxLabel={formatEur(bonus.detrazione_max)}
          />
        </div>
        {haLavori && (
          <div className="mt-4 flex flex-col gap-2">
            <RigaLegenda label="Recuperi in detrazione sui lavori" min={lavoriMin} max={lavoriMax} />
          </div>
        )}
        <p className="mt-3 text-sm text-muted-foreground">
          Che tornano indietro come{" "}
          <span className="font-medium text-foreground tabular-nums">
            {formatEur(bonus.rata_annua_min)} – {formatEur(bonus.rata_annua_max)}
          </span>{" "}
          all'anno.
        </p>
        {detrazioneEsclusa && (
          <p className="mt-2 text-xs text-muted-foreground">
            La detrazione comprende anche l'arredo (Bonus Mobili), che è stimato a parte dal totale lavori.
          </p>
        )}
      </div>

      <div className="divide-y divide-border">
        {bonus.bonus.map((dettaglio) => (
          <div key={dettaglio.code} className="px-6 py-4">
            <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
              <span className="text-sm font-semibold">{dettaglio.nome}</span>
              <span className="text-sm tabular-nums text-muted-foreground">
                {formatAliquota(dettaglio.aliquota_pct)} · {formatEur(dettaglio.detrazione_min)} –{" "}
                {formatEur(dettaglio.detrazione_max)}
              </span>
            </div>
            {dettaglio.descrizione && (
              <p className="mt-1 text-sm text-muted-foreground">{dettaglio.descrizione}</p>
            )}
            {dettaglio.tetto_raggiunto && dettaglio.tetto_spesa_eur !== null && (
              // Va detto, non nascosto: oltre il tetto la spesa in piu' non
              // produce detrazione, ed e' il motivo per cui il range si
              // comprime rispetto a quello dei costi.
              <p className="mt-1 text-sm text-muted-foreground">
                La spesa supera il tetto di {formatEur(dettaglio.tetto_spesa_eur)}: la parte
                eccedente non è detraibile.
              </p>
            )}
          </div>
        ))}
      </div>

      <div className="border-t border-border px-6 py-4">
        <button
          type="button"
          onClick={() => setDettaglioAperto((aperto) => !aperto)}
          aria-expanded={dettaglioAperto}
          className="flex w-full items-center gap-2 text-left text-sm font-medium text-muted-foreground hover:text-foreground"
        >
          <Info className="size-4 shrink-0" aria-hidden />
          Condizioni e limiti
          <ChevronDown
            className={cn(
              "ml-auto size-4 shrink-0 transition-transform",
              dettaglioAperto && "rotate-180"
            )}
            aria-hidden
          />
        </button>
        {dettaglioAperto && (
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{bonus.disclaimer}</p>
        )}
      </div>
    </div>
  );
}
