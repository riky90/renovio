import { formatEur } from "@/lib/currency";
import type { ArredoOut } from "@/api/stima";

interface ArredoCardProps {
  arredo: ArredoOut;
}

/**
 * Il forfait di arredo, FRATELLO del totale e non figlio.
 *
 * La scelta visiva segue quella del dominio: niente `RangeBar` e niente bordo
 * primario, che sono il linguaggio del totale lavori. Questa card e' piu'
 * sobria apposta — se somigliasse al totale, l'utente sommerebbe i due numeri,
 * che e' precisamente la confusione che questa fase esiste per evitare. Il
 * titolo lo dice a parole, non solo con lo stile.
 */
export function ArredoCard({ arredo }: ArredoCardProps) {
  return (
    <div className="overflow-hidden rounded-xl border border-dashed border-border bg-card">
      <div className="border-b border-border px-6 py-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Arredo · non compreso nel totale lavori
        </p>
        <p className="mt-2 text-2xl font-semibold tabular-nums text-foreground">
          {formatEur(arredo.totale_min)} – {formatEur(arredo.totale_max)}
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          Finiture {arredo.livello_nome.toLowerCase()}
        </p>
      </div>

      <ul className="divide-y divide-border">
        {arredo.ambienti.map((ambiente) => (
          <li key={ambiente.code} className="flex justify-between gap-4 px-6 py-2.5 text-sm">
            <span className="text-muted-foreground">{ambiente.nome}</span>
            <span className="tabular-nums text-foreground">
              {formatEur(ambiente.eur_min)} – {formatEur(ambiente.eur_max)}
            </span>
          </li>
        ))}
      </ul>

      <p className="px-6 py-4 text-xs leading-relaxed text-muted-foreground">
        {arredo.disclaimer}
      </p>
    </div>
  );
}
