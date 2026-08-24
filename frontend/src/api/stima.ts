import { ApiError } from "@/api/client";
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
