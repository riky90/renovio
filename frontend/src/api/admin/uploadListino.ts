/**
 * Upload Excel listino a due passi (ADM-01, D-18/D-19/D-20) sopra
 * `routers/admin/upload_listino.py` (04-05). `previewUpload` NON scrive
 * nulla (nemmeno per il ramo "nuova città" — confrontato contro un set
 * vuoto lato server); `confirmUpload` re-invia il payload diff completo
 * ricevuto dal preview (round-trip stateless, RESEARCH.md Pattern 4).
 *
 * Multipart via fetch diretto (nessun apiPost — FormData, non JSON), stesso
 * pattern `credentials: "include"` di `api/stima.ts`/`api/admin/client.ts`.
 */

import { apiPost, ApiError } from "@/api/admin/client";

const API_BASE = import.meta.env.VITE_API_BASE as string | undefined;

export type UploadTarget =
  | { kind: "esistente"; listino_id: number }
  | { kind: "nuova_citta"; citta: string; is_default?: boolean };

export interface VoceRiga {
  categoria_code: string;
  sottocategoria_codice: string | null;
  sottocategoria_nome: string;
  sottocategoria_famiglia: string;
  sottocategoria_ordine: number;
  codice: string | null;
  descrizione: string;
  um: string;
  prezzo_unitario_cliente: number;
  ordine: number;
}

export interface DiffRow {
  riga: VoceRiga;
  valore_precedente: number | null;
  /** D-11: true se il record a database e' stato modificato DOPO il
   * timestamp di generazione del file caricato (`DiffPreview.generato_il`). */
  riga_modificata_dopo_export: boolean;
}

export interface ScartoRow {
  riga: number;
  motivo: string;
}

export interface DiffPreview {
  nuove: DiffRow[];
  modificate: DiffRow[];
  scarti: ScartoRow[];
  target_descr: string;
  generato_il: string | null;
}

interface RawDiffRow {
  riga: VoceRiga;
  valore_precedente: unknown;
  riga_modificata_dopo_export: boolean;
}

interface RawDiffPreview {
  nuove: RawDiffRow[];
  modificate: RawDiffRow[];
  scarti: ScartoRow[];
  target_descr: string;
  generato_il: string | null;
}

function toNumberOrNull(value: unknown): number | null {
  return value === null || value === undefined ? null : Number(value);
}

function normalizeDiffRow(raw: RawDiffRow): DiffRow {
  return {
    riga: raw.riga,
    valore_precedente: toNumberOrNull(raw.valore_precedente),
    riga_modificata_dopo_export: raw.riga_modificata_dopo_export,
  };
}

/**
 * Estrae il `detail` del corpo JSON di errore, con fallback generico —
 * esportata perche' riusata anche da `exportExcel.ts` (blob download, GET),
 * non solo dalle POST multipart di questo modulo: il messaggio di fallback
 * non nomina piu' un verbo HTTP specifico per restare corretto in entrambi
 * i casi.
 */
export async function extractErrorDetail(response: Response, path: string): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body?.detail === "string") return body.detail;
  } catch {
    // corpo non-JSON o vuoto: fallback al messaggio generico
  }
  return `Richiesta a ${path} fallita con status ${response.status}`;
}

/**
 * POST /admin/upload-listino/preview — parse + diff, NIENTE scritture
 * (pre-check client su .xlsx/10MB e' solo UX, l'autorita' resta il server).
 */
export async function previewUpload(file: File, target: UploadTarget): Promise<DiffPreview> {
  if (!API_BASE) {
    throw new Error("VITE_API_BASE non configurato (vedi frontend/.env.example)");
  }

  const formData = new FormData();
  formData.append("file", file);
  formData.append("target", JSON.stringify(target));

  const path = "/admin/upload-listino/preview";
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });

  if (!response.ok) {
    throw new ApiError(response.status, await extractErrorDetail(response, path));
  }

  const raw = (await response.json()) as RawDiffPreview;
  return {
    nuove: raw.nuove.map(normalizeDiffRow),
    modificate: raw.modificate.map(normalizeDiffRow),
    scarti: raw.scarti,
    target_descr: raw.target_descr,
    generato_il: raw.generato_il,
  };
}

export interface ImportResult {
  righe_importate: number;
  listino_id: number;
}

/**
 * POST /admin/upload-listino/confirm — upsert idempotente (mai
 * distruttivo, D-24); ramo "nuova città" crea Listino+ComuneListino qui,
 * mai in preview.
 */
export async function confirmUpload(
  target: UploadTarget,
  nuove: VoceRiga[],
  modificate: VoceRiga[],
  comuniExtra: string[] = [],
): Promise<ImportResult> {
  return apiPost<ImportResult>("/admin/upload-listino/confirm", {
    target,
    nuove,
    modificate,
    comuni_extra: comuniExtra,
  });
}
