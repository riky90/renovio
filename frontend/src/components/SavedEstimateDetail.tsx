import { useQueryClient } from "@tanstack/react-query";
import { ArredoCard } from "@/components/ArredoCard";
import { BudgetAlert } from "@/components/BudgetAlert";
import { BonusPanel } from "@/components/BonusPanel";
import { CategoryCard } from "@/components/CategoryCard";
import { FallbackDisclaimer } from "@/components/FallbackDisclaimer";
import { PdfDownloadButton } from "@/components/PdfDownloadButton";
import { TotalCard } from "@/components/TotalCard";
import { Badge } from "@/components/ui/badge";
import { sommaMediCategorie } from "@/lib/risultato";
import { patchBudgetStima, type StimaSalvataOut } from "@/api/stima";

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
  /**
   * G14(f): la vista snapshot mostra solo stime Free (le Pro si aprono in
   * DettaglioProView), quindi le card hanno sempre il lucchetto, anche se
   * l'utente oggi e' Pro. Per un utente Pro il link del lucchetto porta qui
   * ("Rifai in versione Pro") invece che a "Passa a Pro" (P5, fix bug teaser).
   */
  rifaiProHref?: string;
}

/**
 * Vista snapshot read-only (UI-SPEC F.2): riusa esattamente il layout
 * risultato di Fase 1 (riepilogo input, disclaimer fallback, 4 card
 * categoria, totale) renderizzato dallo snapshot congelato — mai
 * ricalcolato. Nessun bottone soft-wall: l'utente e' gia' autenticato,
 * l'unica azione e' "Scarica PDF".
 */
export function SavedEstimateDetail({ stima, rifaiProHref }: SavedEstimateDetailProps) {
  const sommaMedi = sommaMediCategorie(stima.categorie);
  const queryClient = useQueryClient();
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

      <TotalCard
        totale={stima.totale}
        categorie={stima.categorie}
        extra={stima.extra}
        budget={stima.budget_eur}
      />

      {/* Snapshot pre-fase: budget null -> solo "Aggiungi il tuo budget". */}
      <BudgetAlert
        budget={stima.budget_eur}
        totaleMin={stima.totale.totale_min}
        totaleMax={stima.totale.totale_max}
        confronto={stima.confronto_finiture}
        finitureAlMinimo={stima.finiture_al_minimo}
        onSalva={async (v) => {
          await patchBudgetStima(stima.id, v);
          await queryClient.invalidateQueries({ queryKey: ["stima-dettaglio", stima.id] });
        }}
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {stima.categorie.map((categoria) => (
          <CategoryCard
            key={categoria.code}
            categoria={categoria}
            rifaiProHref={rifaiProHref}
            mq={stima.input.mq}
            sommaMedi={sommaMedi}
          />
        ))}
      </div>

      {/* Assente sugli snapshot v1, salvati prima della feature: la vista si
          degrada senza il pannello invece di rompersi. */}
      {stima.bonus && (
        <BonusPanel
          bonus={stima.bonus}
        />
      )}

      {/* Idem per l'arredo: assente su ogni snapshot anteriore alla fase 07.
          G10: il Bonus Mobili (voci su_arredo) sta nella card, non nel pannello Bonus. */}
      {stima.arredo && <ArredoCard arredo={stima.arredo} bonus={stima.bonus} />}

      <PdfDownloadButton stimaId={stima.id} />
    </div>
  );
}
