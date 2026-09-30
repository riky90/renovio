import { formatEur } from "@/lib/currency";
import { formatAliquota, vociBonusArredo, vociBonusLavori } from "@/lib/risultato";
import type { ArredoOut, BonusOut } from "@/api/stima";

interface ArredoCardProps {
  arredo: ArredoOut;
  /** Bonus del risultato: le voci `su_arredo` (es. Bonus Mobili) si mostrano qui (G10). */
  bonus?: BonusOut | null;
}

/**
 * Il forfait di arredo, FRATELLO del totale e non figlio.
 *
 * La scelta visiva segue quella del dominio: niente `RangeBar` e niente bordo
 * primario, che sono il linguaggio del totale lavori. Questa card e' piu'
 * sobria apposta — se somigliasse al totale, l'utente sommerebbe i due numeri,
 * che e' precisamente la confusione che questa fase esiste per evitare. Il
 * titolo lo dice a parole, non solo con lo stile.
 *
 * G10: le detrazioni sull'arredo (Bonus Mobili) stanno qui e non nel pannello
 * Bonus, perche' l'arredo non e' compreso nel totale lavori. Restano a range,
 * senza barra, per lo stesso motivo. Se il pannello Bonus non c'e' (nessuna
 * voce sui lavori) il disclaimer fiscale accompagna comunque la detrazione.
 */
export function ArredoCard({ arredo, bonus = null }: ArredoCardProps) {
  const vociArredo = vociBonusArredo(bonus);
  const senzaPannelloBonus = vociBonusLavori(bonus).length === 0;

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

      {bonus && vociArredo.length > 0 && (
        <div className="border-t border-border px-6 py-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Detrazione sull'arredo
          </p>
          <div className="mt-2 flex flex-col gap-3">
            {vociArredo.map((voce) => (
              <div key={voce.code} className="text-sm">
                <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                  <span className="font-medium text-foreground">
                    {voce.nome} · {formatAliquota(voce.aliquota_pct)}
                  </span>
                  <span className="tabular-nums text-foreground">
                    {formatEur(voce.detrazione_min)} – {formatEur(voce.detrazione_max)}
                  </span>
                </div>
                <p className="text-muted-foreground">
                  in {voce.rate_annuali} rate annue da {formatEur(voce.rata_annua_min)} –{" "}
                  {formatEur(voce.rata_annua_max)}
                </p>
                {voce.tetto_raggiunto && voce.tetto_spesa_eur !== null && (
                  <p className="text-muted-foreground">
                    La spesa supera il tetto di {formatEur(voce.tetto_spesa_eur)}: la parte
                    eccedente non è detraibile.
                  </p>
                )}
              </div>
            ))}
          </div>
          {senzaPannelloBonus && (
            <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
              {bonus.disclaimer}
            </p>
          )}
        </div>
      )}

      <p className="px-6 py-4 text-xs leading-relaxed text-muted-foreground">
        {arredo.disclaimer}
      </p>
    </div>
  );
}
