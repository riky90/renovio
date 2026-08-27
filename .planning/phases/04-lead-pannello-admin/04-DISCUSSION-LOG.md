# Phase 4: Lead & pannello admin - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-27
**Phase:** 4-lead-pannello-admin
**Areas discussed:** Form di contatto lead, Notifica & destinatario lead, CRUD prezzi & coefficienti, Città/testi/referenti, Validazione upload Excel, Conferma utente post-lead, Dashboard lead, Struttura pannello admin, Coefficienti editabili in v1, Referente iniziale & sicurezza upload

---

## Form di contatto lead

**Chi può inviare?**
| Opzione | Selezione |
|--------|----------|
| Aperto a tutti (anche anonimi) | |
| Solo utenti loggati | ✓ |
| Loggati + anonimo con soft-wall | |

**Campi form (multi):** Telefono ✓, Messaggio libero ✓, Preferenza contatto ✓ (scartato: "solo nome+email+telefono")

**Stima allegata:**
| Opzione | Selezione |
|--------|----------|
| Snapshot della stima visualizzata | ✓ |
| Riferimento a stima salvata | |
| Snapshot completo copiato nel lead | (interpretato: lo snapshot visualizzato viene copiato nel lead) |

**Notes:** "Solo loggati" coerente con roadmap criterio #1; "aperto a tutti" = entrambi i livelli, non anonimi.

---

## Notifica & destinatario lead

**Destinatario email:** Referente attivo della città ✓ (scartati: sempre admin; referente+admin in CC)

**Città senza referente:** Referente di default globale ✓ (scartati: fallback all'admin; salva senza email). Realizzato come referente attivo del listino default (nessun cambio schema).

**Contenuto:** Dati utente + riepilogo stima + link ✓ (scartati: solo contatti+link; Claude decide)

---

## CRUD prezzi & coefficienti

**Edit prezzi:** Entrambi (upload bulk + form ritocchi) ✓ (scartati: solo form; solo upload)

**Admin vs anti-leak:** Sì, admin gestisce coefficiente impresa/base, mai esposti ai non-admin ✓ (scartati: nemmeno l'admin li tocca; Claude decide)

**Effetto edit:** Nuove stime subito, snapshot congelati ✓ (scartati: versioning/storico; Claude decide) — versioning non obbligatorio in v1.

---

## Città/testi/referenti

**Città/mappe:** "L'upload gestisce tutto ma poi l'admin può fare editing come nel Form CRUD su ComuneListino + tipi/extra" (ibrido upload + form).

**Testi/disclaimer:** Nuova tabella testi key/value editabile ✓ (scartati: solo disclaimer principali; Claude decide)

**Referenti:** CRUD completo con attivo/priorità ✓ (scartati: form minimo un referente; Claude decide)

---

## Validazione upload Excel

**Flusso:** Preview del diff, poi conferma ✓ (scartati: applica diretto con report; Claude decide)

**Righe KO:** Scarta le KO, importa le valide, elenca gli scarti ✓ (scartati: blocca tutto; Claude decide)

---

## Conferma utente post-lead

**Conferma:** Messaggio a schermo + email di conferma ✓ (scartati: solo messaggio a schermo; Claude decide)

---

## Dashboard lead

**Stato lead:** Sì, nuovo/gestito (+ note) ✓ (scartati: sola lista; Claude decide)

**Vista:** Lista + filtro città/stato + dettaglio con snapshot ✓ (scartati: lista semplice; Claude decide)

---

## Struttura pannello admin

**Struttura UI:** Area /admin con sezioni a tab/sidebar ✓ (scartati: pagine separate; Claude decide)

---

## Coefficienti editabili in v1

**Set (multi):** Moltiplicatori tipo×categoria ✓, base_eur_mq per categoria ✓, Coeff. quantità-per-m² (Pro) ✓, IVA ed extra ✓ (tutti).

---

## Referente iniziale & sicurezza upload

**Scelta:** Referente configurabile da subito (nessun seed pre-fatto); upload solo .xlsx, solo admin, limite dimensione (~10MB) ✓ (scartati: referente = utente pre-seedato; Claude decide)

---

## Claude's Discretion

- Schema esatto del modello `Lead` e della tabella testi key/value.
- Meccanica retry/flag invio email per il lead; audit/versioning listini se leggero.
- Parser upload Excel e forma esatta della preview del diff.
- Layout preciso delle sezioni/form admin (inline vs modale).
- Set esatto di chiavi testi e valori di seed.

## Deferred Ideas

- Contatto anonimo senza login (v2).
- Versioning/audit trail listini (opzionale/futuro).
- Pagamento reale abbonamento Pro (stub, fuori scope).
- Portale completo rete professionisti (multi-referente attivo simultaneo).
- Moltiplicatori-prezzo per zona geografica (v2).
