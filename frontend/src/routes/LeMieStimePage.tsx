import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, Navigate } from "react-router";
import { AccountMenu } from "@/components/AccountMenu";
import { SavedEstimateDetail } from "@/components/SavedEstimateDetail";
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
 * Storico "Le mie stime" (UI-SPEC F): lista + empty state + dettaglio
 * immutabile (via getStimaDettaglio, mai ricalcolato). Rotta protetta:
 * anonimo -> redirect a /accedi.
 */
export function LeMieStimePage() {
  const { user, isLoading: isAuthLoading } = useAuth();
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const storicoQuery = useQuery<StimaSalvataListItem[]>({
    queryKey: ["storico-stime"],
    queryFn: getStoricoStime,
    enabled: !!user,
  });

  const dettaglioQuery = useQuery({
    queryKey: ["stima-dettaglio", selectedId],
    queryFn: () => getStimaDettaglio(selectedId as number),
    enabled: selectedId !== null,
  });

  if (!isAuthLoading && !user) {
    return <Navigate to="/accedi" replace />;
  }

  return (
    <main className="mx-auto flex min-h-svh w-full max-w-[480px] flex-col gap-8 px-4 py-8 sm:max-w-[640px] sm:px-6 sm:py-12 lg:py-16">
      <Link
        to="/"
        className="self-start text-sm font-medium text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
      >
        ← Torna alla home
      </Link>

      <div className="flex items-center justify-between gap-3">
        <h1 className="text-lg font-semibold text-foreground">Le mie stime</h1>
        {user && !isAuthLoading ? (
          <AccountMenu user={user} />
        ) : (
          <Skeleton className="size-8 rounded-full" />
        )}
      </div>

      {selectedId !== null ? (
        <div className="flex flex-col gap-6">
          <button
            type="button"
            onClick={() => setSelectedId(null)}
            className="self-start text-sm font-medium text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
          >
            ← Le mie stime
          </button>

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
            <SavedEstimateDetail stima={dettaglioQuery.data} />
          )}
        </div>
      ) : (
        <>
          {storicoQuery.isLoading && (
            <div className="flex flex-col gap-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          )}

          {storicoQuery.isSuccess && storicoQuery.data.length === 0 && (
            <div className="flex flex-col items-center gap-4 py-12 text-center">
              <h2 className="text-lg font-semibold text-foreground">
                Non hai ancora stime salvate
              </h2>
              <p className="max-w-sm text-sm text-muted-foreground">
                Calcola una nuova stima per vederla qui: resterà salvata nel tuo account, con
                tutti i dettagli.
              </p>
              <Button asChild className="h-11 bg-primary text-primary-foreground hover:bg-primary/90">
                <Link to="/">Nuova stima</Link>
              </Button>
            </div>
          )}

          {storicoQuery.isSuccess && storicoQuery.data.length > 0 && (
            <div className="flex flex-col gap-2">
              {storicoQuery.data.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setSelectedId(item.id)}
                  className="flex min-h-11 flex-col gap-1 rounded-lg border border-border bg-secondary px-4 py-3 text-left transition-colors hover:border-muted-foreground/40"
                >
                  <span className="flex items-center justify-between gap-3 text-sm font-semibold text-foreground">
                    <span>{item.citta}</span>
                    <span className="tabular-nums">
                      {formatEurRange(item.totale_min, item.totale_max)}
                    </span>
                  </span>
                  <span className="text-sm text-muted-foreground">
                    {item.mq} m² · {TIPO_LABELS[item.tipo] ?? item.tipo} ·{" "}
                    {formatData(item.created_at)}
                  </span>
                </button>
              ))}
            </div>
          )}
        </>
      )}
    </main>
  );
}
