/**
 * Client dell'anteprima stima (PAR-04) sopra `POST /admin/domande/anteprima`
 * (`backend/app/routers/admin/domande.py:496-581`, `require_admin`). Backend
 * gia' completo, questo modulo e' puro consumo — nessun path nuovo.
 *
 * Decimal-as-string wire format: FastAPI serializza i campi `Decimal` come
 * stringa JSON — normalizziamo con la stessa `toNumber()` di
 * `api/admin/listini.ts`, qui applicata anche dentro `categorie[]`,
 * `effetti[]` (`valore`/`unita`/`contributo`, nullable) e la mappa `attese`.
 *
 * La base di confronto lato server e' deliberatamente `risposte=None` (layer
 * degli effetti spento), non `risposte={}`: `base_min`/`base_max` sono quindi
 * la stima senza domande, e `delta` e' esattamente il contributo del
 * catalogo. Il client non ricalcola niente: somme e delta arrivano gia'
 * calcolati dal motore.
 */

import { apiPost } from "@/api/admin/client";

function toNumber(value: unknown): number {
  return typeof value === "number" ? value : Number(value);
}

function toNumberOrNull(value: unknown): number | null {
  return value === null || value === undefined ? null : toNumber(value);
}

export interface AnteprimaIn {
  citta: string;
  mq: number;
  tipo: string;
  risposte: Record<string, unknown>;
}

export interface EffettoTraccia {
  domanda_code: string;
  opzione_code: string;
  tipo_effetto: string;
  categoria_code: string | null;
  valore: number | null;
  unita: number | null;
  contributo: number | null;
  applicato: boolean;
  nota: string | null;
}

interface RawEffettoTraccia {
  domanda_code: string;
  opzione_code: string;
  tipo_effetto: string;
  categoria_code: string | null;
  valore: unknown;
  unita: unknown;
  contributo: unknown;
  applicato: boolean;
  nota: string | null;
}

export interface AnteprimaCategoria {
  code: string;
  nome: string;
  base_min: number;
  base_max: number;
  totale_min: number;
  totale_max: number;
  delta_min: number;
  delta_max: number;
}

interface RawAnteprimaCategoria {
  code: string;
  nome: string;
  base_min: unknown;
  base_max: unknown;
  totale_min: unknown;
  totale_max: unknown;
  delta_min: unknown;
  delta_max: unknown;
}

export interface Anteprima {
  citta: string;
  fallback: boolean;
  mq: number;
  tipo: string;
  attese: Record<string, number>;
  categorie: AnteprimaCategoria[];
  base_totale_min: number;
  base_totale_max: number;
  totale_min: number;
  totale_max: number;
  delta_min: number;
  delta_max: number;
  effetti: EffettoTraccia[];
  avvisi: string[];
}

interface RawAnteprima {
  citta: string;
  fallback: boolean;
  mq: number;
  tipo: string;
  attese: Record<string, unknown>;
  categorie: RawAnteprimaCategoria[];
  base_totale_min: unknown;
  base_totale_max: unknown;
  totale_min: unknown;
  totale_max: unknown;
  delta_min: unknown;
  delta_max: unknown;
  effetti: RawEffettoTraccia[];
  avvisi: string[];
}

function normalizeCategoria(raw: RawAnteprimaCategoria): AnteprimaCategoria {
  return {
    code: raw.code,
    nome: raw.nome,
    base_min: toNumber(raw.base_min),
    base_max: toNumber(raw.base_max),
    totale_min: toNumber(raw.totale_min),
    totale_max: toNumber(raw.totale_max),
    delta_min: toNumber(raw.delta_min),
    delta_max: toNumber(raw.delta_max),
  };
}

function normalizeEffetto(raw: RawEffettoTraccia): EffettoTraccia {
  return {
    domanda_code: raw.domanda_code,
    opzione_code: raw.opzione_code,
    tipo_effetto: raw.tipo_effetto,
    categoria_code: raw.categoria_code,
    valore: toNumberOrNull(raw.valore),
    unita: toNumberOrNull(raw.unita),
    contributo: toNumberOrNull(raw.contributo),
    applicato: raw.applicato,
    nota: raw.nota,
  };
}

function normalizeAttese(raw: Record<string, unknown>): Record<string, number> {
  const out: Record<string, number> = {};
  for (const [key, value] of Object.entries(raw)) {
    out[key] = toNumber(value);
  }
  return out;
}

function normalizeAnteprima(raw: RawAnteprima): Anteprima {
  return {
    citta: raw.citta,
    fallback: raw.fallback,
    mq: raw.mq,
    tipo: raw.tipo,
    attese: normalizeAttese(raw.attese),
    categorie: raw.categorie.map(normalizeCategoria),
    base_totale_min: toNumber(raw.base_totale_min),
    base_totale_max: toNumber(raw.base_totale_max),
    totale_min: toNumber(raw.totale_min),
    totale_max: toNumber(raw.totale_max),
    delta_min: toNumber(raw.delta_min),
    delta_max: toNumber(raw.delta_max),
    effetti: raw.effetti.map(normalizeEffetto),
    avvisi: raw.avvisi,
  };
}

/** POST /admin/domande/anteprima */
export async function calcolaAnteprima(input: AnteprimaIn): Promise<Anteprima> {
  const raw = await apiPost<RawAnteprima>("/admin/domande/anteprima", input);
  return normalizeAnteprima(raw);
}
