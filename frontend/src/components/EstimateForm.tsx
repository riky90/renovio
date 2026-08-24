import { useState, type FormEvent } from "react";
import { CityAutocomplete } from "@/components/CityAutocomplete";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

export type TipoRistrutturazione = "leggera" | "moderata" | "totale";

export interface EstimateFormValues {
  citta: string;
  mq: number;
  tipo: TipoRistrutturazione;
}

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

const CITTA_ERROR = "Inserisci la città dell'immobile.";
const MQ_ERROR = "Inserisci una superficie valida (numero maggiore di 0).";
const TIPO_ERROR = "Seleziona il tipo di ristrutturazione.";

interface EstimateFormProps {
  onSubmit: (values: EstimateFormValues) => void;
  isSubmitting?: boolean;
}

export function EstimateForm({ onSubmit, isSubmitting }: EstimateFormProps) {
  const [citta, setCitta] = useState("");
  const [mqRaw, setMqRaw] = useState("");
  const [tipo, setTipo] = useState<TipoRistrutturazione | null>(null);
  const [touched, setTouched] = useState(false);

  const mq = Number(mqRaw);
  const cittaValid = citta.trim().length > 0;
  const mqValid = mqRaw.trim() !== "" && Number.isFinite(mq) && mq >= 1;
  const tipoValid = tipo !== null;
  const formValid = cittaValid && mqValid && tipoValid;

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setTouched(true);
    if (tipo === null || !cittaValid || !mqValid) return;
    onSubmit({ citta: citta.trim(), mq, tipo });
  }

  return (
    <form onSubmit={handleSubmit} className="flex w-full flex-col gap-8">
      <CityAutocomplete
        value={citta}
        onChange={setCitta}
        error={touched && !cittaValid ? CITTA_ERROR : undefined}
      />

      <div className="flex flex-col gap-2">
        <Label htmlFor="mq">Superficie (m²)</Label>
        <div className="relative">
          <input
            id="mq"
            inputMode="numeric"
            placeholder="Es. 85"
            value={mqRaw}
            onChange={(e) => setMqRaw(e.target.value.replace(/[^0-9]/g, ""))}
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
          {TIPO_OPTIONS.map((option) => {
            const selected = tipo === option.code;
            return (
              <button
                key={option.code}
                type="button"
                onClick={() => setTipo(option.code)}
                aria-pressed={selected}
                className={cn(
                  "flex min-h-11 flex-col gap-1 rounded-lg border px-4 py-3 text-left transition-colors",
                  selected
                    ? "border-primary bg-accent ring-2 ring-primary"
                    : "border-border bg-card hover:border-muted-foreground/40"
                )}
              >
                <span className="text-sm font-semibold">{option.nome}</span>
                <span className="text-sm text-muted-foreground">{option.descrizione}</span>
              </button>
            );
          })}
        </div>
        {touched && !tipoValid && <p className="text-sm text-destructive">{TIPO_ERROR}</p>}
      </div>

      <Button
        type="submit"
        disabled={!formValid || isSubmitting}
        className="h-11 w-full bg-primary text-base font-semibold text-primary-foreground hover:bg-primary/90"
      >
        {isSubmitting ? "Calcolo in corso..." : "Calcola la stima"}
      </Button>
    </form>
  );
}
