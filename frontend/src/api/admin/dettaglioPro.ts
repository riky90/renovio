/**
 * CRUD voci di dettaglio Pro (Sottocategoria/Voce) — base del preventivo di
 * dettaglio Pro, oltre all'upload Excel. Nessun campo impresa: `Voce` non ne
 * ha per costruzione (D-10).
 */

import { apiGet, apiPost, apiPatch, apiDelete } from "@/api/admin/client";

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
}

export interface VoceInput {
  sottocategoria_id: number;
  codice?: string | null;
  descrizione: string;
  um: string;
  prezzo_unitario_cliente: number;
  ordine: number;
}

const SOTTO = "/admin/dettaglio-pro/sottocategorie";
const VOCI = "/admin/dettaglio-pro/voci";

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
