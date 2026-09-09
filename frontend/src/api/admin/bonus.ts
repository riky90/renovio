/**
 * CRUD bonus fiscali sopra `routers/admin/bonus.py`: bonus, aliquote per
 * periodo, mapping categoria->bonus e mapping extra->bonus.
 *
 * E' il pannello che rende vera la promessa del modello: quando l'aliquota
 * cambia per legge non si fa un deploy, si aggiunge una riga con la nuova
 * finestra di validita'. Come gli altri file di questa cartella, non
 * importarlo fuori da `pages/admin/*` (D-10).
 *
 * Stessa conversione string->number al confine (D-22) di `stima.ts`: Pydantic
 * serializza i Decimal come stringhe.
 */

import { apiGet, apiPatch, apiPost, apiDelete } from "@/api/admin/client";

function toNumber(value: unknown): number {
  return typeof value === "number" ? value : Number(value);
}

function toNumberOrNull(value: unknown): number | null {
  return value === null || value === undefined ? null : toNumber(value);
}

// --- Bonus -----------------------------------------------------------------

export interface BonusOut {
  code: string;
  nome: string;
  descrizione: string | null;
  ordine: number;
  attivo: boolean;
}

export async function getBonus(): Promise<BonusOut[]> {
  return apiGet<BonusOut[]>("/admin/bonus");
}

export async function createBonus(payload: BonusOut): Promise<BonusOut> {
  return apiPost<BonusOut>("/admin/bonus", payload);
}

export async function updateBonus(
  code: string,
  payload: Partial<Omit<BonusOut, "code">>
): Promise<BonusOut> {
  return apiPatch<BonusOut>(`/admin/bonus/${code}`, payload);
}

export async function deleteBonus(code: string): Promise<void> {
  return apiDelete(`/admin/bonus/${code}`);
}

// --- Aliquote per periodo ---------------------------------------------------

export type Destinazione = "prima_casa" | "altro";

export interface AliquotaOut {
  id: number;
  bonus_code: string;
  destinazione: Destinazione;
  /** Frazione, non percentuale: 0.5 = 50%. Stessa convenzione di `iva_pct`. */
  aliquota_pct: number;
  /** null = nessun tetto di spesa. */
  tetto_spesa_eur: number | null;
  tetto_modalita: string | null;
  rate_annuali: number;
  valido_dal: string;
  /** null = finestra ancora aperta. */
  valido_al: string | null;
  note: string | null;
}

interface RawAliquotaOut extends Omit<AliquotaOut, "aliquota_pct" | "tetto_spesa_eur"> {
  aliquota_pct: unknown;
  tetto_spesa_eur: unknown;
}

function normalizeAliquota(raw: RawAliquotaOut): AliquotaOut {
  return {
    ...raw,
    aliquota_pct: toNumber(raw.aliquota_pct),
    tetto_spesa_eur: toNumberOrNull(raw.tetto_spesa_eur),
  };
}

export async function getAliquote(bonusCode?: string): Promise<AliquotaOut[]> {
  const qs = bonusCode ? `?bonus_code=${encodeURIComponent(bonusCode)}` : "";
  const raw = await apiGet<RawAliquotaOut[]>(`/admin/bonus/aliquote${qs}`);
  return raw.map(normalizeAliquota);
}

export type AliquotaInput = Omit<AliquotaOut, "id">;

export async function createAliquota(payload: AliquotaInput): Promise<AliquotaOut> {
  return normalizeAliquota(await apiPost<RawAliquotaOut>("/admin/bonus/aliquote", payload));
}

export async function updateAliquota(
  id: number,
  payload: Partial<Omit<AliquotaInput, "bonus_code" | "destinazione">>
): Promise<AliquotaOut> {
  return normalizeAliquota(await apiPatch<RawAliquotaOut>(`/admin/bonus/aliquote/${id}`, payload));
}

export async function deleteAliquota(id: number): Promise<void> {
  return apiDelete(`/admin/bonus/aliquote/${id}`);
}

// --- Mapping categoria -> bonus ---------------------------------------------

export interface BonusCategoriaOut {
  id: number;
  bonus_code: string;
  categoria_code: string;
  quota_ammissibile_pct: number;
}

interface RawBonusCategoriaOut extends Omit<BonusCategoriaOut, "quota_ammissibile_pct"> {
  quota_ammissibile_pct: unknown;
}

function normalizeQuota<T extends { quota_ammissibile_pct: unknown }>(
  raw: T
): Omit<T, "quota_ammissibile_pct"> & { quota_ammissibile_pct: number } {
  return { ...raw, quota_ammissibile_pct: toNumber(raw.quota_ammissibile_pct) };
}

export async function getBonusCategorie(): Promise<BonusCategoriaOut[]> {
  const raw = await apiGet<RawBonusCategoriaOut[]>("/admin/bonus/categorie");
  return raw.map(normalizeQuota);
}

export async function createBonusCategoria(payload: {
  bonus_code: string;
  categoria_code: string;
  quota_ammissibile_pct: number;
}): Promise<BonusCategoriaOut> {
  return normalizeQuota(await apiPost<RawBonusCategoriaOut>("/admin/bonus/categorie", payload));
}

export async function updateBonusCategoria(
  id: number,
  quota_ammissibile_pct: number
): Promise<BonusCategoriaOut> {
  return normalizeQuota(
    await apiPatch<RawBonusCategoriaOut>(`/admin/bonus/categorie/${id}`, { quota_ammissibile_pct })
  );
}

export async function deleteBonusCategoria(id: number): Promise<void> {
  return apiDelete(`/admin/bonus/categorie/${id}`);
}

// --- Mapping extra -> bonus -------------------------------------------------
//
// Gemello del mapping categorie. Esiste perche' CSE/CSP e pratiche
// amministrative sono spesa detraibile ma non sono categorie: un extra che
// resta fuori da qui e' una sottostima silenziosa della detrazione.

export interface BonusExtraOut {
  id: number;
  bonus_code: string;
  extra_code: string;
  quota_ammissibile_pct: number;
}

interface RawBonusExtraOut extends Omit<BonusExtraOut, "quota_ammissibile_pct"> {
  quota_ammissibile_pct: unknown;
}

export async function getBonusExtra(): Promise<BonusExtraOut[]> {
  const raw = await apiGet<RawBonusExtraOut[]>("/admin/bonus/extra");
  return raw.map(normalizeQuota);
}

export async function createBonusExtra(payload: {
  bonus_code: string;
  extra_code: string;
  quota_ammissibile_pct: number;
}): Promise<BonusExtraOut> {
  return normalizeQuota(await apiPost<RawBonusExtraOut>("/admin/bonus/extra", payload));
}

export async function updateBonusExtra(
  id: number,
  quota_ammissibile_pct: number
): Promise<BonusExtraOut> {
  return normalizeQuota(
    await apiPatch<RawBonusExtraOut>(`/admin/bonus/extra/${id}`, { quota_ammissibile_pct })
  );
}

export async function deleteBonusExtra(id: number): Promise<void> {
  return apiDelete(`/admin/bonus/extra/${id}`);
}
