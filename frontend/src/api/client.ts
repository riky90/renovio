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

export async function apiDelete<T>(path: string): Promise<T> {
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

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

/**
 * POST multipart. `apiPost` serializza in JSON e impone Content-Type, quindi
 * non puo' inviare un file: qui il Content-Type si OMETTE di proposito, cosi'
 * il browser genera da solo il boundary del multipart.
 *
 * Il `detail` del backend viene propagato nel messaggio: su questo endpoint
 * distinguere 400 (immagine rifiutata) da 503 (storage non configurato) e'
 * esattamente cio' che l'utente deve leggere.
 */
export async function apiPostFile<T>(path: string, file: File): Promise<T> {
  if (!API_BASE) {
    throw new Error("VITE_API_BASE non configurato (vedi frontend/.env.example)");
  }

  const body = new FormData();
  body.append("file", file);

  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    credentials: "include",
    body,
  });

  if (!response.ok) {
    let detail = `POST ${path} fallita con status ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload?.detail) detail = payload.detail;
    } catch {
      // Risposta senza corpo JSON: resta il messaggio generico.
    }
    throw new ApiError(response.status, detail);
  }

  return (await response.json()) as T;
}
