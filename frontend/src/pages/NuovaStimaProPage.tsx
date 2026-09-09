import { useMutation } from "@tanstack/react-query";
import { Navigate, useNavigate, useSearchParams } from "react-router";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { EstimateFormPro, type EstimateProSubmit } from "@/components/EstimateFormPro";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/hooks/useAuth";
import { postSalvaStima, postStima } from "@/api/stima";
import type { CampiBase, TipoRistrutturazione } from "@/components/EstimateFormFields";

const ERROR_COPY =
  "Non siamo riusciti a calcolare la stima. Controlla i dati inseriti e riprova. Se il problema persiste, riprova tra qualche istante.";

const TIPI: TipoRistrutturazione[] = ["leggera", "moderata", "totale"];

/**
 * Legge i query param del "Rifai in versione Pro" (Fase 1). Ogni valore è
 * validato: arriva dalla barra degli indirizzi, quindi non è fidato.
 */
function inizialiDaQuery(params: URLSearchParams): Partial<CampiBase> {
  const iniziali: Partial<CampiBase> = {};

  const citta = params.get("citta");
  if (citta) iniziali.citta = citta;

  const mq = params.get("mq");
  if (mq && /^\d+$/.test(mq) && Number(mq) >= 1) iniziali.mqRaw = mq;

  const tipo = params.get("tipo");
  if (tipo && (TIPI as string[]).includes(tipo)) iniziali.tipo = tipo as TipoRistrutturazione;

  return iniziali;
}

/**
 * Flusso Pro completo: form a due step → POST /stima → POST /me/stime con le
 * preferenze → dettaglio Pro.
 *
 * Il redirect per i non-Pro è comodità di navigazione, non una difesa: il
 * gate reale resta `require_pro` server-side sugli endpoint del dettaglio.
 */
export function NuovaStimaProPage() {
  const { user, isLoading } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const mutation = useMutation({
    mutationFn: async ({ values, preferenze }: EstimateProSubmit) => {
      const risultato = await postStima(values);
      // Le preferenze viaggiano al salvataggio, non al calcolo: il motore Free
      // non le usa, e il dettaglio Pro le rilegge dalle colonne della stima.
      const { id } = await postSalvaStima(risultato, preferenze);
      return id;
    },
    onSuccess: (id) => navigate(`/dettaglio-pro?stima=${id}`),
  });

  if (isLoading) {
    return (
      <PageShell>
        <Skeleton className="h-96 w-full rounded-2xl" />
      </PageShell>
    );
  }

  if (!user) return <Navigate to="/accedi" replace />;
  if (!user.pro) return <Navigate to="/" replace />;

  return (
    <PageShell>
      <header className="flex flex-col gap-1">
        <h1 className="text-3xl font-bold text-foreground">Nuova stima Pro</h1>
        <p className="text-muted-foreground">
          Due passaggi: l'immobile, poi le finiture. Il dettaglio voce per voce si apre alla
          fine.
        </p>
      </header>

      <div className="mt-8 rounded-2xl border border-border bg-card p-6 shadow-lg shadow-black/[0.03] sm:p-8">
        {mutation.isError && (
          <Alert variant="destructive" className="mb-6">
            <AlertDescription>{ERROR_COPY}</AlertDescription>
          </Alert>
        )}
        <EstimateFormPro
          onSubmit={(payload) => mutation.mutate(payload)}
          isSubmitting={mutation.isPending}
          iniziali={inizialiDaQuery(searchParams)}
        />
      </div>

      <div className="mt-6 text-center">
        <Button type="button" variant="ghost" onClick={() => navigate("/")}>
          Preferisci la stima rapida? Vai alla home
        </Button>
      </div>
    </PageShell>
  );
}

function PageShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-svh flex-col bg-background">
      <SiteHeader />
      <main className="flex-1">
        <div className="mx-auto w-full max-w-2xl px-4 py-10 sm:px-6 sm:py-12">{children}</div>
      </main>
      <SiteFooter />
    </div>
  );
}
