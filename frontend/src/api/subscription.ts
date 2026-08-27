import { apiPost } from "@/api/client";

export interface AttivaProResponse {
  pro: boolean;
  stato: string;
}

/**
 * POST /me/pro/attiva — attivazione stub "production-shaped" (D-07): nessun
 * addebito reale, la tessera abbonamento passa allo stato attivo.
 */
export async function postAttivaPro(): Promise<AttivaProResponse> {
  return apiPost<AttivaProResponse>("/me/pro/attiva", undefined);
}
