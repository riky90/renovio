import { useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const FEEDBACK = "Disponibile a breve. Questa funzione arriverà nelle prossime versioni.";

const SECONDARY_CTAS = [
  "Contatta un professionista",
  "Scarica PDF",
  "Salva / crea account",
] as const;

/**
 * Result-screen CTA cluster. All four actions are soft-wall in Phase 1:
 * clicking shows the "Disponibile a breve" feedback, never navigates.
 */
export function SoftWallCta() {
  const [feedback, setFeedback] = useState<string | null>(null);

  function handleClick() {
    setFeedback(FEEDBACK);
  }

  return (
    <div className="flex flex-col gap-3">
      <Button
        type="button"
        onClick={handleClick}
        className="h-11 w-full bg-primary text-base font-semibold text-primary-foreground hover:bg-primary/90"
      >
        Passa a Pro
      </Button>
      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
        {SECONDARY_CTAS.map((label) => (
          <Button
            key={label}
            type="button"
            variant="outline"
            onClick={handleClick}
            className="h-11 flex-1"
          >
            {label}
          </Button>
        ))}
      </div>
      <p
        role="status"
        aria-live="polite"
        className={cn(
          "text-center text-sm text-muted-foreground transition-opacity",
          feedback ? "opacity-100" : "opacity-0"
        )}
      >
        {feedback ?? " "}
      </p>
    </div>
  );
}
