import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Loader2 } from "lucide-react";
import { SottocategoriaAccordion } from "@/components/SottocategoriaAccordion";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { formatEurRange } from "@/lib/currency";
import { cn } from "@/lib/utils";
import {
  getDettaglioPro,
  postRisposteDettaglioPro,
  scaricaPdfPro,
  type LivelliPerCategoria,
  type RisposteDomande,
} from "@/api/dettaglio-pro";

const DOMANDE_SUBHEADING =
  "Rispondi per affinare le quantità stimate (facoltativo: se salti, usiamo una stima prudente in base ai metri quadri).";
const DEFAULT_NOTE =
  "Se salti una domanda, usiamo una stima prudente basata sui metri quadri dell'immobile.";
const CALC_ERROR_COPY = "Non siamo riusciti a calcolare il dettaglio. Controlla i dati e riprova.";
const PDF_ERROR_COPY = "Non siamo riusciti a generare il PDF. Riprova tra qualche istante.";
const VALIDATION_COPY = "Inserisci un numero valido (0 o superiore).";
const LIVELLI_SUBHEADING =
  "Scegli il livello di finitura: cambia i materiali considerati nel computo, non le lavorazioni.";

type RisposteInput = Record<keyof RisposteDomande, string>;

const FIELD_LABELS: Record<keyof RisposteDomande, string> = {
  bagni: "Quanti bagni ha l'immobile?",
  porte: "Quante porte interne vanno sostituite?",
  condizionatori: "Quanti climatizzatori vuoi installare?",
};

function toRisposteInput(r: RisposteDomande): RisposteInput {
  return {
    bagni: String(r.bagni),
    porte: String(r.porte),
    condizionatori: String(r.condizionatori),
  };
}

function isValid(input: RisposteInput): boolean {
  return (Object.keys(input) as (keyof RisposteInput)[]).every((key) => {
    const n = Number(input[key]);
    return Number.isFinite(n) && n >= 0 && Number.isInteger(n);
  });
}

interface DettaglioProViewProps {
  /** id della stima salvata su cui calcolare il dettaglio (require_pro server-side). */
  stimaId: number;
  /** Abilita la query: false finché lo stima id non è pronto (es. auto-save in corso). */
  enabled?: boolean;
}

/**
 * Vista dettaglio Pro condivisa (domande mirate + accordion per sottocategoria
 * a range + totali backend + "Scarica PDF dettagliato"). Estratta da
 * DettaglioProPage così home, pagina dedicata e "Le mie stime" mostrano lo
 * STESSO dettaglio e non possono divergere. Il gate reale resta server-side
 * (require_pro su ogni endpoint); questo componente assume un utente Pro.
 */
export function DettaglioProView({ stimaId, enabled = true }: DettaglioProViewProps) {
  const queryClient = useQueryClient();

  const [risposteInput, setRisposteInput] = useState<RisposteInput>({
    bagni: "0",
    porte: "0",
    condizionatori: "0",
  });
  const [livelliInput, setLivelliInput] = useState<LivelliPerCategoria>({});
  const [domandeCollassate, setDomandeCollassate] = useState(false);
  const [usataStimaAutomatica, setUsataStimaAutomatica] = useState(false);
  const [initialized, setInitialized] = useState(false);

  const dettaglioQuery = useQuery({
    queryKey: ["dettaglio-pro", stimaId],
    queryFn: () => getDettaglioPro(stimaId),
    enabled: enabled && Number.isFinite(stimaId),
  });

  const risposteMutation = useMutation({
    mutationFn: (risposte: RisposteDomande) =>
      postRisposteDettaglioPro(stimaId, risposte, livelliInput),
    onSuccess: (data) => {
      queryClient.setQueryData(["dettaglio-pro", stimaId], data);
      setDomandeCollassate(true);
    },
  });

  const pdfMutation = useMutation({ mutationFn: () => scaricaPdfPro(stimaId) });

  useEffect(() => {
    if (!initialized && dettaglioQuery.data) {
      setRisposteInput(toRisposteInput(dettaglioQuery.data.risposte));
      // I livelli si inizializzano dall'ECO del server, non da un default nel
      // client: così il selettore mostra ciò che è stato davvero applicato.
      setLivelliInput(dettaglioQuery.data.livelli);
      // Flag ESPLICITO dal server, non la somma delle risposte: `{0, 0, 0}` è
      // una risposta legittima — ed è esattamente quella che invia il form Pro
      // di chi non ha bagni da rifare. Dedurlo dalla somma riaprirebbe il
      // pannello domande addosso a chi ha appena risposto.
      setDomandeCollassate(dettaglioQuery.data.risposte_salvate);
      setInitialized(true);
    }
  }, [dettaglioQuery.data, initialized]);

  function handleFieldChange(field: keyof RisposteDomande, value: string) {
    setRisposteInput((prev) => ({ ...prev, [field]: value }));
  }

  function handleLivelloChange(categoriaCode: string, livelloCode: string) {
    setLivelliInput((prev) => ({ ...prev, [categoriaCode]: livelloCode }));
  }

  function handleCalcola() {
    if (!isValid(risposteInput)) return;
    setUsataStimaAutomatica(false);
    risposteMutation.mutate({
      bagni: Number(risposteInput.bagni),
      porte: Number(risposteInput.porte),
      condizionatori: Number(risposteInput.condizionatori),
    });
  }

  function handleSalta() {
    setUsataStimaAutomatica(true);
    risposteMutation.mutate({ bagni: 0, porte: 0, condizionatori: 0 });
  }

  const validationError = !isValid(risposteInput);

  if (dettaglioQuery.isLoading || !enabled) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-40 w-full" />
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-32 w-full" />
        ))}
      </div>
    );
  }

  if (dettaglioQuery.isError) {
    return (
      <div className="flex flex-col gap-4">
        <Alert variant="destructive">
          <AlertDescription>{CALC_ERROR_COPY}</AlertDescription>
        </Alert>
        <Button type="button" onClick={() => dettaglioQuery.refetch()} className="w-full">
          Riprova
        </Button>
      </div>
    );
  }

  if (!dettaglioQuery.data) {
    return null;
  }

  const dettaglio = dettaglioQuery.data;
  // Quali categorie mostrano un selettore lo decide il SERVER (`livello_scelto`
  // non nullo = categoria selezionabile). Nessun codice categoria cablato qui.
  const categorieConLivello = dettaglio.categorie.filter((cat) => cat.livello_scelto !== null);
  const livelliDisponibili = dettaglio.livelli_disponibili;
  const nomiLivelli = Object.fromEntries(
    dettaglio.livelli_disponibili.map((livello) => [livello.code, livello.nome])
  );
  const riepilogoLivelli = categorieConLivello
    .map((cat) => `${cat.nome}: ${cat.livello_scelto_nome ?? cat.livello_scelto}`)
    .join(" · ");

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-4 rounded-lg border border-border bg-secondary p-6">
        <h2 className="text-base font-semibold text-foreground">Qualche dettaglio in più</h2>
        {domandeCollassate ? (
          <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-foreground">
            <span>
              {usataStimaAutomatica
                ? "Stima automatica"
                : `Bagni: ${risposteInput.bagni} · Porte: ${risposteInput.porte} · Climatizzatori: ${risposteInput.condizionatori}`}
              {riepilogoLivelli && (
                <span className="block text-muted-foreground">{riepilogoLivelli}</span>
              )}
            </span>
            <button
              type="button"
              onClick={() => setDomandeCollassate(false)}
              className="text-sm font-medium text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
            >
              Modifica
            </button>
          </div>
        ) : (
          <>
            {categorieConLivello.length > 0 && livelliDisponibili.length > 0 && (
              <div className="flex flex-col gap-4">
                <p className="text-sm text-muted-foreground">{LIVELLI_SUBHEADING}</p>
                {categorieConLivello.map((categoria) => (
                  <div key={categoria.code} className="flex flex-col gap-2">
                    <Label>{categoria.nome}</Label>
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                      {livelliDisponibili.map((livello) => {
                        const selected =
                          (livelliInput[categoria.code] ?? categoria.livello_scelto) === livello.code;
                        return (
                          <button
                            key={livello.code}
                            type="button"
                            onClick={() => handleLivelloChange(categoria.code, livello.code)}
                            aria-pressed={selected}
                            className={cn(
                              "relative flex min-h-11 flex-col gap-1 rounded-lg border px-4 py-3 text-left transition-all",
                              selected
                                ? "border-primary bg-accent shadow-sm ring-1 ring-primary"
                                : "border-border bg-card hover:border-primary/40 hover:bg-accent/40"
                            )}
                          >
                            {selected && (
                              <span className="absolute right-2.5 top-2.5 flex size-4 items-center justify-center rounded-full bg-primary text-primary-foreground">
                                <Check className="size-3" aria-hidden />
                              </span>
                            )}
                            <span className="text-sm font-semibold">{livello.nome}</span>
                            {livello.descrizione && (
                              <span className="text-sm text-muted-foreground">
                                {livello.descrizione}
                              </span>
                            )}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}

            <p className="text-sm text-muted-foreground">{DOMANDE_SUBHEADING}</p>
            <div className="flex flex-col gap-3">
              {(Object.keys(FIELD_LABELS) as (keyof RisposteDomande)[]).map((field) => (
                <div key={field} className="flex flex-col gap-1">
                  <Label htmlFor={field}>{FIELD_LABELS[field]}</Label>
                  <Input
                    id={field}
                    inputMode="numeric"
                    min={0}
                    value={risposteInput[field]}
                    onChange={(e) => handleFieldChange(field, e.target.value)}
                    className="tabular-nums"
                  />
                </div>
              ))}
            </div>
            {validationError && <p className="text-sm text-destructive">{VALIDATION_COPY}</p>}
            <div className="rounded-md border border-amber-border bg-amber-bg px-3 py-2">
              <p className="text-sm text-amber-fg">{DEFAULT_NOTE}</p>
            </div>
            <div className="flex flex-col gap-2 sm:flex-row">
              <Button
                type="button"
                onClick={handleCalcola}
                disabled={risposteMutation.isPending || validationError}
                className="h-11 flex-1 bg-primary text-base font-semibold text-primary-foreground hover:bg-primary/90"
              >
                {risposteMutation.isPending && !usataStimaAutomatica ? (
                  <span className="flex items-center justify-center gap-2">
                    <Loader2 className="size-4 animate-spin" aria-hidden />
                    Calcolo in corso…
                  </span>
                ) : (
                  "Calcola il dettaglio"
                )}
              </Button>
              <button
                type="button"
                onClick={handleSalta}
                disabled={risposteMutation.isPending}
                className="text-sm font-medium text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
              >
                Salta, usa la stima automatica
              </button>
            </div>
          </>
        )}
      </div>

      <div className="flex flex-col gap-6">
        {dettaglio.categorie.map((categoria) => (
          <SottocategoriaAccordion
            key={categoria.code}
            categoria={categoria}
            nomiLivelli={nomiLivelli}
          />
        ))}
      </div>

      <div className="flex flex-wrap items-baseline justify-between gap-3 rounded-lg border-2 border-primary bg-primary/5 px-5 py-4">
        <span className="text-base font-semibold text-foreground">Totale generale stimato</span>
        <span className="text-xl font-bold tabular-nums text-primary">
          {formatEurRange(dettaglio.totale_min, dettaglio.totale_max)}
        </span>
      </div>

      <div className="flex flex-col gap-2">
        <Button
          type="button"
          onClick={() => pdfMutation.mutate()}
          disabled={pdfMutation.isPending}
          className="h-11 w-full bg-primary text-base font-semibold text-primary-foreground hover:bg-primary/90"
        >
          {pdfMutation.isPending ? (
            <span className="flex items-center justify-center gap-2">
              <Loader2 className="size-4 animate-spin" aria-hidden />
              Generazione in corso…
            </span>
          ) : (
            "Scarica PDF dettagliato"
          )}
        </Button>
        {pdfMutation.isError && (
          <p className="text-center text-sm text-destructive">{PDF_ERROR_COPY}</p>
        )}
      </div>
    </div>
  );
}
