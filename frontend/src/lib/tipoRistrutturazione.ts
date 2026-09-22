/**
 * Etichette dei tre tipi di ristrutturazione, condivise tra pannello admin
 * (dashboard lead, anteprima) e wizard pubblico. Estratte da
 * `LeadDashboardPage.tsx` per non duplicarle nella tab Anteprima di
 * `/admin/coefficienti` (PAR-04).
 */
export const TIPO_LABELS: Record<string, string> = {
  leggera: "Leggera",
  moderata: "Moderata",
  totale: "Totale",
};
