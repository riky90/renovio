import { Label } from "@/components/ui/label";
import { NumberStepper } from "@/components/ui/number-stepper";
import { OptionCard } from "@/components/EstimateFormFields";
import { cn } from "@/lib/utils";
import { isNumerico, type Domanda, type OpzioneDomanda, type ValoreRisposta } from "@/api/domande";

/**
 * Sottoinsieme di `Domanda`/`OpzioneDomanda`: quello che a questo componente
 * serve davvero per disegnare, cosi' il pannello Pro (`DomandaProOut`, meno
 * campi di `Domanda`) puo' passare le sue domande senza un adattamento.
 */
export type DomandaMinima = Pick<Domanda, "code" | "testo" | "help" | "tipo_controllo"> & {
  opzioni: Pick<OpzioneDomanda, "code" | "etichetta" | "descrizione">[];
};

interface DomandaFieldProps {
  domanda: DomandaMinima;
  valore: ValoreRisposta | undefined;
  onChange: (valore: ValoreRisposta) => void;
  /**
   * Griglia 2x2 fissa (UI-SPEC §A.2), invece della regola generica
   * `opzioni.length === 2 ? "sm:grid-cols-2" : "sm:grid-cols-3"`: solo per il
   * pavimento (4 opzioni, pannello largo max 640px). Senza questa prop il
   * comportamento resta identico a oggi — nessun campo del wizard la passa.
   */
  griglia?: "due-colonne";
}

/**
 * Disegna UNA domanda del catalogo, qualunque essa sia.
 *
 * Questo componente e' il motivo per cui aggiungere una domanda torna a essere
 * un lavoro da pannello admin: non conosce nessuna domanda per nome, conosce
 * solo i cinque `tipo_controllo`. Un `code` nuovo in tabella compare nel wizard
 * senza che qui cambi una riga.
 *
 * Il corollario e' che l'insieme dei controlli deve restare chiuso e piccolo,
 * esattamente come l'insieme dei sette tipi di effetto lato motore: un
 * controllo in piu' e' una decisione di design, non una riga di configurazione.
 */
export function DomandaField({ domanda, valore, onChange, griglia }: DomandaFieldProps) {
  const etichettaId = `domanda-${domanda.code}`;
  const helpId = domanda.help ? `${etichettaId}-help` : undefined;

  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor={etichettaId} className="text-sm font-medium">
        {domanda.testo}
      </Label>
      {domanda.help && (
        <p id={helpId} className="text-sm text-muted-foreground">
          {domanda.help}
        </p>
      )}
      <Controllo
        domanda={domanda}
        valore={valore}
        onChange={onChange}
        id={etichettaId}
        helpId={helpId}
        griglia={griglia}
      />
    </div>
  );
}

function Controllo({
  domanda,
  valore,
  onChange,
  id,
  helpId,
  griglia,
}: DomandaFieldProps & { id: string; helpId?: string }) {
  if (isNumerico(domanda.tipo_controllo)) {
    return (
      <NumberStepper
        id={id}
        value={typeof valore === "number" ? valore : 0}
        onChange={onChange}
        aria-label={domanda.testo}
        aria-describedby={helpId}
      />
    );
  }

  if (domanda.tipo_controllo === "scelta_multipla") {
    const scelti = new Set(Array.isArray(valore) ? valore : []);
    return (
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {domanda.opzioni.map((opzione) => (
          <OptionCard
            key={opzione.code}
            nome={opzione.etichetta}
            descrizione={opzione.descrizione ?? ""}
            selected={scelti.has(opzione.code)}
            onSelect={() => {
              const prossimi = new Set(scelti);
              // Toggle e non set: su una scelta multipla il secondo click sulla
              // stessa opzione deve toglierla, altrimenti non si torna indietro.
              if (prossimi.has(opzione.code)) prossimi.delete(opzione.code);
              else prossimi.add(opzione.code);
              onChange([...prossimi]);
            }}
          />
        ))}
      </div>
    );
  }

  // scelta_singola / toggle: stessa forma, cambia solo quante opzioni ci sono.
  // Eccezione dichiarata (UI-SPEC §A.2): con `griglia="due-colonne"` la
  // griglia e' 2x2 fissa a ogni breakpoint, non solo `sm:` — usata solo dal
  // pavimento (4 opzioni in un pannello largo max 640px); senza la prop il
  // wizard non cambia.
  return (
    <div
      className={cn(
        "grid grid-cols-1 gap-3",
        griglia === "due-colonne"
          ? "grid-cols-2"
          : domanda.opzioni.length === 2
            ? "sm:grid-cols-2"
            : "sm:grid-cols-3"
      )}
    >
      {domanda.opzioni.map((opzione) => (
        <OptionCard
          key={opzione.code}
          nome={opzione.etichetta}
          descrizione={opzione.descrizione ?? ""}
          selected={valore === opzione.code}
          onSelect={() => onChange(opzione.code)}
        />
      ))}
    </div>
  );
}
