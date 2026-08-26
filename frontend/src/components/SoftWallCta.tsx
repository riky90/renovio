import { useState } from "react";
import { useNavigate } from "react-router";
import { PdfDownloadButton } from "@/components/PdfDownloadButton";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { StimaResponse } from "@/api/stima";

const FEEDBACK = "Disponibile a breve. Questa funzione arriverà nelle prossime versioni.";
const SAVE_CONFIRMATION = "Stima salvata nel tuo account.";

interface SoftWallCtaProps {
  /** Stima corrente gia' calcolata: e' il payload che viene salvato as-is, mai ricalcolato. */
  result: StimaResponse;
  isAuthenticated: boolean;
  /** id della stima gia' salvata (auto-save da loggato) — null finche' il salvataggio e' in corso. */
  savedId?: number | null;
  isSaving?: boolean;
}

/**
 * Result-screen CTA cluster (UI-SPEC §A). Solo 2 dei 4 bottoni cambiano
 * comportamento per Fase 2 (D-07/D-10): "Scarica PDF" e "Salva / crea
 * account". "Passa a Pro" e "Contatta un professionista" restano soft-wall
 * invariati (Fase 3/4).
 */
export function SoftWallCta({ result, isAuthenticated, savedId, isSaving }: SoftWallCtaProps) {
  const navigate = useNavigate();
  const [feedback, setFeedback] = useState<string | null>(null);

  function handleSoftWallClick() {
    setFeedback(FEEDBACK);
  }

  function handleSalvaClick() {
    navigate("/registrati?intent=save", { state: { pendingStima: result } });
  }

  function handleScaricaPdfAnonimo() {
    navigate("/registrati?intent=save+download", { state: { pendingStima: result } });
  }

  return (
    <div className="flex flex-col gap-3">
      <Button
        type="button"
        onClick={handleSoftWallClick}
        className="h-11 w-full bg-primary text-base font-semibold text-primary-foreground hover:bg-primary/90"
      >
        Passa a Pro
      </Button>
      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
        <Button
          type="button"
          variant="outline"
          onClick={handleSoftWallClick}
          className="h-11 flex-1"
        >
          Contatta un professionista
        </Button>

        {isAuthenticated ? (
          savedId != null ? (
            <PdfDownloadButton stimaId={savedId} variant="outline" className="flex-1" />
          ) : (
            <Button type="button" variant="outline" disabled className="h-11 flex-1">
              {isSaving ? "Salvataggio in corso..." : "Scarica PDF"}
            </Button>
          )
        ) : (
          <Button
            type="button"
            variant="outline"
            onClick={handleScaricaPdfAnonimo}
            className="h-11 flex-1"
          >
            Scarica PDF
          </Button>
        )}

        {!isAuthenticated && (
          <Button
            type="button"
            variant="outline"
            onClick={handleSalvaClick}
            className="h-11 flex-1"
          >
            Salva / crea account
          </Button>
        )}
      </div>

      {isAuthenticated && savedId != null && (
        <p className="text-center text-sm text-muted-foreground">{SAVE_CONFIRMATION}</p>
      )}

      <p
        role="status"
        aria-live="polite"
        className={cn(
          "text-center text-sm text-muted-foreground transition-opacity",
          feedback ? "opacity-100" : "opacity-0"
        )}
      >
        {feedback ?? " "}
      </p>
    </div>
  );
}
