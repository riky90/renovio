# Pagamento del Pro con Stripe — configurazione

Renovio Pro è un abbonamento Stripe con due piani:

| Piano | Prezzo (IVA inclusa) | Lookup key |
|---|---|---|
| Mensile | 3 € al mese | `renovio_pro_mensile` |
| Annuale | 29 € all'anno (circa il 19% in meno di 12 mesi) | `renovio_pro_annuale` |

Il codice è pronto, ma finché su Render non c'è `STRIPE_SECRET_KEY` i pagamenti restano
**spenti** e "Passa a Pro" usa l'attivazione dimostrativa gratuita di prima. Appena la chiave
c'è, l'attivazione gratuita si chiude da sola: non può esistere un Pro gratis con i pagamenti
attivi.

## Come funziona

1. L'utente sceglie il piano su `/passa-a-pro` e accetta l'attivazione immediata, con la
   rinuncia al recesso per i servizi digitali (Codice del Consumo, art. 59, lett. o).
2. Il backend crea una sessione **Stripe Checkout** e l'utente paga sulla pagina di Stripe:
   carta, Apple Pay, Google Pay e codici sconto.
3. Stripe chiama il **webhook** `POST /api/v1/stripe/webhook`. Il backend verifica la firma,
   rilegge l'abbonamento da Stripe e attiva il Pro fino alla fine del periodo pagato, più due
   giorni di margine per il rinnovo.
4. Al ritorno sul sito, `/passa-a-pro?esito=ok` conferma il pagamento anche se il webhook è in
   ritardo.
5. Disdetta, cambio piano, carta e ricevute passano dal **portale clienti** di Stripe:
   Impostazioni → Abbonamento → "Gestisci abbonamento". Con la disdetta il Pro resta attivo
   fino a fine periodo.

I prezzi stanno solo su Stripe. Per cambiarli si crea un nuovo prezzo con la stessa lookup key
(opzione "Transfer lookup key" nel pannello): la pagina lo mostra entro 10 minuti, senza
deploy.

## Passi su Stripe, prima in modalità test

1. **Account**: crea l'account su [dashboard.stripe.com](https://dashboard.stripe.com) e lascia
   attivo l'interruttore **Test mode**.
2. **Prodotto e prezzi**: in Catalogo prodotti → Aggiungi prodotto crea "Renovio Pro" con due
   prezzi ricorrenti in EUR:
   - 3,00 € al mese, con lookup key `renovio_pro_mensile`;
   - 29,00 € all'anno, con lookup key `renovio_pro_annuale`.

   La lookup key sta in "Altre opzioni" del prezzo. Su entrambi i prezzi imposta il
   comportamento fiscale **"IVA inclusa"** (*inclusive*), perché i prezzi mostrati sono IVA
   inclusa.
3. **Portale clienti**: in Impostazioni → Billing → Customer portal attiva:
   - disdetta a fine periodo;
   - cambio piano fra i due prezzi;
   - aggiornamento del metodo di pagamento;
   - storico delle fatture.

   Salva, anche in test mode.
4. **Webhook**: in Sviluppatori → Webhook → Aggiungi endpoint:
   - URL: `https://<backend su Render>/api/v1/stripe/webhook`;
   - eventi:
     - `checkout.session.completed`;
     - `customer.subscription.created`;
     - `customer.subscription.updated`;
     - `customer.subscription.deleted`;
     - `invoice.paid`;
     - `invoice.payment_failed`.

   Copia il **Signing secret** (`whsec_...`).
5. **Email ai clienti**: in Impostazioni → Email clienti attiva le ricevute dei pagamenti
   riusciti e i rimborsi.

## Variabili d'ambiente su Render (servizio backend)

| Variabile | Valore |
|---|---|
| `STRIPE_SECRET_KEY` | `sk_test_...` (Sviluppatori → Chiavi API). In produzione `sk_live_...`. |
| `STRIPE_WEBHOOK_SECRET` | `whsec_...` del webhook al passo 4. |
| `FRONTEND_URL` | Già impostata: serve per gli URL di ritorno dal pagamento. |

Le chiavi vanno **solo** su Render, mai nel codice né in chat. Le lookup key hanno già il valore
giusto di default; le variabili `STRIPE_LOOKUP_KEY_MENSILE` e `STRIPE_LOOKUP_KEY_ANNUALE`
servono solo se le cambi su Stripe.

## Prova in test

1. Su `/passa-a-pro` scegli un piano, spunta il consenso e premi "Continua al pagamento".
2. Paga con la carta di test `4242 4242 4242 4242`, una scadenza futura qualsiasi e un CVC
   qualsiasi.
3. Al ritorno compare "Sei ora Pro"; in Impostazioni → Abbonamento ci sono piano e data di
   rinnovo.
4. "Gestisci abbonamento" → disdici: il Pro resta attivo e la pagina dice "Disdetto: resta
   attivo fino al …".
5. In Stripe → Sviluppatori → Webhook gli eventi devono risultare consegnati con risposta 200.

Carte per i casi di errore: `4000 0000 0000 9995` (fondi insufficienti), `4000 0025 0000 3155`
(autenticazione 3D Secure).

## Passaggio in produzione

1. Completa l'attivazione dell'account Stripe: dati aziendali, IBAN, documento.
2. Ripeti i passi 2-5 con **Test mode spento**: prezzi, portale e webhook sono separati fra
   test e live.
3. Su Render sostituisci `STRIPE_SECRET_KEY` e `STRIPE_WEBHOOK_SECRET` con quelli live.

## Da verificare con il commercialista (non è codice)

- **Documenti fiscali**: Stripe invia ricevute e fatture Stripe, ma non sono fatture
  elettroniche italiane. Per le vendite a privati di servizi digitali vanno chiariti:
  - il regime (corrispettivi o fattura su richiesta);
  - come registrarle;
  - se serve un collegamento con lo SdI per le fatture chieste da partite IVA.
- **IVA**: i prezzi sono IVA inclusa al 22%. Per clienti di altri paesi UE vale l'IVA del paese
  del cliente (regime OSS). Stripe Tax può calcolarla, ma oggi è spento.
- **Termini di vendita e privacy**: serve una pagina con condizioni di vendita, rinnovo, disdetta
  e recesso. Il link si mette anche su Stripe, in Impostazioni → Pubblico → Termini di servizio.
