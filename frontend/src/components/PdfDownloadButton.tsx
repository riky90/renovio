import { useMutation } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { scaricaPdf } from "@/api/stima";

const ERROR_COPY = "Non siamo riusciti a generare il PDF. Riprova tra qualche istante.";

interface PdfDownloadButtonProps {
  stimaId: number;
  className?: string;
  variant?: "default" | "outline";
}

/**
 * UI-SPEC F.4 button contract: default "Scarica PDF" (accent) -> loading
 * "Generazione in corso..." (disabled, spinner) -> success (download nativo,
 * ritorna al label di default) -> errore (testo inline destructive sotto il
 * bottone, non un alert a schermo intero).
 */
export function PdfDownloadButton({ stimaId, className, variant = "default" }: PdfDownloadButtonProps) {
  const mutation = useMutation({
    mutationFn: () => scaricaPdf(stimaId),
  });

  return (
    <div className="flex flex-col gap-2">
      <Button
        type="button"
        variant={variant}
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending}
        className={cn(
          "h-11 w-full text-base font-semibold",
          variant === "default" &&
            "bg-primary text-primary-foreground hover:bg-primary/90",
          className
        )}
      >
        {mutation.isPending ? (
          <span className="flex items-center justify-center gap-2">
            <Loader2 className="size-4 animate-spin" aria-hidden />
            Generazione in corso...
          </span>
        ) : (
          "Scarica PDF"
        )}
      </Button>
      {mutation.isError && (
        <p className="text-center text-sm text-destructive">{ERROR_COPY}</p>
      )}
    </div>
  );
}
