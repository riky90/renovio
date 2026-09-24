import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Power } from "lucide-react";
import { AdminTable } from "@/components/admin/AdminTable";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/api/admin/client";
import { EMPTY_HEADING } from "@/lib/adminCopy";
import { TIPO_LABELS } from "@/lib/tipoRistrutturazione";
import { isNumerico } from "@/api/domande";
import {
  DOMANDE_QUERY_KEY,
  chiaveEffetti,
  getEffetti,
  updateEffetto,
  type DomandaOut,
  type OpzioneOut,
  type EffettoOut,
} from "@/api/admin/domande";
import { ETICHETTE_TIPO_EFFETTO, formattaValore } from "@/pages/admin/domande/effetti";

const SAVE_ERROR = "Non siamo riusciti a salvare la modifica. Riprova.";
const EMPTY_BODY_EFFETTI =
  "Aggiungi il primo effetto con il pulsante qui sopra, oppure carica un file.";

interface EffettiSezioneProps {
  domanda: DomandaOut;
  opzione: OpzioneOut;
  onChiudi: () => void;
}

function bersaglioReso(bersaglio: string) {
  const segmenti = bersaglio.split(" › ");
  return segmenti.map((segmento, i) => (
    <span key={i}>
      {segmento}
      {i < segmenti.length - 1 && <span className="text-muted-foreground"> › </span>}
    </span>
  ));
}

/**
 * Terzo livello del master-detail (D-24): cosa fa al calcolo la risposta
 * scelta. Per le domande a scelta il titolo nomina l'opzione; per le
 * domande stepper/numero nomina direttamente la domanda (D-35), perche' li'
 * il livello Opzioni non compare mai e questa sezione si apre sull'opzione
 * implicita `valore`. Nessun dialog di conferma eliminazione, nessuna icona
 * da cestino: questa pagina non elimina.
 */
export function EffettiSezione({ domanda, opzione, onChiudi }: EffettiSezioneProps) {
  const queryClient = useQueryClient();

  const effettiQuery = useQuery<EffettoOut[]>({
    queryKey: chiaveEffetti(domanda.code),
    queryFn: () => getEffetti(domanda.code),
  });

  const effetti = (effettiQuery.data ?? []).filter((e) => e.opzione_id === opzione.id);

  const toggleMutation = useMutation({
    mutationFn: (row: EffettoOut) => updateEffetto(row.id, { attivo: !row.attivo }),
    onSuccess: () => {
      toast.success("Modifica salvata");
      queryClient.invalidateQueries({ queryKey: DOMANDE_QUERY_KEY });
    },
    onError: (err) => {
      toast.error(err instanceof ApiError && err.detail ? err.detail : SAVE_ERROR);
    },
  });

  const titolo = isNumerico(domanda.tipo_controllo)
    ? `Effetti — ${domanda.testo}`
    : `Effetti — ${opzione.etichetta}`;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-foreground">{titolo}</h2>
        <div className="flex items-center gap-2">
          <Button type="button" size="sm" variant="outline">
            Aggiungi effetto
          </Button>
          <Button type="button" size="sm" variant="ghost" onClick={onChiudi}>
            Chiudi
          </Button>
        </div>
      </div>

      <AdminTable
        columns={["Tipo effetto", "Bersaglio", "Tipo", "Valore", "Attivo", "Azioni"]}
        isLoading={effettiQuery.isLoading}
        isEmpty={effetti.length === 0}
        emptyHeading={EMPTY_HEADING}
        emptyBody={EMPTY_BODY_EFFETTI}
        rows={effetti.map((row) => [
          ETICHETTE_TIPO_EFFETTO[row.tipo_effetto],
          <span key="bersaglio">{bersaglioReso(row.bersaglio)}</span>,
          row.tipo_code ? TIPO_LABELS[row.tipo_code] : "Tutti i tipi",
          <span
            key="valore"
            className={row.valore === null ? "text-muted-foreground" : undefined}
          >
            {formattaValore(row.tipo_effetto, row.valore)}
          </span>,
          <Badge key="attivo" variant={row.attivo ? "default" : "secondary"}>
            {row.attivo ? "Attivo" : "Non attivo"}
          </Badge>,
          <div className="flex gap-1" key="azioni">
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              aria-label={row.attivo ? "Disattiva effetto" : "Riattiva effetto"}
              onClick={() => toggleMutation.mutate(row)}
            >
              <Power className="size-4" />
            </Button>
          </div>,
        ])}
      />
    </div>
  );
}
