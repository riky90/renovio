# Phase 4: Lead & pannello admin - Context

**Gathered:** 2026-08-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Due capability collegate:

1. **Lead / contatto professionista (LEAD-01/02/03):** da Free e da Pro un utente **loggato** invia una richiesta di contatto; il lead (dati utente + snapshot della stima) viene **salvato** e notificato **via email al referente attivo della città**, e compare nella **dashboard admin**. Il modello dati supporta **più referenti per città** (v1: un referente attivo per città; `Referente` già esiste in `catalogo.py`).

2. **Pannello admin senza codice (ADM-01/02/03/04):** l'admin, dietro route protetta `require_admin`, gestisce **listini/prezzi per città**, **coefficienti parametrici del modello**, **città/mappature/tipi/extra**, **testi/disclaimer**, **referenti per città**, e **consulta i lead**. Le nuove stime risentono subito degli edit; le stime già salvate restano congelate.

**In scope:** modello `Lead` (net-new) + form di contatto + notifica email + dashboard lead; UI admin net-new (oggi assente) con sezioni CRUD; upload Excel del computo per listini multi-città (rimandato dalla Fase 3) + form CRUD granulare; tabella testi/impostazioni editabile (oggi i testi sono hardcoded nel backend); CRUD referenti.

**Non include:** pagamento reale / prezzo abbonamento Pro definito (resta stub, Fase 3); portale completo rete professionisti (assegnazione/gestione partner — visione futura); moltiplicatori-prezzo per zona geografica (v2, servono i dati); simulazione finanziamento a rate (out of scope v1). Contatto **anonimo** (senza login) escluso: il lead richiede login (coerente con roadmap criterio #1 "da Free e da Pro l'utente invia").
</domain>

<decisions>
## Implementation Decisions

### Lead — form di contatto (LEAD-01)
- **D-01:** Il contatto è **solo per utenti loggati**, disponibile **sia da Free sia da Pro**. Nome/email presi dall'account. ("Aperto a tutti" nel PROJECT.md = entrambi i livelli, non "anche anonimi".)
- **D-02:** Campi del form oltre a nome+email: **telefono**, **messaggio libero**, **preferenza di contatto** (email/telefono + fascia oraria).
- **D-03:** Al lead si allega uno **snapshot della stima visualizzata** al momento del contatto (Free o Pro): città/mq/tipo/totali a range **copiati nel record `Lead`** in modo autonomo (indipendente da `stima_salvata`, difendibile e leggibile anche se l'utente cancella la stima). Anti-leak: nessun dato impresa.

### Lead — notifica & destinatario (LEAD-02/03)
- **D-04:** L'email del lead va al **referente attivo della città** (risolto via `ComuneListino` → `Listino` → `Referente` attivo con priorità).
- **D-05:** **Città senza referente attivo → fallback al referente del listino di default** (`listino.is_default`), che funge da **catch-all globale**. Nessuna modifica di schema: il "referente globale" è semplicemente il referente attivo del listino di default. Il lead non si perde mai.
- **D-06:** Contenuto della notifica e del record: **dati utente** (nome/email/telefono/preferenza/messaggio) + **riepilogo stima a range** (città/mq/tipo/totali) + **link al lead nella dashboard**. Mai coefficiente/prezzo impresa (anti-leak assoluto verso i non-admin, vale anche per l'email al referente).
- **D-07:** **Lead mai perso in caso di errore email:** il record `Lead` viene **sempre salvato** prima/indipendentemente dall'invio SMTP; se l'invio fallisce il lead resta comunque in dashboard (coerente col dev-fallback di `email_service`, che logga invece di sollevare). *(Meccanica esatta — flag di invio/retry — a discrezione del planner.)*
- **D-08:** **Conferma all'utente:** dopo l'invio, **messaggio a schermo** di conferma **+ email di conferma ricezione** all'utente ("abbiamo ricevuto la tua richiesta, un professionista ti contatterà"), riusando `email_service`.

### Admin — CRUD prezzi & listini (ADM-01)
- **D-09:** Editing prezzi con approccio **ibrido**: **upload Excel del computo per il caricamento bulk** di una città (crea listino + voci + mappatura città) **+ form CRUD granulare in-app** per ritocchi puntuali su voci/categorie. Entrambi i percorsi devono essere **idempotenti** e non distruttivi (D-12 Fase 3).
- **D-10:** **Admin proprietario del margine.** L'admin **vede e modifica** `coefficiente_impresa` e `base_eur_mq` dal pannello (necessari per ADM-01/02). L'invariante anti-leak resta **assoluto solo verso i non-admin** (API/PDF utente finale): questi campi non compaiono mai in risposte esposte ai client non-admin.
- **D-11:** **Effetto degli edit:** le **nuove stime** (calcolate dopo l'edit) usano subito i nuovi valori (criterio di successo #3); le **stime già salvate e i PDF già generati restano immutabili** (snapshot congelato, D-09 Fase 2). Nessun versioning/audit trail obbligatorio in v1 (a discrezione del planner se leggero).

### Admin — coefficienti parametrici (ADM-02)
- **D-12:** In v1 l'admin può editare **tutti** i coefficienti del modello:
  - **Moltiplicatori tipo×categoria** (leggera/moderata/totale per le 4 categorie) — cuore della stima Free;
  - **`base_eur_mq` per categoria** (basi €/m² del motore Free, interne);
  - **Coefficienti quantità-per-m² del motore Pro** (D-04 Fase 3, taratura delle quantità);
  - **IVA per categoria** ed **extra** (CSE/CSP, pratiche — aliquote/importi/regole).

### Admin — città, mappature, tipi, testi (ADM-03)
- **D-13:** **Città/listino/mappatura:** l'**upload gestisce tutto** (crea città, listino e mappatura `ComuneListino`), **poi il form CRUD** consente editing puntuale su `ComuneListino`, tipi di ristrutturazione ed extra.
- **D-14:** **Testi/disclaimer editabili:** i testi oggi **hardcoded nel backend** (city_resolver, schemi stima, disclaimer fallback/legali) migrano in una **nuova tabella testi key/value** (`testo`/`impostazione`: chiave → contenuto), con **seed dei testi attuali**. Il backend legge da DB invece che da costanti; l'admin li modifica da form. Copre ADM-03 pienamente.

### Admin — referenti & dashboard lead (ADM-04)
- **D-15:** **CRUD referenti completo** per listino/città con flag **`attivo`** e **`priorita`** (schema già pronto). V1: **un referente attivo per città**; il referente del listino default fa da catch-all globale (D-05).
- **D-16:** **Referente configurabile da subito, nessun seed pre-fatto:** l'admin crea il referente dal pannello al primo avvio (niente referente "utente stesso" pre-seedato).
- **D-17:** **Dashboard lead** con **stato del lead** (`nuovo` / `gestito`) + **nota** aggiornabile dall'admin/referente (piccola aggiunta al modello `Lead`). Vista: **lista** (data, città, nome, contatti, totale stima, stato) con **filtri per città e stato**, e **dettaglio** con lo **snapshot stima completo**.

### Upload Excel — validazione (D-12 Fase 3 = guardrail bloccante)
- **D-18:** **Flusso a due passi con preview:** l'admin carica → il sistema valida e mostra un'**anteprima del diff** (righe nuove / modificate / errori) → l'admin **conferma** per applicare. Previene azzeramenti accidentali.
- **D-19:** **Import parziale robusto:** le **righe valide vengono importate**, le **righe malformate/non riconosciute vengono scartate ed elencate** all'admin per correzione. Un errore isolato non blocca l'intero import. Upsert per chiave naturale (idempotente).
- **D-20:** **Vincoli upload:** solo file **`.xlsx`**, **solo `require_admin`**, con **limite di dimensione** ragionevole (~10MB). Parsing sicuro. La struttura di riferimento del file è in `docs/computo-struttura-dettaglio.md`.

### Struttura UI admin (net-new)
- **D-21:** **Area `/admin` protetta** (route con `require_admin`) con **navigazione a tab/sidebar** tra le sezioni: **Lead**, **Listini/Prezzi**, **Coefficienti**, **Città/Testi**, **Referenti**. Riusa componenti e stile delle Fasi 1-3 (palette Slate/blue-600, card, form).

### Regole di dominio (portate avanti — non ri-discusse)
- **D-22:** **Anti-leak assoluto verso i non-admin.** `coefficiente_impresa`/`base_eur_mq`/prezzi impresa/margini restano server-side e non compaiono in nessuna risposta API esposta ai client non-admin, nel PDF, nell'email al referente, né nello snapshot del lead. L'admin è l'unica eccezione (D-10).
- **D-23:** Output **sempre a range** anche nella stima allegata al lead e nelle viste utente.
- **D-24:** **Guardrail database (D-12 Fase 3, propagato):** ogni edit/upload admin deve restare **idempotente** e **non azzerare** i dati esistenti; ogni nuova migrazione deve preservare/rieseguire il seed del listino; Free e Pro leggono lo **stesso listino** per città.

### Claude's Discretion
- Schema esatto del modello `Lead` (colonne snapshot dedicate vs JSON, stato/nota, relazione a `user`/`referente`/`comune`) e della tabella testi key/value, purché rispetti D-03/D-14/D-17 e l'anti-leak.
- Meccanica esatta di retry/flag di invio email per il lead (D-07) e forma dell'audit/versioning listini se ritenuto leggero (D-11).
- Parser dell'upload Excel (mapping fogli→tabelle, gestione struttura non uniforme A-EDILE vs cataloghi B/C/D) e forma esatta della preview del diff (D-18/D-19), purché idempotente e non distruttivo.
- Layout preciso di ciascuna sezione admin e dei form (tabelle editabili inline vs modale), coerente con lo stile esistente.
- Set esatto di chiavi della tabella testi e valori iniziali di seed (dai testi hardcoded attuali).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Dominio e decisioni di progetto
- `CLAUDE.md` — regole di dominio non negoziabili (prezzo/coefficiente impresa mai esposto ai non-admin, output a range, città = listino, IVA differenziata, multi-referente).
- `.planning/PROJECT.md` — Core Value, Key Decisions (contatto aperto a tutti = business goal; modello multi-referente dal giorno 1, v1 un referente; prezzi/coefficienti gestiti da pannello admin non nel codice).
- `.planning/REQUIREMENTS.md` — Fase 4 = LEAD-01/02/03, ADM-01/02/03/04.
- `.planning/ROADMAP.md` — confini e success criteria Fase 4 (lead da Free e Pro; email + dashboard; admin edita listini/coefficienti con effetto immediato; multi-referente v1 un attivo; edita città/mappature/testi).
- `.planning/phases/03-pro-dettaglio-sottocategorie/03-CONTEXT.md` — **D-12 (guardrail DB bloccante propagato alla Fase 4: edit/upload idempotenti, no azzeramento)**, D-04/D-05 (coefficienti quantità-per-m² Pro da tarare via admin), motore Pro bottom-up.
- `.planning/phases/02-account-pdf/02-CONTEXT.md` — **D-04 (email_service transazionale costruito apposta per i lead Fase 4)**, D-09 (snapshot immutabile — un edit admin non tocca le stime salvate), D-03 (ruolo admin + require_admin).
- `.planning/phases/01-stima-free-end-to-end/01-CONTEXT.md` — motore Free, listino a livello categoria, anti-leak, SoftWallCta/CTA.

### Fonte dati upload (leggere prima di implementare il parser)
- `docs/computo-struttura-dettaglio.md` — mappa della struttura dei fogli del computo (gerarchia A-EDILE, cataloghi B/C/D, quantità=0, UM, coeff. impresa). Riferimento per il parser upload.
- `docs/computo-base-reggio-emilia.xlsx` — file sorgente reale (formato atteso dall'upload).
- `docs/seed-coefficienti-base.json` — seed attuale (categoria + Pro) da tenere allineato con l'edit admin.

### Codice esistente da integrare
- `backend/app/services/email_service.py` — `send_email(to, subject, html_body)` **già pronto** per la notifica lead e la conferma utente (dev-fallback logga invece di inviare; mai solleva).
- `backend/app/dependencies/auth.py` — `require_admin` (guard 403) da usare su tutte le route admin; `get_current_user` per il lead loggato.
- `backend/app/routers/admin.py` — router stub (`/admin/ping`) da estendere con le sezioni CRUD.
- `backend/app/models/catalogo.py` — `Referente` (listino_id, nome, email, telefono, attivo, priorita — già pronto), `ComuneListino` (comune→listino, fallback su `listino.is_default`), `Categoria`, `TipoRistrutturazione`, `Moltiplicatore`, `Extra`.
- `backend/app/models/listino.py` — `Listino`/`ListinoCategoria` (con `is_default` per il fallback e il catch-all referente).
- `backend/app/models/dettaglio_pro.py` — sottocategorie/voci/coeff quantità Pro (editabili da admin, D-12).
- `backend/app/models/stima_salvata.py` — snapshot immutabile (riferimento per lo snapshot copiato nel Lead).
- `backend/app/services/estimation.py`, `backend/app/services/dettaglio_pro.py` — motori che leggono i coefficienti editati; l'anti-leak passa da qui.
- `backend/app/services/city_resolver.py` — risoluzione città→listino + disclaimer fallback (oggi con testi hardcoded → migrare a tabella testi, D-14).
- `backend/alembic/versions/0005_dettaglio_pro.py` — ultima migrazione (catena 0001→…→0005); le migrazioni Fase 4 (Lead, testi, eventuali colonne referente/lead-stato) partono da qui e devono preservare il seed (D-24).
- `frontend/src/components/SoftWallCta.tsx`, `frontend/src/routes/*`, `frontend/src/pages/EstimatePage.tsx`, `frontend/src/pages/DettaglioProPage.tsx` — pattern di routing/componenti da riusare per l'area /admin e per la CTA contatto; `frontend/src/api/client.ts` per il pattern chiamate.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`email_service.send_email`** — costruito in Fase 2 (D-04) esplicitamente per i lead: env-driven SMTP, dev-fallback che logga, non solleva mai. Usato sia per notifica referente sia per conferma utente. Nessun refactor.
- **`require_admin` / `get_current_user`** (`dependencies/auth.py`) — guard pronti per proteggere tutte le route admin e per identificare l'utente loggato che invia il lead.
- **Modello `Referente`** — già completo (attivo/priorità/per-listino): il CRUD referenti e la risoluzione destinatario lead si appoggiano su schema esistente; nessuna nuova tabella referente.
- **`ComuneListino` + `listino.is_default`** — mappatura città→listino e fallback già modellati; il catch-all globale del lead è il referente attivo del listino default (nessun cambio schema).
- **Motori `estimation`/`dettaglio_pro` (Decimal puro, anti-leak, range)** — leggono i coefficienti che l'admin editerà; l'effetto immediato sulle nuove stime è automatico se l'edit scrive sulle stesse tabelle sorgente.

### Established Patterns
- **Anti-leak a campi chiusi** verso i non-admin (schemi Pydantic che non espongono coefficiente_impresa/base_eur_mq) — da preservare in tutte le nuove risposte lead/admin esposte ai client non-admin; l'admin è l'unica eccezione (D-10).
- **Snapshot immutabile** (`stima_salvata`, Fase 2 D-09) — pattern da replicare per lo snapshot copiato nel `Lead`, e ragione per cui gli edit admin non toccano le stime salvate.
- **Seed idempotente + migrazioni che preservano il seed** (guardrail D-12 Fase 3) — vincolo bloccante per ogni edit/upload admin.

### Integration Points
- Nuovo router lead (POST contatto, loggato) + nuovo router/estensione admin (CRUD listini/coefficienti/città/testi/referenti + dashboard lead) sotto `require_admin`.
- Nuova migrazione Alembic dalla 0005 per: modello `Lead` (+stato/nota), tabella testi key/value; eventuali colonne di supporto. Deve preservare il seed (D-24).
- Frontend: nuova area `/admin` (tab/sidebar) + form CTA contatto agganciata alle schermate risultato Free/Pro; nuovi client API in `frontend/src/api/`.
</code_context>

<specifics>
## Specific Ideas

- Upload → "l'upload gestisce tutto ma poi l'admin può fare editing" (upload bulk + form CRUD di ritocco): vale sia per prezzi/voci sia per città/mappature.
- Preview del diff prima di applicare l'upload, con elenco esplicito degli scarti (righe KO), per rispettare il guardrail anti-azzeramento.
- Testi/disclaimer in tabella key/value con seed dai testi hardcoded attuali — il backend deve smettere di leggerli da costanti.
</specifics>

<deferred>
## Deferred Ideas

- **Contatto anonimo (senza login)** — considerato ma escluso da v1 (roadmap: lead da utente loggato Free/Pro). Eventuale abbassamento dell'attrito in v2.
- **Versioning/audit trail dei listini** — valutato in D-11; non obbligatorio in v1 (a discrezione se leggero), altrimenti candidato a fase futura.
- **Pagamento reale abbonamento Pro** — resta stub (Fase 3), fuori scope.
- **Portale completo rete professionisti** (assegnazione lead, gestione partner, multi-referente attivo simultaneo) — visione futura; v1 resta a un referente attivo per città.
- **Moltiplicatori-prezzo per zona geografica** — v2, servono i dati.
</deferred>

---

*Phase: 4-lead-pannello-admin*
*Context gathered: 2026-08-27*
