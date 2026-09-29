import { useState } from "react";
import { InputGroup, InputGroupAddon, InputGroupInput } from "@/components/ui/input-group";
import { formatImporto, parseImporto, TESTI_AVVISO } from "@/lib/risultato";

interface ImportoFieldProps {
  id: string;
  valore: number | null;
  onChange: (valore: number | null, errore: boolean) => void;
  describedBy?: string;
  autoFocus?: boolean;
  placeholder?: string;
}

const MAX_CIFRE = 9;

/**
 * Campo importo in euro: solo cifre mentre si digita, migliaia it-IT al blur.
 * Vuoto = nessun importo (valido); 0 o non numerico = errore.
 */
export function ImportoField({
  id,
  valore,
  onChange,
  describedBy,
  autoFocus,
  placeholder = "Es. 40.000",
}: ImportoFieldProps) {
  const [testo, setTesto] = useState(valore != null ? formatImporto(valore) : "");
  const [errore, setErrore] = useState(false);
  const erroreId = `${id}-errore`;

  function aggiorna(grezzo: string) {
    const { valore: v, errore: e } = parseImporto(grezzo);
    setErrore(e);
    onChange(v, e);
  }

  return (
    <div className="flex flex-col gap-1.5">
      <InputGroup className="h-11">
        <InputGroupInput
          id={id}
          type="text"
          inputMode="numeric"
          autoComplete="off"
          autoFocus={autoFocus}
          placeholder={placeholder}
          value={testo}
          aria-invalid={errore || undefined}
          aria-describedby={[describedBy, errore ? erroreId : undefined].filter(Boolean).join(" ") || undefined}
          onChange={(e) => {
            // Ripulisce separatori incollati: restano solo le cifre.
            const cifre = e.target.value.replace(/\D/g, "").slice(0, MAX_CIFRE);
            setTesto(cifre);
            aggiorna(cifre);
          }}
          onFocus={() => {
            const { valore: v } = parseImporto(testo);
            if (v != null) setTesto(String(v));
          }}
          onBlur={() => {
            const { valore: v } = parseImporto(testo);
            if (v != null) setTesto(formatImporto(v));
          }}
        />
        <InputGroupAddon align="inline-end">€</InputGroupAddon>
      </InputGroup>
      {errore && (
        <p id={erroreId} className="text-sm text-destructive">
          {TESTI_AVVISO.erroreInput}
        </p>
      )}
    </div>
  );
}
