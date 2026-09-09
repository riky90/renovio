import { useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  CAMPI_BASE_INIZIALI,
  EstimateFormFields,
  OptionCard,
  toEstimateFormValues,
  validaCampiBase,
  type CampiBase,
  type EstimateFormValues,
} from "@/components/EstimateFormFields";
import { cn } from "@/lib/utils";
import { getOpzioniPro, type OpzioniProOut, type PreferenzePro } from "@/api/stima";

/** Le tre domande mirate, con la stessa etichetta usata nella vista Pro. */
const DOMANDE: { key: keyof RisposteInput; label: string }[] = [
  { key: "bagni", label: "Quanti bagni ha l'immobile?" },
  { key: "porte", label: "Quante porte interne vanno sostituite?" },
  { key: "condizionatori", label: "Quanti climatizzatori vuoi installare?" },
];

interface RisposteInput {
  bagni: string;
  porte: string;
  condizionatori: string;
}

const RISPOSTE_INIZIALI: RisposteInput = { bagni: "0", porte: "0", condizionatori: "0" };

function risposteValide(r: RisposteInput): boolean {
  return Object.values(r).every((v) => v.trim() !== "" && Number.isInteger(Number(v)) && Number(v) >= 0);
}

export interface EstimateProSubmit {
  values: EstimateFormValues;
  preferenze: PreferenzePro;
}

interface EstimateFormProProps {
  onSubmit: (payload: EstimateProSubmit) => void;
  isSubmitting?: boolean;
  /** Valori iniziali per il "Rifai in versione Pro" (query param della Fase 1). */
  iniziali?: Partial<CampiBase>;
}

/**
 * Form Pro a due step: prima l'immobile, poi le preferenze di dettaglio.
 *
 * Non è `EstimateForm` con un flag: i due form differiscono nel numero di
 * step, nella navigazione e nel payload di uscita. Condividono solo i campi
 * base, che infatti sono un componente a parte.
 */
export function EstimateFormPro({ onSubmit, isSubmitting, iniziali }: EstimateFormProProps) {
  const [step, setStep] = useState<1 | 2>(1);
  const [campi, setCampi] = useState<CampiBase>({ ...CAMPI_BASE_INIZIALI, ...iniziali });
  const [touched, setTouched] = useState(false);
  const [livelli, setLivelli] = useState<Record<string, string>>({});
  const [risposte, setRisposte] = useState<RisposteInput>(RISPOSTE_INIZIALI);

  const opzioniQuery = useQuery<OpzioniProOut>({
    queryKey: ["opzioni-pro"],
    queryFn: getOpzioniPro,
  });

  const { valid: baseValid } = validaCampiBase(campi);

  function handleChange(patch: Partial<CampiBase>) {
    setCampi((prev) => ({ ...prev, ...patch }));
  }

  function handleAvanti(e: FormEvent) {
    e.preventDefault();
    setTouched(true);
    if (!baseValid) return;
    setStep(2);
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const values = toEstimateFormValues(campi);
    if (values === null || !risposteValide(risposte)) return;
    onSubmit({
      values,
      preferenze: {
        // I livelli vanno solo se scelti: un oggetto vuoto significa comunque
        // "nessuna scelta", e il motore applica i default di tabella.
        ...(Object.keys(livelli).length > 0 ? { livelli } : {}),
        // Le risposte vanno SEMPRE, anche {0, 0, 0}: è una risposta legittima
        // ("non ho bagni da rifare") e va distinta dal non aver risposto.
        // È ciò che il backend registra come `risposte_salvate`.
        risposte: {
          bagni: Number(risposte.bagni),
          porte: Number(risposte.porte),
          condizionatori: Number(risposte.condizionatori),
        },
      },
    });
  }

  if (step === 1) {
    return (
      <form onSubmit={handleAvanti} className="flex w-full flex-col gap-6">
        <StepIndicator step={1} />
        <EstimateFormFields values={campi} onChange={handleChange} touched={touched} />
        <Button
          type="submit"
          disabled={!baseValid}
          className="group h-12 w-full bg-primary text-base font-semibold text-primary-foreground shadow-sm hover:bg-primary/90"
        >
          Continua
          <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
        </Button>
      </form>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex w-full flex-col gap-6">
      <StepIndicator step={2} />

      {opzioniQuery.isLoading && <Skeleton className="h-40 w-full rounded-xl" />}

      {opzioniQuery.data?.categorie.map((categoria) => (
        <div key={categoria.code} className="flex flex-col gap-2">
          <Label>Livello di finitura · {categoria.nome}</Label>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {opzioniQuery.data.livelli.map((livello) => {
              const scelto = livelli[categoria.code] ?? defaultLivello(opzioniQuery.data);
              return (
                <OptionCard
                  key={livello.code}
                  nome={livello.nome}
                  descrizione={livello.descrizione ?? ""}
                  selected={scelto === livello.code}
                  onSelect={() =>
                    setLivelli((prev) => ({ ...prev, [categoria.code]: livello.code }))
                  }
                />
              );
            })}
          </div>
        </div>
      ))}

      <div className="flex flex-col gap-4">
        {DOMANDE.map(({ key, label }) => (
          <div key={key} className="flex flex-col gap-2">
            <Label htmlFor={`pro-${key}`}>{label}</Label>
            <input
              id={`pro-${key}`}
              inputMode="numeric"
              value={risposte[key]}
              onChange={(e) =>
                setRisposte((prev) => ({ ...prev, [key]: e.target.value.replace(/[^0-9]/g, "") }))
              }
              className={cn(
                "h-9 w-full min-w-0 rounded-md border border-input bg-transparent px-2.5 py-1 text-base shadow-xs outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 md:text-sm"
              )}
            />
          </div>
        ))}
        <p className="text-sm text-muted-foreground">
          Lascia zero dove non serve: la stima resta valida, e queste risposte si possono
          cambiare anche dopo, dal dettaglio.
        </p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row">
        <Button type="button" variant="outline" onClick={() => setStep(1)} className="h-12 sm:w-40">
          <ArrowLeft className="size-4" />
          Indietro
        </Button>
        <Button
          type="submit"
          disabled={!risposteValide(risposte) || isSubmitting}
          className="group h-12 flex-1 bg-primary text-base font-semibold text-primary-foreground shadow-sm hover:bg-primary/90"
        >
          {isSubmitting ? (
            "Calcolo in corso..."
          ) : (
            <>
              Calcola la stima Pro
              <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
            </>
          )}
        </Button>
      </div>
    </form>
  );
}

/** Il livello di default arriva dalla tabella, non da una costante nel client. */
function defaultLivello(opzioni: OpzioniProOut): string | undefined {
  return opzioni.livelli.find((l) => l.is_default)?.code;
}

function StepIndicator({ step }: { step: 1 | 2 }) {
  return (
    <div className="flex items-center gap-3">
      {([1, 2] as const).map((n) => (
        <div key={n} className="flex flex-1 flex-col gap-1.5">
          <span
            className={cn(
              "h-1 rounded-full",
              n <= step ? "bg-primary" : "bg-border"
            )}
          />
          <span
            className={cn(
              "text-xs font-medium",
              n <= step ? "text-foreground" : "text-muted-foreground"
            )}
          >
            {n === 1 ? "1. L'immobile" : "2. Le finiture"}
          </span>
        </div>
      ))}
    </div>
  );
}
