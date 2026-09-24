/**
 * CRUD catalogo domande (D-21..D-38) sopra `routers/admin/domande.py`. Solo
 * per `pages/admin/*` — nessun campo prezzo/coefficiente impresa qui, il
 * catalogo non ne ha (CLAUDE.md regola #1).
 *
 * Decimal-as-string wire format: `EffettoOut.valore` arriva come stringa
 * JSON (Pydantic v2 serializza `Decimal` cosi'), normalizzato con
 * `toNumber()` una sola volta qui, come `api/admin/listini.ts`.
 *
 * Nessuna funzione DELETE in questo file (D-39): il catalogo si disattiva,
 * non si cancella.
 */

import { apiGet, apiPost, apiPatch } from "@/api/admin/client";
import type { TipoControllo } from "@/api/domande";

export const DOMANDE_QUERY_KEY = ["admin-domande"] as const;

export function chiaveOpzioni(domandaCode: string) {
  return [...DOMANDE_QUERY_KEY, "opzioni", domandaCode] as const;
}

export function chiaveEffetti(domandaCode: string) {
  return [...DOMANDE_QUERY_KEY, "effetti", domandaCode] as const;
}

function toNumber(value: unknown): number {
  return typeof value === "number" ? value : Number(value);
}

export interface DomandaOut {
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
  attiva: boolean;
}

export interface DomandaCreateInput {
  code: string;
  testo: string;
  help?: string | null;
  tipo_controllo: TipoControllo;
  gruppo: string;
  ordine: number;
  tier_minimo: "free" | "pro";
  attributo_code?: string | null;
  obbligatoria: boolean;
  visibile_se_domanda_code?: string | null;
  visibile_se_opzione_code?: string | null;
  attiva?: boolean;
}

export interface DomandaPatchInput {
  testo?: string;
  help?: string | null;
  tipo_controllo?: TipoControllo;
  gruppo?: string;
  ordine?: number;
  tier_minimo?: "free" | "pro";
  attributo_code?: string | null;
  obbligatoria?: boolean;
  visibile_se_domanda_code?: string | null;
  visibile_se_opzione_code?: string | null;
  attiva?: boolean;
}

export interface OpzioneOut {
  id: number;
  domanda_code: string;
  code: string;
  etichetta: string;
  descrizione: string | null;
  immagine_url: string | null;
  is_default: boolean;
  ordine: number;
  attiva: boolean;
}

export interface OpzioneCreateInput {
  domanda_code: string;
  code: string;
  etichetta: string;
  descrizione?: string | null;
  immagine_url?: string | null;
  is_default?: boolean;
  ordine: number;
  attiva?: boolean;
}

export interface OpzionePatchInput {
  etichetta?: string;
  descrizione?: string | null;
  immagine_url?: string | null;
  is_default?: boolean;
  ordine?: number;
  attiva?: boolean;
}

export type TipoEffetto =
  | "moltiplicatore_categoria"
  | "eur_mq_categoria"
  | "eur_fisso_categoria"
  | "eur_per_scostamento"
  | "includi"
  | "escludi"
  | "fattore_quantita"
  | "quantita_per_unita";

export type TargetEffetto = "categoria" | "sottocategoria" | "voce";

export interface EffettoOut {
  id: number;
  opzione_id: number;
  domanda_code: string;
  opzione_code: string;
  tipo_effetto: TipoEffetto;
  target_categoria_code: string | null;
  target_sottocategoria_id: number | null;
  target_voce_id: number | null;
  tipo_code: "leggera" | "moderata" | "totale" | null;
  valore: number | null;
  attivo: boolean;
}

interface RawEffettoOut extends Omit<EffettoOut, "valore"> {
  valore: unknown;
}

export interface EffettoCreateInput {
  opzione_id: number;
  tipo_effetto: TipoEffetto;
  target_categoria_code?: string | null;
  target_sottocategoria_id?: number | null;
  target_voce_id?: number | null;
  tipo_code?: "leggera" | "moderata" | "totale" | null;
  valore?: number | null;
  attivo?: boolean;
}

export interface EffettoPatchInput {
  valore?: number | null;
  tipo_code?: "leggera" | "moderata" | "totale" | null;
  attivo?: boolean;
}

function normalizeEffetto(raw: RawEffettoOut): EffettoOut {
  return {
    ...raw,
    valore: raw.valore === null || raw.valore === undefined ? null : toNumber(raw.valore),
  };
}

/** GET /admin/domande */
export async function getDomande(): Promise<DomandaOut[]> {
  return apiGet<DomandaOut[]>("/admin/domande");
}

/** POST /admin/domande — upsert per `code` (201). */
export async function createDomanda(payload: DomandaCreateInput): Promise<DomandaOut> {
  return apiPost<DomandaOut>("/admin/domande", payload);
}

/** PATCH /admin/domande/{code} — qualunque sottoinsieme, mai `code`. */
export async function updateDomanda(code: string, payload: DomandaPatchInput): Promise<DomandaOut> {
  return apiPatch<DomandaOut>(`/admin/domande/${code}`, payload);
}

/** GET /admin/domande/opzioni?domanda_code=X */
export async function getOpzioni(domandaCode: string): Promise<OpzioneOut[]> {
  return apiGet<OpzioneOut[]>(`/admin/domande/opzioni?domanda_code=${encodeURIComponent(domandaCode)}`);
}

/** POST /admin/domande/opzioni */
export async function createOpzione(payload: OpzioneCreateInput): Promise<OpzioneOut> {
  return apiPost<OpzioneOut>("/admin/domande/opzioni", payload);
}

/** PATCH /admin/domande/opzioni/{id} — puo' rifiutare con 400 (D-28, `detail`). */
export async function updateOpzione(id: number, payload: OpzionePatchInput): Promise<OpzioneOut> {
  return apiPatch<OpzioneOut>(`/admin/domande/opzioni/${id}`, payload);
}

/** GET /admin/domande/effetti?domanda_code=X */
export async function getEffetti(domandaCode: string): Promise<EffettoOut[]> {
  const raw = await apiGet<RawEffettoOut[]>(`/admin/domande/effetti?domanda_code=${encodeURIComponent(domandaCode)}`);
  return raw.map(normalizeEffetto);
}

/** POST /admin/domande/effetti */
export async function createEffetto(payload: EffettoCreateInput): Promise<EffettoOut> {
  const raw = await apiPost<RawEffettoOut>("/admin/domande/effetti", payload);
  return normalizeEffetto(raw);
}

/** PATCH /admin/domande/effetti/{id} — solo `valore`, `tipo_code`, `attivo`. */
export async function updateEffetto(id: number, payload: EffettoPatchInput): Promise<EffettoOut> {
  const raw = await apiPatch<RawEffettoOut>(`/admin/domande/effetti/${id}`, payload);
  return normalizeEffetto(raw);
}
