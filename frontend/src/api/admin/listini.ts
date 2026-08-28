/**
 * CRUD listini/prezzi (ADM-01, D-09/D-10/D-13) sopra `routers/admin/
 * listini.py` (04-02). Le classi *AdminOut* del backend espongono
 * `base_eur_mq`/`coefficiente_impresa` — campi visibili SOLO dentro
 * `/admin` (D-10) — questo file NON deve mai essere importato fuori da
 * `pages/admin/*`.
 *
 * Decimal-as-string wire format: FastAPI serializza i campi `Decimal` come
 * stringa JSON — normalizziamo con `toNumber()` una sola volta qui, come
 * `api/stima.ts`.
 */

import { apiGet, apiPost, apiPatch, apiDelete } from "@/api/admin/client";

function toNumber(value: unknown): number {
  return typeof value === "number" ? value : Number(value);
}

export interface ListinoOut {
  id: number;
  nome: string;
  citta_riferimento: string;
  is_default: boolean;
  attivo: boolean;
}

export interface ListinoCreateInput {
  nome: string;
  citta_riferimento: string;
  is_default?: boolean;
}

export interface ListinoPatchInput {
  nome?: string;
  is_default?: boolean;
  attivo?: boolean;
}

export interface ListinoCategoriaOut {
  id: number;
  listino_id: number;
  categoria_code: string;
  base_eur_mq: number;
  coefficiente_impresa: number;
}

interface RawListinoCategoriaOut {
  id: number;
  listino_id: number;
  categoria_code: string;
  base_eur_mq: unknown;
  coefficiente_impresa: unknown;
}

export interface ListinoCategoriaCreateInput {
  categoria_code: string;
  base_eur_mq: number;
  coefficiente_impresa: number;
}

export interface ListinoCategoriaPatchInput {
  base_eur_mq?: number;
  coefficiente_impresa?: number;
}

export interface VoceOut {
  id: number;
  sottocategoria_id: number;
  codice: string | null;
  descrizione: string;
  um: string;
  prezzo_cliente: number;
}

interface RawVoceOut {
  id: number;
  sottocategoria_id: number;
  codice: string | null;
  descrizione: string;
  um: string;
  prezzo_cliente: unknown;
}

export interface VocePatchInput {
  prezzo_cliente: number;
  um: string;
}

function normalizeCategoria(raw: RawListinoCategoriaOut): ListinoCategoriaOut {
  return {
    id: raw.id,
    listino_id: raw.listino_id,
    categoria_code: raw.categoria_code,
    base_eur_mq: toNumber(raw.base_eur_mq),
    coefficiente_impresa: toNumber(raw.coefficiente_impresa),
  };
}

function normalizeVoce(raw: RawVoceOut): VoceOut {
  return {
    id: raw.id,
    sottocategoria_id: raw.sottocategoria_id,
    codice: raw.codice,
    descrizione: raw.descrizione,
    um: raw.um,
    prezzo_cliente: toNumber(raw.prezzo_cliente),
  };
}

/** GET /admin/listini */
export async function getListini(): Promise<ListinoOut[]> {
  return apiGet<ListinoOut[]>("/admin/listini");
}

/** POST /admin/listini — crea Listino + mappatura ComuneListino (onboarding città, D-13). */
export async function createListino(payload: ListinoCreateInput): Promise<ListinoOut> {
  return apiPost<ListinoOut>("/admin/listini", payload);
}

/** PATCH /admin/listini/{id} */
export async function updateListino(id: number, payload: ListinoPatchInput): Promise<ListinoOut> {
  return apiPatch<ListinoOut>(`/admin/listini/${id}`, payload);
}

/** GET /admin/listini/{listinoId}/categorie */
export async function getListinoCategorie(listinoId: number): Promise<ListinoCategoriaOut[]> {
  const raw = await apiGet<RawListinoCategoriaOut[]>(`/admin/listini/${listinoId}/categorie`);
  return raw.map(normalizeCategoria);
}

/** POST /admin/listini/{listinoId}/categorie — upsert per categoria_code (D-24). */
export async function createListinoCategoria(
  listinoId: number,
  payload: ListinoCategoriaCreateInput,
): Promise<ListinoCategoriaOut> {
  const raw = await apiPost<RawListinoCategoriaOut>(`/admin/listini/${listinoId}/categorie`, payload);
  return normalizeCategoria(raw);
}

/** PATCH /admin/listini/categorie/{id} */
export async function updateListinoCategoria(
  id: number,
  payload: ListinoCategoriaPatchInput,
): Promise<ListinoCategoriaOut> {
  const raw = await apiPatch<RawListinoCategoriaOut>(`/admin/listini/categorie/${id}`, payload);
  return normalizeCategoria(raw);
}

/** DELETE /admin/listini/categorie/{id} */
export async function deleteListinoCategoria(id: number): Promise<void> {
  return apiDelete(`/admin/listini/categorie/${id}`);
}

/** GET /admin/listini/categorie/{listinoCategoriaId}/voci */
export async function getVoci(listinoCategoriaId: number): Promise<VoceOut[]> {
  const raw = await apiGet<RawVoceOut[]>(`/admin/listini/categorie/${listinoCategoriaId}/voci`);
  return raw.map(normalizeVoce);
}

/** PATCH /admin/listini/voci/{id} — SOLO prezzo_cliente/um (Pitfall 2). */
export async function updateVoce(id: number, payload: VocePatchInput): Promise<VoceOut> {
  const raw = await apiPatch<RawVoceOut>(`/admin/listini/voci/${id}`, payload);
  return normalizeVoce(raw);
}

/** DELETE /admin/listini/voci/{id} */
export async function deleteVoce(id: number): Promise<void> {
  return apiDelete(`/admin/listini/voci/${id}`);
}
