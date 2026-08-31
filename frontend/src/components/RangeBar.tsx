import { cn } from "@/lib/utils";

interface RangeBarProps {
  minLabel: string;
  maxLabel: string;
  className?: string;
}

/**
 * Motivo-firma: la barra min–max. Non è una scala precisa, è la
 * rappresentazione visiva della regola di dominio "output sempre a range".
 */
export function RangeBar({ minLabel, maxLabel, className }: RangeBarProps) {
  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <div className="relative h-2 w-full rounded-full bg-secondary">
        <div
          className="absolute inset-y-0 left-[12%] right-[12%] rounded-full"
          style={{
            background: "linear-gradient(90deg, var(--gold), var(--primary))",
          }}
        />
        <span className="absolute left-[12%] top-1/2 size-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-background bg-gold" />
        <span className="absolute right-[12%] top-1/2 size-3.5 translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-background bg-primary" />
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
