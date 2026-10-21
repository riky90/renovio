/**
 * Computo parametrico (Fase 11): import dell'Excel di grandezze, regole e
 * preset, e validazione della curatela a DB. L'export passa da
 * `scaricaExcel("/admin/computo/export.xlsx")`.
 *
 * L'import e' tutto o niente: con `applica=false` e' un'anteprima che elenca
 * gli errori senza scrivere; con `applica=true` sostituisce il computo solo se
 * non ci sono errori.
 */

import { ApiError, apiGet } from "@/api/admin/client";
import { extractErrorDetail } from "@/api/admin/uploadListino";

const API_BASE = import.meta.env.VITE_API_BASE as string | undefined;

export interface EsitoImportComputo {
  applicato: boolean;
  errori: string[];
  conteggi: Record<string, number>;
}

export async function importaComputo(file: File, applica: boolean): Promise<EsitoImportComputo> {
  if (!API_BASE) {
    throw new Error("VITE_API_BASE non configurato (vedi frontend/.env.example)");
  }
  const formData = new FormData();
  formData.append("file", file);
  const path = `/admin/computo/import?applica=${applica ? "true" : "false"}`;
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });
  if (!response.ok) {
    throw new ApiError(response.status, await extractErrorDetail(response, path));
  }
  return (await response.json()) as EsitoImportComputo;
}

export function getValidazioneComputo(): Promise<{ errori: string[] }> {
  return apiGet<{ errori: string[] }>("/admin/computo/validazione");
}
