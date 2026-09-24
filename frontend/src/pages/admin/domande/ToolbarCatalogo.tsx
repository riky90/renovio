import { useState } from "react";
import { Download, Plus, UploadCloud } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { FlatImportDialog } from "@/components/admin/FlatImportDialog";
import { scaricaExcel } from "@/api/admin/exportExcel";
import { DOMANDE_QUERY_KEY } from "@/api/admin/domande";

const EXPORT_ERROR = "Non siamo riusciti a generare il file. Riprova.";

/**
 * Toolbar in testa a `/admin/domande` (UI-SPEC §A: Scarica · Carica ·
 * Aggiungi domanda). Il piano 05 aggiunge qui "Carica file", tra Scarica e
 * Aggiungi domanda — vive in un file suo apposta perche' quel piano gira in
 * parallelo con quelli che toccano `DomandePage.tsx`.
 *
 * Nessuna variante con margine, nessun `AlertDialog`: il catalogo domande
 * non contiene mai il coefficiente impresa (regola #1 di `CLAUDE.md`), a
 * differenza dell'export parametri di `CoefficientiPage.tsx`. `FlatImportDialog`
 * e `DiffPreviewTable` restano generici, nessuna modifica necessaria.
 */
export function ToolbarCatalogo({ onAggiungiDomanda }: { onAggiungiDomanda: () => void }) {
  const queryClient = useQueryClient();
  const [importOpen, setImportOpen] = useState(false);

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
      <Button type="button" variant="outline" onClick={() => setImportOpen(true)}>
        <UploadCloud className="size-4" />
        Carica file
      </Button>
      <Button type="button" onClick={onAggiungiDomanda}>
        <Plus className="size-4" />
        Aggiungi domanda
      </Button>

      <FlatImportDialog
        open={importOpen}
        onOpenChange={setImportOpen}
        risorsa="domande"
        titolo="Carica catalogo domande"
        onImported={() => {
          // Per prefisso: rinfresca domande, opzioni ed effetti gia' aperti
          // sulla pagina (query key composte in api/admin/domande.ts).
          queryClient.invalidateQueries({ queryKey: DOMANDE_QUERY_KEY });
        }}
      />
    </div>
  );
}
