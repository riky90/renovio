# Nota di sessione — 2026-10-30 — taratura sui computi reali (TAR-01)

Sessione cloud su `claude/great-wozniak-1ysani`, partita da `HANDOVER.md`. Il branch era fermo
a `5bd42d0`, prima del merge della PR #4 e del commit con i computi reali: l'ho portato in
avanti su `main` (`1effb73`, solo avanzamento). Risultati e tabelle: `README.md` in questa
cartella.

## Cosa ho fatto, in ordine

1. **Letto l'handover e la proposta** (`docs/proposta-computo-parametrico.md`, in particolare
   §7 e Appendice A) e il motore (`backend/app/services/computo.py`). Ho poi letto
   `seed-computo.json`: 87 grandezze, 192 regole, 33 preset.
2. **Ispezionato i quattro xlsx**: riepilogo, A-EDILE e fogli B/C/D. Ho trovato quattro cose:
   - i file 2025-26 hanno ancora lo smaltimento come `A.9.5`;
   - il tecnico riscrive alcune righe con lavori suoi (porte, caldaia, nicchie, detentori);
   - nel caso 01 i totali di B e C sono a corpo nel riepilogo;
   - nel caso 03 la quantità della movimentazione è scritta a parole ("T").
3. **Scritto `backend/scripts/estrai_casi_reali.py`**: produce
   `backend/tests/fixtures/casi_reali/caso-0N.json`.
   - Riusa la macchina a stati del seed per i codici, e li verifica sulla descrizione.
   - Riconosce B/C/D per descrizione e prezzo.
   - Non legge le colonne impresa.
4. **Dedotto gli input del wizard** per ogni caso dalle quantità e scritto la motivazione di
   ogni deduzione nella fixture: m², piano, bagni, locali, porte, muri, e le risposte alle
   domande d'intervento.
5. **Scritto `backend/scripts/confronta_casi_reali.py`**: confronta il motore con il computo
   per categoria, voce per voce (anche a prezzi del file) e sul range. Produce il report
   Markdown, e lo riusano i test.
6. **Prima misura con la bozza.** L'edile era già nell'ordine giusto: +16%, +2%, +21%, 0%.
   Però voce per voce c'era una sovrastima sistematica della tinteggiatura, in tutti e quattro
   i casi: 2-8 k€ a cantiere. Nei casi 02 e 04 copriva voci sottostimate.
7. **Tarato i dati** in `seed-computo.json`, con la migrazione `0029_taratura_casi_reali.py`
   per i DB già seminati:
   - tinteggiatura;
   - fondo e rasatura;
   - battiscopa;
   - punti acqua;
   - linee idriche a corpo;
   - impermeabilizzazione;
   - montaggio sanitari;
   - lampadari e foro cappa a 0.

   Ho cambiato solo valori con almeno due casi concordi. Nessuna riga di codice del motore.
8. **Non tarato**, perché sono punti aperti del §7 (si segnalano, non si tarano via):
   - A.9.1;
   - A.9.2;
   - A.0.18.

   Ho calcolato a parte uno scenario con i valori che i dati suggeriscono, per la decisione.
9. **Casi d'oro** in `backend/tests/test_casi_reali.py`:
   - soglia ±15% sull'edile;
   - totale reale nel range;
   - voci obbligatorie col bagno rifatto;
   - andata e ritorno della 0029, che non tocca una regola curata dall'admin;
   - nessun dato impresa nelle fixture.
10. **Rigenerato `frontend/src/data/guide-costi.json`** da un DB seminato col seed tarato.
    Aggiornati i numeri di riferimento in `docs/proposta-computo-parametrico.md` §10,
    `docs/stato-progetto.md` e `.planning/STATE.md`, e il test di testa delle migrazioni
    (`0029`).

## Findings principali

1. **Il motore regge.**
   - Dopo la taratura l'edile sta entro ±12% sui tre appartamenti: 0%, −9%, −12%.
   - Il negozio sta a +2%.
   - L'errore voce per voce scende del 29% (110 → 78 k€ sommati sui quattro casi).
2. **La tinteggiatura era la sovrastima più grossa.** Il tecnico usa una sola voce (A.11.3,
   ~6,5-8 €/m²) per pareti e soffitti, circa 3,2 m² per m² calpestabile. Il motore metteva
   pareti a parte con la lavabile a 10 €/m², più fondo su tutto e rasatura gonfiata
   dall'intonaco nuovo.
3. **Le assistenze murarie e la movimentazione** sono le voci che oggi tengono il motore
   sotto il reale nei lavori totali. Il tecnico le scrive a corpo:
   - A.9.1 al 39-45% degli impianti;
   - A.9.2 al 47-55% dell'elettrico;
   - movimentazione circa 2.000 € al primo piano, cioè il 10-12% di A.6 × (piano + 1).

   Con A.9.1 al 40%, A.9.2 al 45% e A.0.18 al 12% (minimo 100 €), tutti e quattro i casi
   cadono nel range e l'edile sta entro ±8%. **Serve la conferma del tecnico.**
4. **Prezzi del listino diversi dai computi**:
   - massetto 40 contro 30 €/m² in tutti i casi;
   - punto elettrico 65 contro 47-60 €;
   - sicurezza e allestimento molto variabili.

   È un tema di listino, non di motore.
5. **Domande che mancano**, emerse dai casi:
   - bagno nuovo o rifatto;
   - clima con sola predisposizione;
   - bagno cieco;
   - carta da parati;
   - nicchie e varchi;
   - impermeabilizzazione grande o terrazzo;
   - porte fornite fuori contratto.

   Spiegano quasi tutto lo scarto residuo dei casi 02 e 04.
6. **Il caso 02 resta fuori range del 2%.** È un parziale, con range ±10%, e pesano circa
   2.100 € di lavori a corpo non chiesti. Il test è `xfail(strict=True)`. Lo scenario del
   punto 3 lo farebbe rientrare. In generale, ±10% sulla leggera è stretto per lavori
   parziali, che hanno più voci a corpo.
7. **IVA dei serramenti**: i computi reali la calcolano al 10%, l'app al 22%. Da chiarire.

## Domande per Riccardo (e per il tecnico)

1. **Confermi le deduzioni** delle fixture? Le più incerte:
   - caso 02: 55 m² calpestabili;
   - caso 01: 3 bagni e 6 locali;
   - caso 04: 230 m² e porte fuori contratto.

   Se una è sbagliata, la si corregge nella fixture (`input`) e si rilancia
   `confronta_casi_reali.py`.
2. **A.9.1 / A.9.2 / A.0.18**: si passa ai valori dello scenario (40% / 45% / 12% con minimo
   100 €), o il tecnico ha un'altra regola?
3. **IVA C-SERRAMENTI**: 10% come nei computi o 22% come nell'app?
4. **Listino**: si aggiornano massetto ed elettrico ai prezzi 2025-26?
5. **Range della leggera**: ±10% o di più?
6. Quali delle **domande mancanti** del punto 5 entrano nel wizard, e quali solo nel Pro?

## Stato

- TAR-01 è fatto in prima passata e **resta aperto** finché non arrivano le conferme sopra.
  La fase 11 non è chiusa.
- Il commit è sul branch `claude/great-wozniak-1ysani`. Nessuna PR aperta: non è stata chiesta
  in questa sessione.
- Dopo il merge su `renovio` va allineato `stima` (`CLAUDE.md`). La migrazione `0029` gira al
  deploy e cambia i numeri mostrati agli utenti: Free/Pro dell'85 m² totale da 69,3 a 65,6 k€
  imponibili.
