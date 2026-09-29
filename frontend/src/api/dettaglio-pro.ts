import { apiGet, apiPost, ApiError } from "@/api/client";
import { isNumerico, type TipoControllo, type ValoreRisposta } from "@/api/domande";
import {
  normalizeBonus,
  normalizeConfronto,
  type BonusOut,
  type ConfrontoFinitureOut,
  type ExtraOut,
  type RawBonusOut,
  type RawConfrontoFinitureOut,
} from "@/api/stima";
import type { RiepilogoIva } from "@/lib/risultato";

export interface VoceOut {
  codice: string | null;
  descrizione: string;
  um: string;
  quantita_stimata: number;
  prezzo_min: number;
  prezzo_max: number;
  /** Livello di finitura della voce; null = comune a tutti i livelli. */
  livello: string | null;
}

export interface SottocategoriaOut {
  codice: string | null;
  nome: string;
  famiglia: "gerarchica" | "catalogo";
  voci: VoceOut[];
  totale_min: number;
  totale_max: number;
}

export interface CategoriaDettagliataOut {
  code: string;
  nome: string;
  sottocategorie: SottocategoriaOut[];
  totale_min: number;
  totale_max: number;
  /**
   * Livello EFFETTIVAMENTE applicato. null dove la categoria non prevede un
   * livello (A-EDILE): è anche il modo in cui il client sa quali selettori
   * mostrare, senza cablare i codici categoria.
   */
  livello_scelto: string | null;
  livello_scelto_nome: string | null;
}

export interface LivelloFinituraOut {
  code: string;
  nome: string;
  ordine: number;
  descrizione: string | null;
  is_default: boolean;
}

/** Livelli scelti per categoria: { "B-FINITURE": "medio", ... }. */
export type LivelliPerCategoria = Record<string, string>;

/** Un'opzione di una domanda del pannello — stessi campi di `OpzioneDomanda`. */
export interface OpzioneProOut {
  code: string;
  etichetta: string;
  descrizione: string | null;
  is_default: boolean;
}

/**
 * Una domanda del pannello "Qualche dettaglio in più", col valore GIA'
 * risolto dal server (D-07): la risposta salvata se valida, altrimenti il
 * default di catalogo. Sottoinsieme di `Domanda` (api/domande.ts) — compatibile
 * con `DomandaField`, che conosce solo i campi che le servono per disegnare.
 */
export interface DomandaProOut {
  code: string;
  testo: string;
  help: string | null;
  tipo_controllo: TipoControllo;
  opzioni: OpzioneProOut[];
  valore: ValoreRisposta | null;
  /** Solo per le domande a scelta: l'etichetta dell'opzione risolta in `valore`. */
  valore_etichetta: string | null;
}

/** Lettura di una categoria (D-13..D-15): valori del server, mai ricalcolati. */
export interface LetturaCategoriaOut {
  code: string;
  incidenza: { min: number; max: number } | null;
  peso: { etichetta: string; fillPct: number };
}

export interface DettaglioProOut {
  categorie: CategoriaDettagliataOut[];
  totale_min: number;
  totale_max: number;
  /** Totale lavori + extra IVA inclusa (base di barra e budget). */
  totale_ivato_min: number | null;
  totale_ivato_max: number | null;
  riepilogo_iva: RiepilogoIva | null;
  lettura_categorie: LetturaCategoriaOut[];
  confronto_finiture: ConfrontoFinitureOut | null;
  finiture_al_minimo: boolean;
  /** Bonus calcolati server-side sui totali Pro (10-14): il client li mappa soltanto. */
  bonus: BonusOut | null;
  budget_eur: number | null;
  /** Eco delle risposte PERSISTITE ({codice: valore}) — generico dal 09-05. */
  risposte: Record<string, number | string>;
  /**
   * True se l'utente ha DAVVERO risposto alle domande del pannello. Distingue
   * "tutti zero" (risposta legittima) dal non aver mai risposto — cosa che
   * dedurlo dalle risposte non può fare.
   */
  risposte_salvate: boolean;
  /** Le domande del pannello, dal catalogo — nessuna etichetta cablata. */
  domande: DomandaProOut[];
  livelli: LivelliPerCategoria;
  livelli_disponibili: LivelloFinituraOut[];
}

/**
 * Raw wire shape: come in api/stima.ts, Pydantic v2 serializza i Decimal
 * (quantita_stimata/prezzo_min/prezzo_max) come stringhe JSON — normalizzati
 * a number UNA volta al confine API via toNumber(), qui duplicato per non
 * introdurre una dipendenza incrociata tra i due moduli client.
 */
interface RawVoceOut {
  codice: string | null;
  descrizione: string;
  um: string;
  quantita_stimata: unknown;
  prezzo_min: unknown;
  prezzo_max: unknown;
  livello: string | null;
}

interface RawSottocategoriaOut {
  codice: string | null;
  nome: string;
  famiglia: "gerarchica" | "catalogo";
  voci: RawVoceOut[];
  totale_min: unknown;
  totale_max: unknown;
}

interface RawCategoriaDettagliataOut {
  code: string;
  nome: string;
  sottocategorie: RawSottocategoriaOut[];
  totale_min: unknown;
  totale_max: unknown;
  livello_scelto: string | null;
  livello_scelto_nome: string | null;
}

interface RawDomandaProOut {
  code: string;
  testo: string;
  help: string | null;
  tipo_controllo: TipoControllo;
  opzioni: OpzioneProOut[];
  /** Pydantic serializza gli interi come numeri, i codici opzione come stringa. */
  valore: number | string | null;
  valore_etichetta: string | null;
}

interface RawRiepilogoIvaOut {
  imponibile_lavori_min: unknown;
  imponibile_lavori_max: unknown;
  righe_iva: { iva_pct: unknown; min: unknown; max: unknown }[];
  extra: { code: string; nome: string; importo: unknown; iva_pct: unknown }[];
  totale_min: unknown;
  totale_max: unknown;
}

interface RawLetturaCategoriaOut {
  code: string;
  eur_mq_min: number | null;
  eur_mq_max: number | null;
  peso_etichetta: string;
  peso_fill_pct: number;
}

interface RawDettaglioProOut {
  categorie: RawCategoriaDettagliataOut[];
  totale_min: unknown;
  totale_max: unknown;
  totale_ivato_min?: unknown;
  totale_ivato_max?: unknown;
  riepilogo_iva?: RawRiepilogoIvaOut | null;
  lettura_categorie?: RawLetturaCategoriaOut[];
  confronto_finiture?: RawConfrontoFinitureOut | null;
  finiture_al_minimo?: boolean;
  bonus?: RawBonusOut | null;
  budget_eur?: number | null;
  risposte: Record<string, number | string>;
  risposte_salvate?: boolean;
  domande?: RawDomandaProOut[];
  /**
   * `livelli` e `livelli_disponibili` NON passano da toNumber(): sono codici e
   * etichette, non importi. Farceli passare li trasformerebbe in NaN.
   */
  livelli: LivelliPerCategoria;
  livelli_disponibili: LivelloFinituraOut[];
}

function toNumber(value: unknown): number {
  return typeof value === "number" ? value : Number(value);
}

/**
 * Converte `valore` solo per le domande numeriche (come `normalizeCatalogo`
 * in api/domande.ts): su una scelta il valore è un codice opzione, e un
 * codice fatto di cifre non deve diventare un numero.
 */
function normalizeDomandaPro(raw: RawDomandaProOut): DomandaProOut {
  return {
    code: raw.code,
    testo: raw.testo,
    help: raw.help,
    tipo_controllo: raw.tipo_controllo,
    opzioni: raw.opzioni,
    valore:
      raw.valore !== null && isNumerico(raw.tipo_controllo)
        ? Number(raw.valore)
        : (raw.valore as ValoreRisposta | null),
    valore_etichetta: raw.valore_etichetta,
  };
}

function toNumberOrNull(value: unknown): number | null {
  return value == null ? null : toNumber(value);
}

function normalizeRiepilogoIva(raw: RawRiepilogoIvaOut | null | undefined): RiepilogoIva | null {
  if (raw == null) return null;
  const extra: ExtraOut[] = raw.extra.map((e) => ({
    code: e.code,
    nome: e.nome,
    importo: toNumber(e.importo),
    iva_pct: toNumber(e.iva_pct),
  }));
  return {
    imponibileLavoriMin: toNumber(raw.imponibile_lavori_min),
    imponibileLavoriMax: toNumber(raw.imponibile_lavori_max),
    righeIva: raw.righe_iva.map((r) => ({
      ivaPct: toNumber(r.iva_pct),
      min: toNumber(r.min),
      max: toNumber(r.max),
    })),
    extra,
    totaleMin: toNumber(raw.totale_min),
    totaleMax: toNumber(raw.totale_max),
  };
}

function normalizeDettaglioPro(raw: RawDettaglioProOut): DettaglioProOut {
  return {
    totale_ivato_min: toNumberOrNull(raw.totale_ivato_min),
    totale_ivato_max: toNumberOrNull(raw.totale_ivato_max),
    riepilogo_iva: normalizeRiepilogoIva(raw.riepilogo_iva),
    lettura_categorie: (raw.lettura_categorie ?? []).map((l) => ({
      code: l.code,
      incidenza:
        l.eur_mq_min != null && l.eur_mq_max != null
          ? { min: l.eur_mq_min, max: l.eur_mq_max }
          : null,
      peso: { etichetta: l.peso_etichetta, fillPct: l.peso_fill_pct },
    })),
    confronto_finiture: normalizeConfronto(raw.confronto_finiture),
    finiture_al_minimo: raw.finiture_al_minimo ?? false,
    bonus: normalizeBonus(raw.bonus),
    budget_eur: raw.budget_eur ?? null,
    categorie: raw.categorie.map((cat) => ({
      code: cat.code,
      nome: cat.nome,
      sottocategorie: cat.sottocategorie.map((sotto) => ({
        codice: sotto.codice,
        nome: sotto.nome,
        famiglia: sotto.famiglia,
        voci: sotto.voci.map((voce) => ({
          codice: voce.codice,
          descrizione: voce.descrizione,
          um: voce.um,
          quantita_stimata: toNumber(voce.quantita_stimata),
          prezzo_min: toNumber(voce.prezzo_min),
          prezzo_max: toNumber(voce.prezzo_max),
          livello: voce.livello ?? null,
        })),
        totale_min: toNumber(sotto.totale_min),
        totale_max: toNumber(sotto.totale_max),
      })),
      totale_min: toNumber(cat.totale_min),
      totale_max: toNumber(cat.totale_max),
      livello_scelto: cat.livello_scelto ?? null,
      livello_scelto_nome: cat.livello_scelto_nome ?? null,
    })),
    totale_min: toNumber(raw.totale_min),
    totale_max: toNumber(raw.totale_max),
    risposte: raw.risposte,
    risposte_salvate: raw.risposte_salvate ?? false,
    domande: (raw.domande ?? []).map(normalizeDomandaPro),
    livelli: raw.livelli ?? {},
    livelli_disponibili: raw.livelli_disponibili ?? [],
  };
}

/** GET /api/v1/me/stime/{id}/dettaglio-pro — dietro require_pro server-side. */
export async function getDettaglioPro(stimaId: number): Promise<DettaglioProOut> {
  const raw = await apiGet<RawDettaglioProOut>(`/me/stime/${stimaId}/dettaglio-pro`);
  return normalizeDettaglioPro(raw);
}

/**
 * POST /api/v1/me/stime/{id}/dettaglio-pro/risposte — persiste risposte e
 * livelli sulla stessa stima e ricalcola. Un solo endpoint per entrambi: sono
 * i due parametri dello stesso calcolo, e separarli aprirebbe la porta a uno
 * stato incoerente fra due chiamate.
 *
 * Payload generico dal 09-05 (`{risposte: {codice: valore}, livelli}`): non
 * più tre campi bagni/porte/condizionatori cablati.
 */
export async function postRisposteDettaglioPro(
  stimaId: number,
  risposte: Record<string, number | string>,
  livelli?: LivelliPerCategoria
): Promise<DettaglioProOut> {
  const raw = await apiPost<RawDettaglioProOut>(`/me/stime/${stimaId}/dettaglio-pro/risposte`, {
    risposte,
    ...(livelli ? { livelli } : {}),
  });
  return normalizeDettaglioPro(raw);
}

/**
 * GET /api/v1/me/stime/{id}/pdf-pro — rispecchia byte-per-byte scaricaPdf()
 * di api/stima.ts (blob diretto, filename da Content-Disposition, download
 * nativo), ma sull'endpoint Pro.
 */
export async function scaricaPdfPro(stimaId: number): Promise<void> {
  const API_BASE = import.meta.env.VITE_API_BASE as string | undefined;
  if (!API_BASE) {
    throw new Error("VITE_API_BASE non configurato (vedi frontend/.env.example)");
  }

  const response = await fetch(`${API_BASE}/me/stime/${stimaId}/pdf-pro`, {
    credentials: "include",
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `GET /me/stime/${stimaId}/pdf-pro fallita con status ${response.status}`
    );
  }

  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition");
  let filename = "stima-ristrutturazione-dettaglio.pdf";
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
