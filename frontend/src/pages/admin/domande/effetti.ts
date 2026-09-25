/**
 * Vocabolario UI degli otto tipi di effetto (D-31): etichette leggibili,
 * bersagli ammessi per tipo e formattazione del valore (UI-SPEC §D.5). Il
 * server (`services/effetti.py`) resta l'autorita' finale della validazione
 * (T-08.1-50, 400 leggibile su `valida_effetto`) — questo modulo e' solo il
 * filtro di UX che evita di proporre combinazioni che il backend rifiuterebbe
 * comunque.
 */

import type { TipoEffetto } from "@/api/admin/domande";

export const TIPI_EFFETTO = [
  "moltiplicatore_categoria",
  "eur_mq_categoria",
  "eur_fisso_categoria",
  "eur_per_scostamento",
  "includi",
  "escludi",
  "fattore_quantita",
  "quantita_per_unita",
] as const satisfies readonly TipoEffetto[];

export const ETICHETTE_TIPO_EFFETTO: Record<TipoEffetto, string> = {
  moltiplicatore_categoria: "Moltiplicatore su categoria",
  eur_mq_categoria: "€/m² su categoria",
  eur_fisso_categoria: "Importo fisso su categoria",
  eur_per_scostamento: "€ per unità di scostamento",
  includi: "Includi",
  escludi: "Escludi",
  fattore_quantita: "Fattore sulla quantità",
  quantita_per_unita: "Quantità per unità di risposta",
};

export type Livello = "categoria" | "sottocategoria" | "voce";

export const BERSAGLI_AMMESSI: Record<TipoEffetto, Livello[]> = {
  moltiplicatore_categoria: ["categoria"],
  eur_mq_categoria: ["categoria"],
  eur_fisso_categoria: ["categoria"],
  eur_per_scostamento: ["categoria"],
  includi: ["sottocategoria", "voce"],
  escludi: ["categoria", "sottocategoria", "voce"],
  fattore_quantita: ["sottocategoria", "voce"],
  quantita_per_unita: ["voce"],
};

/** Nessun valore numerico: la presenza della riga e' l'effetto. */
export const TIPI_SENZA_VALORE: readonly TipoEffetto[] = ["includi", "escludi"];

/** Valore negativo vietato dal backend per questi due tipi. */
export const TIPI_VALORE_NON_NEGATIVO: readonly TipoEffetto[] = [
  "moltiplicatore_categoria",
  "fattore_quantita",
];

/** Formattazione del valore per colonna Valore (UI-SPEC §D.5), mai il numero grezzo. */
export function formattaValore(tipo: TipoEffetto, valore: number | null): string {
  if (valore === null) return "—";
  switch (tipo) {
    case "moltiplicatore_categoria":
    case "fattore_quantita":
      return `× ${valore}`;
    case "eur_mq_categoria":
      return `${valore} €/m²`;
    case "eur_fisso_categoria":
      return `${valore} €`;
    case "eur_per_scostamento":
      return `${valore} €/unità`;
    case "quantita_per_unita":
      return `${valore} × risposta`;
    case "includi":
    case "escludi":
      return "—";
    default: {
      // IN-01: un tipo che il backend conosce e il frontend non ancora
      // (deploy disallineato) mostra il valore grezzo invece di una cella
      // vuota. `never` tiene l'esaustivita' controllata a compile-time.
      const sconosciuto: never = tipo;
      return `${valore} (${String(sconosciuto)})`;
    }
  }
}
