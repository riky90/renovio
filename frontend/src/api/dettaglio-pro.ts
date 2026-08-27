import { apiGet, apiPost, ApiError } from "@/api/client";

export interface VoceOut {
  codice: string | null;
  descrizione: string;
  um: string;
  quantita_stimata: number;
  prezzo_min: number;
  prezzo_max: number;
}

export interface SottocategoriaOut {
  codice: string | null;
  nome: string;
  famiglia: "gerarchica" | "catalogo";
  voci: VoceOut[];
}

export interface CategoriaDettagliataOut {
  code: string;
  nome: string;
  sottocategorie: SottocategoriaOut[];
}

export interface RisposteDomande {
  bagni: number;
  porte: number;
  condizionatori: number;
}

export interface DettaglioProOut {
  categorie: CategoriaDettagliataOut[];
  risposte: RisposteDomande;
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
}

interface RawSottocategoriaOut {
  codice: string | null;
  nome: string;
  famiglia: "gerarchica" | "catalogo";
  voci: RawVoceOut[];
}

interface RawCategoriaDettagliataOut {
  code: string;
  nome: string;
  sottocategorie: RawSottocategoriaOut[];
}

interface RawDettaglioProOut {
  categorie: RawCategoriaDettagliataOut[];
  risposte: RisposteDomande;
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
        })),
      })),
    })),
    risposte: raw.risposte,
  };
}

/** GET /api/v1/me/stime/{id}/dettaglio-pro — dietro require_pro server-side. */
export async function getDettaglioPro(stimaId: number): Promise<DettaglioProOut> {
  const raw = await apiGet<RawDettaglioProOut>(`/me/stime/${stimaId}/dettaglio-pro`);
  return normalizeDettaglioPro(raw);
}

/** POST /api/v1/me/stime/{id}/dettaglio-pro/risposte — persiste le risposte e ricalcola. */
export async function postRisposteDettaglioPro(
  stimaId: number,
  risposte: RisposteDomande
): Promise<DettaglioProOut> {
  const raw = await apiPost<RawDettaglioProOut>(
    `/me/stime/${stimaId}/dettaglio-pro/risposte`,
    risposte
  );
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
