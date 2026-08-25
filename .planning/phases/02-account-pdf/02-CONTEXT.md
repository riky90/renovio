# Phase 2: Account & PDF - Context

**Gathered:** 2026-08-25
**Status:** Ready for planning

<domain>
## Phase Boundary

L'utente si **registra/accede** (email+password e Google OAuth), la **sessione persiste** con logout, le sue **stime vengono salvate** e associate all'account (con storico), esiste un **ruolo admin** distinto dall'utente finale, e l'utente può **scaricare un PDF Free brandizzato** della propria stima.

**In scope:** AUTH-01 (registrazione email/password), AUTH-02 (login Google), AUTH-03 (sessione persistente + logout), AUTH-04 (ruolo admin distinto), PDF-01 (PDF Free sintetico brandizzato). Introduce le tabelle net-new `user` e `stima` (stima salvata/snapshot) — **oggi non esistono**; le 8 tabelle attuali sono tutte di dominio listino/catalogo.

**Non include:** apertura sottocategorie Pro + paywall + PDF dettagliato (Fase 3); invio lead / contatto professionista + pannello admin CRUD su listini/coefficienti/città/referenti/testi (Fase 4). In Fase 2 il **ruolo** admin esiste e protegge le route, ma **non c'è UI admin** (arriva in Fase 4). Le CTA "Passa a Pro" e "Contatta un professionista" restano soft-wall/rimando.
</domain>

<decisions>
## Implementation Decisions

### Strategia auth & sessione (AUTH-01/02/03/04)
- **D-01:** **Auth self-hosted nel backend FastAPI.** Tabella `user` nel Postgres del progetto. Password con hashing forte (bcrypt/argon2), Google OAuth via Authlib. Motivo: tutti i dati (utenti, stime, futuri lead/referenti di Fase 4) in un solo DB, nessun lock-in né costo, controllo totale sull'invariante anti-leak impresa. Niente provider gestito (Supabase/Auth0/Clerk).
- **D-02:** **Sessione via cookie httpOnly** (JWT o session id in cookie httpOnly + SameSite), invisibile al JS del frontend. Immune al furto via XSS, logout server-side pulito, il frontend non maneggia token. Standard per SPA + API sullo stesso deploy/dominio.
- **D-03:** **Ruolo su `user`** con valori `user` / `admin` (AUTH-04). Il **primo admin** è promosso via **seed o variabile d'ambiente** (es. `ADMIN_EMAIL`). In Fase 2 il ruolo esiste e le route riservate sono protette; **nessuna interfaccia admin** ancora (Fase 4).
- **D-04:** **Verifica email: NO in v1** (attrito minimo alla registrazione). **Reset password: SÌ via link email.** Serve un'utility di **email transazionale** già in Fase 2 (SMTP/provider) — sarà riusata dai lead in Fase 4. Motivo: senza reset, una password dimenticata = account bloccato, e Google non è un percorso di recupero garantito.
- **D-05:** **Un solo account per email** (l'email è la chiave identità). Se la stessa email arriva sia da password sia da "Accedi con Google", **confluisce nello stesso account** (l'email di Google è già verificata da Google), con possibilità di aggiungere la password in seguito. Nessun doppione, nessun blocco.
- **D-06:** **Campi registrazione:** email + password + **nome**. Il nome serve al PDF brandizzato e al lead (Fase 4); chiederlo ora evita una migrazione dopo. (Un campo `nome`, eventuale cognome opzionale.)

### Salvataggio stima ↔ account (onora D-10 della Fase 1)
- **D-07:** **Salva-al-signup della stima corrente.** L'utente fa la stima da anonimo (tenuta nel browser); quando si registra/accede da una CTA soft-wall, **quella stima viene salvata e associata** al nuovo account. Poi, da loggato, ogni nuova stima si salva **automaticamente**. Nessuna persistenza anonima con "reclamo" successivo, nessuna riga anonima da gestire/pulire.

### Storico stime & snapshot (data model `stima`)
- **D-08:** **Storico "Le mie stime":** ogni stima salvata resta in una **lista consultabile** (città, mq, tipo, data, totale). Basso costo, utile per rientrare su una stima, e la Fase 3 (upgrade Pro su una stima) ci si appoggia.
- **D-09:** **Snapshot — numeri congelati.** Al salvataggio si congelano **input + risultato completo** (i 4 range di categoria, totale, IVA, disclaimer/fallback) come snapshot immutabile. Una stima salvata **non cambia mai**, anche quando l'admin aggiornerà i listini (Fase 4): è riproducibile, difendibile legalmente e **coerente col PDF scaricato**. Si conservano **anche gli input** per un eventuale ricalcolo Pro esplicito.

### PDF Free (PDF-01)
- **D-10:** **Gate: solo utente loggato.** Il PDF è dietro l'account, coerente con la soft-wall già scelta in Fase 1 (D-09/D-10): "Scarica PDF" è una delle ragioni per registrarsi e rafforza il funnel. Da anonimo la CTA porta alla registrazione, poi il download.
- **D-11:** **Generazione server-side** (FastAPI, es. WeasyPrint/reportlab) a partire dallo **snapshot salvato**. Anti-leak garantito lato server (mai coefficiente/prezzo impresa nel PDF), branding coerente, e **stesso motore riusabile** per il PDF dettagliato Pro (Fase 3). Niente generazione client-side.
- **D-12:** **Contenuto PDF (1 pagina):** intestazione con branding + nome utente; riepilogo input (città, mq, tipo); le 4 card di categoria a range; totale IVA inclusa; disclaimer (incl. disclaimer fallback città se attivo); data della stima + nota "stima indicativa". Nome file tipo `stima-ristrutturazione-<citta>-<data>.pdf`. **Mai** dati impresa.

### Regole di dominio (portate avanti — non ri-discusse)
- **D-13:** L'invariante anti-leak vale anche qui: `coefficiente_impresa`/`base_eur_mq`/moltiplicatori/`prezzo_impresa` restano server-side e **non compaiono** in risposta API, nello snapshot esposto al client, né nel PDF.
- **D-14:** L'output resta **sempre a range** (categorie e totale), anche nello snapshot e nel PDF.

### Claude's Discretion
- Scelta esatta della libreria auth/OAuth (Authlib vs alternative), della libreria PDF (WeasyPrint vs reportlab vs template HTML→PDF) e del provider email transazionale — delegata a researcher/planner, purché rispetti D-01..D-12.
- Struttura precisa dello snapshot (colonne dedicate vs JSON) e schema di `user`/`stima`, purché: snapshot immutabile, storico per utente, anti-leak, e predisposizione all'upgrade Pro (Fase 3) e ai lead (Fase 4).
- Asset di branding del PDF (logo/colori): base = palette **Slate / blue-600** già definita in `01-UI-SPEC.md`; placeholder logo accettabile se non fornito.
- Meccanica UI del gate soft-wall → registrazione → download (modale vs pagina), coerente con `SoftWallCta` esistente.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Dominio e decisioni di progetto
- `CLAUDE.md` — regole di dominio non negoziabili (prezzo/coefficiente impresa mai esposto, output a range, città = listino, IVA differenziata).
- `.planning/PROJECT.md` — Core Value, Key Decisions, scope.
- `.planning/REQUIREMENTS.md` — requisiti v1; Fase 2 = AUTH-01..04, PDF-01.
- `.planning/ROADMAP.md` — confini e success criteria della Fase 2.
- `.planning/phases/01-stima-free-end-to-end/01-CONTEXT.md` — decisioni Fase 1, in particolare **D-09/D-10** (soft-wall: stima anonima; account per salvare/PDF/contattare; salvataggio automatico alla registrazione) su cui questa fase si innesta.

### Codice esistente da integrare
- `backend/app/routers/stima.py`, `backend/app/schemas/stima.py`, `backend/app/services/estimation.py` — l'endpoint/risultato Free da cui nasce lo snapshot da salvare (rispettare gli schemi anti-leak già in essere).
- `backend/app/models/` — 8 modelli di dominio esistenti (nessun `User`/`Stima`); `backend/alembic/versions/0001_initial_schema.py` — schema di partenza per la nuova migrazione.
- `backend/app/limiter.py`, `backend/app/db.py`, `backend/app/config.py` — pattern condivisi (rate limit, sessione DB, config) da riusare per auth.
- `frontend/src/api/stima.ts`, `frontend/src/api/client.ts` — confine API + normalizzazione Decimal→number; `frontend/src/components/SoftWallCta.tsx`, `frontend/src/pages/EstimatePage.tsx` — punti in cui innestare login/registrazione, salvataggio e download PDF.
- `01-UI-SPEC.md` (in `.planning/phases/01-stima-free-end-to-end/`) — palette e token UI (Slate/blue-600) per il branding di form auth e PDF.

### Dati sorgente
- `docs/computo-base-reggio-emilia.xlsx` — listino RE (rilevante indirettamente: lo snapshot congela i risultati calcolati da questo listino).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Stack e pattern backend già in piedi:** FastAPI + SQLAlchemy 2.0 + Alembic, sessione DB in `db.py`, config in `config.py`, rate limit condiviso in `limiter.py`. Auth si aggancia a questi.
- **Endpoint stima Free** (`routers/stima.py` + `schemas/stima.py`): produce già il risultato anti-leak; lo snapshot da salvare deriva da qui senza ricalcolare in modo diverso.
- **Frontend:** react-query + `api/client.ts` (confine API), `SoftWallCta.tsx` ed `EstimatePage.tsx` come punti d'innesto per auth, salvataggio e download.

### Established Patterns
- **Anti-leak con schemi a campi chiusi** (mai `model_validate` su entità ORM verso il client) — da replicare per user/stima e per il payload del PDF.
- **Decimal puro** per tutti i valori monetari; serializzati come stringhe e normalizzati al confine API — lo snapshot deve preservare questa fedeltà.
- **Nessun router né auth guard esistente** oltre a health/stima: la dependency di autenticazione (cookie → user corrente) e il guard admin sono net-new.

### Integration Points
- Nuove tabelle `user` e `stima` + nuova migrazione Alembic sopra `0001_initial_schema`.
- `stima` va progettata per essere **estesa in Fase 3** (upgrade Pro sullo stesso record/snapshot) e **collegata ai lead in Fase 4**; `user.role` è il gancio del futuro pannello admin (Fase 4).
- Utility email transazionale (per reset password) net-new, riusata dai lead in Fase 4.

</code_context>

<specifics>
## Specific Ideas

- Il salvataggio "cattura il momento di massima intenzione": la stima appena vista viene salvata **all'atto** della registrazione dalla CTA soft-wall, non richiesta a parte.
- Lo snapshot deve combaciare 1:1 col PDF scaricato (stesso dato congelato), così un PDF resta valido nel tempo indipendentemente dagli aggiornamenti di listino.
- Login Google e password devono convergere sullo stesso account quando l'email coincide (Google email fidata).

</specifics>

<deferred>
## Deferred Ideas

- **Apertura sottocategorie Pro + paywall + PDF dettagliato** → Fase 3 (lo snapshot conserva gli input proprio per abilitare l'upgrade Pro).
- **Invio lead / contatto professionista + pannello admin CRUD** (listini, coefficienti, città, referenti, testi) → Fase 4. Qui nascono solo il **ruolo** admin e l'utility email (riusata dai lead).
- **Verifica email obbligatoria** → eventuale hardening post-v1 (in v1 esclusa per attrito).
- **Gestione pagamenti / prezzo abbonamento Pro** → Fase 3 / post-v1.
- **Moltiplicatori prezzo per zona geografica** → fase di prodotto post-v1.

### Reviewed Todos (not folded)
Nessun todo pendente incrociato con questa fase.

</deferred>

---

*Phase: 2-Account & PDF*
*Context gathered: 2026-08-25*
