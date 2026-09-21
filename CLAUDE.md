# ristruttura-stima — Guida progetto

App web di stima costi ristrutturazione. Pianificazione GSD in `.planning/`. Brief fondante in `BRIEF-DISCUSSIONE.md`. Sorgente dati in `docs/computo-base-reggio-emilia.xlsx`.

## Regole di dominio non negoziabili
1. **Mai esporre il prezzo impresa.** Nel computo esistono due prezzi: prezzo cliente (mostrato) e prezzo impresa = prezzo × coefficiente (0.65/0.6/0.55/0.5). Il coefficiente e il prezzo impresa restano server-side, mai inviati al client né nel PDF utente.
2. **Output sempre a range** (min–max), mai un numero secco: è una stima pre-sopralluogo.
3. **Prezzi e coefficienti in database, mai cablati nel codice.** Devono essere modificabili dal pannello admin.
4. **Città = selettore del listino.** I prezzi del file sono di Reggio Emilia. Città senza listino proprio → fallback sul più vicino + disclaimer esplicito.
5. **IVA differenziata per categoria** (Edile 10%, Finiture 22%, Serramenti, Prodotti 10%). Extra (CSE/CSP, pratiche) inclusi; finanziamento a rate escluso da v1.
6. **Modello dati multi-referente per città dal giorno 1**, anche se v1 usa un solo referente.

## Motore di stima (Ibrido C)
- **Free**: costo €/m² per categoria × mq, per tipo (leggera/moderata/totale).
- **Pro**: quantità-per-m² sulle voci-chiave del computo → ricostruisce le sottocategorie a.1/a.2 con voci e quantità stimate.
- Bozza coefficienti da estrarre dal file (listino RE).

## Stato ambiente
GSD è installato e funzionante: `~/.claude/get-shit-done/` contiene workflow, template e
contexts, gli agenti `gsd-*` vivono in `~/.claude/agent-domains/dev/` (agganciato a questa
cartella) e lo shim `gsd-sdk` sul PATH risolve a `~/.claude/gsd-source/bin/gsd-sdk.js`.
I workflow con subagent (`/gsd:plan-phase`, `/gsd:execute-phase`) girano.

La pianificazione di questo progetto è una milestone GSD vera: `.planning/ROADMAP.md`,
`.planning/REQUIREMENTS.md` e `.planning/phases/NN-*/`. Le fasi non ripartono da 01 a ogni
milestone: la v1.0 ha usato 01-04, la v2.0 usa 05-10.

## Ambiente di sviluppo
- Backend: virtualenv in `backend/.venv`. I test si lanciano con
  `backend/.venv/Scripts/python.exe -m pytest` — il `python` di sistema non ha le
  dipendenze. La suite completa impiega ~11 minuti.
- Git: il ramo locale è `master`, il remoto è `main`. Il push è quindi
  `git push origin master:main`, e deploya su Render.
- L'identità git è impostata **per-repo** (`user.email` = account personale): su questo
  PC il default globale è l'email aziendale e Vercel la rifiuta. Mai `--global`.
