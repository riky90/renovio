# Testi legali

I testi di privacy, cookie e condizioni di vendita sono nel sito, non qui:

- testi: `frontend/src/content/legale.ts`;
- dati del titolare (ragione sociale, sede, P. IVA, email, PEC, regione dei server, fornitore
  email): `frontend/src/content/datiLegali.ts`;
- pagine: `/privacy`, `/cookie`, `/condizioni-di-vendita`, linkate dal footer.

Finché un dato del titolare manca, le pagine mostrano "[da completare]" evidenziato in giallo.

Sono **bozze da far verificare a un legale**. Descrivono i trattamenti che il codice fa davvero:
- account;
- stime;
- richieste di contatto inviate al professionista della zona;
- pagamenti Stripe;
- due soli cookie tecnici.

Se il sito aggiunge un trattamento (analytics, newsletter, pubblicità), questi testi vanno
aggiornati nello stesso cambio.

## Prima di accendere i pagamenti

Le condizioni di vendita promettono tre cose che il codice non fa ancora:

1. il pulsante "Recedi dal contratto qui" in Impostazioni → Abbonamento, obbligatorio dal 19
   giugno 2026 (art. 54-bis Codice del Consumo, D.lgs. 209/2025), con "Conferma recesso",
   chiusura dell'abbonamento, rimborso pieno via Stripe e ricevuta via email;
2. l'email di conferma dell'acquisto, con il riepilogo e le condizioni (supporto durevole);
3. il promemoria prima del rinnovo annuale: si attiva su Stripe, in Impostazioni → Billing →
   Subscriptions and emails.
