import { BonusPanel } from "@/components/BonusPanel";
import { CategoryCard } from "@/components/CategoryCard";
import { FallbackDisclaimer } from "@/components/FallbackDisclaimer";
import { PdfDownloadButton } from "@/components/PdfDownloadButton";
import { TotalCard } from "@/components/TotalCard";
import { Badge } from "@/components/ui/badge";
import { formatEur } from "@/lib/currency";
import type { StimaSalvataOut } from "@/api/stima";

const TIPO_LABELS: Record<string, string> = {
  leggera: "Leggera",
  moderata: "Moderata",
  totale: "Totale",
};

const DESTINAZIONE_LABELS: Record<string, string> = {
  prima_casa: "Abitazione principale",
  altro: "Altro immobile",
};

interface SavedEstimateDetailProps {
  stima: StimaSalvataOut;
  /** Utente Pro: nessun teaser di upgrade sulle card categoria (fix bug teaser). */
  isPro?: boolean;
}

/**
 * Vista snapshot read-only (UI-SPEC F.2): riusa esattamente il layout
 * risultato di Fase 1 (riepilogo input, disclaimer fallback, 4 card
 * categoria, totale) renderizzato dallo snapshot congelato — mai
 * ricalcolato. Nessun bottone soft-wall: l'utente e' gia' autenticato,
 * l'unica azione e' "Scarica PDF".
 */
export function SavedEstimateDetail({ stima, isPro = false }: SavedEstimateDetailProps) {
  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-wrap items-center gap-2 rounded-lg border border-border bg-secondary px-4 py-3">
        <Badge variant="secondary">{stima.input.citta}</Badge>
        <Badge variant="secondary">{stima.input.mq} m²</Badge>
        <Badge variant="secondary">{TIPO_LABELS[stima.input.tipo] ?? stima.input.tipo}</Badge>
        <Badge variant="secondary">
          {DESTINAZIONE_LABELS[stima.input.destinazione] ?? stima.input.destinazione}
        </Badge>
      </div>

      {stima.fallback && stima.disclaimer && (
        <FallbackDisclaimer disclaimer={stima.disclaimer} />
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {stima.categorie.map((categoria) => (
          <CategoryCard key={categoria.code} categoria={categoria} isPro={isPro} />
        ))}
      </div>

      <div className="flex flex-col gap-2">
        {stima.extra.map((extra) => (
          <div
            key={extra.code}
            className="flex items-center justify-between text-sm text-muted-foreground"
          >
            <span>{extra.nome}</span>
            <span className="tabular-nums">{formatEur(extra.importo)}</span>
          </div>
        ))}
      </div>

      <TotalCard totale={stima.totale} />

      {/* Assente sugli snapshot v1, salvati prima della feature: la vista si
          degrada senza il pannello invece di rompersi. */}
      {stima.bonus && <BonusPanel bonus={stima.bonus} />}

      <PdfDownloadButton stimaId={stima.id} />
    </div>
  );
}
