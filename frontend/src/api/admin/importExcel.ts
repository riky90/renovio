/**
 * Client per l'import Excel generico per risorsa (piano 08-06,
 * `routers/admin/import_excel.py`). Stesso scheletro fetch multipart di
 * `uploadListino.ts` (`credentials: "include"`, `ApiError`/
 * `extractErrorDetail` riusati, non duplicati) — adattato al contratto
 * generico: nessun passo destinazione, per queste risorse la risorsa
 * stessa e' la destinazione.
 *
 * Round-trip stateless (Fase 4/08-03): il client ricostruisce
 * `RigaPiattaIn` da `DiffRigaOut.valori_nuovi` per `/confirm` — vedi
 * `FlatImportDialog.tsx`.
 */

import { ApiError } from "@/api/admin/client";
import { extractErrorDetail } from "@/api/admin/uploadListino";

const API_BASE = import.meta.env.VITE_API_BASE as string | undefined;

export interface RigaPiattaIn {
  foglio: string;
  id: string | null;
  valori: Record<string, unknown>;
  campi_da_cancellare: string[];
}

export interface DiffRigaOut {
  foglio: string;
  id: string | null;
  chiave_descr: string;
  nuova: boolean;
  campi_modificati: string[];
  valori_precedenti: Record<string, unknown>;
  valori_nuovi: Record<string, unknown>;
}

export interface ScartoRow {
  riga: number;
  motivo: string;
}

export interface DiffPiatto {
  risorsa: string;
  nuove: DiffRigaOut[];
  modificate: DiffRigaOut[];
  scarti: ScartoRow[];
  generato_il: string | null;
}

/** POST /admin/import-excel/{risorsa}/preview — parse + diff, NIENTE scritture. */
export async function previewImport(risorsa: string, file: File): Promise<DiffPiatto> {
  if (!API_BASE) {
    throw new Error("VITE_API_BASE non configurato (vedi frontend/.env.example)");
  }

  const formData = new FormData();
  formData.append("file", file);

  const path = `/admin/import-excel/${risorsa}/preview`;
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });

  if (!response.ok) {
    throw new ApiError(response.status, await extractErrorDetail(response, path));
  }

  return (await response.json()) as DiffPiatto;
}

export interface ConfirmResult {
  righe_applicate: number;
}

/**
 * POST /admin/import-excel/{risorsa}/confirm — round-trip stateless: il
 * client re-invia le righe proposte da `/preview` (ricostruite come
 * `RigaPiattaIn`, vedi `FlatImportDialog.tsx`).
 */
export async function confirmImport(
  risorsa: string,
  nuove: RigaPiattaIn[],
  modificate: RigaPiattaIn[],
): Promise<ConfirmResult> {
  if (!API_BASE) {
    throw new Error("VITE_API_BASE non configurato (vedi frontend/.env.example)");
  }

  const path = `/admin/import-excel/${risorsa}/confirm`;
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ risorsa, nuove, modificate }),
  });

  if (!response.ok) {
    throw new ApiError(response.status, await extractErrorDetail(response, path));
  }

  return (await response.json()) as ConfirmResult;
}
