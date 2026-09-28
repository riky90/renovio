---
status: diagnosed
phase: 09-configuratore-pro
requirement: WIZ-04
source: [09-08-PLAN.md]
started: 2026-09-28T00:00:00Z
updated: 2026-09-28T00:00:00Z
---

## Stato

Collaudo dal vivo **RINVIATO**: vincolo di Riccardo del 2026-09-26, le fasi 09-10 proseguono
senza aspettarlo. Non e' un gate — nessun esecutore spunta le caselle qui sotto o scrive
"approvato": lo fa solo Riccardo, quando potra'.

I controlli automatici del piano 09-08 (Task 1) sono gia' verdi:

| Controllo | Esito |
|---|---|
| `alembic current` su `dev.db` | `0022 (head)` |
| Suite backend completa | verde |
| Build frontend (`npm run build`) | verde |
| Lint frontend (`npm run lint`) | verde (solo warning preesistenti, nessun errore) |
| `/health` | risponde |
| (a) default: A.6 una sola posa (gres), B-FINITURE max 1 voce/famiglia | verde |
| (b) `tipo_pavimento=parquet`: posa parquet presente, quota bagno gres (D-02) resta | verde |
| (c) bagni=2: quantita' raddoppiata rispetto a bagni=1 | verde |
| (d) nessuna chiave JSON con "impresa"/"coefficiente"/"effett" | verde |
| (e) PDF dettagliato Pro (200, content-type pdf) | SKIP — WeasyPrint/GTK3 non disponibile su questa macchina Windows (limite noto dal piano 02-08, non blocca: la logica e' coperta dai test, i byte si verificano in ambiente con GTK3) |

**Importante per chi giudica il totale**: i coefficienti in uso sono la **bozza accettata**,
non la taratura vera — resta cosi' finche' `09-TARATURA-TODO.md` non e' chiuso con il file
compilato da Riccardo. Il totale Pro va letto sapendolo: l'ordine di grandezza conta, il
valore esatto no (D-05).

## Come si avvia

- Frontend: http://localhost:5173
- Backend: http://127.0.0.1:8000

Comandi per riavviare (da una shell nella root del progetto):

```
cd backend && .venv/Scripts/python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
cd frontend && npm run dev
```

## Se una voce fallisce

Annotala nella riga `Note:` corrispondente. Non correggere al volo: Claude aprira' un piano
di gap closure (`/gsd:plan-phase 09 --gaps`) per le voci segnate come fallite.

## Checklist

- [x ] 1. Accedi su http://localhost:5173 con il tuo account Pro. Atteso: badge Pro visibile.
  Note:
- [X ] 2. Crea una NUOVA stima dal wizard (Reggio Emilia, 85 m2, totale). Atteso: il wizard e' identico a prima, nessuna domanda "pavimento" o "livello di finitura" nuova nello step 4.
  Note:
- [ X] 3. Apri il dettaglio Pro della stima appena creata. Atteso: il computo si vede subito, con il riepilogo o il pannello che mostra finitura media e pavimento gres gia' applicati.
  Note: se io ho fatto la stima non salvata e clicco vai a pro lui mi riporta a un modulo vergine, di default ti confermo media
- [X ] 4. In A.6 PAVIMENTI E RIVESTIMENTI. Atteso: una sola posa di pavimento (gres), non quattro.
  Note: v
- [ X] 5. In B-FINITURE, sottocategorie gres, parquet, pavimenti, battiscopa. Atteso: una sola alternativa per famiglia, niente parquet se il pavimento e' gres.
  Note: vedo una voce paviemnti e rivestimenti gres e paviemnti solo, entrameb nel calclo, non posso segliere da nessuna parte se voglio gres parquet o altro
- [X ] 6. In RUBINETTERIE, PORTE, PRODOTTI. Atteso: niente sanitari doppi (a terra + sospeso), niente porte o condizionatori alternativi sommati.
  Note: 
- [ X] 7. Apri il pannello, scegli pavimento "Parquet" e premi "Calcola il dettaglio". Atteso: in A.6 compare la posa parquet, le forniture parquet compaiono in B, il gres del bagno resta (D-02).
  Note: non trovo il pannello
- [ X] 8. Cambia la finitura di B-FINITURE in "Lusso" e ricalcola. Atteso: nel gres entrano le voci alto al posto delle medio; il totale cambia nella direzione giusta.
  Note:
- [ X] 9. Porta i bagni a 2 con lo stepper e ricalcola. Atteso: le voci del bagno raddoppiano la quantita'; nessun messaggio "Inserisci un numero valido".
  Note:
- [x ] 10. Riepilogo collassato. Atteso: "Bagni: 2 · Porte: n · Climatizzatori: n · Pavimento: Parquet" e sotto le finiture per categoria.
  Note:
- [ X] 11. "Salta, usa la stima automatica". Atteso: si torna ai default (gres, finitura media, quantita' sui m2), non a zero bagni.
  Note:
- [ ] 12. Scarica il PDF dettagliato. Atteso: stesse voci e stessi totali della schermata, riga del pavimento scelto nel riepilogo.
  Note: lo posso testare solo live
- [ ] 13. Plausibilita': confronta il totale Pro con la stima Free della stessa casa. Atteso: ordine di grandezza credibile per te (nessuna soglia imposta da test, D-05).
  Note: da fare piu avanti
- [ ] 14. Riapri la stima da "Le mie stime". Atteso: stesse scelte e stesso computo.
  Note:
- [ X] 15. Strumenti sviluppatore > Rete: apri la risposta JSON del dettaglio. Atteso: nessuna chiave con "impresa", "coefficiente", "effett".
  Note:
- [X ] 16. Apri /admin/domande. Atteso: vedi "Livello di finitura" e "Che pavimento vuoi per casa?" con i loro effetti; in /admin/dettaglio-pro il livello della voce e' in sola lettura con il rimando.
  Note:

## Esito

Collaudo di Riccardo del 2026-09-28: non approvato, quattro gap (sotto). Voce 7 riverificata
da Claude nel browser sulla stima 31: il selettore del pavimento esiste nel pannello del
dettaglio (dietro "Modifica") e il ricalcolo con Parquet funziona; la nota di Riccardo nasce
dal flusso della voce 3 (G3). Voce 12 (PDF) verificabile solo in produzione; voce 13 rinviata
da Riccardo; voce 14 non eseguita. Riportati qui anche gli esiti della checklist
`.planning/checklists/2026-09-25-dialog-e-documentazione.md` (voce 2 → G4; voce 8, "Conferma
import" disabilitato a 0 righe, e' il comportamento voluto).

## Gaps

- truth: "Il computo Pro non somma alternative dello stesso pavimento (CFG-02)"
  status: failed
  reason: "In B-FINITURE > PAVIMENTI entrano sempre vinilico LVT, laminato, sottofondo Unilin e moquette, sommati a gres o parquet: nessun effetto del catalogo li governa."
  severity: major
  test: 5
  fix: "Decisione di Riccardo: nuove opzioni della domanda tipo_pavimento (Laminato, Vinilico LVT, Moquette) con effetti includi sulle rispettive voci e sul sottofondo; fuori dall'opzione scelta non entrano. Estendere famiglie_alternative_pro.json e il test di conteggio a questa sottocategoria."
- truth: "In A.6 entra una sola alternativa per lavorazione legata al pavimento"
  status: failed
  reason: "Con pavimento gres entrano comunque A.6.9 (levigatura marmo) e A.6.10 (levigatura parquet); il battiscopa e' posato due volte, A.6.7 legno e A.6.8 ceramica. Il controllo automatico (a) guardava solo le pose A.6.1/.2/.5/.6."
  severity: major
  test: 4
  fix: "Governare A.6.7/A.6.8/A.6.9/A.6.10 con effetti di tipo_pavimento (legno/levigatura parquet solo con parquet, ceramica con gres/maxi lastra/mosaico, levigatura marmo esclusa di default) e allargare il test di conteggio ad A.6 intera."
- truth: "Il pavimento si sceglie in modo evidente nel percorso Pro"
  status: failed
  reason: "Da una stima non salvata 'vai a Pro' riporta al wizard vuoto; il form Pro del wizard ha i livelli di finitura ma non il pavimento; nel dettaglio il pannello parte chiuso e il pavimento si vede solo dopo 'Modifica'."
  severity: major
  test: 3, 7
- truth: "Gli editor admin espongono tutti i campi modificabili"
  status: failed
  reason: "'Aggiungi effetto' si trova solo aprendo domanda > opzione > Effetti; i dialog di modifica di Listini, Coefficienti e Bonus non mostrano tutte le colonne della tabella."
  severity: minor
  test: "checklist 2026-09-25, voce 2"
