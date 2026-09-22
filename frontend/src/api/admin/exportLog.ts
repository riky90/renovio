/**
 * Client tipizzato per GET /admin/export-log (UI-SPEC §D): traccia dei
 * download di tutte e quattro le risorse esportabili del pannello,
 * consumata dalla sezione "Download registrati" in coda a
 * LeadDashboardPage.tsx.
 */

import { apiGet } from "@/api/admin/client";

export interface ExportLogRow {
  id: number;
  user_id: number;
  user_label: string;
  risorsa: string;
  righe: number;
  include_margine: boolean;
  created_at: string;
}

export function getExportLog(): Promise<ExportLogRow[]> {
  return apiGet<ExportLogRow[]>("/admin/export-log");
}
