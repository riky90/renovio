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
- cookie tecnici, più statistiche (Google Analytics 4) e marketing (Google Ads, Meta) solo
  con il consenso del banner (`docs/tracciamento.md`).

Se il sito aggiunge un trattamento (analytics, newsletter, pubblicità), questi testi vanno
aggiornati nello stesso cambio.

## Cosa promettono le condizioni, e dove sta nel codice

1. **Recesso entro 14 giorni con rimborso pieno**: il pulsante "Recedi dal contratto qui" in
   Impostazioni → Abbonamento apre la finestra con "Conferma recesso" (art. 54-bis Codice del
   Consumo, D.lgs. 209/2025). Il backend (`POST /api/v1/pro/recesso`):
   - rimborsa su Stripe tutte le fatture pagate dell'abbonamento;
   - chiude subito l'abbonamento;
   - manda la ricevuta via email.

   Vale una sola volta, sul primo acquisto. Nel footer c'è il link "Recesso dal contratto".
2. **Email di conferma dell'acquisto** (supporto durevole): parte una sola volta per abbonamento
   e contiene piano, prezzo, rinnovo, scadenza del recesso e i link alle condizioni.
   Testi in `backend/app/services/email_pro.py`.
3. **Promemoria prima del rinnovo annuale**: non sta nel codice, va attivato su Stripe
   (Impostazioni → Billing → Subscriptions and emails → "Send emails about upcoming
   renewals").
