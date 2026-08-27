import { CheckCircle, Loader2 } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, Navigate } from "react-router";
import { Button } from "@/components/ui/button";
import { postAttivaPro } from "@/api/subscription";
import { useAuth, AUTH_QUERY_KEY } from "@/hooks/useAuth";

const SUBHEADING =
  "Sblocca il dettaglio per voci e quantità di ogni sottocategoria, con un PDF completo da portare in cantiere.";
const BULLETS = [
  "Vedi ogni voce di lavorazione con quantità stimata",
  "Numeri più precisi, ricostruiti dal basso",
  "PDF dettagliato brandizzato da scaricare",
];
const PRICE_PLACEHOLDER =
  "Prezzo abbonamento in definizione — attivazione dimostrativa gratuita in questa fase";
const LOADING_COPY = "Attivazione in corso…";
const SUCCESS_COPY = "Il tuo account è ora Pro. Il dettaglio è sbloccato.";
const ERROR_COPY = "Non siamo riusciti ad attivare Pro. Riprova tra qualche istante.";

export function PassaAProPage() {
  const { user, isLoading } = useAuth();
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: postAttivaPro,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: AUTH_QUERY_KEY });
    },
  });

  if (isLoading) {
    return null;
  }

  if (!user) {
    return <Navigate to="/registrati?intent=pro" replace />;
  }

  const isPro = user.pro || mutation.isSuccess;

  return (
    <main className="mx-auto flex min-h-svh w-full max-w-[480px] flex-col justify-center gap-8 px-4 py-8">
      <div className="flex flex-col gap-6 rounded-lg border border-border bg-card p-6 shadow-xs">
        {isPro ? (
          <>
            <h1 className="text-xl font-semibold text-foreground">
              {mutation.isSuccess ? "Sei ora Pro" : "Sei già Pro."}
            </h1>
            {mutation.isSuccess && (
              <p role="status" className="text-sm text-muted-foreground">
                {SUCCESS_COPY}
              </p>
            )}
            <Button asChild className="h-11 w-full bg-primary text-base font-semibold text-primary-foreground hover:bg-primary/90">
              <Link to="/le-mie-stime">Vedi le mie stime</Link>
            </Button>
          </>
        ) : (
          <>
            <h1 className="text-xl font-semibold text-foreground">Passa a Pro</h1>
            <p className="text-sm text-muted-foreground">{SUBHEADING}</p>

            <ul className="flex flex-col gap-3">
              {BULLETS.map((bullet) => (
                <li key={bullet} className="flex items-start gap-2 text-sm text-foreground">
                  <CheckCircle className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
                  <span>{bullet}</span>
                </li>
              ))}
            </ul>

            <div className="rounded-lg border border-border bg-secondary px-4 py-3">
              <p className="text-sm text-muted-foreground">{PRICE_PLACEHOLDER}</p>
            </div>

            <Button
              type="button"
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending}
              className="h-11 w-full bg-primary text-base font-semibold text-primary-foreground hover:bg-primary/90"
            >
              {mutation.isPending ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader2 className="size-4 animate-spin" aria-hidden />
                  {LOADING_COPY}
                </span>
              ) : (
                "Attiva Pro"
              )}
            </Button>

            {mutation.isError && (
              <p className="text-center text-sm text-destructive">{ERROR_COPY}</p>
            )}
          </>
        )}
      </div>
    </main>
  );
}
