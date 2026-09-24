import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";

/**
 * Toolbar in testa a `/admin/domande` (UI-SPEC §A). Contiene solo "Aggiungi
 * domanda" in questo piano; i piani 03 e 05 aggiungono qui, PRIMA di questo
 * bottone, "Scarica catalogo domande" e "Carica file" — vive in un file suo
 * apposta perche' quei due piani girano in parallelo con quelli che toccano
 * `DomandePage.tsx`.
 */
export function ToolbarCatalogo({ onAggiungiDomanda }: { onAggiungiDomanda: () => void }) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <Button type="button" onClick={onAggiungiDomanda}>
        <Plus className="size-4" />
        Aggiungi domanda
      </Button>
    </div>
  );
}
