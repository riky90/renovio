import { apiPost } from "@/api/client";
import type { TipoRistrutturazione } from "@/components/EstimateForm";

export type PreferenzaContatto = "email" | "telefono";
export type FasciaOraria = "mattina" | "pomeriggio" | "sera";

/**
 * Payload verso POST /api/v1/lead. GUARDIA DOMINIO (D-22): contiene SOLO i
 * campi a range gia' visibili sullo schermo risultato (citta/mq/tipo/totali
 * min-max) — mai i campi riservati lato server relativi al margine impresa.
 */
export interface LeadCreateInput {
  nome: string;
  email: string;
  telefono: string;
  messaggio?: string;
  preferenza_contatto: PreferenzaContatto;
  fascia_oraria?: FasciaOraria;
  citta: string;
  mq: number;
  tipo: TipoRistrutturazione;
  totale_min: number;
  totale_max: number;
}

/**
 * POST /api/v1/lead — invia la richiesta di contatto (login richiesto lato
 * server, D-01). Nessun ricalcolo: lo snapshot allegato e' quello gia'
 * mostrato sullo schermo risultato.
 */
export async function postLead(payload: LeadCreateInput): Promise<{ id: number }> {
  return apiPost<{ id: number }>("/lead", payload);
}
