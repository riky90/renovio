# Phase 08: Export/import Excel dal pannello admin - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-21
**Phase:** 08-export-import-excel
**Areas discussed:** Formato del round-trip, Come si cancella un valore, Export sensibile e
tracciamento, Anteprima admin della stima (PAR-04), Formato delle risorse gerarchiche,
Pagina CRUD del catalogo domande, Collocazione nel pannello

---

## Formato del round-trip

**Che formato ha il file che l'admin scarica per curare voci e listino?**

| Option | Description | Selected |
|--------|-------------|----------|
| Piatto, una riga per voce | Colonne esplicite; l'import lo riconosce dall'header, `parse_computo` resta intatto per i file del computo | ✓ |
| Imita il computo originale | Fogli A-EDILE + cataloghi B/C/D; round-trip garantito per costruzione ma formato scomodo da curare | |
| Due export distinti | Uno "computo" e uno "curatela"; massima flessibilita', due formati da tenere allineati | |

**Un workbook unico o un file per risorsa?**

| Option | Description | Selected |
|--------|-------------|----------|
| Un file per risorsa | Quattro export separati; permessi e traccia per endpoint | ✓ |
| Un workbook unico multi-foglio | Un download solo; permessi per-foglio, e margine e dati personali nello stesso file | |

**Una riga aggiunta a mano nel file, al re-import?**

| Option | Description | Selected |
|--------|-------------|----------|
| Crea la voce nuova | Upsert pieno; l'Excel aggiunge, non solo corregge | ✓ |
| Scarta e segnala nella preview | Piu' prudente; per aggiungere si torna al CRUD web | |
| Decidi tu | | |

**Come si protegge il round-trip quando l'admin corregge una descrizione?**

| Option | Description | Selected |
|--------|-------------|----------|
| Colonna id tecnica in testa | Sola lettura, chiave del re-import, fallback sulla chiave naturale quando manca | ✓ |
| Descrizione non modificabile da Excel | Chiave naturale intatta, ma toglie dalla curatela il campo piu' letto | |
| Decidi tu | | |

**Notes:** la domanda nasce da un fatto misurato nel codice, non da un'ipotesi: `_voce_key`
(`listino_upload_service.py:82`) ricade su `descrizione` per le voci senza `codice`, quindi
senza colonna id una correzione testuale avrebbe prodotto una riga doppia.

---

## Come si cancella un valore

**Nel file di export, la cella vuota cosa significa al re-import?**

| Option | Description | Selected |
|--------|-------------|----------|
| Vuoto = non toccare, token per cancellare | Coerente con D-24 Fase 4; costo: una convenzione da documentare | ✓ |
| Vuoto = cancella, colonna assente = non toccare | CUR-02 alla lettera e istinto Excel; ma un export ripulito azzera in silenzio | |
| Decidi tu | | |

**Come si elimina una voce dal listino?**

| Option | Description | Selected |
|--------|-------------|----------|
| Non da Excel, solo dal CRUD web | Import additivo e aggiornante, mai distruttivo | ✓ |
| Colonna `azione` con `elimina` | Eliminazione esplicita riga per riga, contata nella preview | |
| Riga assente dal file = eliminata | Il file diventa la verita' completa; un export parziale cancella il resto | |

**Cosa succede se si ricarica un file esportato prima di modifiche fatte dal pannello?**

| Option | Description | Selected |
|--------|-------------|----------|
| Timestamp nell'export, la preview avvisa | L'admin vede riga per riga cosa e' cambiato dopo, poi decide | ✓ |
| Nessun controllo, ultimo che scrive vince | Accettabile con un admin solo, ma il modello multi-referente esiste dal giorno 1 | |
| Blocco duro | Sicuro, ma ogni modifica concorrente costa un giro completo | |

**Come si dimostra CUR-02?**

| Option | Description | Selected |
|--------|-------------|----------|
| Round-trip a vuoto + test esistenti | Esporta, ricarica identico, diff = zero righe modificate | ✓ |
| Estendere il test su `livello` | Meno lavoro, ma copre un campo solo | |
| Decidi tu | | |

---

## Export sensibile e tracciamento

**L'export dei coefficienti contiene il `coefficiente_impresa` sempre o solo su richiesta?**

| Option | Description | Selected |
|--------|-------------|----------|
| Opt-in esplicito | Di default senza margine; la variante marcata admin-only e' su richiesta | ✓ |
| Sempre incluso, file sempre marcato | Un export solo, ma ogni download diventa riservato | |
| Decidi tu | | |

**Il ruolo `consulente` puo' scaricare l'export dei lead?**

| Option | Description | Selected |
|--------|-------------|----------|
| Si', con traccia di chi ha scaricato | Coerente col fatto che vede gia' la dashboard lead | ✓ |
| No, solo admin | Piu' restrittivo; portarsi via un file resta gesto da admin | |
| Decidi tu | | |

**Dove finisce la traccia di chi scarica e quando?**

| Option | Description | Selected |
|--------|-------------|----------|
| Tabella `export_log` per tutti e quattro | Chi, cosa, quando, quante righe, se includeva il margine | ✓ |
| `export_log` solo per i lead | CUR-04 alla lettera; il file col margine resta senza traccia | |
| Solo log applicativo | Zero migrazioni, ma su Render ruota e la domanda resta senza risposta | |

**La traccia si vede nel pannello?**

| Option | Description | Selected |
|--------|-------------|----------|
| No, per ora solo nel database | CUR-04 chiede di tracciare, non di mostrare | |
| Si', lista in fondo alla dashboard lead | Chi guarda i lead vede anche chi se li e' portati via | ✓ |
| Decidi tu | | |

---

## Anteprima admin della stima (PAR-04)

**Scoperta prima di chiedere:** `POST /admin/domande/anteprima` esiste gia' ed e' completo —
breakdown per categoria, lista effetti con `applicato` e `contributo`, avvisi, `require_admin`.
PAR-04 si riduce alla pagina React. Le domande sotto riguardano quindi solo il frontend.

**Dove vive la pagina di anteprima?**

| Option | Description | Selected |
|--------|-------------|----------|
| Tab dentro `/admin/coefficienti` | Lo strumento accanto ai numeri che serve a verificare; sesta tab | ✓ |
| Pagina nuova `/admin/anteprima` | Piu' visibile, ma separa lo strumento dai dati | |
| Decidi tu | | |

**L'anteprima gira su input inventati o su una stima reale?**

| Option | Description | Selected |
|--------|-------------|----------|
| Input sintetici a mano | La forma di `AnteprimaIn`; serve poter provare il caso limite | ✓ |
| Carica una stima gia' salvata | Aderente alla realta', ma vincola ai casi gia' avvenuti | |
| Entrambi | Copre tutto, lavoro in piu' su una fase gia' larga | |

**Cosa si vede della lista effetti?**

| Option | Description | Selected |
|--------|-------------|----------|
| Tutti, con `applicato` si'/no | L'effetto che non spara e' l'informazione che serve per tarare | ✓ |
| Solo quelli applicati | Tabella piu' corta, ma si torna a diagnosticare per differenza | |
| Decidi tu | | |

**La pagina CRUD del catalogo domande entra nella Fase 08?**

| Option | Description | Selected |
|--------|-------------|----------|
| No, resta fuori (raccomandata) | I requisiti della fase sono CUR-01..04 e PAR-04; il chip resta per la sua fase | |
| Si', Excel e pagina CRUD insieme | Chiude il chip e la violazione della regola #3 in un colpo | ✓ |
| Decidi tu | | |

**Notes:** raccomandazione contraria posta esplicitamente ("e' il punto in cui il
plan-checker consigliera' di spezzare") e respinta. Decisione di Riccardo, registrata in
CONTEXT.md come D-21 con il rischio annotato e l'indicazione di quale parte scorporare se la
fase risultasse troppo larga.

---

## Formato delle risorse gerarchiche

**Come si appiattisce il catalogo domande, gerarchico su cinque tabelle?**

| Option | Description | Selected |
|--------|-------------|----------|
| Un foglio per tabella, stesso file | Rispecchia il database; le chiavi restano chiare | ✓ |
| Un foglio unico denormalizzato | Leggibile a colpo d'occhio, ma re-import ambiguo alla prima divergenza | |
| Ibrido: domande+opzioni / effetti | Due fogli, ma attese e derivazioni restano senza posto | |

**`derivazione_risposta` entra nell'export?**

| Option | Description | Selected |
|--------|-------------|----------|
| Si', foglio suo | L'Excel diventa l'unico modo per curarla, meglio di nessun modo | ✓ |
| No, prima servono gli endpoint | Coerente, ma lascia scoperta una tabella che influenza il calcolo | |
| Decidi tu | | |

**Il file "coefficienti + arredo" — quanti fogli?**

| Option | Description | Selected |
|--------|-------------|----------|
| Un foglio per tabella | moltiplicatori, listino_categoria, extra, coefficienti_pro, forfait_arredo | ✓ |
| Due file separati | L'arredo e' a se'; ma D-02 ha gia' fissato quattro risorse | |
| Decidi tu | | |

**Le `attese` stanno col catalogo domande o coi parametri?**

| Option | Description | Selected |
|--------|-------------|----------|
| Col catalogo domande | `attesa_immobile.attributo_code` si lega a `domanda.attributo_code` | ✓ |
| Coi parametri del motore | Sono numeri di taratura come i coefficienti | |
| Decidi tu | | |

---

## Pagina CRUD del catalogo domande

**Quali delle cinque tabelle copre la pagina?**

| Option | Description | Selected |
|--------|-------------|----------|
| Domande + opzioni + effetti | Le tre che si curano in un gesto solo | ✓ |
| Tutte e cinque | Chiude la regola #3 per intero, ma cinque entita' su una fase gia' larga | |
| Solo domande + opzioni | Gli effetti resterebbero solo su Excel, dove si sbaglia piu' facilmente il target | |

**Forma dell'editing?**

| Option | Description | Selected |
|--------|-------------|----------|
| Riusa `AdminTable` + `AdminCrudDialog` | Pattern delle altre otto pagine admin, nessun componente nuovo | ✓ |
| Editing inline nella tabella | Piu' veloce per correzioni a raffica, ma pattern nuovo da costruire | |
| Decidi tu | | |

**Come si arriva agli effetti di una singola opzione?**

| Option | Description | Selected |
|--------|-------------|----------|
| Master-detail annidato | Rende impossibile creare un effetto orfano | ✓ |
| Tre tabelle piatte con filtri | Stessa forma dei fogli, ma si filtra a mano su un id surrogato | |
| Decidi tu | | |

**Cosa fa il bottone elimina su una domanda gia' usata in produzione?**

| Option | Description | Selected |
|--------|-------------|----------|
| Solo `attiva = false`, mai delete fisico | Le stime salvate che la citano restano leggibili | ✓ |
| Delete fisico se non referenziata | Richiede una verifica sugli snapshot che puo' dare falsi negativi | |
| Decidi tu | | |

---

## Collocazione nel pannello

**Dove stanno i bottoni scarica/carica?**

| Option | Description | Selected |
|--------|-------------|----------|
| Su ogni pagina admin esistente | Il file sta dove stanno i dati; il permesso della pagina e' gia' quello giusto | ✓ |
| Una sezione `/admin/dati` unica | Piu' scopribile, ma separa il file dai dati e dalla traccia dei download | |
| Decidi tu | | |

---

## Claude's Discretion

Nessuna domanda e' stata girata a "decidi tu": tutte e ventisei le decisioni sono state
prese da Riccardo. Gli spazi lasciati al planner sono elencati in CONTEXT.md sotto
*Claude's Discretion* e riguardano forma e nomi, non scelte di visione: schema di
`export_log`, nomi delle colonne dei fogli, forma del token di cancellazione e del
timestamp, come l'import distingue i due formati, destino dell'upload listino esistente,
layout dei form, ed eventuale split della fase in piu' piani.

## Deferred Ideas

- Pagina CRUD per `attesa_immobile` e `derivazione_risposta` — curabili solo da Excel.
- Eliminazione di righe da Excel — scartata, resta nel CRUD web.
- Anteprima precompilata da una stima salvata — scartata a favore dei soli input sintetici.
- Blocco duro sul re-import di un file stale — scartato a favore dell'avviso in preview.
- Export dei lead filtrato per citta' del consulente — capability nuova, non esiste il legame.
