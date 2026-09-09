/**
 * CRUD voci di dettaglio Pro (Sottocategoria/Voce) — base del preventivo di
 * dettaglio Pro, oltre all'upload Excel. Nessun campo impresa: `Voce` non ne
 * ha per costruzione (D-10).
 */

import { apiGet, apiPost, apiPatch, apiPut, apiDelete } from "@/api/admin/client";

export type Famiglia = "gerarchica" | "catalogo";

export interface SottocategoriaOut {
  id: number;
  listino_id: number;
  categoria_code: string;
  codice: string | null;
  nome: string;
  famiglia: string;
  ordine: number;
}

export interface SottocategoriaInput {
  listino_id: number;
  categoria_code: string;
  codice?: string | null;
  nome: string;
  famiglia: Famiglia;
  ordine: number;
}

export interface VoceOut {
  id: number;
  sottocategoria_id: number;
  codice: string | null;
  descrizione: string;
  um: string;
  prezzo_unitario_cliente: number;
  ordine: number;
  /**
   * Livello di finitura della voce; null = comune a tutti i livelli, cioè
   * sempre inclusa (posa, materiali di consumo, montaggio).
   */
  livello: string | null;
}

export interface VoceInput {
  sottocategoria_id: number;
  codice?: string | null;
  descrizione: string;
  um: string;
  prezzo_unitario_cliente: number;
  ordine: number;
  livello?: string | null;
}

export interface LivelloFinituraOut {
  code: string;
  nome: string;
  ordine: number;
  descrizione: string | null;
  is_default: boolean;
}

const SOTTO = "/admin/dettaglio-pro/sottocategorie";
const VOCI = "/admin/dettaglio-pro/voci";
const LIVELLI = "/admin/dettaglio-pro/livelli";

/**
 * Livelli assegnabili a una voce. Sola lettura: i tre livelli li possiede il
 * seed, quello che l'admin cura è QUALE VOCE sta in quale livello.
 */
export async function listLivelli(): Promise<LivelloFinituraOut[]> {
  return apiGet<LivelloFinituraOut[]>(LIVELLI);
}

export async function listSottocategorie(listinoId: number): Promise<SottocategoriaOut[]> {
  return apiGet<SottocategoriaOut[]>(`${SOTTO}?listino_id=${listinoId}`);
}

export async function createSottocategoria(payload: SottocategoriaInput): Promise<SottocategoriaOut> {
  return apiPost<SottocategoriaOut>(SOTTO, payload);
}

export async function updateSottocategoria(
  id: number,
  payload: Partial<Omit<SottocategoriaInput, "listino_id">>,
): Promise<SottocategoriaOut> {
  return apiPatch<SottocategoriaOut>(`${SOTTO}/${id}`, payload);
}

export async function deleteSottocategoria(id: number): Promise<void> {
  return apiDelete(`${SOTTO}/${id}`);
}

export async function listVoci(sottocategoriaId: number): Promise<VoceOut[]> {
  return apiGet<VoceOut[]>(`${VOCI}?sottocategoria_id=${sottocategoriaId}`);
}

export async function createVoce(payload: VoceInput): Promise<VoceOut> {
  return apiPost<VoceOut>(VOCI, payload);
}

export async function updateVoce(
  id: number,
  payload: Partial<Omit<VoceInput, "sottocategoria_id">>,
): Promise<VoceOut> {
  return apiPatch<VoceOut>(`${VOCI}/${id}`, payload);
}

export async function deleteVoce(id: number): Promise<void> {
  return apiDelete(`${VOCI}/${id}`);
}

// --- Applicazione per tipo (CoefficienteQuantitaVoce) ---

export interface CoeffVoceOut {
  id: number;
  voce_id: number;
  tipo_code: string;
  coefficiente_qta_per_mq: number | null;
  default_conteggio: number | null;
  domanda_mirata_key: string | null;
}

export interface CoeffVoceInput {
  coefficiente_qta_per_mq?: number | null;
  default_conteggio?: number | null;
  domanda_mirata_key?: string | null;
}

export async function listCoeffVoce(voceId: number): Promise<CoeffVoceOut[]> {
  return apiGet<CoeffVoceOut[]>(`${VOCI}/${voceId}/coefficienti`);
}

/** Include/aggiorna la voce nel tipo indicato (upsert). */
export async function upsertCoeffVoce(
  voceId: number,
  tipoCode: string,
  payload: CoeffVoceInput,
): Promise<CoeffVoceOut> {
  return apiPut<CoeffVoceOut>(`${VOCI}/${voceId}/coefficienti/${tipoCode}`, payload);
}

/** Esclude la voce dal tipo indicato. */
export async function deleteCoeffVoce(voceId: number, tipoCode: string): Promise<void> {
  return apiDelete(`${VOCI}/${voceId}/coefficienti/${tipoCode}`);
}
