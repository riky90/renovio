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

/**
 * Rispecchia `VoceRigaIn` (`backend/app/schemas/admin_upload.py`) campo per
 * campo, `id` e `campi_presenti` compresi.
 *
 * Quei due non sono decorativi e non vanno mai persi nel giro
 * preview -> confirm:
 *
 * - `id` sceglie il percorso di scrittura lato server. Con un id la riga si
 *   risolve per id e si applicano SOLO i campi presenti; senza, si cade
 *   sull'upsert per chiave naturale.
 * - `campi_presenti` elenca le colonne che il file portava davvero. I campi
 *   assenti hanno sull'istanza un placeholder (`"-"`, `0.01`, `0`) che non
 *   va mai scritto a database: e' questa lista a dire al server quali
 *   ignorare (D-09/CUR-02, "campo assente dal file = campo non toccato").
 *
 * Finora il tipo li taceva e funzionava per caso: `normalizeDiffRow` passa
 * `raw.riga` cosi' com'e' e `ExcelUploadDialog` rispedisce lo stesso
 * oggetto, quindi i campi sopravvivevano pur non essendo dichiarati. Il
 * giorno in cui un pezzo di codice ricostruisse una `VoceRiga` campo per
 * campo — per esempio per far correggere una riga a mano prima di
 * confermare — li perderebbe in silenzio, e la riga finirebbe sull'upsert
 * per chiave naturale con i placeholder addosso. Dichiararli fa fallire
 * quel codice a compile-time invece che a runtime.
 */
export interface VoceRiga {
  id: number | null;
  categoria_code: string;
  sottocategoria_codice: string | null;
  sottocategoria_nome: string;
  sottocategoria_famiglia: string;
  sottocategoria_ordine: number;
  codice: string | null;
  descrizione: string;
  um: string;
  /**
   * Decimal-as-string al confine API: pydantic serializza `Decimal` come
   * stringa JSON, non come number (`"12.50"`, non `12.5`). Dichiararlo
   * `number` non era solo un tipo sbagliato, era un difetto visibile:
   * `String.prototype.toLocaleString` ignora gli argomenti, quindi la
   * colonna "nuovo" della tabella di anteprima mostrava `12.50` grezzo
   * accanto a una colonna "precedente" formattata `12,50 €`.
   *
   * Il campo resta stringa QUI perche' l'oggetto `riga` viene rispedito
   * verbatim a `/confirm`: il numero normalizzato sta accanto
   * (`DiffRow.prezzoNuovo`), mai al suo posto.
   */
  prezzo_unitario_cliente: string;
  ordine: number;
  livello: string | null;
  campi_presenti: string[] | null;
}

export interface DiffRow {
  riga: VoceRiga;
  /** `riga.prezzo_unitario_cliente` normalizzato a numero, per la
   * formattazione in euro. Accanto al campo grezzo, non al suo posto:
   * `riga` torna a `/confirm` cosi' com'e' arrivata. */
  prezzoNuovo: number | null;
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
    prezzoNuovo: toNumberOrNull(raw.riga.prezzo_unitario_cliente),
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
