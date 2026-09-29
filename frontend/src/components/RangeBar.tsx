import { cn } from "@/lib/utils";
import { formatEur } from "@/lib/currency";
import { LARGHEZZA_MINIMA_PCT, pctSuScala, scalaBarra } from "@/lib/risultato";

interface RangeBarProps {
  min: number;
  max: number;
  minLabel: string;
  maxLabel: string;
  /** Budget dichiarato: disegna la tacca a budget/tetto e alza il tetto se serve. */
  budget?: number | null;
  /** Secondo segmento sulla stessa scala (es. costo dopo le detrazioni). */
  evidenza?: { min: number; max: number; etichetta: string } | null;
  className?: string;
}

/**
 * Motivo-firma: la barra min–max su un asse 0 -> tetto (D-11). La larghezza del
 * segmento riflette l'incertezza reale: +-10% e +-20% sono visibilmente diversi.
 */
export function RangeBar({
  min,
  max,
  minLabel,
  maxLabel,
  budget,
  evidenza,
  className,
}: RangeBarProps) {
  const { tetto, leftPct, rightPct, budgetPct } = scalaBarra(min, max, budget);
  let evLeft = 0;
  let evWidth = 0;
  if (evidenza) {
    evLeft = pctSuScala(evidenza.min, tetto);
    evWidth = Math.max(pctSuScala(evidenza.max, tetto) - evLeft, LARGHEZZA_MINIMA_PCT);
    evLeft = Math.min(evLeft, 100 - evWidth);
  }
  // L'etichetta segue la tacca ma non esce dai bordi: a sinistra sotto il 15%,
  // a destra sopra l'85%, altrimenti centrata.
  const traslaEtichetta =
    budgetPct === null ? "" : budgetPct < 15 ? "0%" : budgetPct > 85 ? "-100%" : "-50%";

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      {budgetPct !== null && (
        <div className="relative h-4" aria-hidden>
          <span
            className="absolute top-0 whitespace-nowrap text-xs font-semibold text-foreground"
            style={{ left: `${budgetPct}%`, transform: `translateX(${traslaEtichetta})` }}
          >
            Il tuo budget
          </span>
        </div>
      )}
      <div
        role="img"
        aria-label={`Stima da ${formatEur(min)} a ${formatEur(max)}${
          typeof budget === "number" && budget > 0 ? ` · budget ${formatEur(budget)}` : ""
        }${
          evidenza
            ? ` · ${evidenza.etichetta} da ${formatEur(evidenza.min)} a ${formatEur(evidenza.max)}`
            : ""
        }`}
        className="relative h-2 w-full rounded-full bg-secondary"
      >
        {evidenza && (
          <div
            className="absolute inset-y-0 rounded-full border border-gold bg-gold/40"
            style={{ left: `${evLeft}%`, width: `${evWidth}%` }}
          />
        )}
        <div
          className="absolute inset-y-0 rounded-full"
          style={{
            left: `${leftPct}%`,
            width: `${rightPct - leftPct}%`,
            background: "linear-gradient(90deg, var(--gold), var(--primary))",
          }}
        />
        <span
          className="absolute top-1/2 size-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-background bg-gold"
          style={{ left: `${leftPct}%` }}
        />
        <span
          className="absolute top-1/2 size-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-background bg-primary"
          style={{ left: `${rightPct}%` }}
        />
        {budgetPct !== null && (
          <span
            className="absolute top-1/2 h-6 w-0.5 -translate-x-1/2 -translate-y-1/2 bg-foreground"
            style={{ left: `${budgetPct}%` }}
          />
        )}
      </div>
      {/* Le cifre stanno sotto gli estremi del segmento: due spaziatori comprimibili
          + un blocco centrale largo quanto il segmento (mai piu' stretto delle cifre). */}
      <div className="flex w-full items-baseline overflow-hidden font-display tabular-nums">
        <div style={{ flexBasis: `${leftPct}%`, flexGrow: 0, flexShrink: 1, minWidth: 0 }} />
        <div
          className="flex items-baseline justify-between gap-2"
          style={{
            flexBasis: `${rightPct - leftPct}%`,
            flexGrow: 0,
            flexShrink: 0,
            minWidth: "max-content",
          }}
        >
          <span className="text-lg font-bold text-foreground sm:text-xl">{minLabel}</span>
          {rightPct - leftPct >= 35 && (
            <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              fino a
            </span>
          )}
          <span className="text-lg font-bold text-primary sm:text-xl">{maxLabel}</span>
        </div>
        <div
          style={{ flexBasis: `${100 - rightPct}%`, flexGrow: 0, flexShrink: 1, minWidth: 0 }}
        />
      </div>
    </div>
  );
}
