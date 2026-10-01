# Collaudo WIZ-04 — percorso Pro dal vivo (2026-10-01)

Scopo: chiudere WIZ-04, l'unico requisito rimasto aperto nell'audit della milestone v2.0
(`.planning/v2.0-MILESTONE-AUDIT.md`, `status: gaps_found`). Si percorre il Pro end-to-end
partendo dal wizard, e si verificano dal vivo i due fix dell'audit:

- **M2** (`4d44e3c`): il livello scelto nel wizard ("Che livello di finiture hai in mente?")
  guida l'asse finitura del dettaglio Pro. Prima chi sceglieva "Alte" vedeva il totale alto
  e il dettaglio Pro al default "Medio".
- **M1** (`1f43856`): il PDF Pro contiene detrazioni e blocco arredo come il PDF Free.
  **Differito al go-live**: WeasyPrint/GTK3 non c'e' su questa macchina, il PDF si prova su
  Render (sezione in fondo).

Corrispondenza dei livelli (stessi codici sulle due domande):

| Wizard (`livello_finiture`) | Dettaglio Pro (`finitura`) |
|---|---|
| Economiche | Entry level |
| Medie | Medio (default) |
| Alte | Lusso |

## Come si avvia

Backend e frontend sono gia' attivi:

- Frontend: http://localhost:5173
- Backend: http://127.0.0.1:8000 (controllo: http://127.0.0.1:8000/api/v1/health/db)

Se servisse riavviarli:

```
cd backend && .venv/Scripts/python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
cd frontend && npm run dev
```

- Serve l'account Pro (abbonamento attivo).
- Per vedere la card Arredo serve il bonus MOBILI acceso (pannello admin Bonus) e almeno due
  ambienti da arredare nel wizard.
- Usa stime **nuove**: quelle salvate prima del 2026-10-01 non hanno il ponte M2.
- I coefficienti sono ancora la bozza accettata: conta la direzione dei totali, non il valore.

Spunta `[x]` e scrivi nella riga `Note:` cosa hai visto (obbligatorio se non torna). Non
correggere al volo: le voci fallite diventano un piano di gap closure.

## Avvio

- [ ] **0. Apri http://localhost:5173 ed entra con l'account Pro** — badge Pro visibile, nessun
  errore in console, nessuna schermata bianca.
  Note:

## A — Percorso principale: finiture Alte → Lusso nel Pro (M2)

- [x ] **1. Nuova stima dal wizard: Reggio Emilia, 85 m², ristrutturazione totale, almeno due
  ambienti da arredare. Alla domanda "Che livello di finiture hai in mente?" scegli "Alte"** —
  il wizard prosegue normalmente fino allo step "Le finiture".
  Note:
- [x ] **2. Step "Le finiture" (Pro)** — in **ogni** categoria la card gia' selezionata e'
  "Lusso", non "Medio". Il pavimento e' selezionabile, di default "Gres".
  Note:
- [ x] **3. Nello stesso step scegli il pavimento "Parquet" e concludi il wizard** — la stima
  viene salvata e si apre il risultato senza errori.
  Note:
- [ x] **4. Apri il dettaglio Pro della stima** — il riepilogo dice "Pavimento: Parquet" e le
  finiture per categoria sono tutte "Lusso".
  Note:
- [x ] **5. Nel computo: A.6 PAVIMENTI E RIVESTIMENTI e PAVIMENTI E RIVESTIMENTI GRES** — posa
  rivestimenti **A.6.4** (quella di Lusso), non A.6.3; posa parquet A.6.2, battiscopa legno
  A.6.7, levigatura parquet A.6.10; nel gres (quota bagno) le voci di livello alto.
  Note:
- [x ] **6. Coerenza col totale del wizard** — il totale del dettaglio Pro e' dello stesso ordine
  del range mostrato dal wizard con finiture "Alte", non visibilmente piu' basso (era il sintomo
  di M2).
  Note:

## B — Modifiche nel dettaglio Pro

- [ x] **7. Cambia una sola categoria da "Lusso" a "Medio" e ricalcola** — cambia solo quella
  categoria, le altre restano Lusso; il totale scende.
  Note:
- [x ] **8. Cambia il pavimento in "Gres" dal pannello, senza premere "Modifica"** — il computo si
  aggiorna subito: sparisce la posa parquet, il battiscopa diventa ceramica (A.6.8), sparisce la
  levigatura parquet.
  Note:
- [x ] **9. Card Arredo e pannello Bonus nel dettaglio Pro** — la card Arredo mostra gli ambienti
  e "Detrazione sull'arredo" con Bonus Mobili a range; il pannello Bonus mostra le detrazioni sui
  lavori a range. Nessun numero secco. (Sono gli stessi blocchi che M1 porta nel PDF Pro.)
  Note:
- [ x] **10. Torna a "Le mie stime" e riapri la stima** — stesse scelte dell'ultima modifica
  (categoria a Medio, pavimento Gres, il resto Lusso) e stesso totale; non ricade sul default.
  Note:

## C — Controprove sugli altri livelli

- [x] **11. Nuova stima uguale alla 1 ma con "Economiche"** — allo step "Le finiture" tutte le
  categorie partono da "Entry level"; nel dettaglio Pro il riepilogo dice Entry level e il totale
  e' sotto quello della stima "Alte".
  Note:
- [ x] **12. Nuova stima uguale alla 1 ma con "Medie"** — tutte le categorie partono da "Medio",
  come prima dei fix.
  Note:

## D — Sicurezza e plausibilita'

- [ x] **13. Strumenti sviluppatore > Rete: apri la risposta JSON del dettaglio Pro** — nessuna
  chiave che contenga "impresa", "coefficiente" o "effett".
  Note:
- [ x] **14. Plausibilita' (voce 13 del 28/09): confronta il totale Pro della stima "Medie" con
  una stima Free della stessa casa** — ordine di grandezza credibile per te. Nessuna soglia
  imposta: e' un giudizio tuo (D-05).
  Note:

## E — Differito al go-live (Render): PDF Pro (M1)

Da fare dopo il push, su produzione. Restano qui per non perderle.

- [x ] **15. Scarica il PDF dettagliato della stima "Alte" con ambienti da arredare** — stesse voci
  e stessi totali della schermata; riga del pavimento scelto nel riepilogo.
  Note:
- [ x] **16. Nello stesso PDF Pro, blocco detrazioni** — detrazioni sui lavori a range, rata
  annua a range, etichetta della rata come nel PDF Free (WR-05).
  Note:
- [x ] **17. Nello stesso PDF Pro, blocco Arredo** — ambienti e Bonus Mobili dentro il blocco
  Arredo, a range; cifre ai bordi della barra con "fino a" fra le cifre (G13).
  Note:
- [x ] **18. PDF senza prezzo impresa** — nel PDF Free e nel PDF Pro nessun prezzo impresa e
  nessun coefficiente.
  Note:

## Esito

Riccardo, 2026-10-01: "completo e approvato". Voci 1-14 (sezioni A-D) passate senza note:
WIZ-04 e' chiuso e il fix M2 e' verificato dal vivo.

Voci 15-18 (PDF Pro, M1): spuntate nel file, ma su questa macchina il PDF non si puo' generare
(WeasyPrint fallisce all'import: `cannot load library 'libgobject-2.0-0'`, riverificato il
2026-10-01). Restano **differite al go-live su Render**, insieme alla sezione PDF di
`10-HUMAN-UAT.md`. La logica di M1 e' coperta da `backend/tests/test_pdf_pro.py`.
