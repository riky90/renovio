---
status: complete
phase: 09-configuratore-pro
requirement: WIZ-04
source: [09-08-PLAN.md, 09-14-PLAN.md]
started: 2026-09-28T00:00:00Z
updated: 2026-10-01T00:00:00Z
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

## Ri-collaudo gap G1..G4

Chiusura codice+dati dei quattro gap sopra (piano 09-09..09-14). `dev.db` e'
a `0023 (head)` (backup `backend/dev.db.bak-pre-0023-20260928-191114` prima
della migrazione). Qui sotto i controlli automatici del 09-14 Task 3 e la
checklist per il tuo ri-collaudo dal vivo: le caselle restano vuote, le
spunti tu.

### Controlli automatici (script usa-e-getta su una COPIA di dev.db)

Computo Pro reale, Reggio Emilia, 85 m², tipo "totale", finitura "medio",
per ognuna delle 7 opzioni di `tipo_pavimento` lette dal DB (non una lista
scritta a mano):

| Opzione | A.6 (codici presenti) | Battiscopa | Levigatura marmo | Levigatura parquet | Posa rivestimenti | Fornitura gres a pavimento | B-FINITURE > PAVIMENTI |
|---|---|---|---|---|---|---|---|
| gres | A.6.1, A.6.3, A.6.8, A.6.11 | 1 (ceramica) | assente | assente | 1 | 1 | 0 voci (il gres vive in PAVIMENTI E RIVESTIMENTI GRES, non in PAVIMENTI) |
| parquet | A.6.1, A.6.2, A.6.3, A.6.7, A.6.10, A.6.11 | 1 (legno) | assente | presente | 1 | 1 (quota bagno) | 0 voci (parquet vive in PAVIMENTI PARQUET: 1 voce) |
| maxi_lastra | A.6.1, A.6.3, A.6.5, A.6.8, A.6.11 | 1 (ceramica) | assente | assente | 1 | 1 (quota bagno) | 1 voce (maxi lastra) |
| mosaico | A.6.1, A.6.3, A.6.6, A.6.8, A.6.11 | 1 (ceramica) | assente | assente | 1 | 1 (quota bagno) | 1 voce (tesserine mosaico) |
| laminato | A.6.1, A.6.2, A.6.3, A.6.7, A.6.11 | 1 (legno) | assente | assente | 1 | 1 (quota bagno) | 2 voci (laminato + sottofondo Unilin) |
| vinilico_lvt | A.6.1, A.6.2, A.6.3, A.6.7, A.6.11 | 1 (legno) | assente | assente | 1 | 1 (quota bagno) | 1 voce (vinilico LVT) |
| moquette | A.6.1, A.6.3, A.6.7, A.6.11 | 1 (legno) | assente | assente | 1 | 1 (quota bagno) | 1 voce (moquette) |

Esito: nessuna doppia posa, nessuna doppia battiscopa, levigatura marmo mai
presente, levigatura parquet solo con parquet, posa rivestimenti sempre 1
(A.6.3, finitura medio — A.6.4 e' la sua alternativa per Lusso, non sommata),
LVT/laminato/sottofondo/moquette entrano solo con la loro opzione. A.6.1
compare anche con maxi_lastra/mosaico/parquet/laminato/vinilico: e' la posa
condivisa che copre la quota bagno a gres (D-02) insieme alla posa dedicata
del pavimento scelto per il resto della casa — non un doppione, sono due
zone diverse. Con moquette resta solo A.6.1 (decisione di Claude: nessuna
posa dedicata, vedi sotto). A.6.11 (taglio porta blindata) compare sempre:
e' un difetto di taratura gia' noto (`09-TARATURA-TODO.md`), non un
sintomo di G1/G2 — non corretto qui.

Anti-leak: `VoceEstimata`/`SottocategoriaEstimata`/`CategoriaDettagliata`
(le dataclass che il servizio restituisce) non hanno nessun campo
`impresa`/`coefficiente`/`effett` per costruzione (verificato leggendo
`app/services/dettaglio_pro.py`); la suite completa (sotto) include
`test_no_leak.py` su tutte le route Pro coinvolte.

### Gate

| Controllo | Esito |
|---|---|
| `alembic current` su `dev.db` | `0023 (head)` |
| `scripts/seed.py` su `dev.db` dopo la migrazione | create-if-missing: 0 righe nuove (374 effetti e 7 opzioni `tipo_pavimento` invariati prima/dopo) |
| Suite backend completa (`pytest -q`) | vedi riga aggiunta a questa tabella subito dopo l'esecuzione, sotto |
| `npm run build` | verde |
| `npm run lint` | verde (solo warning preesistenti `react(set-state-in-effect)`/`react(only-export-components)`, nessun errore) |

### Checklist per te

- [ ] G1. Apri il dettaglio Pro con pavimento Gres. Atteso: in B-FINITURE >
  PAVIMENTI non c'e' ne' LVT ne' laminato ne' sottofondo ne' moquette; in
  PAVIMENTI E RIVESTIMENTI GRES una sola fornitura a pavimento.
  Note:
- [ ] G1. Scegli Laminato. Atteso: compaiono laminato + sottofondo Unilin,
  la posa A.6.2 e il battiscopa legno; spariscono parquet e la fornitura
  gres a pavimento (resta solo la quota bagno).
  Note:
- [ ] G1. Scegli Vinilico LVT, poi Moquette. Atteso: ciascuno entra solo
  con la sua opzione, mai insieme agli altri.
  Note:
- [ ] G2. Con Gres in A.6. Atteso: un solo battiscopa (ceramica), nessuna
  levigatura, una sola posa rivestimenti.
  Note:
- [ ] G2. Con Parquet in A.6. Atteso: battiscopa legno e levigatura
  parquet; mai levigatura marmo.
  Note:
- [ ] G3. Dalla home, fai una stima rapida e premi "Vai alla stima Pro".
  Atteso: il wizard si apre sullo step "Le finiture" con i tuoi dati e il
  pavimento selezionabile (non un modulo vergine).
  Note:
- [ ] G3. Nel dettaglio Pro il pavimento si vede e si cambia senza premere
  "Modifica". Atteso: il computo si aggiorna subito al cambio.
  Note:
- [ ] G3. Da "Le mie stime", premi "Rifai in versione Pro". Atteso: apre il
  wizard Pro gia' compilato con i dati di quella stima.
  Note:
- [ ] G4. Vai su /admin/domande > una domanda > "Opzioni ed effetti" >
  un'opzione > "Effetti (n)" > "Aggiungi effetto". Atteso: il comando e'
  visibile senza cercarlo.
  Note:
- [ ] G4. In Listini, Coefficienti e Bonus, apri "Modifica" (anche il nuovo
  "Modifica listino"). Atteso: il dialog mostra tutte le colonne della
  tabella, modificabili o spiegate in sola lettura.
  Note:
- [ ] Scelta di Claude: battiscopa legno anche con laminato/vinilico/
  moquette (non solo parquet). Confermi o preferisci un battiscopa
  diverso per questi pavimenti?
  Note:
- [ ] Scelta di Claude: la moquette non ha una posa dedicata, usa A.6.1 a
  quantita' piena (nessuna riduzione per la quota bagno). Confermi?
  Note:
- [ ] Scelta di Claude: la posa rivestimenti A.6.3 vale per Entry/Medio e
  A.6.4 per Lusso. Confermi questa divisione?
  Note:
- [ ] Scelta di Claude: la fornitura gres a pavimento che resta per ogni
  livello di finitura e' la prima per id fra quelle del listino (non
  necessariamente la piu' economica o la piu' rappresentativa). Ti sta
  bene, o vuoi indicare tu quale voce tenere per livello?
  Note:
- [ ] Scelta di Claude: il sottofondo Unilin compare solo con il
  laminato (non con vinilico o altri pavimenti). Confermi?
  Note:

**Voci invariate del collaudo precedente, ancora aperte** (richiamate qui
senza duplicarne il testo, vedi checklist originale sopra): voce 12 (PDF
solo verificabile in produzione, limite GTK3/Windows), voce 13
(plausibilita' dei totali, rimandata da te), voce 14 (riapertura da "Le mie
stime", non eseguita).

**Nota fuori dai gap** (osservata durante la pianificazione, non corretta
qui): A.6.11 "Taglio porta blindata" (um `ac`) esce con quantita' 72,25
perche' ha il coefficiente per m² invece che a conteggio — e' un difetto di
taratura (`09-TARATURA-TODO.md`), non un'alternativa sommata: segnalato,
non corretto in questo piano.

## Esito ri-collaudo 2026-09-29

Ri-collaudo di Riccardo sulla checklist
`.planning/checklists/2026-09-29-ricollaudo-09.md` (22 voci: G1..G4, fix della
review CR-01/WR-07, scelte del planner, voci residue del 28/09).

- **G1, G2, G3, G4: passati.** Le due domande nelle note (gres a 7,14 m² con
  parquet; posa battiscopa con LVT/moquette) sono comportamenti voluti: quota
  bagno D-02 e battiscopa legno A.6.7.
- **CR-01 e WR-07: passati** (switch predefinito bloccato, rinomina di RE con
  riavvio pulito, cambio pavimento con rollback offline).
- **Voce 15:** "Aggiungi listino" falliva con 422 (POST senza body, difetto
  presente dalla 04-08). Corretto in `4e4b50a`, ripetuta: passa.
- **Scelte del planner:** tutte e cinque confermate (battiscopa legno con
  laminato/vinilico/moquette, moquette su A.6.1, A.6.3 Entry/Medio e A.6.4
  Lusso, fornitura gres con id piu' basso per livello, sottofondo Unilin solo
  con laminato).
- **Voce 14 del 28/09** (riapertura da "Le mie stime"): passata.
- **Ancora aperte:** voce 12 del 28/09 (PDF, solo in produzione) e voce 13
  (plausibilita' dei totali, rinviata da Riccardo a fine Fase 10).

Stato: gap G1..G4 chiusi e approvati dal vivo.

## Collaudo WIZ-04 del 2026-10-01

Percorso Pro end-to-end dal vivo dopo i fix dell'audit della milestone (M2 `4d44e3c`, M1
`1f43856`), checklist `.planning/checklists/2026-10-01-collaudo-wiz-04.md`: voci 1-14
**approvate da Riccardo** senza note (finiture del wizard Alte/Economiche/Medie riportate sul
dettaglio Pro, modifiche nel dettaglio, riapertura da "Le mie stime", anti-leak, plausibilita'
Pro contro Free, che chiude anche la voce 13 del 28/09). WIZ-04 e' chiuso.

Il PDF Pro (voci 15-18 della checklist, voce 12 del 28/09) non si puo' generare su questa
macchina e resta da provare al go-live su Render.
