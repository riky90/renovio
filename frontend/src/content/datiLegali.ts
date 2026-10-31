/**
 * Dati del titolare del sito e venditore del Pro, usati da privacy, cookie e
 * condizioni di vendita (`content/legale.ts`) e dal footer.
 *
 * DA COMPLETARE prima di accendere i pagamenti: finché un campo vale
 * `null`, le pagine legali mostrano "[da completare]" evidenziato, così un
 * dato mancante si vede e non passa inosservato.
 */
export interface DatiLegali {
  /** Ragione sociale o nome della ditta individuale. */
  titolare: string | null;
  sede: string | null;
  partitaIva: string | null;
  codiceFiscale: string | null;
  /** Email per privacy e assistenza. */
  email: string | null;
  pec: string | null;
  /** Regione di Render dove stanno database e backend (es. "Francoforte, Germania"). */
  regioneHosting: string | null;
  /** Fornitore delle email transazionali (SMTP). */
  fornitoreEmail: string | null;
}

export const DATI_LEGALI: DatiLegali = {
  titolare: null,
  sede: null,
  partitaIva: null,
  codiceFiscale: null,
  email: null,
  pec: null,
  regioneHosting: null,
  fornitoreEmail: null,
};

/** Data dell'ultimo aggiornamento dei testi legali, mostrata in testa alle pagine. */
export const AGGIORNAMENTO_LEGALE = "31 ottobre 2026";
