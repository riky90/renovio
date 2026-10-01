import type { Domanda, Risposte } from "@/api/domande";
import type { StimaRequest } from "@/api/stima";

// Logica pura di confronto delle richieste e di ricalcolo delle risposte del
// wizard. Solo `import type`: la esegue anche `scripts/check-richiesta-stima.ts`
// con node, senza backend (G12).

export function normalizzaRisposte(r: StimaRequest["risposte"]): string {
  const ordinate: Record<string, unknown> = {};
  for (const k of Object.keys(r ?? {}).sort()) {
    const v = (r as Record<string, unknown>)[k];
    ordinate[k] = Array.isArray(v) ? [...v].sort() : v;
  }
  return JSON.stringify(ordinate);
}

export function stessaRichiesta(a: StimaRequest, b: StimaRequest): boolean {
  return (
    a.citta.trim() === b.citta.trim() &&
    a.mq === b.mq &&
    a.tipo === b.tipo &&
    (a.destinazione ?? "prima_casa") === (b.destinazione ?? "prima_casa") &&
    normalizzaRisposte(a.risposte) === normalizzaRisposte(b.risposte)
  );
}

/**
 * Le risposte alle domande nascoste non partono.
 *
 * Il motore le ignorerebbe comunque -- ri-applica la visibilita' per conto suo
 * -- ma finirebbero nello snapshot congelato, dove sembrerebbero risposte date.
 * Una stima salvata deve restare spiegabile, e "ho risposto a una domanda che
 * non mi e' stata fatta" non lo e'.
 */
export function soloVisibili(risposte: Risposte, visibili: Domanda[]): Risposte {
  const codici = new Set(visibili.map((d) => d.code));
  return Object.fromEntries(Object.entries(risposte).filter(([code]) => codici.has(code)));
}

/**
 * Cosa fa il wizard quando arriva un catalogo (effetto del primo catalogo e di
 * ogni cambio di m2): i default sostituiscono le risposte, tranne quelle
 * "toccate" dall'utente.
 *
 * Al PRIMO catalogo (`primo`), le chiavi di `risposteDiPartenza` con valore
 * diverso dal default contano come toccate: la richiesta ripassata da "Modifica"
 * porta il valore di ogni domanda, default compresi. `toccate` viene modificato
 * sul posto (e' il `useRef` del wizard).
 */
export function risposteDopoCatalogo(
  defaults: Risposte,
  precedenti: Risposte,
  toccate: Set<string>,
  risposteDiPartenza: Risposte | undefined,
  primo: boolean
): Risposte {
  if (primo) {
    for (const [code, valore] of Object.entries(risposteDiPartenza ?? {})) {
      if (JSON.stringify(valore) !== JSON.stringify(defaults[code])) {
        toccate.add(code);
      }
    }
  }
  const nuove: Risposte = { ...defaults };
  for (const code of toccate) {
    if (code in precedenti) nuove[code] = precedenti[code];
  }
  return nuove;
}

/**
 * G14: cosa fa l'auto-save quando arriva un risultato per un utente loggato.
 *
 * - `post`: stima nuova (pagina aperta da zero) o primo salvataggio fallito.
 * - `put`: dopo "Modifica" esiste gia' una stima salvata: si aggiorna quella,
 *   identica o no, e MAI un POST (niente doppioni, G12).
 * - `attendi`: dopo "Modifica" il primo POST e' ancora in volo, l'id non c'e'
 *   ancora: si rimanda l'invio a quando arriva.
 */
export type AzioneSalvataggio = "post" | "put" | "attendi";

export function azioneSalvataggio(stato: {
  stimaInModifica: boolean;
  idEsistente: number | null;
  postInVolo: boolean;
}): AzioneSalvataggio {
  if (!stato.stimaInModifica) return "post";
  if (stato.idEsistente !== null) return "put";
  if (stato.postInVolo) return "attendi";
  return "post";
}
