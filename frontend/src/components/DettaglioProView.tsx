import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Loader2 } from "lucide-react";
import { DomandaField } from "@/components/DomandaField";
import { SottocategoriaAccordion } from "@/components/SottocategoriaAccordion";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { formatEurRange } from "@/lib/currency";
import { cn } from "@/lib/utils";
import { isNumerico, type ValoreRisposta } from "@/api/domande";
import {
  getDettaglioPro,
  postRisposteDettaglioPro,
  scaricaPdfPro,
  type DomandaProOut,
  type LivelliPerCategoria,
} from "@/api/dettaglio-pro";

const DOMANDE_SUBHEADING =
  "Rispondi per affinare le quantità stimate (facoltativo: se salti, usiamo una stima prudente in base ai metri quadri).";
const DEFAULT_NOTE =
  "Se salti una domanda, usiamo i default: finitura media, pavimento gres, quantità stimate sui metri quadri.";
const CALC_ERROR_COPY = "Non siamo riusciti a calcolare il dettaglio. Controlla i dati e riprova.";
const PDF_ERROR_COPY = "Non siamo riusciti a generare il PDF. Riprova tra qualche istante.";
const LIVELLI_SUBHEADING =
  "Scegli il livello di finitura: cambia i materiali considerati nel computo, non le lavorazioni.";

/**
 * Etichette del riepilogo collassato — SOLO presentazione (UI-SPEC
 * §Copywriting): non governano il calcolo, solo l'ordine/nome con cui il
 * riepilogo mostra le domande che gia' conosciamo. Un codice non in mappa
 * cade su `domanda.testo`, cosi' una domanda futura del configuratore non
 * sparisce dal riepilogo in attesa di una voce qui.
 */
const ETICHETTE_RIEPILOGO: Record<string, string> = {
  bagni: "Bagni",
  porte: "Porte",
  condizionatori: "Climatizzatori",
  tipo_pavimento: "Pavimento",
};

function risposteIniziali(domande: DomandaProOut[]): Record<string, ValoreRisposta> {
  const risposte: Record<string, ValoreRisposta> = {};
  for (const domanda of domande) {
    if (domanda.valore !== null) {
      risposte[domanda.code] = domanda.valore;
    }
  }
  return risposte;
}

function etichettaValore(domanda: DomandaProOut): string {
  return domanda.valore_etichetta ?? String(domanda.valore ?? "");
}

interface DettaglioProViewProps {
  /** id della stima salvata su cui calcolare il dettaglio (require_pro server-side). */
  stimaId: number;
  /** Abilita la query: false finché lo stima id non è pronto (es. auto-save in corso). */
  enabled?: boolean;
}

/**
 * Vista dettaglio Pro condivisa (domande del configuratore + accordion per
 * sottocategoria a range + totali backend + "Scarica PDF dettagliato").
 * Estratta da DettaglioProPage così home, pagina dedicata e "Le mie stime"
 * mostrano lo STESSO dettaglio e non possono divergere. Il gate reale resta
 * server-side (require_pro su ogni endpoint); questo componente assume un
 * utente Pro.
 *
 * Le domande a scelta/stepper del pannello arrivano dal catalogo
 * (`dettaglio.domande`, DomandaProOut) e si disegnano con `DomandaField`
 * (CFG-01/QST-05): nessuna etichetta cablata qui dentro, a differenza di
 * prima del 09-05.
 */
export function DettaglioProView({ stimaId, enabled = true }: DettaglioProViewProps) {
  const queryClient = useQueryClient();

  const [risposteInput, setRisposteInput] = useState<Record<string, ValoreRisposta>>({});
  const [livelliInput, setLivelliInput] = useState<LivelliPerCategoria>({});
  const [domandeCollassate, setDomandeCollassate] = useState(false);
  const [initialized, setInitialized] = useState(false);

  const dettaglioQuery = useQuery({
    queryKey: ["dettaglio-pro", stimaId],
    queryFn: () => getDettaglioPro(stimaId),
    enabled: enabled && Number.isFinite(stimaId),
  });

  const risposteMutation = useMutation({
    mutationFn: (risposte: Record<string, number | string>) =>
      postRisposteDettaglioPro(stimaId, risposte, livelliInput),
    onSuccess: (data) => {
      queryClient.setQueryData(["dettaglio-pro", stimaId], data);
      setDomandeCollassate(true);
    },
  });

  /**
   * Cambio di una domanda a scelta (es. pavimento), sempre visibile fuori dal
   * pannello collassato (09-12, gap G3): ricalcola SUBITO, senza passare da
   * "Modifica"/"Calcola il dettaglio" (D-06). `onSuccess` ricollassa comunque
   * il pannello — il blocco del pavimento resta visibile lo stesso, e' fuori
   * dall'alternativa collassato/espanso.
   */
  function handleSceltaChange(code: string, valore: ValoreRisposta) {
    // Nessun invio concorrente (T-09-52): finche' una mutation e' in corso, un
    // secondo click su un'altra opzione non parte.
    if (risposteMutation.isPending) return;
    const aggiornate = { ...risposteInput, [code]: valore };
    setRisposteInput(aggiornate);
    risposteMutation.mutate(aggiornate as Record<string, number | string>);
  }

  const pdfMutation = useMutation({ mutationFn: () => scaricaPdfPro(stimaId) });

  useEffect(() => {
    if (!initialized && dettaglioQuery.data) {
      // I valori iniziali arrivano gia' risolti dal server (D-07: risposta
      // salvata o default di catalogo) — nessun default nel client.
      setRisposteInput(risposteIniziali(dettaglioQuery.data.domande));
      setLivelliInput(dettaglioQuery.data.livelli);
      setDomandeCollassate(dettaglioQuery.data.risposte_salvate);
      setInitialized(true);
    }
  }, [dettaglioQuery.data, initialized]);

  function handleFieldChange(code: string, valore: ValoreRisposta) {
    setRisposteInput((prev) => ({ ...prev, [code]: valore }));
  }

  function handleLivelloChange(categoriaCode: string, livelloCode: string) {
    setLivelliInput((prev) => ({ ...prev, [categoriaCode]: livelloCode }));
  }

  function handleCalcola() {
    risposteMutation.mutate(risposteInput as Record<string, number | string>);
  }

  function handleSalta() {
    risposteMutation.mutate({});
  }

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

  // Ordine del riepilogo (UI-SPEC §Copywriting): le numeriche (bagni/porte/
  // condizionatori) prima, le domande a scelta (pavimento) dopo — anche se
  // il catalogo le ordina diversamente (pavimento ha `ordine` minore).
  const domandeNumeriche = dettaglio.domande.filter((d) => isNumerico(d.tipo_controllo));
  const domandeScelta = dettaglio.domande.filter((d) => !isNumerico(d.tipo_controllo));
  const riepilogoDomande = [...domandeNumeriche, ...domandeScelta]
    .map((d) => `${ETICHETTE_RIEPILOGO[d.code] ?? d.testo}: ${etichettaValore(d)}`)
    .join(" · ");

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-4 rounded-lg border border-border bg-secondary p-6">
        <h2 className="text-base font-semibold text-foreground">Qualche dettaglio in più</h2>

        {/* Domande a scelta (pavimento incluso): SEMPRE visibili, fuori
            dall'alternativa collassato/espanso (09-12, gap G3) — cambiarle
            ricalcola subito, senza aprire il pannello con "Modifica". */}
        {domandeScelta.length > 0 && (
          <div className="flex flex-col gap-4">
            {domandeScelta.map((domanda) => (
              <DomandaField
                key={domanda.code}
                domanda={domanda}
                valore={risposteInput[domanda.code] ?? domanda.valore ?? undefined}
                onChange={(valore) => handleSceltaChange(domanda.code, valore)}
                griglia={domanda.opzioni.length === 4 ? "due-colonne" : undefined}
              />
            ))}
            {risposteMutation.isPending && (
              <span className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="size-4 animate-spin" aria-hidden />
                Ricalcolo in corso…
              </span>
            )}
            {risposteMutation.isError && (
              <Alert variant="destructive">
                <AlertDescription>{CALC_ERROR_COPY}</AlertDescription>
              </Alert>
            )}
          </div>
        )}

        {domandeCollassate ? (
          <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-foreground">
            <span>
              {riepilogoDomande}
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

            {domandeNumeriche.length > 0 && (
              <>
                <p className="text-sm text-muted-foreground">{DOMANDE_SUBHEADING}</p>
                <div className="flex flex-col gap-3">
                  {domandeNumeriche.map((domanda) => (
                    <DomandaField
                      key={domanda.code}
                      domanda={domanda}
                      valore={risposteInput[domanda.code] ?? domanda.valore ?? undefined}
                      onChange={(valore) => handleFieldChange(domanda.code, valore)}
                    />
                  ))}
                </div>
              </>
            )}

            <div className="rounded-md border border-amber-border bg-amber-bg px-3 py-2">
              <p className="text-sm text-amber-fg">{DEFAULT_NOTE}</p>
            </div>
            <div className="flex flex-col gap-2 sm:flex-row">
              <Button
                type="button"
                onClick={handleCalcola}
                disabled={risposteMutation.isPending}
                className="h-11 flex-1 bg-primary text-base font-semibold text-primary-foreground hover:bg-primary/90"
              >
                {risposteMutation.isPending ? (
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
