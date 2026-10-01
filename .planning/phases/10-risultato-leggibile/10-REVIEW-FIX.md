---
phase: 10-risultato-leggibile
fixed_at: 2026-10-01T00:00:00Z
review_path: .planning/phases/10-risultato-leggibile/10-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Fase 10: report delle correzioni dalla code review

**Data correzioni:** 2026-10-01
**Review di origine:** .planning/phases/10-risultato-leggibile/10-REVIEW.md
**Iterazione:** 1

**Riepilogo:**
- Finding in scope: 4 (WR-01, WR-03, WR-05, WR-06, scelti dall'utente)
- Corretti: 4
- Saltati: 0 in scope. WR-02, WR-04 e IN-01..IN-07 erano fuori scope, vedi sotto.

## Finding corretti

### WR-06: `input.mq` / `input.citta` non validati nel payload salvato

**File modificati:** `backend/app/schemas/stima.py`, `backend/app/schemas/stima_salvata.py`, `backend/tests/test_stime_salvate.py`
**Commit:** 37bd9d9
**Correzione:** nuovo schema di ingresso `StimaInputSalvataIn(StimaInputEcho)` con gli stessi vincoli di `StimaRequest` (`citta` da 1 a 100 caratteri, `mq` tra 1 e 2000). Lo usa `StimaSalvataCreate.input`, quindi vale sia per POST che per PUT `/me/stime`: un input non valido riceve 422 e la riga resta com'era. `StimaInputEcho` resta permissivo, perché serve a rileggere gli snapshot storici. I test parametrizzati coprono mq 0, negativo, 2001 e 2^31, oltre a città vuota e città di 101 caratteri, sul PUT, e mq 0 sul POST.

### WR-05: "Rata annua (10 anni)" cablato nel PDF Free

**File modificati:** `backend/app/services/pdf_service.py`, `backend/app/templates/pdf_stima.html`, `backend/tests/test_pdf.py`
**Commit:** e4dd19d
**Correzione:** la nuova funzione `_etichetta_rata` ricava l'etichetta dal campo `rate_annuali` delle voci bonus sui lavori. Con una sola durata scrive "Rata annua (N anni)". Con durate diverse scrive "Rata annua (primi N anni)", dove N è la durata più breve: la rata aggregata è la somma delle rate solo finché sono tutte attive. Sugli snapshot che non hanno il dato scrive solo "Rata annua". Ogni riga bonus, sia lavori sia arredo, riporta anche "in N rate annue", come fa `ArredoCard` sul web. La classe `TestPdfDurataRate` contiene 4 test nuovi.

### WR-01: PUT concorrenti sulla stessa stima, vince l'ultimo che arriva

**File modificati:** `frontend/src/pages/EstimatePage.tsx`, `frontend/src/lib/richiestaStima.ts`, `frontend/scripts/check-richiesta-stima.ts`
**Commit:** 3f82ea2
**Stato:** corretto, da verificare a mano (logica a stati)
**Correzione:** i PUT ora partono uno alla volta lato client. Il ref `putInVolo` viene messo a `true` in modo sincrono prima di `updateMutation.mutate` e torna `false` nell'`onSettled` dichiarato nelle opzioni di `useMutation`, che scatta anche dopo un `reset()`. Lo stesso `onSettled` incrementa il contatore che fa ripartire l'effetto. Quando `putInVolo` è attivo, `azioneSalvataggio` restituisce `"attendi"`. Alla fine del PUT in corso l'effetto riparte e invia il PUT del risultato attualmente mostrato. Ho aggiunto 3 asserzioni in `check-richiesta-stima.ts`. Lato server non c'è un controllo di versione: con un solo client è la serializzazione a garantire l'ordine.

### WR-03: errori di salvataggio silenziosi, CTA Pro bloccata, budget non persistito

**File modificati:** `frontend/src/pages/EstimatePage.tsx`, `frontend/src/components/SoftWallCta.tsx`
**Commit:** 4ed2acc
**Stato:** corretto, da verificare a mano (logica a stati)
**Correzione:**
1. Se il POST di auto-save o il PUT falliscono, compare un `Alert` con il pulsante "Riprova a salvare". Il pulsante ripete la stessa operazione (PUT sulla stima in modifica, altrimenti POST) con il risultato mostrato a schermo e il budget attuale.
2. `SoftWallCta` riceve la nuova prop `saveFailed`. Quando è attiva, il bottone Pro mostra "Stima non salvata" al posto di "Salvataggio in corso…" senza fine. `isSaving` ora copre anche l'attesa del PUT precedente introdotta con WR-01.
3. Se la PATCH del budget lanciata dall'effetto fallisce, l'errore non viene più ignorato: compare un `Alert` "Non siamo riusciti a salvare il budget nella stima salvata." con il pulsante "Riprova".
4. Scelta consapevole: **non** ho applicato il ripiego `idSalvato ?? ultimoSalvataggio?.id` proposto dalla review. Dopo un PUT fallito, lo snapshot salvato non coincide con ciò che l'utente vede, quindi PDF e dettaglio Pro restano disabilitati finché il salvataggio non riesce (invariante D-09). La review lasciava aperta questa scelta.

## Finding saltati (fuori scope per scelta dell'utente)

### WR-02: dopo il primo "Modifica" ogni ricalcolo sovrascrive la stima salvata

**File:** `frontend/src/pages/EstimatePage.tsx:105-109`
**Motivo:** è il comportamento voluto. La regola G14, approvata dall'utente, prevede che "Modifica" aggiorni sempre la stima salvata.
**Problema originale:** non esiste un percorso "salva come nuova" e la stima salvata viene sostituita senza conferma.

### WR-04: il PDF Pro non riporta bonus né arredo

**File:** `backend/app/templates/pdf_stima_pro.html:526-601`
**Motivo:** rimandato al backlog (bonus/arredo nel PDF Pro).
**Problema originale:** la schermata Pro mostra `BonusPanel` e `ArredoCard`, ma il PDF Pro li omette.

### IN-01 – IN-07

**Motivo:** i finding Info sono esclusi dallo scope scelto dall'utente.

## Verifiche eseguite

- Backend (`backend/.venv/Scripts/python.exe -m pytest`), tutti verdi:
  - `test_stime_salvate.py` e `test_stima_tier.py`: 43 passati, 1 saltato.
  - `test_pdf.py`, `test_no_leak.py`, `test_pdf_pro.py`, `test_dettaglio_pro_budget.py` e `test_dettaglio_pro_bonus.py`: verdi dopo WR-06.
  - `test_pdf.py`, `test_no_leak.py` e `test_pdf_pro.py`: 44 passati, 4 saltati dopo WR-05.
- Frontend:
  - `npx tsc -b`: OK.
  - `npm run lint`: exit 0, con gli stessi 16 warning già presenti nel ramo base.
  - `node scripts/check-richiesta-stima.ts`: OK.

---

_Data: 2026-10-01_
_Fixer: Claude (gsd-code-fixer)_
_Iterazione: 1_

## Conferma di Riccardo (2026-10-01)

Collaudo manuale di WR-01 e WR-03 eseguito da Riccardo: passa. Confermata la scelta su WR-03:
dopo un salvataggio fallito PDF e dettaglio Pro restano disabilitati finche' "Riprova a salvare"
non riesce (lo snapshot salvato deve coincidere con lo schermo, D-09).
