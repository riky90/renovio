/**
 * Client HTTP admin — estende api/client.ts con PATCH/DELETE (apiGet/apiPost
 * riesportati da qui per comodità d'uso nelle pagine /admin). Stessa guardia
 * VITE_API_BASE, stesso ApiError, stesse credentials:"include".
 */

export { apiGet, apiPost, ApiError, type ApiError as ApiErrorType } from "@/api/client";
import { ApiError } from "@/api/client";

const API_BASE = import.meta.env.VITE_API_BASE as string | undefined;

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  if (!API_BASE) {
    throw new Error("VITE_API_BASE non configurato (vedi frontend/.env.example)");
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new ApiError(response.status, `PATCH ${path} fallita con status ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export async function apiDelete(path: string): Promise<void> {
  if (!API_BASE) {
    throw new Error("VITE_API_BASE non configurato (vedi frontend/.env.example)");
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method: "DELETE",
    credentials: "include",
  });

  if (!response.ok) {
    throw new ApiError(response.status, `DELETE ${path} fallita con status ${response.status}`);
  }
}
