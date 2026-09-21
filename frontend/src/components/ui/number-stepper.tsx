import { Minus, Plus } from "lucide-react";
import { cn } from "@/lib/utils";

interface NumberStepperProps {
  id?: string;
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  "aria-label"?: string;
  "aria-describedby"?: string;
  disabled?: boolean;
}

/**
 * Contatore −/valore/+ per le quantita' del wizard.
 *
 * Sostituisce gli `<input inputMode="numeric">` grezzi per una ragione precisa:
 * questi campi arrivano pre-compilati con il valore atteso per i metri quadri,
 * e l'utente li AGGIUSTA invece di compilarli. Un input di testo invita a
 * cancellare e ridigitare — e passa per lo stato vuoto, che non e' un numero e
 * non e' nemmeno zero. Con i bottoni lo stato vuoto non esiste: il valore e'
 * sempre un numero valido, dal primo render all'invio.
 *
 * Il campo resta digitabile per chi deve saltare da 2 a 14, ma una digitazione
 * non valida non azzera il valore: viene ignorata finche' non torna un numero.
 * Il fallback del campo vuoto e' `min` e non 0, perche' 0 puo' essere fuori
 * dal dominio della domanda.
 */
export function NumberStepper({
  id,
  value,
  onChange,
  min = 0,
  max = 999,
  step = 1,
  disabled,
  ...aria
}: NumberStepperProps) {
  const clamp = (n: number) => Math.min(max, Math.max(min, n));

  return (
    <div
      className={cn(
        "inline-flex h-11 items-stretch overflow-hidden rounded-lg border border-input bg-card shadow-xs",
        disabled && "opacity-50"
      )}
    >
      <StepButton
        label="Diminuisci"
        onClick={() => onChange(clamp(value - step))}
        disabled={disabled || value <= min}
      >
        <Minus className="size-4" aria-hidden />
      </StepButton>

      <input
        id={id}
        type="text"
        inputMode="numeric"
        value={String(value)}
        onChange={(e) => {
          const grezzo = e.target.value.replace(/[^0-9]/g, "");
          // Campo svuotato: si torna al minimo invece di uscire dai numeri.
          if (grezzo === "") return onChange(min);
          onChange(clamp(Number(grezzo)));
        }}
        disabled={disabled}
        className="w-14 border-x border-input bg-transparent text-center text-base font-semibold tabular-nums outline-none focus-visible:bg-accent/40 md:text-sm"
        {...aria}
      />

      <StepButton
        label="Aumenta"
        onClick={() => onChange(clamp(value + step))}
        disabled={disabled || value >= max}
      >
        <Plus className="size-4" aria-hidden />
      </StepButton>
    </div>
  );
}

/** 44px di lato: la soglia di tap su mobile, dove questo wizard si compila. */
function StepButton({
  label,
  onClick,
  disabled,
  children,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "flex w-11 items-center justify-center text-muted-foreground transition-colors",
        "hover:bg-accent hover:text-foreground disabled:pointer-events-none disabled:opacity-40"
      )}
    >
      {children}
    </button>
  );
}
