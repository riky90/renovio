import { apiGet, apiPost } from "@/api/client";

export interface AttivaProResponse {
  pro: boolean;
  stato: string;
}

/**
 * POST /me/pro/attiva — attivazione stub "production-shaped" (D-07): nessun
 * addebito reale, la tessera abbonamento passa allo stato attivo.
 */
export async function postAttivaPro(): Promise<AttivaProResponse> {
  return apiPost<AttivaProResponse>("/me/pro/attiva", undefined);
}

/* ---------------------------------------------------- Pagamento (Stripe) */

export type PianoCode = "mensile" | "annuale";

export interface PianoPro {
  code: PianoCode;
  nome: string;
  /** IVA inclusa; arriva come stringa decimale dal backend. */
  importo: number;
  valuta: string;
  intervallo: "month" | "year";
}

export interface PianiPro {
  /** False finché Stripe non è configurato: resta l'attivazione dimostrativa. */
  pagamenti_attivi: boolean;
  piani: PianoPro[];
}

export interface Abbonamento {
  pro: boolean;
  stato: string;
  piano_code: PianoCode | null;
  scade_il: string | null;
  rinnovo_automatico: boolean;
  gestibile: boolean;
}

export async function getPianiPro(): Promise<PianiPro> {
  const raw = await apiGet<{ pagamenti_attivi: boolean; piani: Array<Omit<PianoPro, "importo"> & { importo: unknown }> }>(
    "/pro/piani",
  );
  return { ...raw, piani: raw.piani.map((p) => ({ ...p, importo: Number(p.importo) })) };
}

export async function getAbbonamento(): Promise<Abbonamento> {
  return apiGet<Abbonamento>("/me/abbonamento");
}

/** Crea la sessione di pagamento Stripe e restituisce l'URL a cui mandare l'utente. */
export async function postCheckout(piano: PianoCode, accettaEsecuzioneImmediata: boolean): Promise<string> {
  const { url } = await apiPost<{ url: string }>("/pro/checkout", {
    piano,
    accetta_esecuzione_immediata: accettaEsecuzioneImmediata,
  });
  return url;
}

/** Al ritorno da Stripe: attiva il Pro anche se il webhook non è ancora arrivato. */
export async function postConfermaCheckout(sessionId: string): Promise<Abbonamento> {
  return apiPost<Abbonamento>("/pro/checkout/conferma", { session_id: sessionId });
}

/** Portale clienti Stripe: disdetta, cambio piano, carta, ricevute. */
export async function postPortale(): Promise<string> {
  const { url } = await apiPost<{ url: string }>("/pro/portale", undefined);
  return url;
}
