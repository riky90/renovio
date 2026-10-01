import type {
  CatalogoDomande,
  Domanda,
  RawCatalogo,
  Risposte,
  TipoControllo,
  ValoreRisposta,
} from "@/api/domande";

// Funzioni pure del catalogo domande, senza import runtime (solo tipi): cosi'
// lo script `scripts/check-richiesta-stima.ts` le esegue con node, senza
// backend ne' alias `@/`. `api/domande.ts` le ri-esporta: gli import esistenti
// non cambiano.

const CONTROLLI_NUMERICI: TipoControllo[] = ["stepper", "numero"];

export function isNumerico(tipo: TipoControllo): boolean {
  return CONTROLLI_NUMERICI.includes(tipo);
}

/**
 * Normalizza al confine API, come fa `normalizeResponse()` per la stima: i
 * `Decimal` di Pydantic arrivano come stringhe, e uno stepper inizializzato con
 * `"2"` invece che con `2` fa `"2" + 1 === "21"` al primo click.
 *
 * Il default numerico si converte solo se il controllo e' numerico: su una
 * scelta il valore e' un codice opzione, e un codice fatto di cifre non deve
 * diventare un numero.
 */
export function normalizeCatalogo(raw: RawCatalogo): CatalogoDomande {
  return {
    tier: raw.tier,
    mq: raw.mq,
    attese: Object.fromEntries(
      Object.entries(raw.attese).map(([k, v]) => [k, Number(v)])
    ),
    domande: raw.domande.map((d) => ({
      ...d,
      valore_default:
        d.valore_default !== null && isNumerico(d.tipo_controllo)
          ? Number(d.valore_default)
          : (d.valore_default as ValoreRisposta | null),
    })),
  };
}

/**
 * Le risposte iniziali: ogni domanda sul suo default. Le domande senza default
 * restano FUORI dall'oggetto invece di entrarci con un valore finto — il motore
 * tratta l'assenza come "cade sul default di tabella", che e' esattamente
 * quello che vogliamo, mentre uno zero sarebbe una risposta.
 */
export function risposteIniziali(catalogo: CatalogoDomande): Risposte {
  const risposte: Risposte = {};
  for (const domanda of catalogo.domande) {
    if (domanda.valore_default === null) continue;
    if (Array.isArray(domanda.valore_default) && domanda.valore_default.length === 0) continue;
    risposte[domanda.code] = domanda.valore_default;
  }
  return risposte;
}

/**
 * Risolve la visibilita' condizionale nell'ordine del catalogo, con la stessa
 * regola del backend (`services/effetti.py::_visibili`): una domanda governata
 * da un gate non visibile e' a sua volta non visibile, e un riferimento in
 * avanti non si risolve.
 *
 * Il client la ri-implementa perche' deve decidere cosa DISEGNARE; il motore la
 * ri-applica perche' deve decidere cosa CONTA. Sono due domande diverse e il
 * server non si fida di questa: una risposta a una domanda nascosta arriva
 * comunque nel payload, e li' viene ignorata.
 */
export function domandeVisibili(domande: Domanda[], risposte: Risposte): Domanda[] {
  const stato = new Map<string, boolean>();
  const visibili: Domanda[] = [];

  for (const domanda of domande) {
    const gate = domanda.visibile_se_domanda_code;
    let visibile: boolean;

    if (gate === null) {
      visibile = true;
    } else if (!stato.get(gate)) {
      visibile = false;
    } else {
      const attesa = domanda.visibile_se_opzione_code;
      visibile = attesa === null || scelte(risposte[gate]).has(attesa);
    }

    stato.set(domanda.code, visibile);
    if (visibile) visibili.push(domanda);
  }

  return visibili;
}

/** I codici opzione attivi in una risposta, qualunque forma abbia. */
function scelte(risposta: ValoreRisposta | undefined): Set<string> {
  if (risposta === undefined) return new Set();
  if (Array.isArray(risposta)) return new Set(risposta);
  if (typeof risposta === "string") return new Set([risposta]);
  return new Set();
}
