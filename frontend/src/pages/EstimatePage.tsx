import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { useMutation } from "@tanstack/react-query";
import { Gauge, MapPin, Zap, type LucideIcon } from "lucide-react";
import { ArredoCard } from "@/components/ArredoCard";
import { CategoryCard } from "@/components/CategoryCard";
import { EstimateWizard, type EstimateWizardSubmit } from "@/components/EstimateWizard";
import { FallbackDisclaimer } from "@/components/FallbackDisclaimer";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { SoftWallCta } from "@/components/SoftWallCta";
import { TotalCard } from "@/components/TotalCard";
import { BudgetAlert } from "@/components/BudgetAlert";
import { BonusPanel } from "@/components/BonusPanel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { sommaMediCategorie } from "@/lib/risultato";
import { patchBudgetStima, postSalvaStima, postStima, type StimaRequest, type StimaResponse } from "@/api/stima";
import type { EstimateFormValues } from "@/components/EstimateFormFields";
import { useAuth } from "@/hooks/useAuth";

const TIPO_LABELS: Record<EstimateFormValues["tipo"], string> = {
  leggera: "Leggera",
  moderata: "Moderata",
  totale: "Totale",
};

const DESTINAZIONE_LABELS: Record<EstimateFormValues["destinazione"], string> = {
  prima_casa: "Abitazione principale",
  altro: "Altro immobile",
};

const ERROR_COPY =
  "Non siamo riusciti a calcolare la stima. Controlla i dati inseriti e riprova. Se il problema persiste, riprova tra qualche istante.";

interface Benefit {
  icon: LucideIcon;
  title: string;
  body: string;
}

const BENEFITS: Benefit[] = [
  {
    icon: Gauge,
    title: "Sempre a range",
    body: "Mai un numero secco: un minimo e un massimo onesti, prima del sopralluogo.",
  },
  {
    icon: MapPin,
    title: "Su misura per la città",
    body: "Prezzi calibrati sul listino locale, non su medie nazionali generiche.",
  },
  {
    icon: Zap,
    title: "Pronta in 30 secondi",
    body: "Tre informazioni, nessuna registrazione. Il calcolo è gratuito.",
  },
];

const STEPS: { n: string; title: string; body: string }[] = [
  {
    n: "01",
    title: "Inserisci i dati",
    body: "Città dell'immobile, superficie in m² e tipo di lavori. Bastano tre informazioni.",
  },
  {
    n: "02",
    title: "Ottieni il range",
    body: "Una stima onesta minimo–massimo, IVA inclusa, divisa per categoria di lavori.",
  },
  {
    n: "03",
    title: "Approfondisci",
    body: "Sblocca il dettaglio voce per voce con Pro, o fatti ricontattare da un referente.",
  },
];

export function EstimatePage() {
  const mutation = useMutation<StimaResponse, Error, StimaRequest>({
    mutationFn: postStima,
  });
  const { user } = useAuth();
  // Il budget non entra in POST /stima ne' in `risposte`: sta nello stato della
  // pagina e viaggia col salvataggio (auto-save o pendingStima) e col PATCH.
  const [budget, setBudget] = useState<number | null>(null);
  // Budget inviato con l'auto-save: se nel frattempo e' cambiato, si sincronizza.
  const budgetSalvato = useRef<number | null>(null);

  // Auto-save da loggato (D-07): nessun ricalcolo, si congela esattamente il
  // payload gia' mostrato dal risultato corrente.
  // L'arrow è necessaria: `postSalvaStima` ha un secondo parametro opzionale
  // (`preferenze_pro`, usato dal form Pro) e react-query passerebbe lì il
  // proprio context. Qui la home non ha preferenze da mandare.
  const saveMutation = useMutation({
    mutationFn: (payload: StimaResponse & { budget_eur: number | null }) =>
      postSalvaStima(payload),
  });

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
      budgetSalvato.current = budget;
      saveMutation.mutate({ ...result, budget_eur: budget });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mutation.isSuccess, result, user]);

  // Budget cambiato mentre l'auto-save era in corso: appena c'e' l'id lo si allinea.
  const savedId = saveMutation.data?.id;
  useEffect(() => {
    if (savedId !== undefined && budgetSalvato.current !== budget) {
      const daInviare = budget;
      budgetSalvato.current = daInviare;
      patchBudgetStima(savedId, daInviare).catch(() => {
        budgetSalvato.current = null;
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [savedId]);

  async function handleSalvaBudget(v: number | null) {
    if (savedId !== undefined) {
      // Se la PATCH fallisce l'errore risale al BudgetAlert, che lo mostra.
      await patchBudgetStima(savedId, v);
      budgetSalvato.current = v;
    }
    setBudget(v);
  }

  function handleSubmit({ values, risposte, budget: budgetDichiarato }: EstimateWizardSubmit) {
    setBudget(budgetDichiarato ?? null);
    // `risposte` viaggia SEMPRE, anche quando e' identico ai default: il
    // backend distingue "layer spento" (assente) da "tutte le domande sui
    // default" (presente e pieno), e la home ha appena chiesto quelle domande.
    mutation.mutate({ ...values, risposte });
  }

  function handleModifica() {
    mutation.reset();
    saveMutation.reset();
  }

  const showResult = mutation.isSuccess && result;
  const sommaMedi = result ? sommaMediCategorie(result.categorie) : 0;
  const showLoading = mutation.isPending;
  const showError = mutation.isError;
  const isIdle = !showResult && !showLoading && !showError;

  return (
    <div className="flex min-h-svh flex-col bg-background">
      <SiteHeader />

      <main className="flex-1">
        {isIdle ? (
          <section className="mx-auto w-full max-w-5xl px-4 py-12 sm:px-6 sm:py-16 lg:py-20">
            <div className="mx-auto max-w-2xl text-center">
              <span className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                <span className="size-1.5 rounded-full bg-primary" />
                Stima pre-sopralluogo · gratuita
              </span>
              <h1 className="mt-5 text-balance text-4xl font-bold leading-[1.05] text-foreground sm:text-5xl">
                Quanto costa <span className="text-primary">ristrutturare</span> casa?
              </h1>
              <p className="mx-auto mt-4 max-w-xl text-balance text-base text-muted-foreground sm:text-lg">
                Una stima onesta, a range, in trenta secondi. Bastano città, superficie e tipo
                di lavori — niente registrazione.
              </p>
            </div>

            <div className="mx-auto mt-10 max-w-xl rounded-2xl border border-border bg-card p-6 shadow-lg shadow-black/[0.03] sm:p-8">
              <EstimateWizard
                tier="free"
                onSubmit={handleSubmit}
                isSubmitting={mutation.isPending}
                budgetIniziale={budget}
              />
            </div>

            <ul className="mx-auto mt-12 grid max-w-4xl grid-cols-1 gap-6 sm:grid-cols-3">
              {BENEFITS.map(({ icon: Icon, title, body }) => (
                <li key={title} className="flex flex-col gap-3">
                  <span className="flex size-10 items-center justify-center rounded-xl bg-accent text-primary">
                    <Icon className="size-5" aria-hidden />
                  </span>
                  <h3 className="text-base font-semibold text-foreground">{title}</h3>
                  <p className="text-sm leading-relaxed text-muted-foreground">{body}</p>
                </li>
              ))}
            </ul>

            <div className="mx-auto mt-20 max-w-4xl border-t border-border pt-12">
              <h2 className="text-center text-2xl font-bold text-foreground sm:text-3xl">
                Come funziona
              </h2>
              <ol className="mt-10 grid grid-cols-1 gap-8 sm:grid-cols-3">
                {STEPS.map((step) => (
                  <li key={step.n} className="flex flex-col gap-3">
                    <span className="font-display text-3xl font-bold tabular-nums text-primary/30">
                      {step.n}
                    </span>
                    <h3 className="text-base font-semibold text-foreground">{step.title}</h3>
                    <p className="text-sm leading-relaxed text-muted-foreground">{step.body}</p>
                  </li>
                ))}
              </ol>
            </div>

            <div className="mx-auto mt-20 max-w-4xl overflow-hidden rounded-2xl border border-border bg-card px-6 py-10 text-center shadow-sm sm:px-10 sm:py-12">
              <h2 className="text-2xl font-bold text-foreground sm:text-3xl">
                Scopri quanto costa, senza impegno
              </h2>
              <p className="mx-auto mt-3 max-w-md text-muted-foreground">
                Gratis e senza registrazione. Prezzi calibrati sul listino reale della tua città.
              </p>
              <Button
                type="button"
                onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
                className="mt-6 h-11 px-6 text-base font-semibold"
              >
                Calcola la tua stima
              </Button>
            </div>
          </section>
        ) : (
          <div className="mx-auto flex w-full max-w-2xl flex-col gap-8 px-4 py-10 sm:px-6 sm:py-12">
            {showLoading && input && (
              <>
                <SummaryPanel input={input} onModifica={handleModifica} disabled />
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <Skeleton key={i} className="h-32 w-full rounded-xl" />
                  ))}
                </div>
                <Skeleton className="h-40 w-full rounded-xl" />
              </>
            )}

            {showError && input && (
              <>
                <SummaryPanel input={input} onModifica={handleModifica} />
                <Alert variant="destructive">
                  <AlertDescription>{ERROR_COPY}</AlertDescription>
                </Alert>
                <Button type="button" onClick={() => mutation.mutate(input)} className="w-full">
                  Riprova
                </Button>
              </>
            )}

            {showResult && result && input && (
              <>
                <SummaryPanel input={input} onModifica={handleModifica} />

                {/* Il risultato sintetico si mostra a TUTTI, Pro inclusi: e' anche
                    l'unico posto in cui i bonus compaiono, perche' si calcolano
                    sui totali lordi del motore Free (il motore Pro non modella
                    l'IVA). Il dettaglio voce per voce vive su /nuova-stima e
                    /dettaglio-pro, dove le domande mirate sono state poste. */}
                <>
                    {result.fallback && result.disclaimer && (
                      <FallbackDisclaimer disclaimer={result.disclaimer} />
                    )}

                    <TotalCard
                      totale={result.totale}
                      categorie={result.categorie}
                      extra={result.extra}
                      budget={budget}
                    />

                    <BudgetAlert
                      budget={budget}
                      totaleMin={result.totale.totale_min}
                      totaleMax={result.totale.totale_max}
                      onSalva={handleSalvaBudget}
                      confronto={result.confronto_finiture}
                      finitureAlMinimo={result.finiture_al_minimo}
                    />

                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                      {result.categorie.map((categoria) => (
                        <CategoryCard
                          key={categoria.code}
                          categoria={categoria}
                          isPro={!!user?.pro}
                          mq={result.input.mq}
                          sommaMedi={sommaMedi}
                        />
                      ))}
                    </div>

                    {result.bonus && <BonusPanel bonus={result.bonus} />}

                    {/* Dopo il totale e i bonus: l'arredo e' un'informazione
                        in piu', non parte della cifra che l'utente confronta. */}
                    {result.arredo && <ArredoCard arredo={result.arredo} />}

                    <SoftWallCta
                      result={{ ...result, budget_eur: budget }}
                      isAuthenticated={!!user}
                      savedId={saveMutation.data?.id ?? null}
                      isSaving={saveMutation.isPending}
                      isPro={!!user?.pro}
                    />
                </>

                {user?.pro && <CtaDettaglioPro input={input} />}
              </>
            )}
          </div>
        )}
      </main>

      <SiteFooter />
    </div>
  );
}

/**
 * Per un utente Pro la home resta la stima rapida: il dettaglio voce per voce
 * richiede le domande mirate e i livelli di finitura, che si raccolgono nel
 * form a due step su /nuova-stima.
 *
 * (09-12, gap G3) La stima appena calcolata viaggia con la navigazione: citta'/
 * mq/tipo in query string (come "Rifai in versione Pro"), risposte e
 * destinazione in `history.state` (non fidato, NuovaStimaProPage li rivalida).
 * Cosi' il wizard Pro riparte dallo step "Le finiture" invece che da zero.
 */
function CtaDettaglioPro({ input }: { input: StimaRequest }) {
  const navigate = useNavigate();

  function vaiAllaStimaPro() {
    navigate(
      `/nuova-stima?citta=${encodeURIComponent(input.citta)}&mq=${input.mq}&tipo=${input.tipo}`,
      {
        state: {
          risposte: input.risposte ?? {},
          destinazione: input.destinazione ?? "prima_casa",
          daStima: true,
        },
      }
    );
  }

  return (
    <div className="flex flex-col items-start gap-3 rounded-xl border border-primary/30 bg-accent/40 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-col gap-0.5">
        <span className="text-sm font-semibold text-foreground">
          Vuoi il dettaglio voce per voce?
        </span>
        <span className="text-sm text-muted-foreground">
          Ripartiamo da questa stima: scegli finiture e pavimento e ottieni il computo completo.
        </span>
      </div>
      <Button type="button" onClick={vaiAllaStimaPro} className="shrink-0">
        Vai alla stima Pro
      </Button>
    </div>
  );
}

interface SummaryPanelProps {
  /** La richiesta inviata, non i valori del form: e' cio' che ha prodotto
      questo risultato, comprese le risposte del wizard. */
  input: StimaRequest;
  onModifica: () => void;
  disabled?: boolean;
}

function SummaryPanel({ input, onModifica, disabled }: SummaryPanelProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-card px-4 py-3 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="secondary">{input.citta}</Badge>
        <Badge variant="secondary">{input.mq} m²</Badge>
        <Badge variant="secondary">{TIPO_LABELS[input.tipo]}</Badge>
        <Badge variant="secondary">
          {DESTINAZIONE_LABELS[input.destinazione ?? "prima_casa"]}
        </Badge>
      </div>
      <button
        type="button"
        onClick={onModifica}
        disabled={disabled}
        className="text-sm font-medium text-primary underline-offset-4 hover:underline disabled:pointer-events-none disabled:opacity-50"
      >
        Modifica
      </button>
    </div>
  );
}
