import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { formatEurRange } from "@/lib/currency";
import type { CategoriaDettagliataOut, SottocategoriaOut, VoceOut } from "@/api/dettaglio-pro";

const EMPTY_COPY = "Nessuna voce stimata per questa sottocategoria con i dati inseriti.";

interface SottocategoriaAccordionProps {
  categoria: CategoriaDettagliataOut;
}

/**
 * Accordion shadcn con un item per sottocategoria (UI-SPEC §C.3): trigger =
 * codice·nome per la famiglia gerarchica (A-EDILE), nome-gruppo per la
 * famiglia catalogo (B/C/D). Contenuto = righe-voce a range, nessun accent
 * sulle righe (solo il chevron del trigger, gestito dal primitivo shadcn).
 */
export function SottocategoriaAccordion({ categoria }: SottocategoriaAccordionProps) {
  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-base font-semibold text-foreground">{categoria.nome}</h3>
      <Accordion type="multiple" className="rounded-lg border border-border bg-card px-4">
        {categoria.sottocategorie.map((sottocategoria, index) => (
          <AccordionItem
            key={sottocategoria.codice ?? `${categoria.code}-${index}`}
            value={sottocategoria.codice ?? `${categoria.code}-${index}`}
          >
            <AccordionTrigger>{triggerLabel(sottocategoria)}</AccordionTrigger>
            <AccordionContent>
              {sottocategoria.voci.length === 0 ? (
                <p className="py-2 text-center text-sm text-muted-foreground">{EMPTY_COPY}</p>
              ) : (
                <div className="flex flex-col gap-2">
                  {sottocategoria.voci.map((voce, voceIndex) => (
                    <VoceRow key={voce.codice ?? voceIndex} voce={voce} />
                  ))}
                </div>
              )}
            </AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </div>
  );
}

function triggerLabel(sottocategoria: SottocategoriaOut): string {
  if (sottocategoria.famiglia === "gerarchica" && sottocategoria.codice) {
    return `${sottocategoria.codice} · ${sottocategoria.nome}`;
  }
  return sottocategoria.nome;
}

function VoceRow({ voce }: { voce: VoceOut }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 border-b border-border py-1 text-sm last:border-b-0">
      <p className="flex-1 basis-full text-foreground sm:basis-auto">{voce.descrizione}</p>
      <p className="tabular-nums text-muted-foreground">
        {formatQuantita(voce.quantita_stimata)} {voce.um}
      </p>
      <p className="tabular-nums font-medium text-foreground">
        {formatEurRange(voce.prezzo_min, voce.prezzo_max)}
      </p>
    </div>
  );
}

function formatQuantita(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toLocaleString("it-IT");
}
