/**
 * API CRUD referenti admin (04-04, ADM-04/D-15/D-16). Nessun campo impresa
 * qui: Referente (models/catalogo.py) non ha coefficiente/prezzo impresa.
 */

import { apiGet, apiPost, apiPatch, apiDelete } from "@/api/admin/client";

export interface ReferenteOut {
  id: number;
  listino_id: number;
  nome: string;
  email: string;
  telefono: string | null;
  attivo: boolean;
  priorita: number;
}

export interface ReferenteCreateInput {
  listino_id: number;
  nome: string;
  email: string;
  telefono?: string | null;
  attivo: boolean;
  priorita: number;
}

export interface ReferenteUpdateInput {
  listino_id?: number;
  nome?: string;
  email?: string;
  telefono?: string | null;
  attivo?: boolean;
  priorita?: number;
}

/** GET /api/v1/admin/referenti — lista referenti. */
export async function listReferenti(): Promise<ReferenteOut[]> {
  return apiGet<ReferenteOut[]>("/admin/referenti");
}

/** POST /api/v1/admin/referenti — crea referente. */
export async function createReferente(payload: ReferenteCreateInput): Promise<ReferenteOut> {
  return apiPost<ReferenteOut>("/admin/referenti", payload);
}

/** PATCH /api/v1/admin/referenti/{id} — aggiorna referente (parziale). */
export async function updateReferente(id: number, payload: ReferenteUpdateInput): Promise<ReferenteOut> {
  return apiPatch<ReferenteOut>(`/admin/referenti/${id}`, payload);
}

/** DELETE /api/v1/admin/referenti/{id} — elimina referente. */
export async function deleteReferente(id: number): Promise<void> {
  return apiDelete(`/admin/referenti/${id}`);
}

export interface ListinoOut {
  id: number;
  nome: string;
  citta_riferimento: string;
  is_default: boolean;
  attivo: boolean;
}

/**
 * GET /api/v1/admin/listini — solo per popolare il select città/listino nel
 * form referente (04-08 possiede il file api/admin/listini.ts dedicato;
 * qui usiamo solo la lettura minima necessaria a questo form, stessa rotta).
 */
export async function listListiniForSelect(): Promise<ListinoOut[]> {
  return apiGet<ListinoOut[]>("/admin/listini");
}
