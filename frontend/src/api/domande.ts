import { apiGet } from "@/api/client";
import { normalizeCatalogo } from "@/lib/domande";

// Le funzioni pure stanno in lib/domande.ts (eseguibili da node, G12); qui si ri-esportano.
export { domandeVisibili, isNumerico, risposteIniziali } from "@/lib/domande";

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

export interface RawDomanda extends Omit<Domanda, "valore_default"> {
  /** Pydantic serializza i Decimal come stringa: "2" e non 2. */
  valore_default: number | string | string[] | null;
}

export interface RawCatalogo extends Omit<CatalogoDomande, "attese" | "domande"> {
  attese: Record<string, unknown>;
  domande: RawDomanda[];
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
