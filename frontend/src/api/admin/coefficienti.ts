/**
 * CRUD coefficienti (ADM-02, D-12) sopra `routers/admin/coefficienti.py`
 * (04-10): moltiplicatori tipo×categoria, IVA per categoria, extra
 * (CSE/CSP, pratiche), coefficienti quantità-per-m² Pro, più `base` in
 * sola lettura (la scrittura di `base_eur_mq` resta sul CRUD listini,
 * `api/admin/listini.ts`). Come `listini.ts`, non importare fuori da
 * `pages/admin/*` (D-10).
 */

import { apiGet, apiPatch, apiPost, apiDelete } from "@/api/admin/client";

function toNumber(value: unknown): number {
  return typeof value === "number" ? value : Number(value);
}

function toNumberOrNull(value: unknown): number | null {
  return value === null || value === undefined ? null : toNumber(value);
}

// --- Moltiplicatori tipo × categoria ---------------------------------------

export interface MoltiplicatoreOut {
  id: number;
  tipo_code: string;
  categoria_code: string;
  valore: number;
}

interface RawMoltiplicatoreOut {
  id: number;
  tipo_code: string;
  categoria_code: string;
  valore: unknown;
}

function normalizeMoltiplicatore(raw: RawMoltiplicatoreOut): MoltiplicatoreOut {
  return { ...raw, valore: toNumber(raw.valore) };
}

export async function getMoltiplicatori(): Promise<MoltiplicatoreOut[]> {
  const raw = await apiGet<RawMoltiplicatoreOut[]>("/admin/coefficienti/moltiplicatori");
  return raw.map(normalizeMoltiplicatore);
}

export async function updateMoltiplicatore(id: number, valore: number): Promise<MoltiplicatoreOut> {
  const raw = await apiPatch<RawMoltiplicatoreOut>(`/admin/coefficienti/moltiplicatori/${id}`, { valore });
  return normalizeMoltiplicatore(raw);
}

// --- IVA per categoria -------------------------------------------------------

export interface CategoriaIvaOut {
  code: string;
  nome: string;
  iva_pct: number;
}

interface RawCategoriaIvaOut {
  code: string;
  nome: string;
  iva_pct: unknown;
}

function normalizeIva(raw: RawCategoriaIvaOut): CategoriaIvaOut {
  return { ...raw, iva_pct: toNumber(raw.iva_pct) };
}

export async function getIva(): Promise<CategoriaIvaOut[]> {
  const raw = await apiGet<RawCategoriaIvaOut[]>("/admin/coefficienti/iva");
  return raw.map(normalizeIva);
}

export async function updateIva(categoriaCode: string, ivaPct: number): Promise<CategoriaIvaOut> {
  const raw = await apiPatch<RawCategoriaIvaOut>(`/admin/coefficienti/iva/${categoriaCode}`, {
    iva_pct: ivaPct,
  });
  return normalizeIva(raw);
}

// --- Extra (CSE/CSP, pratiche) ----------------------------------------------

export interface ExtraOut {
  code: string;
  nome: string;
  importo: number;
  iva_pct: number;
  tipo_calcolo: string;
  attivo: boolean;
}

interface RawExtraOut {
  code: string;
  nome: string;
  importo: unknown;
  iva_pct: unknown;
  tipo_calcolo: string;
  attivo: boolean;
}

export interface ExtraCreateInput {
  code: string;
  nome: string;
  importo: number;
  iva_pct: number;
  tipo_calcolo?: string;
  attivo?: boolean;
}

export interface ExtraPatchInput {
  nome?: string;
  importo?: number;
  iva_pct?: number;
  attivo?: boolean;
}

function normalizeExtra(raw: RawExtraOut): ExtraOut {
  return { ...raw, importo: toNumber(raw.importo), iva_pct: toNumber(raw.iva_pct) };
}

export async function listExtra(): Promise<ExtraOut[]> {
  const raw = await apiGet<RawExtraOut[]>("/admin/coefficienti/extra");
  return raw.map(normalizeExtra);
}

export async function createExtra(payload: ExtraCreateInput): Promise<ExtraOut> {
  const raw = await apiPost<RawExtraOut>("/admin/coefficienti/extra", payload);
  return normalizeExtra(raw);
}

export async function updateExtra(code: string, payload: ExtraPatchInput): Promise<ExtraOut> {
  const raw = await apiPatch<RawExtraOut>(`/admin/coefficienti/extra/${code}`, payload);
  return normalizeExtra(raw);
}

export async function deleteExtra(code: string): Promise<void> {
  return apiDelete(`/admin/coefficienti/extra/${code}`);
}

// --- Coefficienti quantità-per-m² Pro ---------------------------------------

export interface CoeffProOut {
  id: number;
  voce_id: number;
  tipo_code: string;
  valore: number | null;
  domanda_mirata_key: string | null;
  default_conteggio: number | null;
}

interface RawCoeffProOut {
  id: number;
  voce_id: number;
  tipo_code: string;
  valore: unknown;
  domanda_mirata_key: string | null;
  default_conteggio: number | null;
}

function normalizeCoeffPro(raw: RawCoeffProOut): CoeffProOut {
  return { ...raw, valore: toNumberOrNull(raw.valore) };
}

export async function getCoeffPro(): Promise<CoeffProOut[]> {
  const raw = await apiGet<RawCoeffProOut[]>("/admin/coefficienti/coeff-pro");
  return raw.map(normalizeCoeffPro);
}

export async function updateCoeffPro(id: number, valore: number): Promise<CoeffProOut> {
  const raw = await apiPatch<RawCoeffProOut>(`/admin/coefficienti/coeff-pro/${id}`, { valore });
  return normalizeCoeffPro(raw);
}

// --- Base €/m² (sola lettura — la scrittura resta su api/admin/listini.ts) --

export interface BaseEurMqOut {
  id: number;
  listino_id: number;
  categoria_code: string;
  base_eur_mq: number;
}

interface RawBaseEurMqOut {
  id: number;
  listino_id: number;
  categoria_code: string;
  base_eur_mq: unknown;
}

export async function getBaseEurMq(): Promise<BaseEurMqOut[]> {
  const raw = await apiGet<RawBaseEurMqOut[]>("/admin/coefficienti/base");
  return raw.map((row) => ({ ...row, base_eur_mq: toNumber(row.base_eur_mq) }));
}
