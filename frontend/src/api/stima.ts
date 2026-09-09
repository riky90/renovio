import { apiGet, apiPost, ApiError } from "@/api/client";
import type { TipoRistrutturazione } from "@/components/EstimateForm";

export type { TipoRistrutturazione };

/** Abitazione principale vs altri immobili: e' cio' che separa il 50% dal 36%. */
export type Destinazione = "prima_casa" | "altro";

export interface StimaRequest {
  citta: string;
  mq: number;
  tipo: TipoRistrutturazione;
  /** Opzionale sul filo: il backend applica "prima_casa" quando manca. */
  destinazione?: Destinazione;
}

export interface StimaInputEcho {
  citta: string;
  mq: number;
  tipo: TipoRistrutturazione;
  destinazione: Destinazione;
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

export interface BonusDettaglioOut {
  code: string;
  nome: string;
  descrizione: string | null;
  base_min: number;
  base_max: number;
  aliquota_pct: number;
  /** null = nessun tetto di spesa per questo bonus. */
  tetto_spesa_eur: number | null;
  tetto_modalita: string | null;
  tetto_raggiunto: boolean;
  rate_annuali: number;
  detrazione_min: number;
  detrazione_max: number;
  rata_annua_min: number;
  rata_annua_max: number;
}

export interface BonusOut {
  bonus: BonusDettaglioOut[];
  detrazione_min: number;
  detrazione_max: number;
  rata_annua_min: number;
  rata_annua_max: number;
  /** Viaggia nel payload, non nella UI: non e' rimovibile lato client. */
  disclaimer: string;
}

export interface StimaResponse {
  input: StimaInputEcho;
  fallback: boolean;
  disclaimer: string | null;
  valuta: "EUR";
  categorie: CategoriaOut[];
  extra: ExtraOut[];
  totale: TotaleOut;
  /**
   * null quando non c'e' nulla da mostrare (nessun bonus attivo, nessuna
   * aliquota valida) e sugli snapshot v1 salvati prima della feature.
   */
  bonus: BonusOut | null;
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
interface RawBonusDettaglioOut {
  code: string;
  nome: string;
  descrizione: string | null;
  tetto_modalita: string | null;
  tetto_raggiunto: boolean;
  rate_annuali: number;
  [key: string]: unknown;
}
interface RawBonusOut {
  bonus: RawBonusDettaglioOut[];
  disclaimer: string;
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
  /** Assente sugli snapshot v1: non e' un errore, e' l'assenza della feature. */
  bonus?: RawBonusOut | null;
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

const NUMERIC_BONUS_FIELDS = [
  "detrazione_min",
  "detrazione_max",
  "rata_annua_min",
  "rata_annua_max",
] as const;

/**
 * `tetto_spesa_eur` NON e' in questa lista: e' nullable, e passarlo da
 * toNumber() trasformerebbe "nessun tetto" in 0, cioe' in "tetto a zero
 * euro" — l'esatto contrario. Si converte a parte, preservando il null.
 */
const NUMERIC_BONUS_DETTAGLIO_FIELDS = [
  "base_min",
  "base_max",
  "aliquota_pct",
  "detrazione_min",
  "detrazione_max",
  "rata_annua_min",
  "rata_annua_max",
] as const;

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

function normalizeBonus(raw: RawBonusOut | null | undefined): BonusOut | null {
  if (raw == null) return null;
  const out = {
    bonus: raw.bonus.map((d) => {
      const dettaglio = {
        code: d.code,
        nome: d.nome,
        descrizione: d.descrizione,
        tetto_spesa_eur: d.tetto_spesa_eur == null ? null : toNumber(d.tetto_spesa_eur),
        tetto_modalita: d.tetto_modalita,
        tetto_raggiunto: d.tetto_raggiunto,
        rate_annuali: d.rate_annuali,
      } as BonusDettaglioOut;
      for (const field of NUMERIC_BONUS_DETTAGLIO_FIELDS) {
        dettaglio[field] = toNumber(d[field]);
      }
      return dettaglio;
    }),
    disclaimer: raw.disclaimer,
  } as BonusOut;
  for (const field of NUMERIC_BONUS_FIELDS) {
    out[field] = toNumber(raw[field]);
  }
  return out;
}

/**
 * ATTENZIONE, PRIMA DI AGGIUNGERE UN CAMPO ALLA RISPOSTA: questa funzione
 * RICOSTRUISCE l'oggetto campo per campo, non fa spread. Tutto cio' che non e'
 * elencato qui viene scartato in silenzio — e `postSalvaStima()` rimanda al
 * backend PROPRIO QUESTO oggetto, non la risposta grezza. Un campo dimenticato
 * qui non manca solo alla UI: sparisce dallo snapshot congelato, per sempre,
 * senza un errore da nessuna parte. E' successo con `bonus`.
 */
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
    bonus: normalizeBonus(raw.bonus),
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

/** Storico item — proiezione dalle sole colonne scalari di StimaSalvata. */
/**
 * Tier con cui la stima e' stata creata, congelato al salvataggio lato
 * backend. E' QUESTO — mai `user.pro` — a decidere quale vista mostrare:
 * il piano dell'utente cambia nel tempo, il tier della stima no.
 */
export type StimaTier = "free" | "pro";

export interface StimaSalvataListItem {
  id: number;
  citta: string;
  mq: number;
  tipo: TipoRistrutturazione;
  totale_min: number;
  totale_max: number;
  tier: StimaTier;
  created_at: string;
}

interface RawStimaSalvataListItem {
  id: number;
  citta: string;
  mq: number;
  tipo: TipoRistrutturazione;
  totale_min: unknown;
  totale_max: unknown;
  tier: StimaTier;
  created_at: string;
}

/**
 * Preferenze Pro raccolte nel form al momento della stima. NON entrano nello
 * snapshot: il backend le scrive in `livelli_pro_json`/`risposte_pro_json`.
 */
export interface PreferenzePro {
  livelli?: Record<string, string>;
  risposte?: { bagni: number; porte: number; condizionatori: number };
}

/** Dettaglio snapshot immutabile — StimaResponse + id/created_at. */
export interface StimaSalvataOut extends StimaResponse {
  id: number;
  tier: StimaTier;
  created_at: string;
}

interface RawStimaSalvataOut extends RawStimaResponse {
  id: number;
  tier: StimaTier;
  created_at: string;
}

/**
 * POST /api/v1/me/stime — congela lo snapshot gia' calcolato (nessun
 * ricalcolo, D-09/Pitfall 5): il payload e' esattamente la StimaResponse
 * gia' mostrata all'utente.
 */
export async function postSalvaStima(
  payload: StimaResponse,
  preferenzePro?: PreferenzePro
): Promise<{ id: number }> {
  // `preferenze_pro` viaggia ACCANTO allo snapshot, non dentro: il backend lo
  // esclude da `risultato_json` e lo scrive nelle sue colonne. Sono parametri
  // di ricalcolo, e lo snapshot deve restare la prova di cio' che l'utente ha
  // visto quel giorno.
  const body = preferenzePro ? { ...payload, preferenze_pro: preferenzePro } : payload;
  return apiPost<{ id: number }>("/me/stime", body);
}

/** Opzioni per il selettore di livello del form Pro (GET /me/opzioni-pro). */
export interface CategoriaLivelloOut {
  code: string;
  nome: string;
}

export interface LivelloOut {
  code: string;
  nome: string;
  ordine: number;
  descrizione: string | null;
  is_default: boolean;
}

export interface OpzioniProOut {
  categorie: CategoriaLivelloOut[];
  livelli: LivelloOut[];
}

/**
 * GET /api/v1/me/opzioni-pro — livelli disponibili e categorie che li
 * ammettono, per costruire i selettori del form Pro prima che una stima
 * esista. Nessun importo qui, quindi nessuna normalizzazione numerica.
 */
export async function getOpzioniPro(): Promise<OpzioniProOut> {
  return apiGet<OpzioniProOut>("/me/opzioni-pro");
}

/** GET /api/v1/me/stime — storico dell'utente loggato, piu' recenti prima. */
export async function getStoricoStime(): Promise<StimaSalvataListItem[]> {
  const raw = await apiGet<RawStimaSalvataListItem[]>("/me/stime");
  return raw.map((item) => ({
    id: item.id,
    citta: item.citta,
    mq: item.mq,
    tipo: item.tipo,
    totale_min: toNumber(item.totale_min),
    totale_max: toNumber(item.totale_max),
    tier: item.tier,
    created_at: item.created_at,
  }));
}

/** GET /api/v1/me/stime/{id} — dettaglio snapshot immutabile (anti-IDOR 404 lato backend). */
export async function getStimaDettaglio(id: number): Promise<StimaSalvataOut> {
  const raw = await apiGet<RawStimaSalvataOut>(`/me/stime/${id}`);
  const normalized = normalizeResponse(raw);
  return { ...normalized, id: raw.id, tier: raw.tier, created_at: raw.created_at };
}

/**
 * GET /api/v1/me/stime/{id}/pdf — scarica il PDF brandizzato leggendo il
 * blob della risposta e attivando il download nativo del browser, usando
 * il filename da Content-Disposition quando presente.
 */
export async function scaricaPdf(id: number): Promise<void> {
  const API_BASE = import.meta.env.VITE_API_BASE as string | undefined;
  if (!API_BASE) {
    throw new Error("VITE_API_BASE non configurato (vedi frontend/.env.example)");
  }

  const response = await fetch(`${API_BASE}/me/stime/${id}/pdf`, {
    credentials: "include",
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `GET /me/stime/${id}/pdf fallita con status ${response.status}`
    );
  }

  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition");
  let filename = "stima-ristrutturazione.pdf";
  if (disposition) {
    const match = disposition.match(/filename="?([^";]+)"?/);
    if (match?.[1]) {
      filename = match[1];
    }
  }

  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
