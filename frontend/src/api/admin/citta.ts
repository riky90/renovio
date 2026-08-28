import { apiGet, apiPost, apiPatch, apiDelete } from "@/api/admin/client";

/**
 * Client CRUD città→listino (ComuneListino) + tipi di ristrutturazione
 * (TipoRistrutturazione), sopra `routers/admin/citta.py` (04-03, ADM-03).
 *
 * `comune_slug` NON è mai inviato nel body: è ricalcolato server-side dallo
 * stesso `slugify` usato da `city_resolver.resolve_listino`, così una
 * mappatura creata/modificata dall'admin resta coerente con la risoluzione
 * del motore (T-04-12). `range_pct` (Decimal lato backend) arriva come
 * stringa JSON — normalizzato con `toNumber` allo stesso pattern di
 * `api/stima.ts`.
 */

export interface ComuneListino {
  id: number;
  comune_nome: string;
  comune_slug: string;
  codice_istat: string | null;
  listino_id: number;
}

export interface ComuneListinoBody {
  comune_nome: string;
  codice_istat?: string | null;
  listino_id: number;
}

export interface TipoRistrutturazione {
  code: string;
  nome: string;
  ordine: number;
  range_pct: number;
}

interface RawTipoRistrutturazione {
  code: string;
  nome: string;
  ordine: number;
  range_pct: unknown;
}

/** Listino minimo per popolare il select "listino mappato" nel dialog città. */
export interface ListinoOption {
  id: number;
  nome: string;
  citta_riferimento: string;
}

function toNumber(value: unknown): number {
  return typeof value === "number" ? value : Number(value);
}

function normalizeTipo(raw: RawTipoRistrutturazione): TipoRistrutturazione {
  return {
    code: raw.code,
    nome: raw.nome,
    ordine: raw.ordine,
    range_pct: toNumber(raw.range_pct),
  };
}

export async function listComuni(): Promise<ComuneListino[]> {
  return apiGet<ComuneListino[]>("/admin/citta");
}

export async function createComune(body: ComuneListinoBody): Promise<ComuneListino> {
  return apiPost<ComuneListino>("/admin/citta", body);
}

export async function updateComune(
  id: number,
  body: Partial<ComuneListinoBody>,
): Promise<ComuneListino> {
  return apiPatch<ComuneListino>(`/admin/citta/${id}`, body);
}

export async function deleteComune(id: number): Promise<void> {
  return apiDelete(`/admin/citta/${id}`);
}

export async function listTipi(): Promise<TipoRistrutturazione[]> {
  const raw = await apiGet<RawTipoRistrutturazione[]>("/admin/citta/tipi");
  return raw.map(normalizeTipo);
}

export async function updateTipo(
  code: string,
  body: { nome?: string; ordine?: number; range_pct?: number },
): Promise<TipoRistrutturazione> {
  const raw = await apiPatch<RawTipoRistrutturazione>(`/admin/citta/tipi/${code}`, body);
  return normalizeTipo(raw);
}

/**
 * Elenco listini minimo per il select "listino mappato" nel dialog
 * mappatura città (backend 04-01/04-03 `routers/admin/listini.py`, GET ""):
 * definito qui — non in un file `api/admin/listini.ts` condiviso — per
 * restare nel perimetro `files_modified` di questo piano (04-08 possiede
 * il client completo listini/voci in parallelo).
 */
export async function listListiniOptions(): Promise<ListinoOption[]> {
  const raw = await apiGet<
    Array<{ id: number; nome: string; citta_riferimento: string }>
  >("/admin/listini");
  return raw.map((l) => ({ id: l.id, nome: l.nome, citta_riferimento: l.citta_riferimento }));
}
