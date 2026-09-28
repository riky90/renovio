---
status: pending
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

- [ ] 1. Accedi su http://localhost:5173 con il tuo account Pro. Atteso: badge Pro visibile.
  Note:
- [ ] 2. Crea una NUOVA stima dal wizard (Reggio Emilia, 85 m2, totale). Atteso: il wizard e' identico a prima, nessuna domanda "pavimento" o "livello di finitura" nuova nello step 4.
  Note:
- [ ] 3. Apri il dettaglio Pro della stima appena creata. Atteso: il computo si vede subito, con il riepilogo o il pannello che mostra finitura media e pavimento gres gia' applicati.
  Note:
- [ ] 4. In A.6 PAVIMENTI E RIVESTIMENTI. Atteso: una sola posa di pavimento (gres), non quattro.
  Note:
- [ ] 5. In B-FINITURE, sottocategorie gres, parquet, pavimenti, battiscopa. Atteso: una sola alternativa per famiglia, niente parquet se il pavimento e' gres.
  Note:
- [ ] 6. In RUBINETTERIE, PORTE, PRODOTTI. Atteso: niente sanitari doppi (a terra + sospeso), niente porte o condizionatori alternativi sommati.
  Note:
- [ ] 7. Apri il pannello, scegli pavimento "Parquet" e premi "Calcola il dettaglio". Atteso: in A.6 compare la posa parquet, le forniture parquet compaiono in B, il gres del bagno resta (D-02).
  Note:
- [ ] 8. Cambia la finitura di B-FINITURE in "Lusso" e ricalcola. Atteso: nel gres entrano le voci alto al posto delle medio; il totale cambia nella direzione giusta.
  Note:
- [ ] 9. Porta i bagni a 2 con lo stepper e ricalcola. Atteso: le voci del bagno raddoppiano la quantita'; nessun messaggio "Inserisci un numero valido".
  Note:
- [ ] 10. Riepilogo collassato. Atteso: "Bagni: 2 · Porte: n · Climatizzatori: n · Pavimento: Parquet" e sotto le finiture per categoria.
  Note:
- [ ] 11. "Salta, usa la stima automatica". Atteso: si torna ai default (gres, finitura media, quantita' sui m2), non a zero bagni.
  Note:
- [ ] 12. Scarica il PDF dettagliato. Atteso: stesse voci e stessi totali della schermata, riga del pavimento scelto nel riepilogo.
  Note:
- [ ] 13. Plausibilita': confronta il totale Pro con la stima Free della stessa casa. Atteso: ordine di grandezza credibile per te (nessuna soglia imposta da test, D-05).
  Note:
- [ ] 14. Riapri la stima da "Le mie stime". Atteso: stesse scelte e stesso computo.
  Note:
- [ ] 15. Strumenti sviluppatore > Rete: apri la risposta JSON del dettaglio. Atteso: nessuna chiave con "impresa", "coefficiente", "effett".
  Note:
- [ ] 16. Apri /admin/domande. Atteso: vedi "Livello di finitura" e "Che pavimento vuoi per casa?" con i loro effetti; in /admin/dettaglio-pro il livello della voce e' in sola lettura con il rimando.
  Note:

## Esito

(da compilare da Riccardo: approvato / note)
