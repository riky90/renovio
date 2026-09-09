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
 * Etichette dei livelli, risolte dal catalogo del server e passate qui per
 * nome: il badge mostra "Lusso", non "alto".
 */
type NomiLivelli = Record<string, string>;

/**
 * Accordion shadcn con un item per sottocategoria (UI-SPEC §C.3): trigger =
 * codice·nome per la famiglia gerarchica (A-EDILE), nome-gruppo per la
 * famiglia catalogo (B/C/D). Contenuto = righe-voce a range, nessun accent
 * sulle righe (solo il chevron del trigger, gestito dal primitivo shadcn).
 */
export function SottocategoriaAccordion({
  categoria,
  nomiLivelli = {},
}: SottocategoriaAccordionProps & { nomiLivelli?: NomiLivelli }) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-base font-semibold text-foreground">{categoria.nome}</h3>
        {categoria.livello_scelto && (
          <span className="rounded-full border border-border bg-secondary px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
            Finitura:{" "}
            {categoria.livello_scelto_nome ??
              nomiLivelli[categoria.livello_scelto] ??
              categoria.livello_scelto}
          </span>
        )}
      </div>
      <Accordion type="multiple" className="rounded-lg border border-border bg-card px-4">
        {categoria.sottocategorie.map((sottocategoria, index) => (
          <AccordionItem
            key={sottocategoria.codice ?? `${categoria.code}-${index}`}
            value={sottocategoria.codice ?? `${categoria.code}-${index}`}
          >
            <AccordionTrigger>{triggerLabel(sottocategoria)}</AccordionTrigger>
            <AccordionContent>
              {(() => {
                // Nascondi le voci non applicate a questo tipo (quantità 0):
                // contribuiscono €0 e creerebbero solo confusione nell'elenco.
                const vociVisibili = sottocategoria.voci.filter((v) => v.quantita_stimata > 0);
                return vociVisibili.length === 0 ? (
                  <p className="py-2 text-center text-sm text-muted-foreground">{EMPTY_COPY}</p>
                ) : (
                  <div className="flex flex-col gap-2">
                    {vociVisibili.map((voce, voceIndex) => (
                      <VoceRow
                        key={voce.codice ?? voceIndex}
                        voce={voce}
                        nomiLivelli={nomiLivelli}
                      />
                    ))}
                  <div className="flex items-baseline justify-between gap-3 pt-2 text-sm font-medium text-foreground">
                    <span className="text-muted-foreground">Subtotale</span>
                    <span className="tabular-nums">
                      {formatEurRange(sottocategoria.totale_min, sottocategoria.totale_max)}
                    </span>
                    </div>
                  </div>
                );
              })()}
            </AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
      <div className="flex items-baseline justify-between gap-3 px-4 text-sm font-semibold text-foreground">
        <span>Totale {categoria.nome}</span>
        <span className="tabular-nums">
          {formatEurRange(categoria.totale_min, categoria.totale_max)}
        </span>
      </div>
    </div>
  );
}

function triggerLabel(sottocategoria: SottocategoriaOut): string {
  if (sottocategoria.famiglia === "gerarchica" && sottocategoria.codice) {
    return `${sottocategoria.codice} · ${sottocategoria.nome}`;
  }
  return sottocategoria.nome;
}

function VoceRow({ voce, nomiLivelli }: { voce: VoceOut; nomiLivelli: NomiLivelli }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 border-b border-border py-1 text-sm last:border-b-0">
      <p className="flex-1 basis-full text-foreground sm:basis-auto">
        {voce.descrizione}
        {voce.livello && (
          <span className="ml-2 rounded-full bg-secondary px-2 py-0.5 text-xs text-muted-foreground">
            {nomiLivelli[voce.livello] ?? voce.livello}
          </span>
        )}
      </p>
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
