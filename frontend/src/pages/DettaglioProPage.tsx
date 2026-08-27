import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, Navigate, useSearchParams } from "react-router";
import { Loader2 } from "lucide-react";
import { AccountMenu } from "@/components/AccountMenu";
import { SottocategoriaAccordion } from "@/components/SottocategoriaAccordion";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getDettaglioPro,
  postRisposteDettaglioPro,
  scaricaPdfPro,
  type RisposteDomande,
} from "@/api/dettaglio-pro";
import { useAuth } from "@/hooks/useAuth";

const INTRO_COPY =
  "Voci e quantità stimate a partire da superficie e tipo di intervento. Questo dettaglio è una stima indipendente, più precisa del totale rapido — i due numeri possono differire.";
const DOMANDE_SUBHEADING =
  "Rispondi per affinare le quantità stimate (facoltativo: se salti, usiamo una stima prudente in base ai metri quadri).";
const DEFAULT_NOTE =
  "Se salti una domanda, usiamo una stima prudente basata sui metri quadri dell'immobile.";
const CALC_ERROR_COPY = "Non siamo riusciti a calcolare il dettaglio. Controlla i dati e riprova.";
const PDF_ERROR_COPY = "Non siamo riusciti a generare il PDF. Riprova tra qualche istante.";
const VALIDATION_COPY = "Inserisci un numero valido (0 o superiore).";

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

/**
 * /dettaglio-pro?stima={id} (UI-SPEC §C): schermata dettaglio Pro dietro
 * il gate lato UI (il gate reale resta server-side, require_pro su ogni
 * endpoint T-03-13). Domande mirate + accordion per sottocategoria a range
 * + "Scarica PDF dettagliato" (scaricaPdfPro, stesso pattern PdfDownloadButton).
 */
export function DettaglioProPage() {
  const [searchParams] = useSearchParams();
  const stimaIdParam = searchParams.get("stima");
  const stimaId = stimaIdParam ? Number(stimaIdParam) : NaN;
  const { user, isLoading: isAuthLoading } = useAuth();
  const queryClient = useQueryClient();

  const [risposteInput, setRisposteInput] = useState<RisposteInput>({
    bagni: "0",
    porte: "0",
    condizionatori: "0",
  });
  const [domandeCollassate, setDomandeCollassate] = useState(false);
  const [usataStimaAutomatica, setUsataStimaAutomatica] = useState(false);
  const [initialized, setInitialized] = useState(false);

  const dettaglioQuery = useQuery({
    queryKey: ["dettaglio-pro", stimaId],
    queryFn: () => getDettaglioPro(stimaId),
    enabled: !!user?.pro && Number.isFinite(stimaId),
  });

  const risposteMutation = useMutation({
    mutationFn: (risposte: RisposteDomande) => postRisposteDettaglioPro(stimaId, risposte),
    onSuccess: (data) => {
      queryClient.setQueryData(["dettaglio-pro", stimaId], data);
      setDomandeCollassate(true);
    },
  });

  const pdfMutation = useMutation({ mutationFn: () => scaricaPdfPro(stimaId) });

  useEffect(() => {
    if (!initialized && dettaglioQuery.data) {
      setRisposteInput(toRisposteInput(dettaglioQuery.data.risposte));
      const hasRisposte =
        dettaglioQuery.data.risposte.bagni > 0 ||
        dettaglioQuery.data.risposte.porte > 0 ||
        dettaglioQuery.data.risposte.condizionatori > 0;
      setDomandeCollassate(hasRisposte);
      setInitialized(true);
    }
  }, [dettaglioQuery.data, initialized]);

  if (!isAuthLoading && (!user || !user.pro)) {
    return <Navigate to="/passa-a-pro" replace />;
  }

  if (!stimaIdParam || !Number.isFinite(stimaId)) {
    return <Navigate to="/le-mie-stime" replace />;
  }

  if (isAuthLoading) {
    return null;
  }

  function handleFieldChange(field: keyof RisposteDomande, value: string) {
    setRisposteInput((prev) => ({ ...prev, [field]: value }));
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

      {dettaglioQuery.isLoading && (
        <div className="flex flex-col gap-4">
          <Skeleton className="h-40 w-full" />
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>
      )}

      {dettaglioQuery.isError && (
        <div className="flex flex-col gap-4">
          <Alert variant="destructive">
            <AlertDescription>{CALC_ERROR_COPY}</AlertDescription>
          </Alert>
          <Button type="button" onClick={() => dettaglioQuery.refetch()} className="w-full">
            Riprova
          </Button>
        </div>
      )}

      {dettaglioQuery.isSuccess && dettaglioQuery.data && (
        <div className="flex flex-col gap-8">
          <div className="flex flex-col gap-4 rounded-lg border border-border bg-secondary p-6">
            <h2 className="text-base font-semibold text-foreground">Qualche dettaglio in più</h2>
            {domandeCollassate ? (
              <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-foreground">
                <span>
                  {usataStimaAutomatica
                    ? "Stima automatica"
                    : `Bagni: ${risposteInput.bagni} · Porte: ${risposteInput.porte} · Climatizzatori: ${risposteInput.condizionatori}`}
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
            {dettaglioQuery.data.categorie.map((categoria) => (
              <SottocategoriaAccordion key={categoria.code} categoria={categoria} />
            ))}
          </div>

          <div className="flex flex-col gap-3">
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
            <Button variant="outline" asChild className="h-11 w-full">
              <Link to="/">Torna alla stima</Link>
            </Button>
          </div>
        </div>
      )}
    </main>
  );
}
