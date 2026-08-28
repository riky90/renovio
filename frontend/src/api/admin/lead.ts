/**
 * API dashboard lead admin (04-04, ADM-04/D-17): list con filtri
 * citta/stato, dettaglio, PATCH stato/nota. Normalizza i Decimal totali
 * (wire string -> number) come stima.ts::normalizeResponse (D-22: nessun
 * campo relativo al margine impresa qui, coerente con LeadOut backend
 * che non ha nessuna colonna del genere).
 */

import { apiGet, apiPatch } from "@/api/admin/client";

export interface LeadOut {
  id: number;
  nome: string;
  email: string;
  telefono: string | null;
  preferenza_contatto: string;
  fascia_oraria: string | null;
  messaggio: string | null;
  citta: string;
  mq: number;
  tipo: string;
  totale_min: number;
  totale_max: number;
  referente_id: number | null;
  email_inviata: boolean;
  stato: string;
  nota: string | null;
  created_at: string;
}

interface RawLeadOut extends Omit<LeadOut, "totale_min" | "totale_max"> {
  totale_min: unknown;
  totale_max: unknown;
}

function toNumber(value: unknown): number {
  return typeof value === "number" ? value : Number(value);
}

function normalizeLead(raw: RawLeadOut): LeadOut {
  return {
    ...raw,
    totale_min: toNumber(raw.totale_min),
    totale_max: toNumber(raw.totale_max),
  };
}

export interface AdminLeadFilters {
  citta?: string;
  stato?: string;
}

/** GET /api/v1/admin/lead?citta=&stato= — lista lead filtrabile per città/stato. */
export async function getAdminLeads(filters: AdminLeadFilters = {}): Promise<LeadOut[]> {
  const params = new URLSearchParams();
  if (filters.citta) params.set("citta", filters.citta);
  if (filters.stato) params.set("stato", filters.stato);
  const qs = params.toString();
  const raw = await apiGet<RawLeadOut[]>(`/admin/lead${qs ? `?${qs}` : ""}`);
  return raw.map(normalizeLead);
}

/** GET /api/v1/admin/lead/{id} — dettaglio lead (dati contatto + snapshot stima a range). */
export async function getAdminLead(id: number): Promise<LeadOut> {
  const raw = await apiGet<RawLeadOut>(`/admin/lead/${id}`);
  return normalizeLead(raw);
}

export interface UpdateAdminLeadInput {
  stato: string;
  nota: string | null;
}

/** PATCH /api/v1/admin/lead/{id} — aggiorna stato/nota (D-17). */
export async function updateAdminLead(id: number, payload: UpdateAdminLeadInput): Promise<LeadOut> {
  const raw = await apiPatch<RawLeadOut>(`/admin/lead/${id}`, payload);
  return normalizeLead(raw);
}
