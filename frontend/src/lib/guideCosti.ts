/**
 * Le cifre delle guide ai costi.
 *
 * Fonte unica: il motore della stima (`GET /api/v1/guide/costi`). Al build le
 * guide si prerenderizzano con l'istantanea `src/data/guide-costi.json`
 * (rigenerata da `backend/scripts/esporta_dati_guide.py`), cosi' l'HTML
 * statico che leggono Google e gli assistenti AI contiene numeri veri; nel
 * browser la stessa query si aggiorna dal vivo, e se l'API non risponde resta
 * l'istantanea.
 */

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/api/client";
import istantanea from "@/data/guide-costi.json";

export interface FasciaCategoria {
  code: string;
  nome: string;
  min: number;
  max: number;
}

export interface Fascia {
  mq: number;
  tipo: string;
  min: number;
  max: number;
  eur_mq_min: number;
  eur_mq_max: number;
  categorie: FasciaCategoria[];
}

export interface FasciaScenario extends Fascia {
  code: string;
  etichetta: string;
}

export interface DatiGuide {
  aggiornato_il: string;
  citta_listino: string;
  mq_riferimento: number;
  per_tipo: Record<"leggera" | "moderata" | "totale", Fascia[]>;
  per_livello: Record<"base" | "medio" | "alto", Fascia>;
  guide: Record<string, FasciaScenario[]>;
  extra: { code: string; nome: string; importo_ivato: number }[];
}

export const DATI_ISTANTANEA = istantanea as DatiGuide;

export function useDatiGuide(): DatiGuide {
  const { data } = useQuery<DatiGuide>({
    queryKey: ["guide-costi"],
    queryFn: () => apiGet<DatiGuide>("/guide/costi"),
    initialData: DATI_ISTANTANEA,
    // L'istantanea va bene subito; il dato vivo arriva in background.
    initialDataUpdatedAt: 0,
    staleTime: 10 * 60 * 1000,
    retry: false,
  });
  return data;
}

/** "ottobre 2026" dalla data ISO di aggiornamento. */
export function meseAnno(isoData: string): string {
  return new Date(`${isoData}T12:00:00`).toLocaleDateString("it-IT", { month: "long", year: "numeric" });
}

export function anno(isoData: string): string {
  return isoData.slice(0, 4);
}

export function fasciaDi(dati: DatiGuide, tipo: keyof DatiGuide["per_tipo"], mq: number): Fascia | undefined {
  return dati.per_tipo[tipo].find((f) => f.mq === mq);
}

export function scenario(dati: DatiGuide, guida: string, code: string): FasciaScenario | undefined {
  return dati.guide[guida]?.find((s) => s.code === code);
}
