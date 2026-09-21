import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { DomandaField } from "@/components/DomandaField";
import {
  CAMPI_BASE_INIZIALI,
  CittaField,
  DestinazioneField,
  MqField,
  OptionCard,
  TipoField,
  toEstimateFormValues,
  validaCampiBase,
  type CampiBase,
  type EstimateFormValues,
} from "@/components/EstimateFormFields";
import { cn } from "@/lib/utils";
import {
  domandeVisibili,
  getCatalogoDomande,
  isNumerico,
  risposteIniziali,
  type CatalogoDomande,
  type Domanda,
  type Risposte,
  type ValoreRisposta,
} from "@/api/domande";
import { getOpzioniPro, type OpzioniProOut, type PreferenzePro } from "@/api/stima";

export interface EstimateWizardSubmit {
  values: EstimateFormValues;
  risposte: Risposte;
  /** Solo in tier Pro: livelli di finitura e domande mirate del motore Pro. */
  preferenze?: PreferenzePro;
}

interface EstimateWizardProps {
  tier: "free" | "pro";
  onSubmit: (payload: EstimateWizardSubmit) => void;
  isSubmitting?: boolean;
  /** Valori iniziali del "Rifai in versione Pro" (query param). */
  iniziali?: Partial<CampiBase>;
}

/**
 * Il wizard unico: un solo form per Free e Pro, con gli step che cambiano.
 *
 * Prima erano due componenti -- `EstimateForm` (uno step) e `EstimateFormPro`
 * (due) -- e le domande erano una costante dentro il secondo. Il motivo per cui
 * collassano qui non e' la duplicazione del markup: e' che il catalogo domande
 * rende i due form lo stesso form con un filtro diverso sul tier. Tenerli
 * separati avrebbe significato due posti in cui montare le stesse domande.
 *
 * Gli step sono di presentazione, non di dominio: raggruppano le domande per
 * `gruppo`, e un gruppo che il wizard non conosce finisce nello step 3 invece
 * di sparire. Una domanda nuova in un gruppo nuovo resta visibile anche senza
 * un deploy del frontend -- che e' tutto il punto della fase.
 */
export function EstimateWizard({
  tier,
  onSubmit,
  isSubmitting,
  iniziali,
}: EstimateWizardProps) {
  const [step, setStep] = useState(1);
  const [campi, setCampi] = useState<CampiBase>({ ...CAMPI_BASE_INIZIALI, ...iniziali });
  const [touched, setTouched] = useState(false);
  const [risposte, setRisposte] = useState<Risposte>({});
  const [risposteToccate, setRisposteToccate] = useState(false);
  const [livelli, setLivelli] = useState<Record<string, string>>({});

  const { mq, valid: baseValid, cittaValid, mqValid } = validaCampiBase(campi);
  const step1Valid = cittaValid && mqValid;

  // Il catalogo si ricarica quando cambiano i m2: i default degli stepper
  // dipendono dalla fascia, e servirli per una superficie diversa da quella
  // digitata farebbe partire lo scostamento da una baseline sbagliata.
  const catalogoQuery = useQuery<CatalogoDomande>({
    queryKey: ["catalogo-domande", tier, step1Valid ? mq : null],
    queryFn: () => getCatalogoDomande({ tier, mq: step1Valid ? mq : undefined }),
    enabled: step1Valid,
  });

  const opzioniProQuery = useQuery<OpzioniProOut>({
    queryKey: ["opzioni-pro"],
    queryFn: getOpzioniPro,
    enabled: tier === "pro",
  });

  const catalogo = catalogoQuery.data;

  // I default arrivano dal server, quindi si applicano quando il catalogo
  // arriva -- e di nuovo a ogni cambio di m2. `risposteToccate` protegge le
  // risposte gia' date: chi ha messo 3 bagni e poi corregge i m2 non se li
  // vede riportare al valore standard.
  useEffect(() => {
    if (!catalogo) return;
    setRisposte((precedenti) => (risposteToccate ? precedenti : risposteIniziali(catalogo)));
  }, [catalogo, risposteToccate]);

  const visibili = useMemo(
    () => (catalogo ? domandeVisibili(catalogo.domande, risposte) : []),
    [catalogo, risposte]
  );

  const steps = useMemo(() => costruisciStep(visibili, tier), [visibili, tier]);
  const ultimoStep = steps.length;

  function handleChange(patch: Partial<CampiBase>) {
    setCampi((prev) => ({ ...prev, ...patch }));
  }

  function handleRisposta(code: string, valore: ValoreRisposta) {
    setRisposteToccate(true);
    setRisposte((prev) => ({ ...prev, [code]: valore }));
  }

  function applicaValoriStandard() {
    if (!catalogo) return;
    setRisposteToccate(true);
    setRisposte(risposteIniziali(catalogo));
  }

  function avanti(e: FormEvent) {
    e.preventDefault();
    setTouched(true);
    if (step === 1 && !step1Valid) return;
    if (step === 3 && !baseValid) return;
    // `touched` si azzera passando allo step successivo: e' "hai gia' provato a
    // mandare QUESTO step", non "hai gia' provato a mandare qualcosa". Senza
    // questa riga, chi arriva allo step 3 ci trova gia' scritto "seleziona il
    // tipo" — un errore su un campo che non ha ancora avuto modo di compilare.
    setTouched(false);
    setStep((s) => Math.min(ultimoStep, s + 1));
  }

  function invia(e: FormEvent) {
    e.preventDefault();
    setTouched(true);
    const values = toEstimateFormValues(campi);
    if (values === null) {
      // Un campo base invalido vive allo step 1 o allo step 3: ci si torna,
      // invece di lasciare un bottone che non fa niente.
      setStep(step1Valid ? 3 : 1);
      return;
    }
    // Le risposte vanno SEMPRE, anche identiche ai default: `{}` accende il
    // layer con tutte le domande sui loro default, `undefined` lo spegne -- e
    // spegnerlo qui vorrebbe dire buttare via quello che l'utente ha appena
    // compilato.
    onSubmit({
      values,
      risposte: soloVisibili(risposte, visibili),
      ...(tier === "pro" ? { preferenze: preferenzePro(livelli, risposte) } : {}),
    });
  }

  const stepCorrente = steps[step - 1];

  return (
    <form onSubmit={step === ultimoStep ? invia : avanti} className="flex w-full flex-col gap-6">
      <StepIndicator steps={steps} corrente={step} />

      {step === 1 && (
        <>
          <CittaField values={campi} onChange={handleChange} touched={touched} />
          <MqField values={campi} onChange={handleChange} touched={touched} />
          <p className="text-sm text-muted-foreground">
            La superficie serve subito: da quella dipendono i valori standard che ti
            proponiamo nei passaggi successivi.
          </p>
        </>
      )}

      {step > 1 && catalogoQuery.isLoading && <Skeleton className="h-64 w-full rounded-xl" />}

      {step > 1 && catalogoQuery.isError && (
        <Alert variant="destructive">
          <AlertDescription>
            Non siamo riusciti a caricare le domande. Torna indietro e riprova.
          </AlertDescription>
        </Alert>
      )}

      {step === 2 && stepCorrente && (
        <>
          <ValoriStandardHint onApplica={applicaValoriStandard} domande={stepCorrente.domande} />
          {stepCorrente.domande.map((domanda) => (
            <DomandaField
              key={domanda.code}
              domanda={domanda}
              valore={risposte[domanda.code]}
              onChange={(valore) => handleRisposta(domanda.code, valore)}
            />
          ))}
        </>
      )}

      {step === 3 && (
        <>
          <TipoField values={campi} onChange={handleChange} touched={touched} />
          <DestinazioneField values={campi} onChange={handleChange} />
          {stepCorrente?.domande.map((domanda) => (
            <DomandaField
              key={domanda.code}
              domanda={domanda}
              valore={risposte[domanda.code]}
              onChange={(valore) => handleRisposta(domanda.code, valore)}
            />
          ))}
        </>
      )}

      {step === 4 && (
        <FinitureStep
          opzioni={opzioniProQuery.data}
          isLoading={opzioniProQuery.isLoading}
          livelli={livelli}
          onLivello={(categoria, livello) =>
            setLivelli((prev) => ({ ...prev, [categoria]: livello }))
          }
          domande={stepCorrente?.domande ?? []}
          risposte={risposte}
          onRisposta={handleRisposta}
        />
      )}

      <Navigazione
        step={step}
        ultimoStep={ultimoStep}
        indietro={() => setStep((s) => Math.max(1, s - 1))}
        avantiDisabilitato={step === 1 ? !step1Valid : step === 3 ? !baseValid : false}
        isSubmitting={isSubmitting}
        tier={tier}
      />
    </form>
  );
}

// --- composizione degli step ------------------------------------------------

interface StepDef {
  numero: number;
  titolo: string;
  domande: Domanda[];
}

/**
 * Quali gruppi del catalogo finiscono in quale step.
 *
 * E' una mappa di PRESENTAZIONE e non di dominio: dice dove si disegna una
 * domanda, mai cosa fa. Un gruppo assente da questa mappa non sparisce -- cade
 * nello step 3 -- perche' il modo in cui questa fase puo' fallire in silenzio
 * e' proprio quello: l'admin crea un gruppo nuovo, il wizard non lo riconosce,
 * e la domanda non viene mai posta pur restando attiva in tabella.
 */
const GRUPPI_PER_STEP: Record<string, number> = {
  immobile: 2,
  ambienti: 2,
  ristrutturazione: 3,
  energia: 3,
};

const STEP_DI_RIPIEGO = 3;

function costruisciStep(domande: Domanda[], tier: "free" | "pro"): StepDef[] {
  const perStep = new Map<number, Domanda[]>();

  for (const domanda of domande) {
    // Le domande Pro hanno il loro step; le Free restano dove il gruppo dice,
    // anche per un utente Pro, cosi' il wizard e' lo stesso per entrambi.
    const numero =
      domanda.tier_minimo === "pro" ? 4 : (GRUPPI_PER_STEP[domanda.gruppo] ?? STEP_DI_RIPIEGO);
    perStep.set(numero, [...(perStep.get(numero) ?? []), domanda]);
  }

  const steps: StepDef[] = [
    { numero: 1, titolo: "Dove", domande: [] },
    { numero: 2, titolo: "L'immobile", domande: perStep.get(2) ?? [] },
    { numero: 3, titolo: "La ristrutturazione", domande: perStep.get(3) ?? [] },
  ];

  if (tier === "pro") {
    steps.push({ numero: 4, titolo: "Le finiture", domande: perStep.get(4) ?? [] });
  }

  return steps;
}

/**
 * Le risposte alle domande nascoste non partono.
 *
 * Il motore le ignorerebbe comunque -- ri-applica la visibilita' per conto suo
 * -- ma finirebbero nello snapshot congelato, dove sembrerebbero risposte date.
 * Una stima salvata deve restare spiegabile, e "ho risposto a una domanda che
 * non mi e' stata fatta" non lo e'.
 */
function soloVisibili(risposte: Risposte, visibili: Domanda[]): Risposte {
  const codici = new Set(visibili.map((d) => d.code));
  return Object.fromEntries(Object.entries(risposte).filter(([code]) => codici.has(code)));
}

/**
 * Le tre domande mirate del motore Pro (`coefficiente_qta_voce.domanda_mirata_key`).
 *
 * NON e' il catalogo: e' il contratto che il motore Pro si aspetta ancora, e
 * che la Fase 5 sostituisce quando anche il configuratore Pro passera' dal
 * catalogo. Fino ad allora due delle tre chiavi esistono gia' come domande
 * (`bagni`, `porte`) e si leggono da li' invece di chiederle una seconda volta;
 * `condizionatori` non ha ancora una domanda corrispondente e resta a zero
 * finche' non gliela si crea.
 */
function preferenzePro(livelli: Record<string, string>, risposte: Risposte): PreferenzePro {
  const numero = (code: string): number => {
    const valore = risposte[code];
    return typeof valore === "number" ? valore : 0;
  };

  return {
    ...(Object.keys(livelli).length > 0 ? { livelli } : {}),
    risposte: {
      bagni: numero("bagni"),
      porte: numero("porte"),
      condizionatori: numero("condizionatori"),
    },
  };
}

// --- pezzi di UI ------------------------------------------------------------

function ValoriStandardHint({
  onApplica,
  domande,
}: {
  onApplica: () => void;
  domande: Domanda[];
}) {
  // Il suggerimento ha senso solo se in questo step c'e' qualcosa di numerico
  // da riportare allo standard.
  if (!domande.some((d) => isNumerico(d.tipo_controllo))) return null;

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-border bg-accent/30 p-4 sm:flex-row sm:items-center sm:justify-between">
      <p className="text-sm text-muted-foreground">
        Abbiamo gia' compilato i valori tipici per la tua superficie. Puoi cambiarli anche
        dopo.
      </p>
      <Button type="button" variant="outline" size="sm" onClick={onApplica} className="shrink-0">
        Vai avanti con i valori standard
      </Button>
    </div>
  );
}

function FinitureStep({
  opzioni,
  isLoading,
  livelli,
  onLivello,
  domande,
  risposte,
  onRisposta,
}: {
  opzioni: OpzioniProOut | undefined;
  isLoading: boolean;
  livelli: Record<string, string>;
  onLivello: (categoria: string, livello: string) => void;
  domande: Domanda[];
  risposte: Risposte;
  onRisposta: (code: string, valore: ValoreRisposta) => void;
}) {
  const defaultLivello = opzioni?.livelli.find((l) => l.is_default)?.code;

  return (
    <>
      {isLoading && <Skeleton className="h-40 w-full rounded-xl" />}

      {opzioni?.categorie.map((categoria) => (
        <div key={categoria.code} className="flex flex-col gap-2">
          <Label>Livello di finitura · {categoria.nome}</Label>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {opzioni.livelli.map((livello) => (
              <OptionCard
                key={livello.code}
                nome={livello.nome}
                descrizione={livello.descrizione ?? ""}
                selected={(livelli[categoria.code] ?? defaultLivello) === livello.code}
                onSelect={() => onLivello(categoria.code, livello.code)}
              />
            ))}
          </div>
        </div>
      ))}

      {domande.map((domanda) => (
        <DomandaField
          key={domanda.code}
          domanda={domanda}
          valore={risposte[domanda.code]}
          onChange={(valore) => onRisposta(domanda.code, valore)}
        />
      ))}
    </>
  );
}

function Navigazione({
  step,
  ultimoStep,
  indietro,
  avantiDisabilitato,
  isSubmitting,
  tier,
}: {
  step: number;
  ultimoStep: number;
  indietro: () => void;
  avantiDisabilitato: boolean;
  isSubmitting?: boolean;
  tier: "free" | "pro";
}) {
  const ultimo = step === ultimoStep;

  return (
    <div className="flex flex-col gap-3 sm:flex-row">
      {step > 1 && (
        <Button type="button" variant="outline" onClick={indietro} className="h-12 sm:w-40">
          <ArrowLeft className="size-4" />
          Indietro
        </Button>
      )}
      <Button
        type="submit"
        disabled={avantiDisabilitato || (ultimo && isSubmitting)}
        className="group h-12 flex-1 bg-primary text-base font-semibold text-primary-foreground shadow-sm hover:bg-primary/90"
      >
        {ultimo && isSubmitting ? (
          "Calcolo in corso..."
        ) : (
          <>
            {ultimo ? (tier === "pro" ? "Calcola la stima Pro" : "Calcola la stima") : "Continua"}
            <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
          </>
        )}
      </Button>
    </div>
  );
}

function StepIndicator({ steps, corrente }: { steps: StepDef[]; corrente: number }) {
  return (
    <div className="flex items-center gap-3">
      {steps.map((step) => (
        <div key={step.numero} className="flex flex-1 flex-col gap-1.5">
          <span
            className={cn("h-1 rounded-full", step.numero <= corrente ? "bg-primary" : "bg-border")}
          />
          <span
            className={cn(
              "text-xs font-medium",
              step.numero <= corrente ? "text-foreground" : "text-muted-foreground"
            )}
          >
            {step.numero}. {step.titolo}
          </span>
        </div>
      ))}
    </div>
  );
}
