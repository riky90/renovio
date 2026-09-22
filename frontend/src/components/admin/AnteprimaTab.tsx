import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { TrendingDown, TrendingUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { AdminTable } from "@/components/admin/AdminTable";
import { CityAutocomplete } from "@/components/CityAutocomplete";
import { NumberStepper } from "@/components/ui/number-stepper";
import { DomandaField } from "@/components/DomandaField";
import { formatEurRange } from "@/lib/currency";
import { TIPO_LABELS } from "@/lib/tipoRistrutturazione";
import { EMPTY_HEADING, EMPTY_BODY } from "@/lib/adminCopy";
import {
  domandeVisibili,
  getCatalogoDomande,
  risposteIniziali,
  type CatalogoDomande,
  type Risposte,
  type ValoreRisposta,
} from "@/api/domande";
import {
  calcolaAnteprima,
  type Anteprima,
  type AnteprimaCategoria,
  type EffettoTraccia,
} from "@/api/admin/anteprima";

const CALCOLO_ERROR =
  "Non siamo riusciti a calcolare l'anteprima. Controlla i valori e riprova.";

const TIPI: Array<"leggera" | "moderata" | "totale"> = ["leggera", "moderata", "totale"];

/** Le otto voci chiuse di `services/effetti.py::TIPI_EFFETTO`, per etichettare la colonna. */
const TIPO_EFFETTO_LABELS: Record<string, string> = {
  moltiplicatore_categoria: "Moltiplicatore categoria",
  eur_mq_categoria: "€/m² categoria",
  eur_fisso_categoria: "€ fisso categoria",
  eur_per_scostamento: "€ per scostamento",
  includi: "Includi",
  escludi: "Escludi",
  fattore_quantita: "Fattore quantità",
  quantita_per_unita: "Quantità per unità",
};

function formatNumero(valore: number | null): string {
  if (valore === null) return "—";
  return valore.toLocaleString("it-IT", { maximumFractionDigits: 3 });
}

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

function RisultatoAnteprima({ anteprima }: { anteprima: Anteprima }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {anteprima.categorie.map((categoria) => (
          <CategoriaCard key={categoria.code} categoria={categoria} />
        ))}
      </div>

      {anteprima.avvisi.length > 0 && (
        <div className="rounded-lg border border-amber-border bg-amber-bg px-4 py-3 text-sm text-amber-fg">
          {anteprima.avvisi.map((avviso, i) => (
            <p key={i}>{avviso}</p>
          ))}
        </div>
      )}

      <AdminTable
        columns={["Domanda", "Opzione", "Tipo effetto", "Categoria", "Valore", "Contributo", "Stato"]}
        isLoading={false}
        isEmpty={anteprima.effetti.length === 0}
        emptyHeading={EMPTY_HEADING}
        emptyBody={EMPTY_BODY}
        rows={anteprima.effetti.map((effetto, i) => rigaEffetto(effetto, i))}
      />
    </div>
  );
}

function CategoriaCard({ categoria }: { categoria: AnteprimaCategoria }) {
  const deltaPositivo = categoria.delta_min + categoria.delta_max >= 0;
  const IconaDelta = deltaPositivo ? TrendingUp : TrendingDown;

  return (
    <div className="flex flex-col gap-1 rounded-xl border border-border bg-card p-4">
      <span className="text-sm font-semibold text-foreground">{categoria.nome}</span>
      <span className="text-sm tabular-nums text-muted-foreground">
        {formatEurRange(categoria.base_min, categoria.base_max)}
      </span>
      <span className="text-sm font-semibold tabular-nums text-foreground">
        {formatEurRange(categoria.totale_min, categoria.totale_max)}
      </span>
      <span className="flex items-center gap-1 text-sm tabular-nums text-foreground">
        <IconaDelta className="size-3.5" aria-hidden />
        Δ {formatEurRange(categoria.delta_min, categoria.delta_max)}
      </span>
    </div>
  );
}

function rigaEffetto(effetto: EffettoTraccia, i: number) {
  return [
    effetto.domanda_code,
    effetto.opzione_code,
    TIPO_EFFETTO_LABELS[effetto.tipo_effetto] ?? effetto.tipo_effetto,
    effetto.categoria_code ?? "—",
    <div key={`valore-${i}`}>
      <span className="tabular-nums">{formatNumero(effetto.valore)}</span>
      {effetto.nota && <p className="text-xs text-muted-foreground">{effetto.nota}</p>}
    </div>,
    <span key={`contributo-${i}`} className="tabular-nums">
      {formatNumero(effetto.contributo)}
    </span>,
    effetto.applicato ? (
      <Badge key={`stato-${i}`} className="bg-primary/10 text-primary">
        Applicato
      </Badge>
    ) : (
      <Badge key={`stato-${i}`} variant="outline">
        Non applicato
      </Badge>
    ),
  ];
}
