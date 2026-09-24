import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Power } from "lucide-react";
import { AdminTable } from "@/components/admin/AdminTable";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/api/admin/client";
import { EMPTY_HEADING } from "@/lib/adminCopy";
import {
  DOMANDE_QUERY_KEY,
  chiaveOpzioni,
  getOpzioni,
  updateOpzione,
  type DomandaOut,
  type OpzioneOut,
} from "@/api/admin/domande";

const SAVE_ERROR = "Non siamo riusciti a salvare la modifica. Riprova.";
const EMPTY_BODY_OPZIONI =
  "Aggiungi la prima opzione con il pulsante qui sopra, oppure carica un file.";

interface OpzioniSezioneProps {
  domanda: DomandaOut;
  selectedOpzioneId: number | null;
  onSelectOpzione: (id: number) => void;
  onChiudi: () => void;
}

/**
 * Secondo livello del master-detail (D-24): sotto la domanda scelta, le sue
 * opzioni. Il toggle Attiva puo' essere rifiutato dal backend (D-27/D-28) —
 * il `detail` arriva verbatim nel toast, mai riformulato. Nessun dialog di
 * conferma eliminazione, nessuna icona da cestino (D-39): questa pagina non
 * elimina.
 *
 * Non viene mai renderizzato per una domanda `stepper`/`numero` (D-35): lo
 * decide `DomandePage.tsx` con `isNumerico()`, non un filtro qui sulla lista
 * delle opzioni.
 */
export function OpzioniSezione({
  domanda,
  selectedOpzioneId,
  onSelectOpzione,
  onChiudi,
}: OpzioniSezioneProps) {
  const queryClient = useQueryClient();

  const opzioniQuery = useQuery<OpzioneOut[]>({
    queryKey: chiaveOpzioni(domanda.code),
    queryFn: () => getOpzioni(domanda.code),
  });

  const toggleMutation = useMutation({
    mutationFn: (row: OpzioneOut) => updateOpzione(row.id, { attiva: !row.attiva }),
    onSuccess: () => {
      toast.success("Modifica salvata");
      queryClient.invalidateQueries({ queryKey: DOMANDE_QUERY_KEY });
    },
    onError: (err) => {
      toast.error(err instanceof ApiError && err.detail ? err.detail : SAVE_ERROR);
    },
  });

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-foreground">Opzioni — {domanda.testo}</h2>
        <div className="flex items-center gap-2">
          <Button type="button" size="sm" variant="outline">
            Aggiungi opzione
          </Button>
          <Button type="button" size="sm" variant="ghost" onClick={onChiudi}>
            Chiudi
          </Button>
        </div>
      </div>

      <AdminTable
        columns={["Codice", "Etichetta", "Default", "Attiva", "Azioni"]}
        isLoading={opzioniQuery.isLoading}
        isEmpty={(opzioniQuery.data ?? []).length === 0}
        emptyHeading={EMPTY_HEADING}
        emptyBody={EMPTY_BODY_OPZIONI}
        rows={(opzioniQuery.data ?? []).map((row) => {
          const selected = row.id === selectedOpzioneId;
          const selezionaRiga = () => onSelectOpzione(row.id);
          return [
            <button
              type="button"
              key="codice"
              onClick={selezionaRiga}
              aria-expanded={selected}
              className="block w-full text-left"
            >
              {row.code}
            </button>,
            <button type="button" key="etichetta" onClick={selezionaRiga} className="block w-full text-left">
              {row.etichetta}
            </button>,
            row.is_default ? "Sì" : "",
            <Badge key="attiva" variant={row.attiva ? "default" : "secondary"}>
              {row.attiva ? "Attiva" : "Non attiva"}
            </Badge>,
            <div className="flex gap-1" key="azioni">
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                aria-label={row.attiva ? "Disattiva opzione" : "Riattiva opzione"}
                onClick={() => toggleMutation.mutate(row)}
              >
                <Power className="size-4" />
              </Button>
            </div>,
          ];
        })}
      />
    </div>
  );
}
