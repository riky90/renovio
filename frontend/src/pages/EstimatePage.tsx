import { useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link } from "react-router";
import { CategoryCard } from "@/components/CategoryCard";
import { DettaglioProView } from "@/components/DettaglioProView";
import { EstimateForm, type EstimateFormValues } from "@/components/EstimateForm";
import { FallbackDisclaimer } from "@/components/FallbackDisclaimer";
import { SoftWallCta } from "@/components/SoftWallCta";
import { TotalCard } from "@/components/TotalCard";
import { AccountMenu } from "@/components/AccountMenu";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { formatEur } from "@/lib/currency";
import { postSalvaStima, postStima, type StimaResponse } from "@/api/stima";
import { useAuth } from "@/hooks/useAuth";

const TIPO_LABELS: Record<EstimateFormValues["tipo"], string> = {
  leggera: "Leggera",
  moderata: "Moderata",
  totale: "Totale",
};

const ERROR_COPY =
  "Non siamo riusciti a calcolare la stima. Controlla i dati inseriti e riprova. Se il problema persiste, riprova tra qualche istante.";
const SAVE_ERROR_COPY =
  "Non siamo riusciti a salvare la stima per aprire il dettaglio. Riprova tra qualche istante.";

export function EstimatePage() {
  const mutation = useMutation<StimaResponse, Error, EstimateFormValues>({
    mutationFn: postStima,
  });
  const { user, isLoading: isAuthLoading } = useAuth();

  // Auto-save da loggato (D-07): nessun ricalcolo, si congela esattamente il
  // payload gia' mostrato dal risultato corrente.
  const saveMutation = useMutation({ mutationFn: postSalvaStima });

  const result = mutation.data;
  const input = mutation.variables;

  useEffect(() => {
    if (
      mutation.isSuccess &&
      result &&
      user &&
      saveMutation.data === undefined &&
      !saveMutation.isPending &&
      !saveMutation.isError
    ) {
      saveMutation.mutate(result);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mutation.isSuccess, result, user]);

  function handleSubmit(values: EstimateFormValues) {
    mutation.mutate(values);
  }

  function handleModifica() {
    mutation.reset();
    saveMutation.reset();
  }

  const showResult = mutation.isSuccess && result;
  const showLoading = mutation.isPending;
  const showError = mutation.isError;

  return (
    <main className="mx-auto flex min-h-svh w-full max-w-[480px] flex-col gap-8 px-4 py-8 sm:max-w-[640px] sm:px-6 sm:py-12 lg:py-16">
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between gap-3">
          <h1 className="text-lg font-semibold text-foreground">ristruttura-stima</h1>
          {isAuthLoading ? (
            <Skeleton className="size-8 rounded-full" />
          ) : user ? (
            <AccountMenu user={user} />
          ) : (
            <Button variant="outline" size="sm" asChild>
              <Link to="/accedi">Accedi</Link>
            </Button>
          )}
        </div>
        {!showResult && !showLoading && !showError && (
          <p className="text-center text-sm text-muted-foreground">
            Inserisci i dati per ottenere la tua stima gratuita. Bastano tre informazioni:
            città, superficie in m² e tipo di ristrutturazione. La stima è gratuita e non
            richiede registrazione.
          </p>
        )}
      </div>

      {!showResult && !showLoading && (
        <EstimateForm onSubmit={handleSubmit} isSubmitting={mutation.isPending} />
      )}

      {showLoading && input && (
        <div className="flex flex-col gap-8">
          <SummaryPanel input={input} onModifica={handleModifica} disabled />
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-28 w-full" />
            ))}
          </div>
          <Skeleton className="h-32 w-full" />
        </div>
      )}

      {showError && input && (
        <div className="flex flex-col gap-6">
          <SummaryPanel input={input} onModifica={handleModifica} />
          <Alert variant="destructive">
            <AlertDescription>{ERROR_COPY}</AlertDescription>
          </Alert>
          <Button type="button" onClick={() => mutation.mutate(input)} className="w-full">
            Riprova
          </Button>
        </div>
      )}

      {showResult && result && input && (
        <div className="flex flex-col gap-8">
          <SummaryPanel input={input} onModifica={handleModifica} />

          {user?.pro ? (
            // Pro (P2): dettaglio inline al posto del riepilogo a card, sulla
            // stima appena auto-salvata. Finché il save è in corso mostra lo
            // skeleton (enabled=false); se il save fallisce, offre un retry.
            saveMutation.isError ? (
              <div className="flex flex-col gap-4">
                <Alert variant="destructive">
                  <AlertDescription>{SAVE_ERROR_COPY}</AlertDescription>
                </Alert>
                <Button
                  type="button"
                  onClick={() => saveMutation.mutate(result)}
                  className="w-full"
                >
                  Riprova
                </Button>
              </div>
            ) : (
              <DettaglioProView
                stimaId={saveMutation.data?.id ?? NaN}
                enabled={saveMutation.data?.id != null}
              />
            )
          ) : (
            <>
              {result.fallback && result.disclaimer && (
                <FallbackDisclaimer disclaimer={result.disclaimer} />
              )}

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {result.categorie.map((categoria) => (
                  <CategoryCard key={categoria.code} categoria={categoria} isPro={!!user?.pro} />
                ))}
              </div>

              <div className="flex flex-col gap-2">
                {result.extra.map((extra) => (
                  <div
                    key={extra.code}
                    className="flex items-center justify-between text-sm text-muted-foreground"
                  >
                    <span>{extra.nome}</span>
                    <span className="tabular-nums">{formatEur(extra.importo)}</span>
                  </div>
                ))}
              </div>

              <TotalCard totale={result.totale} />

              <SoftWallCta
                result={result}
                isAuthenticated={!!user}
                savedId={saveMutation.data?.id ?? null}
                isSaving={saveMutation.isPending}
                isPro={!!user?.pro}
              />
            </>
          )}
        </div>
      )}
    </main>
  );
}

interface SummaryPanelProps {
  input: EstimateFormValues;
  onModifica: () => void;
  disabled?: boolean;
}

function SummaryPanel({ input, onModifica, disabled }: SummaryPanelProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-secondary px-4 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="secondary">{input.citta}</Badge>
        <Badge variant="secondary">{input.mq} m²</Badge>
        <Badge variant="secondary">{TIPO_LABELS[input.tipo]}</Badge>
      </div>
      <button
        type="button"
        onClick={onModifica}
        disabled={disabled}
        className="text-sm font-medium text-muted-foreground underline-offset-4 hover:text-foreground hover:underline disabled:pointer-events-none disabled:opacity-50"
      >
        Modifica
      </button>
    </div>
  );
}
