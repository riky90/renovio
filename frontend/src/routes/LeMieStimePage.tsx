import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, Navigate } from "react-router";
import { ArrowLeft, ArrowRight, CalendarDays, MapPin, Plus, Ruler, Sparkles } from "lucide-react";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { DettaglioProView } from "@/components/DettaglioProView";
import { SavedEstimateDetail } from "@/components/SavedEstimateDetail";
import { LeadContactDialog } from "@/components/LeadContactDialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { formatEurRange } from "@/lib/currency";
import { getStimaDettaglio, getStoricoStime, type StimaSalvataListItem } from "@/api/stima";
import { useAuth } from "@/hooks/useAuth";

const TIPO_LABELS: Record<string, string> = {
  leggera: "Leggera",
  moderata: "Moderata",
  totale: "Totale",
};

function formatData(iso: string): string {
  return new Date(iso).toLocaleDateString("it-IT");
}

/**
 * "I miei progetti" (ex "Le mie stime", UI-SPEC F): dashboard a card + empty
 * state + dettaglio immutabile (via getStimaDettaglio, mai ricalcolato).
 * Rotta protetta: anonimo -> redirect a /accedi.
 */
export function LeMieStimePage() {
  const { user, isLoading: isAuthLoading } = useAuth();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [contactOpen, setContactOpen] = useState(false);

  const storicoQuery = useQuery<StimaSalvataListItem[]>({
    queryKey: ["storico-stime"],
    queryFn: getStoricoStime,
    enabled: !!user,
  });

  // Il piano dell'utente. Serve solo per il teaser di upgrade e per offrire
  // il "rifai in versione Pro": NON decide quale vista mostrare.
  const isUtentePro = !!user?.pro;

  // Il tier CONGELATO della stima selezionata — questo si' decide la vista.
  // Letto dall'item di lista gia' in cache invece che dal dettaglio, cosi' non
  // c'e' un frame in cui si mostra la vista sbagliata mentre il dettaglio carica.
  const selected = storicoQuery.data?.find((item) => item.id === selectedId);
  const isStimaPro = selected?.tier === "pro";
  // Stessa destinazione del banner e del lucchetto sulle card (G14(f)).
  const rifaiProHref = selected
    ? `/nuova-stima?citta=${encodeURIComponent(selected.citta)}&mq=${selected.mq}&tipo=${selected.tipo}`
    : undefined;

  // Snapshot base immutabile della stima selezionata. Per il Pro il dettaglio
  // è ricalcolato da DettaglioProView, ma lo snapshot base serve comunque come
  // payload (a range, client-safe) del contatto lead — quindi lo carichiamo per
  // tutti gli utenti, non solo per i Free.
  const dettaglioQuery = useQuery({
    queryKey: ["stima-dettaglio", selectedId],
    queryFn: () => getStimaDettaglio(selectedId as number),
    enabled: selectedId !== null,
  });

  if (!isAuthLoading && !user) {
    return <Navigate to="/accedi" replace />;
  }

  return (
    <div className="flex min-h-svh flex-col bg-background">
      <SiteHeader />
      <main className="flex-1">
        <div className="mx-auto w-full max-w-4xl px-4 py-10 sm:px-6 sm:py-12">
          {selectedId !== null ? (
            <div className="mx-auto flex max-w-2xl flex-col gap-6">
              <button
                type="button"
                onClick={() => {
                  setContactOpen(false);
                  setSelectedId(null);
                }}
                className="flex items-center gap-1.5 self-start text-sm font-medium text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
              >
                <ArrowLeft className="size-4" /> I miei progetti
              </button>

              {isStimaPro ? (
                <DettaglioProView stimaId={selectedId} />
              ) : (
                <>
                  {isUtentePro && selected && (
                    <div className="flex flex-col gap-3 rounded-xl border border-primary/30 bg-accent/60 p-4 sm:flex-row sm:items-center sm:justify-between">
                      <p className="text-sm text-accent-foreground">
                        <span className="font-semibold">Questa stima è stata creata con il piano Free.</span>{" "}
                        Resta com'è: per il dettaglio voce per voce rifalla in versione Pro.
                      </p>
                      <Button asChild size="sm" className="shrink-0">
                        <Link to={rifaiProHref ?? "/nuova-stima"}>
                          <Sparkles className="size-4" /> Rifai in versione Pro
                        </Link>
                      </Button>
                    </div>
                  )}

                  {dettaglioQuery.isLoading && (
                    <div className="flex flex-col gap-4">
                      <Skeleton className="h-14 w-full" />
                      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                        {Array.from({ length: 4 }).map((_, i) => (
                          <Skeleton key={i} className="h-28 w-full" />
                        ))}
                      </div>
                      <Skeleton className="h-32 w-full" />
                    </div>
                  )}

                  {dettaglioQuery.isSuccess && dettaglioQuery.data && (
                    <SavedEstimateDetail
                      stima={dettaglioQuery.data}
                      rifaiProHref={isUtentePro ? rifaiProHref : undefined}
                    />
                  )}
                </>
              )}

              {dettaglioQuery.isSuccess && dettaglioQuery.data && (
                <div className="flex flex-col gap-3 border-t border-border pt-6">
                  <Button
                    type="button"
                    variant="outline"
                    className="h-11 w-full"
                    onClick={() => setContactOpen(true)}
                  >
                    Contatta un professionista
                  </Button>
                  <LeadContactDialog
                    open={contactOpen}
                    onOpenChange={setContactOpen}
                    result={dettaglioQuery.data}
                  />
                </div>
              )}
            </div>
          ) : (
            <>
              <header className="flex flex-wrap items-end justify-between gap-4">
                <div className="flex flex-col gap-1">
                  <h1 className="text-3xl font-bold text-foreground">I miei progetti</h1>
                  <p className="text-muted-foreground">
                    Le stime che hai salvato, sempre a portata di mano.
                  </p>
                </div>
                <Button asChild>
                  <Link to="/">
                    <Plus className="size-4" /> Nuova stima
                  </Link>
                </Button>
              </header>

              <div className="mt-8">
                {storicoQuery.isLoading && (
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    {Array.from({ length: 4 }).map((_, i) => (
                      <Skeleton key={i} className="h-36 w-full rounded-xl" />
                    ))}
                  </div>
                )}

                {storicoQuery.isSuccess && storicoQuery.data.length === 0 && (
                  <div className="flex flex-col items-center gap-4 rounded-2xl border border-dashed border-border bg-secondary/30 px-6 py-16 text-center">
                    <h2 className="text-xl font-bold text-foreground">
                      Non hai ancora progetti salvati
                    </h2>
                    <p className="max-w-sm text-sm text-muted-foreground">
                      Calcola una nuova stima per vederla qui: resterà salvata nel tuo account, con
                      tutti i dettagli.
                    </p>
                    <Button asChild className="h-11 px-6">
                      <Link to="/">
                        <Plus className="size-4" /> Nuova stima
                      </Link>
                    </Button>
                  </div>
                )}

                {storicoQuery.isSuccess && storicoQuery.data.length > 0 && (
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    {storicoQuery.data.map((item) => (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => setSelectedId(item.id)}
                        className="group flex flex-col gap-4 rounded-xl border border-border bg-card p-5 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <span className="flex items-center gap-2 font-display text-lg font-bold text-foreground">
                            <MapPin className="size-4 text-primary" aria-hidden />
                            {item.citta}
                          </span>
                          <span className="flex shrink-0 items-center gap-2">
                            {item.tier === "pro" && (
                              <Badge variant="secondary" className="text-[0.65rem] uppercase tracking-wide">
                                Pro
                              </Badge>
                            )}
                            <ArrowRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary" />
                          </span>
                        </div>

                        <span className="font-display text-xl font-bold tabular-nums text-foreground">
                          {formatEurRange(item.totale_min, item.totale_max)}
                        </span>

                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
                          <span className="flex items-center gap-1.5">
                            <Ruler className="size-3.5" aria-hidden /> {item.mq} m²
                          </span>
                          <span>{TIPO_LABELS[item.tipo] ?? item.tipo}</span>
                          <span className="flex items-center gap-1.5">
                            <CalendarDays className="size-3.5" aria-hidden />
                            {formatData(item.created_at)}
                          </span>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
