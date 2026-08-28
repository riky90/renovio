import { apiGet, apiPatch } from "@/api/admin/client";

/**
 * Client CRUD testi/disclaimer key/value (D-14, ADM-03), sopra
 * `routers/admin/testi.py` (04-03). Nessuna create/delete: le chiavi sono
 * seedate da `scripts/seed.py`, l'admin ne modifica solo il `valore`.
 */

export interface Testo {
  chiave: string;
  valore: string;
  updated_at: string;
}

export async function listTesti(): Promise<Testo[]> {
  return apiGet<Testo[]>("/admin/testi");
}

export async function updateTesto(chiave: string, body: { valore: string }): Promise<Testo> {
  return apiPatch<Testo>(`/admin/testi/${encodeURIComponent(chiave)}`, body);
}
