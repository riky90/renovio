const formatter = new Intl.NumberFormat("it-IT", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
  // Force the thousands separator on every 4+ digit amount. The it-IT locale
  // defaults to minimumGroupingDigits=2, which suppresses the separator below
  // 10.000 (so 7466 rendered as "7466 €"); "always" restores 7.466 €.
  useGrouping: "always",
});

export function formatEur(value: number): string {
  return formatter.format(value);
}

const numberFormatter = new Intl.NumberFormat("it-IT", {
  maximumFractionDigits: 0,
  useGrouping: "always",
});

/** Incidenza al metro quadro: "310–380 €/m²". */
export function formatRangeEurMq(min: number, max: number): string {
  return `${numberFormatter.format(min)}–${numberFormatter.format(max)} €/m²`;
}

export function formatEurRange(min: number, max: number): string {
  return `${formatEur(min)} – ${formatEur(max)}`;
}
