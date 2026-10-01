# Retrospective — ristruttura-stima

## Milestone: v2.0 — domande e motore parametrico

**Completata:** 2026-10-01 (non ancora in produzione)
**Phases:** 7 | **Plans:** 53 | **Commits:** 350 | **Timeline:** 11 giorni (2026-09-21 → 2026-10-01)

### What Was Built

- Catalogo domande/opzioni/effetti in database, motore Free parametrico identico alla v1 senza risposte.
- Wizard unico Free/Pro a quattro step, forfait arredo e Bonus Mobili.
- Export/import Excel a round-trip zero per listini, parametri, lead e catalogo domande; pagina `/admin/domande`.
- Configuratore Pro su finitura e pavimento, senza alternative sommate.
- Risultato leggibile e budget dichiarato, sul web e nei PDF.

### What Worked

- Gli oracoli numerici (85 m², totale, RE → 47.985–70.575 €) hanno tenuto fermo il motore Free
  attraverso sette fasi di cambiamenti.
- Un test che *conta* le voci per famiglia (CFG-02) ha chiuso il bug delle alternative sommate
  in modo verificabile, invece che a occhio.
- Il collaudo dal vivo di Riccardo con checklist e note per voce ha trovato difetti che la suite
  non vedeva: G1-G4 nella 09, G1-G15 nella 10.
- L'audit di milestone ha trovato due major cross-fase (M1, M2) che le verifiche per fase non
  potevano vedere.

### What Was Inefficient

- La Fase 10 e' passata da 9 a 24 piani: tre giri di gap closure, quasi tutti nati dal collaudo
  dal vivo. Molti gap erano di presentazione (cifre della barra, posizione del Bonus Mobili)
  e si sarebbero potuti fissare nel UI-SPEC.
- Le fasi 05-06 sono state eseguite fuori da GSD e hanno avuto la verifica solo
  retroattivamente.
- Push rimandato a fine milestone: 350 commit e undici migrazioni arrivano in produzione in
  un colpo solo.
- La suite completa e' passata da 11 a circa 40 minuti: le verifiche complete costano.
- `STATE.md` riscritto male dall'SDK piu' volte (contatori), corretto a mano ogni volta.
- Il PDF non si genera su questa macchina Windows (WeasyPrint/GTK3): ogni verifica dei PDF
  slitta al go-live.

### Patterns Established

- Effetti del catalogo come unico canale fra risposte e motore, per Free e Pro.
- Disattivare invece di cancellare per tutto cio' che una stima salvata puo' citare.
- Checklist di collaudo in `.planning/checklists/`, con casella e riga `Note:` per voce.
- Audit di milestone prima della chiusura, con correzione dei major nello stesso giro.

### Key Lessons

- Una domanda chiesta in due tier (`livello_finiture` nel Free, `finitura` nel Pro) deve avere
  un ponte esplicito, altrimenti il percorso Free → Pro perde la scelta (M2).
- Il collaudo visivo va previsto nel piano di fase, non dopo: i gap di presentazione costano un
  ciclo intero ciascuno.
- Pushare piu' spesso: il go-live di una milestone intera e' il passo piu' rischioso rimasto.

### Cost Observations

- Sessioni lunghe (125-150 turni) ricorrenti; esecutori interrotti due volte dal limite
  settimanale.
- Worktree GSD inutilizzabili su questo repo (niente `.venv`/`node_modules`): esecuzione
  sequenziale.

## Cross-Milestone Trends

| Milestone | Fasi | Piani | Giorni | Gap closure | In produzione |
|-----------|------|-------|--------|-------------|---------------|
| v1.0 | 4 | 30 | 6 (+ deploy al 2026-09-09) | — | si' |
| v2.0 | 7 | 53 | 11 | 09: 6 piani, 10: 15 piani | push in attesa |
