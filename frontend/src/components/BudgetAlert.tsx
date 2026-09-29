import { useState } from "react";
import { AlertTriangle, CheckCircle2, Info, type LucideIcon } from "lucide-react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { ImportoField } from "@/components/ImportoField";
import type { ConfrontoFinitureOut } from "@/api/stima";
import { formatEur, formatEurRange } from "@/lib/currency";
import { cn } from "@/lib/utils";
import { deltaConfronto, statoBudget, TESTI_AVVISO, type StatoBudget } from "@/lib/risultato";

interface BudgetAlertProps {
  budget: number | null;
  /** Totale lavori IVA inclusa, arredo escluso (D-08). */
  totaleMin: number;
  totaleMax: number;
  onSalva: (budget: number | null) => Promise<void>;
  /** Confronto a finiture inferiori calcolato dal server (D-09). */
  confronto?: ConfrontoFinitureOut | null;
  finitureAlMinimo?: boolean;
}

interface AspettoStato {
  superficie: string;
  Icona: LucideIcon;
  titolo: string;
  corpo: (budget: number) => string;
}

const ASPETTO: Record<StatoBudget, AspettoStato> = {
  fuori: {
    superficie: "bg-amber-bg border-amber-border text-amber-fg",
    Icona: AlertTriangle,
    titolo: TESTI_AVVISO.titoloFuori,
    corpo: () => TESTI_AVVISO.fuoriMenoLavori,
  },
  limite: {
    superficie: "bg-amber-bg border-amber-border text-amber-fg",
    Icona: Info,
    titolo: TESTI_AVVISO.titoloLimite,
    corpo: () => TESTI_AVVISO.corpoLimite,
  },
  dentro: {
    superficie: "bg-accent/60 border-border text-accent-foreground",
    Icona: CheckCircle2,
    titolo: TESTI_AVVISO.titoloDentro,
    corpo: (b) => TESTI_AVVISO.corpoDentro(formatEur(b)),
  },
};

/**
 * Avviso budget a tre stati. Confronta il budget dichiarato con il totale
 * cliente gia' nel DTO: non tocca mai il prezzo e non usa la variante
 * destructive (sforare il budget non e' un errore).
 */
export function BudgetAlert({
  budget,
  totaleMin,
  totaleMax,
  onSalva,
  confronto = null,
  finitureAlMinimo = false,
}: BudgetAlertProps) {
  const [aperto, setAperto] = useState(false);

  const stato = statoBudget(budget, totaleMin, totaleMax);

  if (budget === null || stato === null) {
    if (!aperto) {
      return (
        <div>
          <button
            type="button"
            onClick={() => setAperto(true)}
            className="text-sm font-medium text-primary underline-offset-4 hover:underline"
          >
            {TESTI_AVVISO.aggiungi}
          </button>
        </div>
      );
    }
    return (
      <div className="flex flex-col gap-4 rounded-lg border border-border bg-card px-4 py-4">
        <CampoModifica valoreIniziale={null} onSalva={onSalva} autoFocus />
        <p className="text-xs text-muted-foreground">{TESTI_AVVISO.nota}</p>
      </div>
    );
  }

  const { superficie, Icona, titolo, corpo } = ASPETTO[stato];

  const delta =
    stato === "fuori" && confronto
      ? deltaConfronto(totaleMin, totaleMax, confronto.totale_min, confronto.totale_max)
      : null;
  const livello = confronto?.livello_nome.toLowerCase() ?? "";
  let testoCorpo = corpo(budget);
  if (stato === "fuori") {
    if (confronto && delta) {
      testoCorpo = TESTI_AVVISO.confrontoCorpo(
        livello,
        formatEurRange(confronto.totale_min, confronto.totale_max),
        formatEurRange(delta.min, delta.max),
      );
    } else if (finitureAlMinimo) {
      testoCorpo = TESTI_AVVISO.fuoriEconomiche;
    }
  }

  return (
    <Alert
      role="status"
      aria-live="polite"
      className={cn(
        "flex flex-col gap-4 px-4 py-4 transition-opacity duration-150 motion-reduce:transition-none",
        superficie,
      )}
    >
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <Icona className="size-5 shrink-0" aria-hidden />
          <p className="font-display text-xl font-semibold">{titolo}</p>
        </div>
        <p className="text-sm">{testoCorpo}</p>
        {confronto && delta && (
          <dl className="flex flex-col gap-1 text-sm">
            <div className="flex flex-wrap justify-between gap-x-4">
              <dt>Ora (IVA inclusa)</dt>
              <dd className="font-display tabular-nums">{formatEurRange(totaleMin, totaleMax)}</dd>
            </div>
            <div className="flex flex-wrap justify-between gap-x-4">
              <dt>Con finiture {livello}</dt>
              <dd className="font-display tabular-nums">
                {formatEurRange(confronto.totale_min, confronto.totale_max)}
              </dd>
            </div>
            <p className="text-xs text-muted-foreground">
              circa {formatEurRange(delta.min, delta.max)} in meno
            </p>
          </dl>
        )}
      </div>
      <CampoModifica key={budget} valoreIniziale={budget} onSalva={onSalva} />
      <p className="text-xs text-muted-foreground">{TESTI_AVVISO.nota}</p>
    </Alert>
  );
}

function CampoModifica({
  valoreIniziale,
  onSalva,
  autoFocus,
}: {
  valoreIniziale: number | null;
  onSalva: (budget: number | null) => Promise<void>;
  autoFocus?: boolean;
}) {
  const [valore, setValore] = useState<number | null>(valoreIniziale);
  const [errore, setErrore] = useState(false);
  const [pending, setPending] = useState(false);
  const [erroreSalvataggio, setErroreSalvataggio] = useState(false);

  async function salva(nuovo: number | null) {
    setPending(true);
    setErroreSalvataggio(false);
    try {
      await onSalva(nuovo);
    } catch {
      setErroreSalvataggio(true);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor="budget-avviso" className="text-sm font-semibold">
        {TESTI_AVVISO.labelCampo}
      </Label>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start">
        <div className="sm:flex-1">
          <ImportoField
            id="budget-avviso"
            valore={valoreIniziale}
            autoFocus={autoFocus}
            onChange={(v, e) => {
              setValore(v);
              setErrore(e);
            }}
          />
        </div>
        <Button
          type="button"
          disabled={pending || errore || valore === null}
          onClick={() => void salva(valore)}
          className="h-11 w-full sm:w-auto"
        >
          {pending ? TESTI_AVVISO.ctaAggiorno : TESTI_AVVISO.cta}
        </Button>
      </div>
      {erroreSalvataggio && (
        <p className="text-sm text-destructive">{TESTI_AVVISO.erroreSalvataggio}</p>
      )}
      {valoreIniziale !== null && (
        <button
          type="button"
          disabled={pending}
          onClick={() => void salva(null)}
          className="self-start text-sm text-muted-foreground hover:underline"
        >
          {TESTI_AVVISO.togli}
        </button>
      )}
    </div>
  );
}
