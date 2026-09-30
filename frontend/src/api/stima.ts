import { apiGet, apiPatch, apiPost, ApiError } from "@/api/client";
import type { Risposte } from "@/api/domande";
import type { DomandaProOut } from "@/api/dettaglio-pro";
import type { TipoRistrutturazione } from "@/components/EstimateFormFields";

export type { TipoRistrutturazione };

/** Abitazione principale vs altri immobili: e' cio' che separa il 50% dal 36%. */
export type Destinazione = "prima_casa" | "altro";

export interface StimaRequest {
  citta: string;
  mq: number;
  tipo: TipoRistrutturazione;
  /** Opzionale sul filo: il backend applica "prima_casa" quando manca. */
  destinazione?: Destinazione;
  /**
   * Le risposte del wizard. `undefined` NON e' `{}`: il primo spegne il layer
   * parametrico e riproduce la stima di prima che il catalogo esistesse, il
   * secondo lo accende con tutte le domande sui loro default. Un client vecchio
   * che posta {citta, mq, tipo} continua a ricevere il numero di sempre.
   */
  risposte?: Risposte;
}

export interface StimaInputEcho {
  citta: string;
  mq: number;
  tipo: TipoRistrutturazione;
  destinazione: Destinazione;
  /**
   * Le risposte tornano nell'eco perche' finiscono nello snapshot congelato:
   * una stima salvata deve restare spiegabile anche dopo che l'admin ha
   * cambiato la taratura. Assente sugli snapshot salvati prima della feature.
   */
  risposte?: Risposte | null;
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
  /** G10: voce che esiste solo per la base arredo (es. Bonus Mobili), decisa dal server. Assente negli snapshot vecchi = false. */
  su_arredo: boolean;
}

export interface BonusOut {
  bonus: BonusDettaglioOut[];
  detrazione_min: number;
  detrazione_max: number;
  rata_annua_min: number;
  rata_annua_max: number;
  /** Viaggia nel payload, non nella UI: non e' rimovibile lato client. */
  disclaimer: string;
  /** Detrazione sui soli lavori (senza la base arredo). null negli snapshot precedenti a G5. */
  detrazione_lavori_min: number | null;
  detrazione_lavori_max: number | null;
  /** Totale IVA inclusa - detrazione sui lavori, calcolato dal server. */
  netto_min: number | null;
  netto_max: number | null;
  /** Rata annua sui soli lavori (G10). null negli snapshot precedenti a G10. */
  rata_annua_lavori_min: number | null;
  rata_annua_lavori_max: number | null;
}

export interface ArredoAmbienteOut {
  code: string;
  nome: string;
  eur_min: number;
  eur_max: number;
}

export interface ArredoOut {
  livello_code: string;
  livello_nome: string;
  ambienti: ArredoAmbienteOut[];
  totale_min: number;
  totale_max: number;
  /** Viaggia nel payload, non nella UI: non e' rimovibile lato client. */
  disclaimer: string;
}

export interface ConfrontoFinitureOut {
  livello_code: string;
  livello_nome: string;
  /** Totali lavori IVA inclusa, arredo escluso: calcolati dal server (D-09). */
  totale_min: number;
  totale_max: number;
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
  /**
   * null quando non ci sono ambienti da arredare scelti, o nessun forfait
   * curato per quel livello, e sugli snapshot salvati prima della feature.
   * E' FRATELLO di `totale`, mai dentro: l'arredo non e' una lavorazione.
   */
  arredo: ArredoOut | null;
  /** Stessa ristrutturazione con finiture un livello sotto; null se non c'e'. */
  confronto_finiture: ConfrontoFinitureOut | null;
  /** true quando le finiture scelte sono gia' al livello piu' basso. */
  finiture_al_minimo: boolean;
  /**
   * Solo client: NON arriva da POST /stima. Lo aggiunge la pagina prima del
   * salvataggio (piano 10-05).
   */
  budget_eur?: number | null;
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
export interface RawBonusOut {
  bonus: RawBonusDettaglioOut[];
  disclaimer: string;
  detrazione_lavori_min?: string | number | null;
  detrazione_lavori_max?: string | number | null;
  netto_min?: string | number | null;
  netto_max?: string | number | null;
  rata_annua_lavori_min?: string | number | null;
  rata_annua_lavori_max?: string | number | null;
  [key: string]: unknown;
}
interface RawArredoAmbienteOut {
  code: string;
  nome: string;
  [key: string]: unknown;
}
interface RawArredoOut {
  livello_code: string;
  livello_nome: string;
  ambienti: RawArredoAmbienteOut[];
  disclaimer: string;
  [key: string]: unknown;
}
export interface RawConfrontoFinitureOut {
  livello_code: string;
  livello_nome: string;
  totale_min: string | number;
  totale_max: string | number;
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
  /** Idem: assente su ogni snapshot salvato prima della fase 07. */
  arredo?: RawArredoOut | null;
  /** Assente sugli snapshot precedenti la fase 10. */
  confronto_finiture?: RawConfrontoFinitureOut | null;
  finiture_al_minimo?: boolean;
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

const NUMERIC_BONUS_OPZIONALI = [
  "detrazione_lavori_min",
  "detrazione_lavori_max",
  "netto_min",
  "netto_max",
  "rata_annua_lavori_min",
  "rata_annua_lavori_max",
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

export function normalizeBonus(raw: RawBonusOut | null | undefined): BonusOut | null {
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
        su_arredo: d.su_arredo === true,
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
  // Campi opzionali (G5): assenti negli snapshot vecchi -> null, mai 0.
  for (const field of NUMERIC_BONUS_OPZIONALI) {
    const valore = raw[field];
    out[field] = valore == null ? null : toNumber(valore);
  }
  return out;
}

const NUMERIC_ARREDO_FIELDS = ["totale_min", "totale_max"] as const;

function normalizeArredo(raw: RawArredoOut | null | undefined): ArredoOut | null {
  if (raw == null) return null;
  const out = {
    livello_code: raw.livello_code,
    livello_nome: raw.livello_nome,
    ambienti: raw.ambienti.map((a) => ({
      code: a.code,
      nome: a.nome,
      eur_min: toNumber(a.eur_min),
      eur_max: toNumber(a.eur_max),
    })),
    disclaimer: raw.disclaimer,
  } as ArredoOut;
  for (const field of NUMERIC_ARREDO_FIELDS) {
    out[field] = toNumber(raw[field]);
  }
  return out;
}

export function normalizeConfronto(
  raw: RawConfrontoFinitureOut | null | undefined,
): ConfrontoFinitureOut | null {
  if (raw == null) return null;
  return {
    livello_code: raw.livello_code,
    livello_nome: raw.livello_nome,
    totale_min: toNumber(raw.totale_min),
    totale_max: toNumber(raw.totale_max),
  };
}

/**
 * ATTENZIONE, PRIMA DI AGGIUNGERE UN CAMPO ALLA RISPOSTA: questa funzione
 * RICOSTRUISCE l'oggetto campo per campo, non fa spread. Tutto cio' che non e'
 * elencato qui viene scartato in silenzio — e `postSalvaStima()` rimanda al
 * backend PROPRIO QUESTO oggetto, non la risposta grezza. Un campo dimenticato
 * qui non manca solo alla UI: sparisce dallo snapshot congelato, per sempre,
 * senza un errore da nessuna parte. E' successo con `bonus`. Vale anche per
 * `confronto_finiture` e `finiture_al_minimo`.
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
    arredo: normalizeArredo(raw.arredo),
    confronto_finiture: normalizeConfronto(raw.confronto_finiture),
    finiture_al_minimo: raw.finiture_al_minimo ?? false,
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
  /** Scelte del configuratore Pro raccolte nel wizard (09-11, es. pavimento). */
  scelte?: Record<string, string>;
}

/** Dettaglio snapshot immutabile — StimaResponse + id/created_at. */
export interface StimaSalvataOut extends StimaResponse {
  id: number;
  tier: StimaTier;
  created_at: string;
  /** Budget dichiarato (EUR, IVA inclusa), dalla colonna: null = nessun budget. */
  budget_eur: number | null;
}

interface RawStimaSalvataOut extends RawStimaResponse {
  id: number;
  tier: StimaTier;
  created_at: string;
  budget_eur: number | null;
}

/**
 * POST /api/v1/me/stime — congela lo snapshot gia' calcolato (nessun
 * ricalcolo, D-09/Pitfall 5): il payload e' esattamente la StimaResponse
 * gia' mostrata all'utente.
 */
export async function postSalvaStima(
  payload: StimaResponse & { budget_eur?: number | null },
  preferenzePro?: PreferenzePro
): Promise<{ id: number }> {
  // `preferenze_pro` viaggia ACCANTO allo snapshot, non dentro: il backend lo
  // esclude da `risultato_json` e lo scrive nelle sue colonne. Sono parametri
  // di ricalcolo, e lo snapshot deve restare la prova di cio' che l'utente ha
  // visto quel giorno.
  // Idem `budget_eur` dentro il payload: e' un parametro, il backend lo esclude
  // dallo snapshot e lo scrive nella colonna `stima.budget_eur`.
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
  /** Domande a scelta del configuratore (09-11, es. tipo_pavimento) — il
   * wizard Pro le disegna allo step 4 accanto ai livelli. */
  domande: DomandaProOut[];
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
  return {
    ...normalized,
    id: raw.id,
    tier: raw.tier,
    created_at: raw.created_at,
    budget_eur: raw.budget_eur ?? null,
  };
}

/**
 * PATCH /api/v1/me/stime/{id}/budget — aggiorna solo il budget della stima
 * salvata (null = lo toglie). Non tocca snapshot ne' prezzo.
 */
export async function patchBudgetStima(
  id: number,
  budget: number | null
): Promise<{ budget_eur: number | null }> {
  return apiPatch<{ budget_eur: number | null }>(`/me/stime/${id}/budget`, {
    budget_eur: budget,
  });
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
