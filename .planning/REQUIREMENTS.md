# Requirements — ristruttura-stima

## v1 Requirements

### Autenticazione (AUTH)
- [x] **AUTH-01**: L'utente può registrarsi con email e password
- [x] **AUTH-02**: L'utente può accedere con Google (OAuth)
- [x] **AUTH-03**: L'utente resta autenticato tra le sessioni e può fare logout
- [x] **AUTH-04**: Esiste un ruolo admin distinto dall'utente finale

### Input & Stima (EST)
- [x] **EST-01**: L'utente inserisce città, mq e tipo di ristrutturazione (leggera/moderata/totale)
- [x] **EST-02**: Il sistema calcola una stima Free con i 4 totali di categoria (Edile, Finiture, Serramenti/Porte, Prodotti) come range min–max
- [x] **EST-03**: La stima applica l'IVA differenziata per categoria (Edile 10%, Finiture 22%, Serramenti, Prodotti 10%)
- [x] **EST-04**: La stima include i costi extra (CSE/CSP, pratiche amministrative) nel totale
- [x] **EST-05**: L'utente vede solo il prezzo cliente; il prezzo/coefficiente impresa non è mai esposto
- [x] **EST-06**: Se la città non ha un listino proprio, il sistema usa il listino più vicino e mostra un disclaimer

### Motore parametrico (ENG)
- [x] **ENG-01**: Motore Ibrido C: coefficienti €/m² per categoria (Free) e quantità-per-m² sulle voci-chiave (Pro), per ciascun tipo di ristrutturazione
- [x] **ENG-02**: I coefficienti e i prezzi sono letti da database, non cablati nel codice
- [x] **ENG-03**: Bozza iniziale dei coefficienti estratta dal file computo (listino Reggio Emilia)

### Pro & Monetizzazione (PRO)
- [ ] **PRO-01**: L'utente Pro vede l'apertura per sottocategorie (a.1/a.2…) con voci e quantità stimate
- [x] **PRO-02**: Il dettaglio sottocategorie è dietro paywall (abbonamento Pro)
- [x] **PRO-03**: Gestione dell'abbonamento (attivazione/stato Pro sull'account)

### PDF (PDF)
- [x] **PDF-01**: L'utente Free può scaricare un PDF sintetico brandizzato della stima
- [ ] **PDF-02**: L'utente Pro può scaricare un PDF dettagliato brandizzato con le sottocategorie

### Lead & Contatto (LEAD)
- [ ] **LEAD-01**: Da ogni livello (Free e Pro) l'utente può richiedere il contatto di un professionista
- [ ] **LEAD-02**: Il lead (dati utente + stima) arriva via email e viene salvato nella dashboard admin
- [ ] **LEAD-03**: Il modello dati supporta più referenti per città (v1 con un unico referente configurato)

### Admin (ADM)
- [ ] **ADM-01**: L'admin gestisce i listini prezzi per città (voci, prezzi unitari, coefficiente impresa)
- [ ] **ADM-02**: L'admin gestisce i coefficienti parametrici del modello di stima
- [ ] **ADM-03**: L'admin gestisce città, mappatura città→listino, tipi di ristrutturazione e testi/disclaimer
- [ ] **ADM-04**: L'admin consulta i lead ricevuti e configura i referenti per città

## v2 / Deferred Requirements
- Moltiplicatori prezzo per zona geografica (fase 2, richiede dati)
- Portale rete professionisti (assegnazione lead, onboarding partner)
- Prezzo abbonamento Pro definito e integrazione pagamenti completa

## Out of Scope
- **Simulazione finanziamento a rate** — presente nel file ma escluso da v1 (variabili di credito)
- **Prezzi differenziati per zona** in v1 — la città seleziona il listino, non un moltiplicatore
- **Gestione multi-partner completa** — solo modello dati predisposto, non l'operatività

## Traceability

| Requisiti | Fase |
|-----------|------|
| EST-01..06, ENG-01..03 | 1 — Stima Free end-to-end |
| AUTH-01..04, PDF-01 | 2 — Account & PDF |
| PRO-01..03, PDF-02 | 3 — Pro & sottocategorie |
| LEAD-01..03, ADM-01..04 | 4 — Lead & pannello admin |

Copertura: 21/21 requisiti v1 mappati.
