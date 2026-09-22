import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CityAutocomplete } from "@/components/CityAutocomplete";
import { NumberStepper } from "@/components/ui/number-stepper";
import { DomandaField } from "@/components/DomandaField";
import { formatEurRange } from "@/lib/currency";
import { TIPO_LABELS } from "@/lib/tipoRistrutturazione";
import {
  domandeVisibili,
  getCatalogoDomande,
  risposteIniziali,
  type CatalogoDomande,
  type Risposte,
  type ValoreRisposta,
} from "@/api/domande";
import { calcolaAnteprima, type Anteprima } from "@/api/admin/anteprima";

const CALCOLO_ERROR =
  "Non siamo riusciti a calcolare l'anteprima. Controlla i valori e riprova.";

const TIPI: Array<"leggera" | "moderata" | "totale"> = ["leggera", "moderata", "totale"];

/**
 * Sesta tab di `/admin/coefficienti` (PAR-04): un caso inventato (città, mq,
 * tipo, risposte) contro `POST /admin/domande/anteprima`, per vedere quali
 * effetti del catalogo sparano prima di passare da un caso reale nel wizard
 * pubblico. Riusa i componenti del wizard — `CityAutocomplete`,
 * `NumberStepper`, `DomandaField` — nessun clone.
 *
 * Il form non collassa e non si azzera dopo il calcolo (D-19): resta sopra il
 * risultato, cosi' l'admin cambia un valore e ricalcola senza ricompilare da
 * zero.
 */
export function AnteprimaTab() {
  const [citta, setCitta] = useState("");
  const [mq, setMq] = useState(85);
  const [tipo, setTipo] = useState<string>("moderata");
  const [risposte, setRisposte] = useState<Risposte>({});
  const [risposteToccate, setRisposteToccate] = useState(false);

  const catalogoQuery = useQuery<CatalogoDomande>({
    queryKey: ["admin-anteprima-catalogo", mq],
    queryFn: () => getCatalogoDomande({ tier: "pro", mq }),
  });

  const catalogo = catalogoQuery.data;

  // Stesso pattern di EstimateWizard: i default arrivano dal server e si
  // riapplicano a ogni cambio di m2, ma non sopra risposte gia' toccate.
  useEffect(() => {
    if (!catalogo) return;
    setRisposte((precedenti) => (risposteToccate ? precedenti : risposteIniziali(catalogo)));
  }, [catalogo, risposteToccate]);

  const visibili = useMemo(
    () => (catalogo ? domandeVisibili(catalogo.domande, risposte) : []),
    [catalogo, risposte]
  );

  const mutation = useMutation({
    mutationFn: () => calcolaAnteprima({ citta, mq, tipo, risposte }),
  });

  function handleRisposta(code: string, valore: ValoreRisposta) {
    setRisposteToccate(true);
    setRisposte((prev) => ({ ...prev, [code]: valore }));
  }

  const puoCalcolare = citta.trim().length > 0 && Number.isFinite(mq) && mq >= 1 && mq <= 2000;

  return (
    <div className="flex flex-col gap-6 pt-4">
      <form
        className="flex max-w-xl flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          mutation.mutate();
        }}
      >
        <CityAutocomplete value={citta} onChange={setCitta} />

        <div className="flex flex-col gap-2">
          <Label htmlFor="anteprima-mq">M²</Label>
          <NumberStepper id="anteprima-mq" value={mq} onChange={setMq} min={1} max={2000} />
        </div>

        <div className="flex flex-col gap-2">
          <Label htmlFor="anteprima-tipo">Tipo</Label>
          <Select value={tipo} onValueChange={setTipo}>
            <SelectTrigger id="anteprima-tipo">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TIPI.map((t) => (
                <SelectItem key={t} value={t}>
                  {TIPO_LABELS[t]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {visibili.map((domanda) => (
          <DomandaField
            key={domanda.code}
            domanda={domanda}
            valore={risposte[domanda.code]}
            onChange={(valore) => handleRisposta(domanda.code, valore)}
          />
        ))}

        <div className="flex flex-col gap-2">
          <Button type="submit" disabled={!puoCalcolare || mutation.isPending}>
            {mutation.isPending ? "Calcolo…" : "Calcola anteprima"}
          </Button>
          {mutation.isError && <p className="text-sm text-destructive">{CALCOLO_ERROR}</p>}
        </div>
      </form>

      {mutation.data && <RisultatoAnteprima anteprima={mutation.data} />}
    </div>
  );
}

/** Placeholder minimo: il breakdown per categoria e la tabella effetti arrivano nel Task 3. */
function RisultatoAnteprima({ anteprima }: { anteprima: Anteprima }) {
  return (
    <div className="text-sm tabular-nums text-foreground">
      Totale: {formatEurRange(anteprima.totale_min, anteprima.totale_max)}
    </div>
  );
}
