# Handover — taratura del motore sui computi reali

> **Stato (2026-10-30):** eseguito in prima passata. Esito, cosa è stato tarato e domande aperte:
> `.planning/prove/2026-11-taratura/README.md` e `NOTA-SESSIONE-2026-10-30.md`.

**Data:** 2026-10-30 · **Base:** `main` a `c8785a7` + questo commit · **Requisito:** TAR-01
(fase 11, milestone v3.0)

Contesto generale: `docs/stato-progetto.md`. Il motore e le sue regole sono descritti in
`docs/proposta-computo-parametrico.md` (§3 il modello, §6 la precisione, §10 lo stato,
Appendice A la regola di ogni voce di A-EDILE).

## Obiettivo

Verificare il computo parametrico su quattro computi veri e tararlo finché l'errore resta dentro
una soglia. La soglia proposta è **±15% sull'edile** e il totale reale deve cadere dentro il range
min–max mostrato all'utente. Ogni caso diventa un **caso d'oro** nella suite di test, così la
taratura non regredisce.

## I quattro casi

In `docs/casi-reali/`. Sono copie dei computi del tecnico (Reggio Emilia e provincia), con la
stessa struttura di `docs/computo-base-reggio-emilia.xlsx`. Le copie sono **anonimizzate**:
nomi, indirizzi, telefono, email e percorso del file sono sostituiti, e prezzi, quantità e
formule restano intatti. Gli originali restano solo sul PC di Riccardo e non vanno committati.

| File | Lavoro | Data | Totali reali (IVA inclusa) |
|---|---|---|---|
| `caso-01-appartamento-totale-2025-04.xlsx` | Appartamento al primo piano, ristrutturazione totale | 2025-04 | Edile 72.130 · Finiture 15.730 · Serramenti 15.950 · **Totale 103.810** |
| `caso-02-appartamento-parziale-2026-05.xlsx` | Ristrutturazione parziale, appartamento al piano terra (Quattro Castella) | 2026-05 | Edile 18.117 · CSE/CSP 1.512 · **Totale 19.629** |
| `caso-03-negozio-nuovo-bagno-2026-10.xlsx` | Nuovo bagno in un negozio al piano terra (Cavriago) | 2026-10 | Edile 19.866 · CSE/CSP 1.512 · **Totale 21.378** |
| `caso-04-appartamento-edile-2025-05.xlsx` | Appartamento al primo piano, ristrutturazione totale, solo edile | 2025-05 | Edile 92.224 · **Totale 92.224** |

Voci con quantità > 0: caso 01 ha 36 voci A e 8 voci B, caso 02 ha 23 voci A, caso 03 ne ha
29 e caso 04 ne ha 49. B, C e D sono vuoti tranne nel caso 01.

Dove leggere i dati in ogni file:

- **Foglio `Analisi preliminareTOTALI`**: totali per categoria IVA inclusa, extra (CSE/CSP,
  pratiche), descrizione sintetica.
- **Foglio `A-EDILE`**: la riga con intestazioni `DESCRIZIONE | UM | Qta | Prezzo U. | Totale`.
  - Colonne a sinistra: categoria impianto (EDILE, ELETTRICO…) e codice voce (`A.1`, `A.0.3`…).
  - Colonne a destra: note del tecnico ("NOTE (non stampare mai)") e colonne **impresa**.
- **Fogli `B-FINITURE`, `C- SERRAMENTI PORTE  `, `D- PRODOTTI`**: stesso schema. Il nome del
  foglio C ha spazi finali.
- Le celle formula hanno il valore in cache: `openpyxl.load_workbook(..., data_only=True)` legge
  i numeri senza aprire Excel.

## Piano

1. **Estrarre i casi** in fixture versionate, per esempio `backend/tests/fixtures/casi_reali/caso-0N.json`.
   Per ogni voce: codice, UM, quantità, prezzo cliente, totale cliente. Servono anche i totali per
   categoria e gli extra. Lo script di estrazione va in `backend/scripts/`, sul modello di
   `extract_dettaglio_pro.py` e `computo_parsing.py`.
   **Non portare nelle fixture le colonne impresa, il coefficiente o il guadagno** (regola di
   dominio 1).
2. **Ricostruire gli input del wizard** per ogni caso: m², tipo (leggera/moderata/totale) e
   risposte alle 18 domande d'intervento. Nei file i m² non sono scritti, e va dedotto dalle
   quantità: pavimenti in m², tinteggiatura, massetto. Va dedotto anche cosa si fa: bagni,
   cucina, impianti, serramenti.
   Le deduzioni vanno annotate nella fixture e fatte confermare a Riccardo. Una deduzione
   sbagliata qui falsa tutta la taratura.
3. **Confronto voce per voce**: eseguire `computo_free(session, listino, mq=..., tipo=..., risposte=...)`
   (`backend/app/services/computo.py`) su un DB seminato in memoria, come fa la fixture `session`
   di `backend/tests/test_computo.py`. Confrontare con il computo reale:
   - voci presenti in uno solo dei due lati;
   - quantità diverse;
   - totale per categoria.

   La traccia per voce dice da quale grandezza o preset viene ogni quantità.
4. **Report di scarto** in `.planning/prove/2026-11-taratura/`: una tabella per caso con scarto
   per categoria e le 10 voci più lontane, ciascuna con la causa (grandezza sbagliata, preset,
   regola, domanda mancante).
5. **Tarare i dati, non il codice**: valori delle grandezze, preset e regole sono in DB e si
   curano da Excel (scheda "Computo parametrico"), oppure con una migrazione `0029` per il seed.
   Il codice si tocca solo se manca un tipo di regola.
6. **Casi d'oro nella suite**, per esempio `backend/tests/test_casi_reali.py`:
   - ogni caso verifica che lo scarto per categoria sia sotto soglia;
   - verifica che il totale reale cada nel range;
   - verifica le regole "deve essere presente" delle note (bagno rifatto ⇒ A.0.3-10, A.0.11, A.7.1,
     A.8.5, A.10.5).
7. **Chiudere la fase 11**: aggiornare `.planning/STATE.md` (oggi indietro) e il §10 della
   proposta, poi la PR su `riky90/renovio`.

## Attenzione

- **Caso 03 è un negozio**, non un'abitazione: il wizard potrebbe non coprirlo bene. Va tenuto
  come caso di frontiera o escluso dalla soglia, ma la scelta va motivata nel report.
- **Casi 02 e 03 sono interventi parziali**: mettono alla prova i preset "leggera/moderata" e
  le risposte esplicite che vincono sul preset.
- **Date diverse (2025–2026)**: i prezzi unitari possono differire dal listino seminato.
  Confrontare prima le **quantità**, poi gli importi; uno scarto solo di prezzo non è un errore
  del motore.
- **Incoerenze note del file** (proposta §7): il 7% senza etichetta su `(B+C+D)`, A.9.1 30/35%,
  movimentazione A.0.18. Se pesano sullo scarto, vanno segnalate e non "tarate via".
- Domande non ancora nel wizard (muro demolito, doccia/vasca, bagni ciechi, carta da parati): se
  un caso ne dipende, va annotato come domanda mancante e non compensato con un preset.
- **Repo pubblico**: `riky90/renovio` è pubblico. Niente dati personali nei commit, nei report o
  nei nomi file.

## Comandi

```bash
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_computo.py
```

```bash
backend/.venv/Scripts/python.exe -m pytest
```

In una sessione cloud o Linux il percorso è `backend/.venv/bin/python`. Se il virtualenv
manca: `pip install -e .` dentro `backend/` (dipendenze in `backend/pyproject.toml`).

Dopo il merge su `renovio`, allineare `stima` come da `CLAUDE.md`, senza `--force`:

```bash
git push stima renovio/main:main
```
