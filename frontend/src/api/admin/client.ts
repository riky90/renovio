/**
 * Client HTTP admin — riesporta api/client.ts per comodità d'uso nelle
 * pagine /admin, senza duplicarne il corpo (WR-02): un domani un header
 * aggiuntivo, un retry o un nuovo status code cambiano una volta sola,
 * invece di dover ricordarsi di toccare due copie identiche.
 *
 * `apiDelete` qui accetta un generic `<T>` (prima non lo aveva, e tornava
 * sempre `Promise<void>`): resta compatibile con ogni chiamante esistente,
 * che ignora comunque il valore di ritorno.
 *
 * `apiPut` NON ha un equivalente in api/client.ts (nessun consumer pubblico
 * usa PUT) — resta definito qui, unica copia, invece di essere un quarto
 * "riesporta" fittizio.
 */

export {
  apiGet,
  apiPost,
  apiPatch,
  apiDelete,
  ApiError,
  type ApiError as ApiErrorType,
} from "@/api/client";
import { ApiError, leggiDetail } from "@/api/client";

const API_BASE = import.meta.env.VITE_API_BASE as string | undefined;

export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  if (!API_BASE) {
    throw new Error("VITE_API_BASE non configurato (vedi frontend/.env.example)");
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const detail = await leggiDetail(response);
    throw new ApiError(response.status, detail ?? `PUT ${path} fallita con status ${response.status}`, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
