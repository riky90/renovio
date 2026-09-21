import { apiGet } from "@/api/client";

/**
 * GET /api/v1/domande — il catalogo che costruisce il wizard.
 *
 * Fine dell'hardcoding: prima le domande vivevano in `EstimateFormPro.tsx` e in
 * `DettaglioProView.tsx` come costanti, e aggiungerne una voleva dire un deploy
 * del frontend. Ora il client non conosce nessuna domanda per nome — sa solo
 * come si disegna un `tipo_controllo`.
 *
 * Quello che il catalogo NON porta sono gli effetti: cosa fa una risposta al
 * prezzo resta server-side. Il client raccoglie le risposte e le rimanda; il
 * totale lo fa il motore.
 */

export type TipoControllo =
  | "stepper"
  | "numero"
  | "scelta_singola"
  | "scelta_multipla"
  | "toggle";

/** Il valore di una risposta, nelle tre forme che i controlli producono. */
export type ValoreRisposta = number | string | string[];

/** `{ codice_domanda: risposta }` — la forma che `POST /stima` si aspetta. */
export type Risposte = Record<string, ValoreRisposta>;

export interface OpzioneDomanda {
  code: string;
  etichetta: string;
  descrizione: string | null;
  immagine_url: string | null;
  is_default: boolean;
  ordine: number;
}

export interface Domanda {
  code: string;
  testo: string;
  help: string | null;
  tipo_controllo: TipoControllo;
  gruppo: string;
  ordine: number;
  tier_minimo: "free" | "pro";
  attributo_code: string | null;
  obbligatoria: boolean;
  visibile_se_domanda_code: string | null;
  visibile_se_opzione_code: string | null;
  /** Gia' risolto per i m² richiesti: numero, codice opzione o lista di codici. */
  valore_default: ValoreRisposta | null;
  opzioni: OpzioneDomanda[];
}

export interface CatalogoDomande {
  tier: "free" | "pro";
  mq: number | null;
  attese: Record<string, number>;
  domande: Domanda[];
}

interface RawDomanda extends Omit<Domanda, "valore_default"> {
  /** Pydantic serializza i Decimal come stringa: "2" e non 2. */
  valore_default: number | string | string[] | null;
}

interface RawCatalogo extends Omit<CatalogoDomande, "attese" | "domande"> {
  attese: Record<string, unknown>;
  domande: RawDomanda[];
}

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
function normalizeCatalogo(raw: RawCatalogo): CatalogoDomande {
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
 * `mq` e' opzionale ma quasi sempre presente: senza, gli stepper tornano con
 * `valore_default: null` e il wizard mostra i campi vuoti invece di proporre i
 * valori standard.
 */
export async function getCatalogoDomande(params: {
  tier?: "free" | "pro";
  mq?: number;
}): Promise<CatalogoDomande> {
  const query = new URLSearchParams();
  query.set("tier", params.tier ?? "free");
  if (params.mq !== undefined) query.set("mq", String(params.mq));
  const raw = await apiGet<RawCatalogo>(`/domande?${query.toString()}`);
  return normalizeCatalogo(raw);
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
