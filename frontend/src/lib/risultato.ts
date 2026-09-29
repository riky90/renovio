import type { CategoriaOut, ExtraOut, TotaleOut } from "@/api/stima";

// Funzioni pure di presentazione del risultato Free. Nessun prezzo qui: il fattore
// del tetto e i passi di arrotondamento sono geometria della barra (D-11), non
// listino. Le rispecchia il mirror Python del piano 10-02 (PDF).

/** Il tetto della barra e' 1,2 x il massimo (D-11). */
export const FATTORE_TETTO = 1.2;
/** Larghezza minima del segmento, in punti percentuali, perche' resti visibile. */
export const LARGHEZZA_MINIMA_PCT = 4;

const SOGLIA_PASSO = 100000;
const PASSO_PICCOLO = 1000;
const PASSO_GRANDE = 5000;

export interface ScalaBarra {
  tetto: number;
  leftPct: number;
  rightPct: number;
  budgetPct: number | null;
}

/** Asse 0 -> tetto (D-11): il segmento min-max occupa la sua quota reale. */
export function scalaBarra(min: number, max: number, budget?: number | null): ScalaBarra {
  const grezzo = Math.max(FATTORE_TETTO * max, budget ?? 0);
  const passo = grezzo < SOGLIA_PASSO ? PASSO_PICCOLO : PASSO_GRANDE;
  const tetto = Math.max(passo, Math.ceil(grezzo / passo) * passo);

  let leftPct = (min / tetto) * 100;
  let rightPct = (max / tetto) * 100;

  if (rightPct - leftPct < LARGHEZZA_MINIMA_PCT) {
    const centro = (leftPct + rightPct) / 2;
    leftPct = centro - LARGHEZZA_MINIMA_PCT / 2;
    rightPct = centro + LARGHEZZA_MINIMA_PCT / 2;
    if (leftPct < 0) {
      rightPct -= leftPct;
      leftPct = 0;
    }
    if (rightPct > 100) {
      leftPct -= rightPct - 100;
      rightPct = 100;
    }
    leftPct = Math.max(0, leftPct);
    rightPct = Math.min(100, rightPct);
  }

  const budgetPct = typeof budget === "number" && budget > 0 ? (budget / tetto) * 100 : null;
  return { tetto, leftPct, rightPct, budgetPct };
}

/** Incidenza €/m² su imponibile (IVA esclusa), D-14. */
export function incidenzaEurMq(
  imponibileMin: number,
  imponibileMax: number,
  mq: number,
): { min: number; max: number } | null {
  if (!(mq > 0)) return null;
  return { min: Math.round(imponibileMin / mq), max: Math.round(imponibileMax / mq) };
}

/** Denominatore del peso: solo categorie, senza extra ne' arredo. */
export function sommaMediCategorie(categorie: CategoriaOut[]): number {
  return categorie.reduce((acc, c) => acc + (c.totale_min + c.totale_max) / 2, 0);
}

/** Peso della categoria sul valore medio (D-15). */
export function pesoCategoria(
  categoria: CategoriaOut,
  sommaMedi: number,
): { etichetta: string; fillPct: number } {
  if (sommaMedi <= 0) return { etichetta: "0%", fillPct: 0 };
  const medio = (categoria.totale_min + categoria.totale_max) / 2;
  const raw = (medio / sommaMedi) * 100;
  return {
    etichetta: raw < 1 ? "<1%" : `${Math.round(raw)}%`,
    fillPct: Math.min(100, Math.max(raw, 2)),
  };
}

export interface RigaIva {
  ivaPct: number;
  min: number;
  max: number;
}

export interface RiepilogoIva {
  imponibileLavoriMin: number;
  imponibileLavoriMax: number;
  righeIva: RigaIva[];
  extra: ExtraOut[];
  totaleMin: number;
  totaleMax: number;
}

/**
 * Riepilogo D-16. L'imponibile lavori somma le categorie (totale.imponibile_*
 * include gli extra). Le righe IVA raggruppano sui valori iva_pct dei dati; la
 * riga con aliquota piu' alta assorbe l'arrotondamento cosi' che le righe
 * sommino esattamente a totale.iva.
 */
export function riepilogoIva(
  categorie: CategoriaOut[],
  extra: ExtraOut[],
  totale: TotaleOut,
): RiepilogoIva {
  const gruppi = new Map<number, RigaIva>();
  const riga = (ivaPct: number): RigaIva => {
    const chiave = Math.round(ivaPct * 10000);
    let r = gruppi.get(chiave);
    if (!r) {
      r = { ivaPct, min: 0, max: 0 };
      gruppi.set(chiave, r);
    }
    return r;
  };

  let imponibileLavoriMin = 0;
  let imponibileLavoriMax = 0;
  for (const c of categorie) {
    imponibileLavoriMin += c.imponibile_min;
    imponibileLavoriMax += c.imponibile_max;
    const r = riga(c.iva_pct);
    r.min += c.iva_min;
    r.max += c.iva_max;
  }
  for (const e of extra) {
    const r = riga(e.iva_pct);
    const iva = e.importo * e.iva_pct;
    r.min += iva;
    r.max += iva;
  }

  const righeIva = [...gruppi.entries()].sort((a, b) => a[0] - b[0]).map(([, r]) => r);

  if (righeIva.length > 0) {
    const ultima = righeIva[righeIva.length - 1];
    const altreMin = righeIva.slice(0, -1).reduce((s, r) => s + r.min, 0);
    const altreMax = righeIva.slice(0, -1).reduce((s, r) => s + r.max, 0);
    ultima.min = totale.iva_min - altreMin;
    ultima.max = totale.iva_max - altreMax;
  }

  return {
    imponibileLavoriMin,
    imponibileLavoriMax,
    righeIva,
    extra,
    totaleMin: totale.totale_min,
    totaleMax: totale.totale_max,
  };
}
