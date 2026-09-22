/**
 * Download blob generico per gli export Excel del pannello admin (D-09/D-15,
 * UI-SPEC §A). Una sola funzione, non una per risorsa: le pagine passano il
 * proprio path (`/admin/listini/{id}/export.xlsx`, e in piani successivi
 * `/admin/domande/export.xlsx` ecc.), cosi' questo file non si tocca piu'
 * mano a mano che la Fase 08 aggiunge bottoni.
 *
 * Fetch diretto (non `apiGet`, che parserebbe JSON) — stesso scheletro
 * `credentials: "include"` di `uploadListino.ts`, adattato a `.blob()`.
 * `ApiError`/`extractErrorDetail` riusati da `uploadListino.ts`, non
 * duplicati.
 */

import { ApiError } from "@/api/admin/client";
import { extractErrorDetail } from "@/api/admin/uploadListino";

const API_BASE = import.meta.env.VITE_API_BASE as string | undefined;

export async function scaricaExcel(path: string): Promise<void> {
  if (!API_BASE) {
    throw new Error("VITE_API_BASE non configurato (vedi frontend/.env.example)");
  }

  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
  });

  if (!response.ok) {
    throw new ApiError(response.status, await extractErrorDetail(response, path));
  }

  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const filename = /filename="([^"]+)"/.exec(disposition)?.[1] ?? "export.xlsx";

  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
