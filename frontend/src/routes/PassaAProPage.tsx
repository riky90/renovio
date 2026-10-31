import { useEffect, useRef, useState } from "react";
import { CheckCircle, Loader2 } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, Navigate, useSearchParams } from "react-router";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { ApiError } from "@/api/client";
import {
  getPianiPro,
  postAttivaPro,
  postCheckout,
  postConfermaCheckout,
  type PianoCode,
  type PianoPro,
} from "@/api/subscription";
import { useAuth, AUTH_QUERY_KEY } from "@/hooks/useAuth";
import { PATH_CONDIZIONI, PATH_PRIVACY } from "@/content/legale";
import { tracciaEvento } from "@/lib/tracciamento";

const SUBHEADING =
  "Sblocca il dettaglio per voci e quantità di ogni sottocategoria, con un PDF completo da portare in cantiere.";
const BULLETS = [
  "Vedi ogni voce di lavorazione con quantità stimata",
  "Configura finiture, pavimenti e i lavori particolari della tua casa",
  "PDF dettagliato da scaricare per ogni stima",
];
const DEMO_COPY = "Attivazione dimostrativa gratuita: i pagamenti non sono ancora attivi.";
const SUCCESS_COPY = "Il tuo account è ora Pro. Il dettaglio è sbloccato.";
const ERROR_COPY = "Non siamo riusciti a completare l'operazione. Riprova tra qualche istante.";
const ANNULLATO_COPY = "Pagamento annullato: non ti abbiamo addebitato nulla.";
const IN_ATTESA_COPY =
  "Pagamento ricevuto. L'attivazione può richiedere qualche secondo: se il Pro non compare, ricarica la pagina tra poco.";
const ESECUZIONE_COPY =
  "Chiedo di attivare il Pro subito. Resta il diritto di recesso entro 14 giorni con rimborso completo.";

function formatEuro(importo: number): string {
  return new Intl.NumberFormat("it-IT", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: Number.isInteger(importo) ? 0 : 2,
  }).format(importo);
}

function etichettaPiano(piano: PianoPro): string {
  return piano.intervallo === "year" ? `${formatEuro(piano.importo)} all'anno` : `${formatEuro(piano.importo)} al mese`;
}

/** Risparmio dell'annuale rispetto a 12 mesi del mensile, in percentuale intera. */
function risparmioAnnuale(piani: PianoPro[]): number | null {
  const mensile = piani.find((p) => p.code === "mensile");
  const annuale = piani.find((p) => p.code === "annuale");
  if (!mensile || !annuale || mensile.importo <= 0) return null;
  const risparmio = 1 - annuale.importo / (mensile.importo * 12);
  return risparmio > 0 ? Math.round(risparmio * 100) : null;
}

export function PassaAProPage() {
  const { user, isLoading } = useAuth();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const esito = searchParams.get("esito");
  const sessionId = searchParams.get("session_id");

  const pianiQuery = useQuery({ queryKey: ["pro-piani"], queryFn: getPianiPro, staleTime: 5 * 60 * 1000 });
  const [piano, setPiano] = useState<PianoCode>("annuale");
  const [condizioni, setCondizioni] = useState(false);
  const [esecuzione, setEsecuzione] = useState(false);

  const demoMutation = useMutation({
    mutationFn: postAttivaPro,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: AUTH_QUERY_KEY }),
  });

  const checkoutMutation = useMutation({
    mutationFn: () => postCheckout(piano, { condizioni, esecuzioneImmediata: esecuzione }),
    onSuccess: (url) => {
      window.location.assign(url);
    },
  });

  const confermaMutation = useMutation({
    mutationFn: (id: string) => postConfermaCheckout(id),
    onSuccess: (abbonamento, id) => {
      void queryClient.invalidateQueries({ queryKey: AUTH_QUERY_KEY });
      const pianoPagato = pianiQuery.data?.piani.find((p) => p.code === abbonamento.piano_code);
      if (abbonamento.pro && pianoPagato) {
        tracciaEvento({
          tipo: "acquisto_pro",
          valore: pianoPagato.importo,
          valuta: pianoPagato.valuta,
          piano: pianoPagato.code,
          idTransazione: id,
        });
      }
    },
  });
  const confermaInviata = useRef(false);
  useEffect(() => {
    if (esito === "ok" && sessionId && user && !confermaInviata.current) {
      confermaInviata.current = true;
      confermaMutation.mutate(sessionId);
    }
  }, [esito, sessionId, user, confermaMutation]);

  if (isLoading) {
    return null;
  }

  if (!user) {
    return <Navigate to="/registrati?intent=pro" replace />;
  }

  const appenaAttivato = demoMutation.isSuccess || (esito === "ok" && confermaMutation.data?.pro === true);
  const isPro = user.pro || appenaAttivato;
  const pagamentiAttivi = pianiQuery.data?.pagamenti_attivi === true;
  const piani = pianiQuery.data?.piani ?? [];
  const risparmio = risparmioAnnuale(piani);
  const erroreCheckout =
    checkoutMutation.error instanceof ApiError && checkoutMutation.error.detail
      ? checkoutMutation.error.detail
      : ERROR_COPY;

  return (
    <main className="mx-auto flex min-h-svh w-full max-w-[480px] flex-col justify-center gap-8 px-4 py-8">
      <div className="flex flex-col gap-6 rounded-lg border border-border bg-card p-6 shadow-xs">
        {isPro ? (
          <>
            <h1 className="text-xl font-semibold text-foreground">{appenaAttivato ? "Sei ora Pro" : "Sei già Pro."}</h1>
            {appenaAttivato && (
              <p role="status" className="text-sm text-muted-foreground">
                {SUCCESS_COPY}
              </p>
            )}
            <Button asChild className="h-11 w-full bg-primary text-base font-semibold text-primary-foreground hover:bg-primary/90">
              <Link to="/le-mie-stime">Vedi le mie stime</Link>
            </Button>
            <Button asChild variant="outline" className="h-11 w-full">
              <Link to="/impostazioni/abbonamento">Il mio abbonamento</Link>
            </Button>
          </>
        ) : (
          <>
            <h1 className="text-xl font-semibold text-foreground">Passa a Pro</h1>
            <p className="text-sm text-muted-foreground">{SUBHEADING}</p>

            {esito === "annullato" && (
              <p role="status" className="rounded-lg border border-border bg-secondary px-4 py-3 text-sm text-foreground">
                {ANNULLATO_COPY}
              </p>
            )}
            {esito === "ok" && (
              <p role="status" className="rounded-lg border border-border bg-secondary px-4 py-3 text-sm text-foreground">
                {confermaMutation.isPending ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="size-4 animate-spin" aria-hidden /> Verifica del pagamento…
                  </span>
                ) : (
                  IN_ATTESA_COPY
                )}
              </p>
            )}

            <ul className="flex flex-col gap-3">
              {BULLETS.map((bullet) => (
                <li key={bullet} className="flex items-start gap-2 text-sm text-foreground">
                  <CheckCircle className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
                  <span>{bullet}</span>
                </li>
              ))}
            </ul>

            {pianiQuery.isLoading ? (
              <div className="flex justify-center py-4">
                <Loader2 className="size-5 animate-spin text-muted-foreground" aria-label="Caricamento dei piani" />
              </div>
            ) : pagamentiAttivi && piani.length > 0 ? (
              <>
                <RadioGroup
                  value={piano}
                  onValueChange={(v) => setPiano(v as PianoCode)}
                  className="flex flex-col gap-3"
                  aria-label="Scegli il piano"
                >
                  {piani.map((p) => (
                    <Label
                      key={p.code}
                      htmlFor={`piano-${p.code}`}
                      className="flex cursor-pointer items-center gap-3 rounded-lg border border-border px-4 py-3 has-[[data-state=checked]]:border-primary has-[[data-state=checked]]:bg-primary/5"
                    >
                      <RadioGroupItem id={`piano-${p.code}`} value={p.code} />
                      <span className="flex flex-1 flex-col gap-0.5">
                        <span className="font-semibold text-foreground">
                          {p.code === "annuale" ? "Annuale" : "Mensile"}
                          {p.code === "annuale" && risparmio !== null && (
                            <span className="ml-2 rounded-full bg-primary px-2 py-0.5 text-xs font-medium text-primary-foreground">
                              risparmi {risparmio}%
                            </span>
                          )}
                        </span>
                        <span className="text-sm text-muted-foreground">
                          {etichettaPiano(p)}, IVA inclusa. Si rinnova da solo, disdici quando vuoi.
                        </span>
                      </span>
                    </Label>
                  ))}
                </RadioGroup>

                <div className="flex flex-col gap-3">
                  <label className="flex items-start gap-3 text-sm text-foreground">
                    <input
                      type="checkbox"
                      checked={condizioni}
                      onChange={(e) => setCondizioni(e.target.checked)}
                      className="mt-1 size-4 shrink-0 accent-primary"
                    />
                    <span>
                      Ho letto e accetto le{" "}
                      <Link to={PATH_CONDIZIONI} target="_blank" className="font-medium text-primary underline underline-offset-4">
                        condizioni di vendita
                      </Link>{" "}
                      e ho preso visione dell'
                      <Link to={PATH_PRIVACY} target="_blank" className="font-medium text-primary underline underline-offset-4">
                        informativa privacy
                      </Link>
                      .
                    </span>
                  </label>
                  <label className="flex items-start gap-3 text-sm text-foreground">
                    <input
                      type="checkbox"
                      checked={esecuzione}
                      onChange={(e) => setEsecuzione(e.target.checked)}
                      className="mt-1 size-4 shrink-0 accent-primary"
                    />
                    <span>{ESECUZIONE_COPY}</span>
                  </label>
                </div>

                <Button
                  type="button"
                  onClick={() => checkoutMutation.mutate()}
                  disabled={!condizioni || !esecuzione || checkoutMutation.isPending || checkoutMutation.isSuccess}
                  className="h-11 w-full bg-primary text-base font-semibold text-primary-foreground hover:bg-primary/90"
                >
                  {checkoutMutation.isPending || checkoutMutation.isSuccess ? (
                    <span className="flex items-center justify-center gap-2">
                      <Loader2 className="size-4 animate-spin" aria-hidden />
                      Ti porto al pagamento…
                    </span>
                  ) : (
                    "Continua al pagamento"
                  )}
                </Button>
                <p className="text-center text-xs text-muted-foreground">
                  Pagamento sicuro con Stripe: carta, Apple Pay o Google Pay.
                </p>
                {checkoutMutation.isError && <p className="text-center text-sm text-destructive">{erroreCheckout}</p>}
              </>
            ) : (
              <>
                <div className="rounded-lg border border-border bg-secondary px-4 py-3">
                  <p className="text-sm text-muted-foreground">
                    {pianiQuery.isError ? ERROR_COPY : DEMO_COPY}
                  </p>
                </div>
                {!pianiQuery.isError && (
                  <Button
                    type="button"
                    onClick={() => demoMutation.mutate()}
                    disabled={demoMutation.isPending}
                    className="h-11 w-full bg-primary text-base font-semibold text-primary-foreground hover:bg-primary/90"
                  >
                    {demoMutation.isPending ? (
                      <span className="flex items-center justify-center gap-2">
                        <Loader2 className="size-4 animate-spin" aria-hidden />
                        Attivazione in corso…
                      </span>
                    ) : (
                      "Attiva Pro"
                    )}
                  </Button>
                )}
                {demoMutation.isError && <p className="text-center text-sm text-destructive">{ERROR_COPY}</p>}
              </>
            )}
          </>
        )}
      </div>
    </main>
  );
}
