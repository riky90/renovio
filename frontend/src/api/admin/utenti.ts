/**
 * API gestione utenti/ruoli admin. Nessun dato sensibile: lo schema server
 * (UserAdminOut) non espone mai `password_hash`. Solo l'admin può leggere la
 * lista e cambiare i ruoli (guard server-side `require_admin`).
 */

import { apiGet, apiPatch } from "@/api/admin/client";

export type Ruolo = "user" | "consulente" | "admin";

export interface UtenteOut {
  id: number;
  email: string;
  nome: string;
  role: Ruolo;
  created_at: string;
}

/** GET /api/v1/admin/utenti — lista utenti con ruolo. */
export async function listUtenti(): Promise<UtenteOut[]> {
  return apiGet<UtenteOut[]>("/admin/utenti");
}

/** PATCH /api/v1/admin/utenti/{id} — assegna un ruolo all'utente. */
export async function updateRuolo(id: number, role: Ruolo): Promise<UtenteOut> {
  return apiPatch<UtenteOut>(`/admin/utenti/${id}`, { role });
}
