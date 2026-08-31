import { cn } from "@/lib/utils";

interface BrandMarkProps {
  className?: string;
  /** Mostra solo il simbolo, senza il testo. */
  iconOnly?: boolean;
}

/**
 * Marchio: un tetto (chevron) su una barra min–max con due tacche.
 * Racconta il prodotto — casa + stima a range — in un solo segno.
 */
export function BrandMark({ className, iconOnly = false }: BrandMarkProps) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <svg
        width="28"
        height="28"
        viewBox="0 0 28 28"
        fill="none"
        aria-hidden
        className="shrink-0"
      >
        <rect width="28" height="28" rx="8" fill="var(--primary)" />
        {/* tetto */}
        <path
          d="M7 13.5 14 8l7 5.5"
          stroke="#fff"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* barra range */}
        <path d="M8 18h12" stroke="#fff" strokeWidth="2" strokeLinecap="round" />
        {/* tacche min/max */}
        <circle cx="8" cy="18" r="1.6" fill="var(--gold)" />
        <circle cx="20" cy="18" r="1.6" fill="var(--gold)" />
      </svg>
      {!iconOnly && (
        <span className="font-display text-lg font-bold leading-none tracking-tight text-foreground">
          Renov<span className="text-primary">i</span>o
        </span>
      )}
    </span>
  );
}
