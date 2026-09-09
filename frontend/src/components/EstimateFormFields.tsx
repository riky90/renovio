import { Check } from "lucide-react";
import { CityAutocomplete } from "@/components/CityAutocomplete";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

export type TipoRistrutturazione = "leggera" | "moderata" | "totale";

/** Abitazione principale vs altri immobili: separa il 50% dal 36% di detrazione. */
export type Destinazione = "prima_casa" | "altro";

export interface EstimateFormValues {
  citta: string;
  mq: number;
  tipo: TipoRistrutturazione;
  destinazione: Destinazione;
}

/**
 * Stato grezzo dei campi condivisi, prima della validazione. `mqRaw` resta
 * una stringa e non un numero: l'input è mascherato mentre si digita, e un
 * campo vuoto non è lo stesso valore di zero.
 */
export interface CampiBase {
  citta: string;
  mqRaw: string;
  tipo: TipoRistrutturazione | null;
  destinazione: Destinazione;
}

export const CAMPI_BASE_INIZIALI: CampiBase = {
  citta: "",
  mqRaw: "",
  tipo: null,
  destinazione: "prima_casa",
};

interface TipoOption {
  code: TipoRistrutturazione;
  nome: string;
  descrizione: string;
}

const TIPO_OPTIONS: TipoOption[] = [
  {
    code: "leggera",
    nome: "Leggera",
    descrizione: "Tinteggiature, nuovi pavimenti e sanitari, piccole opere.",
  },
  {
    code: "moderata",
    nome: "Moderata",
    descrizione: "Rifacimento bagno/cucina, impianti parziali, alcuni serramenti.",
  },
  {
    code: "totale",
    nome: "Totale",
    descrizione: "Demolizioni diffuse, tutti gli impianti, pavimenti e serramenti nuovi.",
  },
];

interface DestinazioneOption {
  code: Destinazione;
  nome: string;
  descrizione: string;
}

/**
 * PRE-SELEZIONATA su "prima_casa", non lasciata vuota: e' il caso di gran
 * lunga piu' frequente ed e' gia' il default del backend, quindi obbligare a
 * scegliere aggiungerebbe un attrito senza aggiungere informazione. Chi ha un
 * secondo immobile lo sa e cambia.
 */
const DESTINAZIONE_OPTIONS: DestinazioneOption[] = [
  {
    code: "prima_casa",
    nome: "Abitazione principale",
    descrizione: "La casa in cui vivi.",
  },
  {
    code: "altro",
    nome: "Altro immobile",
    descrizione: "Seconda casa o immobile a reddito.",
  },
];

const CITTA_ERROR = "Inserisci la città dell'immobile.";
const MQ_ERROR = "Inserisci una superficie valida (numero maggiore di 0).";
const TIPO_ERROR = "Seleziona il tipo di ristrutturazione.";

export interface ValidazioneCampiBase {
  mq: number;
  cittaValid: boolean;
  mqValid: boolean;
  tipoValid: boolean;
  valid: boolean;
}

/** Unica definizione di "campi base validi", condivisa da form Free e Pro. */
export function validaCampiBase(campi: CampiBase): ValidazioneCampiBase {
  const mq = Number(campi.mqRaw);
  const cittaValid = campi.citta.trim().length > 0;
  const mqValid = campi.mqRaw.trim() !== "" && Number.isFinite(mq) && mq >= 1;
  const tipoValid = campi.tipo !== null;
  return { mq, cittaValid, mqValid, tipoValid, valid: cittaValid && mqValid && tipoValid };
}

/** Converte i campi grezzi nel payload della stima, o null se non validi. */
export function toEstimateFormValues(campi: CampiBase): EstimateFormValues | null {
  const { mq, valid } = validaCampiBase(campi);
  if (!valid || campi.tipo === null) return null;
  return { citta: campi.citta.trim(), mq, tipo: campi.tipo, destinazione: campi.destinazione };
}

interface EstimateFormFieldsProps {
  values: CampiBase;
  onChange: (patch: Partial<CampiBase>) => void;
  /** Mostra gli errori solo dopo il primo tentativo di invio. */
  touched?: boolean;
}

/**
 * I quattro campi comuni ai due form (città, m², tipo, destinazione).
 *
 * Estratti per COMPOSIZIONE e non lasciati in `EstimateForm` con un flag
 * `isPro`: il form Free e quello Pro divergono nel numero di step e nella
 * navigazione, cioè in tutto tranne questi campi. Un flag avrebbe fatto
 * convivere due layout in un solo componente.
 */
export function EstimateFormFields({ values, onChange, touched }: EstimateFormFieldsProps) {
  const { cittaValid, mqValid, tipoValid } = validaCampiBase(values);

  return (
    <>
      <CityAutocomplete
        value={values.citta}
        onChange={(citta) => onChange({ citta })}
        error={touched && !cittaValid ? CITTA_ERROR : undefined}
      />

      <div className="flex flex-col gap-2">
        <Label htmlFor="mq">Superficie (m²)</Label>
        <div className="relative">
          <input
            id="mq"
            inputMode="numeric"
            placeholder="Es. 85"
            value={values.mqRaw}
            onChange={(e) => onChange({ mqRaw: e.target.value.replace(/[^0-9]/g, "") })}
            className={cn(
              "h-9 w-full min-w-0 rounded-md border border-input bg-transparent px-2.5 py-1 pr-10 text-base shadow-xs outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 md:text-sm",
              touched && !mqValid && "border-destructive"
            )}
          />
          <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-sm text-muted-foreground">
            m²
          </span>
        </div>
        {touched && !mqValid && <p className="text-sm text-destructive">{MQ_ERROR}</p>}
      </div>

      <div className="flex flex-col gap-2">
        <Label>Tipo di ristrutturazione</Label>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {TIPO_OPTIONS.map((option) => (
            <OptionCard
              key={option.code}
              nome={option.nome}
              descrizione={option.descrizione}
              selected={values.tipo === option.code}
              onSelect={() => onChange({ tipo: option.code })}
            />
          ))}
        </div>
        {touched && !tipoValid && <p className="text-sm text-destructive">{TIPO_ERROR}</p>}
      </div>

      <div className="flex flex-col gap-2">
        <Label>Destinazione dell'immobile</Label>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {DESTINAZIONE_OPTIONS.map((option) => (
            <OptionCard
              key={option.code}
              nome={option.nome}
              descrizione={option.descrizione}
              selected={values.destinazione === option.code}
              onSelect={() => onChange({ destinazione: option.code })}
            />
          ))}
        </div>
        <p className="text-sm text-muted-foreground">
          Cambia l'aliquota delle detrazioni fiscali.
        </p>
      </div>
    </>
  );
}

interface OptionCardProps {
  nome: string;
  descrizione: string;
  selected: boolean;
  onSelect: () => void;
}

/** Button-card selezionabile, stessa forma per tipo e destinazione. */
export function OptionCard({ nome, descrizione, selected, onSelect }: OptionCardProps) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={cn(
        "relative flex min-h-11 flex-col gap-1 rounded-lg border px-4 py-3 text-left transition-all",
        selected
          ? "border-primary bg-accent shadow-sm ring-1 ring-primary"
          : "border-border bg-card hover:border-primary/40 hover:bg-accent/40"
      )}
    >
      {selected && (
        <span className="absolute right-2.5 top-2.5 flex size-4 items-center justify-center rounded-full bg-primary text-primary-foreground">
          <Check className="size-3" aria-hidden />
        </span>
      )}
      <span className="text-sm font-semibold">{nome}</span>
      <span className="text-sm text-muted-foreground">{descrizione}</span>
    </button>
  );
}
