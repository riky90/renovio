import { cn } from "@/lib/utils";
import { formatEur } from "@/lib/currency";
import { scalaBarra } from "@/lib/risultato";

interface RangeBarProps {
  min: number;
  max: number;
  minLabel: string;
  maxLabel: string;
  className?: string;
}

/**
 * Motivo-firma: la barra min–max su un asse 0 -> tetto (D-11). La larghezza del
 * segmento riflette l'incertezza reale: +-10% e +-20% sono visibilmente diversi.
 */
export function RangeBar({ min, max, minLabel, maxLabel, className }: RangeBarProps) {
  const { leftPct, rightPct } = scalaBarra(min, max);

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <div
        role="img"
        aria-label={`Stima da ${formatEur(min)} a ${formatEur(max)}`}
        className="relative h-2 w-full rounded-full bg-secondary"
      >
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
      </div>
      <div className="flex items-baseline justify-between font-display tabular-nums">
        <span className="text-lg font-bold text-foreground sm:text-xl">{minLabel}</span>
        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          fino a
        </span>
        <span className="text-lg font-bold text-primary sm:text-xl">{maxLabel}</span>
      </div>
    </div>
  );
}
