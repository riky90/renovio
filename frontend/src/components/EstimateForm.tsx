import { useState, type FormEvent } from "react";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  CAMPI_BASE_INIZIALI,
  EstimateFormFields,
  toEstimateFormValues,
  validaCampiBase,
  type CampiBase,
} from "@/components/EstimateFormFields";

/**
 * Form Free: un solo step con i campi condivisi. Le domande mirate e i livelli
 * di finitura vivono in `EstimateFormPro`, non dietro un flag qui.
 *
 * I tipi restano ri-esportati da questo modulo perché sono il punto di import
 * storico di `api/stima.ts` e `api/lead.ts`.
 */
export type {
  Destinazione,
  EstimateFormValues,
  TipoRistrutturazione,
} from "@/components/EstimateFormFields";

import type { EstimateFormValues } from "@/components/EstimateFormFields";

interface EstimateFormProps {
  onSubmit: (values: EstimateFormValues) => void;
  isSubmitting?: boolean;
}

export function EstimateForm({ onSubmit, isSubmitting }: EstimateFormProps) {
  const [campi, setCampi] = useState<CampiBase>(CAMPI_BASE_INIZIALI);
  const [touched, setTouched] = useState(false);

  const { valid } = validaCampiBase(campi);

  function handleChange(patch: Partial<CampiBase>) {
    setCampi((prev) => ({ ...prev, ...patch }));
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setTouched(true);
    const values = toEstimateFormValues(campi);
    if (values === null) return;
    onSubmit(values);
  }

  return (
    <form onSubmit={handleSubmit} className="flex w-full flex-col gap-6">
      <EstimateFormFields values={campi} onChange={handleChange} touched={touched} />

      <Button
        type="submit"
        disabled={!valid || isSubmitting}
        className="group h-12 w-full bg-primary text-base font-semibold text-primary-foreground shadow-sm hover:bg-primary/90"
      >
        {isSubmitting ? (
          "Calcolo in corso..."
        ) : (
          <>
            Calcola la stima
            <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
          </>
        )}
      </Button>
    </form>
  );
}
