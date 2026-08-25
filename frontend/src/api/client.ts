/**
 * Typed fetch wrapper pointing at the backend API base URL.
 *
 * VITE_API_BASE must be set (see .env.example); no fallback to a hardcoded
 * origin so misconfiguration fails loudly instead of silently hitting the
 * wrong host.
 */

const API_BASE = import.meta.env.VITE_API_BASE as string | undefined;

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  if (!API_BASE) {
    throw new Error("VITE_API_BASE non configurato (vedi frontend/.env.example)");
  }

  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
  });

  if (!response.ok) {
    throw new ApiError(response.status, `GET ${path} fallita con status ${response.status}`);
  }

  return (await response.json()) as T;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  if (!API_BASE) {
    throw new Error("VITE_API_BASE non configurato (vedi frontend/.env.example)");
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new ApiError(response.status, `POST ${path} fallita con status ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
