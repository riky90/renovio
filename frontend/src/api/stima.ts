import { apiGet, apiPost, ApiError } from "@/api/client";
import type { TipoRistrutturazione } from "@/components/EstimateForm";

export type { TipoRistrutturazione };

export interface StimaRequest {
  citta: string;
  mq: number;
  tipo: TipoRistrutturazione;
}

export interface StimaInputEcho {
  citta: string;
  mq: number;
  tipo: TipoRistrutturazione;
}

export interface CategoriaOut {
  code: string;
  nome: string;
  imponibile_min: number;
  imponibile_max: number;
  iva_pct: number;
  iva_min: number;
  iva_max: number;
  totale_min: number;
  totale_max: number;
}

export interface ExtraOut {
  code: string;
  nome: string;
  importo: number;
  iva_pct: number;
}

export interface TotaleOut {
  imponibile_min: number;
  imponibile_max: number;
  iva_min: number;
  iva_max: number;
  totale_min: number;
  totale_max: number;
}

export interface StimaResponse {
  input: StimaInputEcho;
  fallback: boolean;
  disclaimer: string | null;
  valuta: "EUR";
  categorie: CategoriaOut[];
  extra: ExtraOut[];
  totale: TotaleOut;
}

/**
 * Raw wire shape: FastAPI/Pydantic v2 serializes Decimal fields as JSON
 * strings (e.g. "20400", "0.100") to avoid float precision loss on the
 * wire. The typed StimaResponse above is the app-facing contract (plain
 * numbers) — normalizeResponse() converts every monetary/pct field once,
 * at the API boundary, so the rest of the app never deals with strings.
 */
interface RawCategoriaOut {
  code: string;
  nome: string;
  [key: string]: unknown;
}
interface RawExtraOut {
  code: string;
  nome: string;
  [key: string]: unknown;
}
interface RawStimaResponse {
  input: StimaInputEcho;
  fallback: boolean;
  disclaimer: string | null;
  valuta: "EUR";
  categorie: RawCategoriaOut[];
  extra: RawExtraOut[];
  totale: Record<string, unknown>;
}

const NUMERIC_CATEGORIA_FIELDS = [
  "imponibile_min",
  "imponibile_max",
  "iva_pct",
  "iva_min",
  "iva_max",
  "totale_min",
  "totale_max",
] as const;

const NUMERIC_EXTRA_FIELDS = ["importo", "iva_pct"] as const;

const NUMERIC_TOTALE_FIELDS = [
  "imponibile_min",
  "imponibile_max",
  "iva_min",
  "iva_max",
  "totale_min",
  "totale_max",
] as const;

function toNumber(value: unknown): number {
  return typeof value === "number" ? value : Number(value);
}

function normalizeResponse(raw: RawStimaResponse): StimaResponse {
  return {
    input: raw.input,
    fallback: raw.fallback,
    disclaimer: raw.disclaimer,
    valuta: raw.valuta,
    categorie: raw.categorie.map((c) => {
      const out = { code: c.code, nome: c.nome } as CategoriaOut;
      for (const field of NUMERIC_CATEGORIA_FIELDS) {
        out[field] = toNumber(c[field]);
      }
      return out;
    }),
    extra: raw.extra.map((e) => {
      const out = { code: e.code, nome: e.nome } as ExtraOut;
      for (const field of NUMERIC_EXTRA_FIELDS) {
        out[field] = toNumber(e[field]);
      }
      return out;
    }),
    totale: NUMERIC_TOTALE_FIELDS.reduce((acc, field) => {
      acc[field] = toNumber(raw.totale[field]);
      return acc;
    }, {} as TotaleOut),
  };
}

/**
 * POST /api/v1/stima — through the shared apiGet-style fetch wrapper's base
 * URL/error handling, but as a POST since apiGet only covers GET requests.
 */
export async function postStima(request: StimaRequest): Promise<StimaResponse> {
  const API_BASE = import.meta.env.VITE_API_BASE as string | undefined;
  if (!API_BASE) {
    throw new Error("VITE_API_BASE non configurato (vedi frontend/.env.example)");
  }

  const response = await fetch(`${API_BASE}/stima`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new ApiError(response.status, `POST /stima fallita con status ${response.status}`);
  }

  const raw = (await response.json()) as RawStimaResponse;
  return normalizeResponse(raw);
}

/** Storico item — proiezione dalle sole colonne scalari di StimaSalvata. */
export interface StimaSalvataListItem {
  id: number;
  citta: string;
  mq: number;
  tipo: TipoRistrutturazione;
  totale_min: number;
  totale_max: number;
  created_at: string;
}

interface RawStimaSalvataListItem {
  id: number;
  citta: string;
  mq: number;
  tipo: TipoRistrutturazione;
  totale_min: unknown;
  totale_max: unknown;
  created_at: string;
}

/** Dettaglio snapshot immutabile — StimaResponse + id/created_at. */
export interface StimaSalvataOut extends StimaResponse {
  id: number;
  created_at: string;
}

interface RawStimaSalvataOut extends RawStimaResponse {
  id: number;
  created_at: string;
}

/**
 * POST /api/v1/me/stime — congela lo snapshot gia' calcolato (nessun
 * ricalcolo, D-09/Pitfall 5): il payload e' esattamente la StimaResponse
 * gia' mostrata all'utente.
 */
export async function postSalvaStima(payload: StimaResponse): Promise<{ id: number }> {
  return apiPost<{ id: number }>("/me/stime", payload);
}

/** GET /api/v1/me/stime — storico dell'utente loggato, piu' recenti prima. */
export async function getStoricoStime(): Promise<StimaSalvataListItem[]> {
  const raw = await apiGet<RawStimaSalvataListItem[]>("/me/stime");
  return raw.map((item) => ({
    id: item.id,
    citta: item.citta,
    mq: item.mq,
    tipo: item.tipo,
    totale_min: toNumber(item.totale_min),
    totale_max: toNumber(item.totale_max),
    created_at: item.created_at,
  }));
}

/** GET /api/v1/me/stime/{id} — dettaglio snapshot immutabile (anti-IDOR 404 lato backend). */
export async function getStimaDettaglio(id: number): Promise<StimaSalvataOut> {
  const raw = await apiGet<RawStimaSalvataOut>(`/me/stime/${id}`);
  const normalized = normalizeResponse(raw);
  return { ...normalized, id: raw.id, created_at: raw.created_at };
}

/**
 * GET /api/v1/me/stime/{id}/pdf — scarica il PDF brandizzato leggendo il
 * blob della risposta e attivando il download nativo del browser, usando
 * il filename da Content-Disposition quando presente.
 */
export async function scaricaPdf(id: number): Promise<void> {
  const API_BASE = import.meta.env.VITE_API_BASE as string | undefined;
  if (!API_BASE) {
    throw new Error("VITE_API_BASE non configurato (vedi frontend/.env.example)");
  }

  const response = await fetch(`${API_BASE}/me/stime/${id}/pdf`, {
    credentials: "include",
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `GET /me/stime/${id}/pdf fallita con status ${response.status}`
    );
  }

  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition");
  let filename = "stima-ristrutturazione.pdf";
  if (disposition) {
    const match = disposition.match(/filename="?([^";]+)"?/);
    if (match?.[1]) {
      filename = match[1];
    }
  }

  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
