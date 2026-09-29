import { Link, Navigate, useSearchParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { AccountMenu } from "@/components/AccountMenu";
import { DettaglioProView } from "@/components/DettaglioProView";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/useAuth";
import { getStimaDettaglio } from "@/api/stima";
import { ArredoCard } from "@/components/ArredoCard";

const INTRO_COPY =
  "Voci e quantità stimate a partire da superficie e tipo di intervento. Questo dettaglio è una stima indipendente, più precisa del totale rapido — i due numeri possono differire.";

/**
 * /dettaglio-pro?stima={id} (UI-SPEC §C): schermata dettaglio Pro dietro
 * il gate lato UI (il gate reale resta server-side, require_pro su ogni
 * endpoint T-03-13). Il contenuto è renderizzato da DettaglioProView,
 * condiviso con la home (Pro) e "Le mie stime" così i tre punti d'ingresso
 * non possono divergere.
 */
export function DettaglioProPage() {
  const [searchParams] = useSearchParams();
  const stimaIdParam = searchParams.get("stima");
  const stimaId = stimaIdParam ? Number(stimaIdParam) : NaN;
  const { user, isLoading: isAuthLoading } = useAuth();

  // Dallo snapshot arriva solo l'arredo. I bonus del Pro (10-14) arrivano dal
  // dettaglio Pro, calcolati server-side sui totali Pro dentro DettaglioProView.
  const snapshotQuery = useQuery({
    queryKey: ["stima-dettaglio", stimaId],
    queryFn: () => getStimaDettaglio(stimaId),
    enabled: Number.isFinite(stimaId),
  });

  if (!isAuthLoading && (!user || !user.pro)) {
    return <Navigate to="/passa-a-pro" replace />;
  }

  if (!stimaIdParam || !Number.isFinite(stimaId)) {
    return <Navigate to="/le-mie-stime" replace />;
  }

  if (isAuthLoading) {
    return null;
  }

  return (
    <main className="mx-auto flex min-h-svh w-full max-w-[480px] flex-col gap-8 px-4 py-8 sm:max-w-[640px] sm:px-6 sm:py-12 lg:py-16">
      <div className="flex items-center justify-between gap-3">
        <Link
          to="/"
          className="text-sm font-medium text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
        >
          ← Torna alla stima
        </Link>
        {user && <AccountMenu user={user} />}
      </div>

      <div className="flex flex-col gap-2">
        <h1 className="text-xl font-semibold text-foreground">Dettaglio Pro</h1>
        <p className="text-sm text-muted-foreground">{INTRO_COPY}</p>
      </div>

      <DettaglioProView stimaId={stimaId} />

      {/* L'arredo viene dallo snapshot per la stessa ragione dei bonus: e'
          calcolato dal motore Free e congelato in `risultato_json`. Sta QUI e
          non dentro `DettaglioProView` perche' `E-ARREDO` resta fuori dal
          dettaglio voce per voce -- non e' una lavorazione -- ma il Pro deve
          comunque vederlo, come lo vede il Free sulla sintesi. */}
      {snapshotQuery.data?.arredo && <ArredoCard arredo={snapshotQuery.data.arredo} />}

      <Button variant="outline" asChild className="h-11 w-full">
        <Link to="/">Torna alla stima</Link>
      </Button>
    </main>
  );
}
