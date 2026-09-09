import { apiGet, apiPost, ApiError } from "@/api/client";

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

export interface RisposteDomande {
  bagni: number;
  porte: number;
  condizionatori: number;
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

export interface DettaglioProOut {
  categorie: CategoriaDettagliataOut[];
  totale_min: number;
  totale_max: number;
  risposte: RisposteDomande;
  /**
   * True se l'utente ha DAVVERO risposto alle domande mirate. Distingue
   * `{0, 0, 0}` (risposta legittima) dal non aver mai risposto — cosa che la
   * somma delle tre risposte non può fare.
   */
  risposte_salvate: boolean;
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

interface RawDettaglioProOut {
  categorie: RawCategoriaDettagliataOut[];
  totale_min: unknown;
  totale_max: unknown;
  risposte: RisposteDomande;
  risposte_salvate?: boolean;
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

function normalizeDettaglioPro(raw: RawDettaglioProOut): DettaglioProOut {
  return {
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
 */
export async function postRisposteDettaglioPro(
  stimaId: number,
  risposte: RisposteDomande,
  livelli?: LivelliPerCategoria
): Promise<DettaglioProOut> {
  const raw = await apiPost<RawDettaglioProOut>(`/me/stime/${stimaId}/dettaglio-pro/risposte`, {
    ...risposte,
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
