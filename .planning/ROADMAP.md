# Roadmap — ristruttura-stima

**Mode:** Vertical MVP · **Granularity:** coarse · 4 fasi · 21 requisiti v1 mappati (100%)

Ogni fase consegna una capability utente end-to-end. Il valore centrale (stima a range) arriva già in Fase 1.

---

### Phase 1: Stima Free end-to-end

**Goal:** Da (città, mq, tipo) a una stima Free a range con i 4 totali di categoria, IVA ed extra, alimentata da un listino Reggio Emilia in database.
**Mode:** mvp
**UI hint:** yes
**Requirements:** EST-01, EST-02, EST-03, EST-04, EST-05, EST-06, ENG-01, ENG-02, ENG-03
**Success Criteria:**

1. L'utente inserisce città, mq e tipo e ottiene 4 totali di categoria come range min–max in pochi secondi
2. I totali applicano l'IVA differenziata per categoria e includono i costi extra
3. Nessun prezzo/coefficiente impresa è visibile o inviato al client
4. Prezzi e coefficienti provengono dal database (seed listino RE), non dal codice
5. Una città senza listino proprio produce comunque una stima con disclaimer esplicito

**Plans:** 4/4 plans complete
Plans:

- [x] 01-01-PLAN.md — Walking Skeleton: scaffold backend/frontend + schema Alembic + loop health end-to-end (ENG-02)
- [x] 01-02-PLAN.md — Seed idempotente RE + motore di stima Decimal (IVA/categoria, extra, fallback) [TDD] (ENG-01, ENG-03, EST-03, EST-04, EST-06)
- [x] 01-03-PLAN.md — API POST /api/v1/stima + schemi anti-leak + test assenza chiavi impresa (EST-01, EST-02, EST-05, EST-06)
- [x] 01-04-PLAN.md — UI Free: form input + schermata risultato (4 card + totale + disclaimer + CTA soft-wall) (EST-01, EST-02, EST-06)

### Phase 2: Account & PDF

**Goal:** L'utente si registra/accede (email + Google), le sue stime vengono salvate e può scaricare un PDF Free brandizzato.
**Mode:** mvp
**UI hint:** yes
**Requirements:** AUTH-01, AUTH-02, AUTH-03, AUTH-04, PDF-01
**Success Criteria:**

1. L'utente crea un account con email/password e accede anche con Google
2. La sessione persiste e l'utente può fare logout
3. Le stime effettuate restano associate all'account
4. L'utente scarica un PDF sintetico brandizzato della propria stima
5. Esiste un ruolo admin separato dall'utente finale

**Plans:** 9/9 plans complete
Plans:

- [x] 02-01-PLAN.md — Setup dipendenze e configurazione Account & PDF
- [x] 02-02-PLAN.md — Fondazione backend autenticazione (AUTH-01, AUTH-03, AUTH-04)
- [x] 02-03-PLAN.md — Endpoint HTTP auth + guard admin (AUTH-01, AUTH-03, AUTH-04)
- [x] 02-04-PLAN.md — Frontend autenticazione (router, pagine, sessione) (AUTH-01, AUTH-03)
- [x] 02-05-PLAN.md — Login Google (OAuth Authlib) + convergenza account (AUTH-02)
- [x] 02-06-PLAN.md — Recupero password via email (D-04) (AUTH-01)
- [x] 02-07-PLAN.md — Salvataggio stima e storico backend
- [x] 02-08-PLAN.md — PDF Free branded download (PDF-01)
- [x] 02-09-PLAN.md — Save-at-signup, storico, download PDF frontend end-to-end (PDF-01, AUTH-03) — Task 1-2 completi, Task 3 checkpoint human-verify aperto

### Phase 3: Pro & dettaglio sottocategorie

**Status:** ✅ Complete & verified (2026-08-27) — 6/6 plans; 03-VERIFICATION.md 9/9 code-level; human-verify approvato; override PDF (GTK3) concesso come Fase 2
**Goal:** L'utente Pro sblocca l'apertura per sottocategorie (a.1/a.2) con voci e quantità stimate dal motore parametrico, dietro paywall, con PDF dettagliato.
**Mode:** mvp
**UI hint:** yes
**Requirements:** PRO-01, PRO-02, PRO-03, PDF-02
**Success Criteria:**

1. L'utente Pro vede le sottocategorie con voci e quantità stimate; l'utente Free no
2. Il dettaglio Pro è ricostruito bottom-up dalle voci del computo (quantità stimate da mq+tipo): è una stima più precisa e indipendente dal totale Free, non deve riconciliare con esso
3. Il dettaglio è correttamente protetto da paywall in base allo stato Pro dell'account
4. L'utente Pro scarica un PDF dettagliato brandizzato con le sottocategorie

### Phase 4: Lead & pannello admin

**Goal:** Da ogni livello l'utente contatta un professionista (lead via email + dashboard); l'admin gestisce listini, coefficienti, città, referenti e testi senza toccare codice.
**Mode:** mvp
**UI hint:** yes
**Requirements:** LEAD-01, LEAD-02, LEAD-03, ADM-01, ADM-02, ADM-03, ADM-04
**Success Criteria:**

1. Da Free e da Pro l'utente invia una richiesta di contatto con i dati della stima
2. Il lead arriva via email e compare nella dashboard admin
3. L'admin crea/modifica listini prezzi per città e coefficienti del modello, e le stime ne risentono subito
4. L'admin configura i referenti per città (modello multi-referente, un referente attivo in v1)
5. L'admin modifica città, mappature e testi/disclaimer dall'interfaccia

**Plans:** 11 plans
Plans:
**Wave 1**

- [ ] 04-01-PLAN.md — Lead capture backend: modello Lead + migr. 0006 + resolve_referente + POST /lead (LEAD-01/02/03)
- [ ] 04-02-PLAN.md — Admin backend: package + CRUD listino (create città) + categoria + voce prezzo/UM (ADM-01)

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 04-03-PLAN.md — Admin backend: Testo migr. 0007 + disclaimer read-through + CRUD città/testi (ADM-03)
- [ ] 04-04-PLAN.md — Admin backend: dashboard lead (filtri/detail/patch) + CRUD referenti (ADM-04)
- [ ] 04-05-PLAN.md — Admin backend: upload Excel due-passi (destinazione esistente/nuova città) hardened + gate pacchetti (ADM-01)
- [ ] 04-06-PLAN.md — Lead frontend: LeadContactDialog + SoftWallCta reale (LEAD-01)
- [ ] 04-10-PLAN.md — Admin backend: CRUD coefficienti (moltiplicatori/iva/extra/Pro) + effetto immediato (ADM-02)

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 04-07-PLAN.md — Admin frontend: shell /admin + componenti condivisi + rotte + stub pages (ADM-04 fondazione)

**Wave 4** *(blocked on Wave 3 completion)*

- [ ] 04-08-PLAN.md — Admin frontend: CRUD listini/voci + coefficienti + upload Excel UI (esistente/nuova città) (ADM-01/02)
- [ ] 04-09-PLAN.md — Admin frontend: CRUD città/mappature/tipi + testi (ADM-03)
- [ ] 04-11-PLAN.md — Admin frontend: dashboard lead + CRUD referenti (ADM-04)

---

## Traceability

| Requisito | Fase |
|-----------|------|
| AUTH-01..04 | 2 |
| EST-01..06 | 1 |
| ENG-01..03 | 1 |
| PRO-01..03 | 3 |
| PDF-01 | 2 |
| PDF-02 | 3 |
| LEAD-01..03 | 4 |
| ADM-01..04 | 4 |

Tutti i 21 requisiti v1 sono mappati a esattamente una fase.
