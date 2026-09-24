import { Download, Plus } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { scaricaExcel } from "@/api/admin/exportExcel";

const EXPORT_ERROR = "Non siamo riusciti a generare il file. Riprova.";

/**
 * Toolbar in testa a `/admin/domande` (UI-SPEC §A: Scarica · Carica ·
 * Aggiungi domanda). Il piano 05 aggiunge qui "Carica file", tra Scarica e
 * Aggiungi domanda — vive in un file suo apposta perche' quel piano gira in
 * parallelo con quelli che toccano `DomandePage.tsx`.
 *
 * Nessuna variante con margine, nessun `AlertDialog`: il catalogo domande
 * non contiene mai il coefficiente impresa (regola #1 di `CLAUDE.md`), a
 * differenza dell'export parametri di `CoefficientiPage.tsx`.
 */
export function ToolbarCatalogo({ onAggiungiDomanda }: { onAggiungiDomanda: () => void }) {
  const scaricaCatalogoMutation = useMutation({
    mutationFn: () => scaricaExcel("/admin/domande/export.xlsx"),
    onError: () => {
      toast.error(EXPORT_ERROR);
    },
  });

  return (
    <div className="flex flex-wrap items-center gap-3">
      <Button
        type="button"
        variant="outline"
        onClick={() => scaricaCatalogoMutation.mutate()}
        disabled={scaricaCatalogoMutation.isPending}
      >
        <Download className="size-4" />
        {scaricaCatalogoMutation.isPending ? "Generazione…" : "Scarica catalogo domande"}
      </Button>
      <Button type="button" onClick={onAggiungiDomanda}>
        <Plus className="size-4" />
        Aggiungi domanda
      </Button>
    </div>
  );
}
