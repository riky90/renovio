const formatter = new Intl.NumberFormat("it-IT", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});

export function formatEur(value: number): string {
  return formatter.format(value);
}

export function formatEurRange(min: number, max: number): string {
  return `${formatEur(min)} – ${formatEur(max)}`;
}
