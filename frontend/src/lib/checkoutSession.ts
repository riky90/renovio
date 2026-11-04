/**
 * Il `session_id` del checkout Stripe non deve restare nella barra degli
 * indirizzi: il Pixel di Meta e GA4 leggono l'URL completo della pagina, e
 * il primo PageView parte all'avvio, prima che qualunque componente possa
 * ripulirlo.
 *
 * Questo modulo va importato PER PRIMO in `main.tsx` (prima di `App`, che
 * crea il router leggendo `window.location`): al caricamento sposta il
 * parametro in `sessionStorage` e lo toglie dall'URL con `replaceState`.
 * `PassaAProPage` lo riprende con `prendiSessionIdCheckout()`.
 */

const CHIAVE = "renovio.checkout_session_id";

function memoria(): Storage | null {
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

if (typeof window !== "undefined") {
  const url = new URL(window.location.href);
  const sessionId = url.searchParams.get("session_id");
  if (sessionId) {
    memoria()?.setItem(CHIAVE, sessionId);
    url.searchParams.delete("session_id");
    window.history.replaceState(window.history.state, "", url.pathname + url.search + url.hash);
  }
}

/** Il `session_id` del checkout appena concluso, se c'e'. Non lo cancella:
 * la pagina puo' rimontare (StrictMode) e la conferma lato server e'
 * idempotente. Lo cancella `dimenticaSessionIdCheckout()`. */
export function prendiSessionIdCheckout(): string | null {
  return memoria()?.getItem(CHIAVE) ?? null;
}

export function dimenticaSessionIdCheckout(): void {
  memoria()?.removeItem(CHIAVE);
}
