# Requirements — ristruttura-stima

**Milestone attiva:** v3.0 — *computo parametrico*
**Milestone precedenti:** v1.0 (MVP), v2.0 (domande e motore parametrico) — archiviate in `.planning/milestones/`

La v2 risponde a *com'è fatta la casa e cosa vuoi farci*, ma il Pro calcola ogni quantità come
`coefficiente × m²` e il Free si tara a parte in €/m²: per 85 m² · totale il Pro dà 386–579 k€
contro i 48–70 k€ del Free. La v3 traduce in dati il ragionamento del computo Excel (colonne
T/U e note H di `2025_Computo Base_ER_PREZZI IMPRESE DEFINITI (2) (1).xlsx`): grandezze della
casa, interventi scelti, una regola di quantità per voce. Free e Pro diventano lo stesso motore.
Fonte: `docs/proposta-computo-parametrico.md`.

---

## v3 Requirements

### Grandezze (GRD)

- [ ] **GRD-01**: Le grandezze della casa (pavimento, pareti, bagni, punti acqua, punti luce, radiatori…) sono dati in DB, ognuna con un default calcolato in forma chiusa (costante + somma di termini `fattore × sorgente [× grandezza]`, sorgenti `mq`, `tipo_<code>` o altre grandezze), mai formule libere
- [ ] **GRD-02**: Una grandezza si sovrascrive con la risposta numerica della domanda che la porta (`attributo_code`) o con il valore assegnato dall'opzione scelta di una domanda a scelta
- [ ] **GRD-03**: Le grandezze si valutano in ordine di dipendenza; un ciclo è un errore di curatela segnalato, mai un 500

### Regole per voce (RGL)

- [ ] **RGL-01**: Ogni voce ha al massimo una regola di quantità, da un insieme chiuso di sei tipi: `fisso`, `grandezza`, `da_voci`, `percentuale`, `percentuale_per_grandezza`, `scaglioni`
- [ ] **RGL-02**: Una regola può avere una condizione (grandezza > 0) e un importo minimo "a corpo"
- [ ] **RGL-03**: Le regole sono legate al **codice** della voce, non all'id: valgono per ogni listino che usa quei codici. Tutte le voci, anche B/C/D, hanno un codice stabile
- [ ] **RGL-04**: Le voci in percentuale (assistenze, smaltimento, movimentazione) hanno importo calcolato dalle voci sorgente: nessuna voce a prezzo 0 per costruzione
- [ ] **RGL-05**: Una traccia per voce spiega da dove viene la quantità (regola, grandezza o sorgenti, valori)

### Interventi e preset (INT)

- [ ] **INT-01**: Le domande sugli interventi (pavimenti, bagni da rifare, cucina, elettrico, idrico, riscaldamento, clima, controsoffitti, porte, serramenti, caldaia) sono nel wizard **Free**
- [ ] **INT-02**: Il tipo di ristrutturazione è un **preset** delle risposte agli interventi: cambia i default, non scala le quantità
- [ ] **INT-03**: Il catalogo `GET /domande` restituisce i default già risolti per il tipo scelto; il wizard li riapplica alle domande non toccate quando il tipo cambia

### Motore unico (MOT)

- [ ] **MOT-01**: Il Free è il computo sommato per categoria; il Pro lo mostra voce per voce. A parità di input i totali coincidono
- [ ] **MOT-02**: Le correzioni senza voce corrispondente (tipo immobile, epoca, accessibilità, efficientamento, "non rifare") restano effetti di categoria; gli effetti `eur_per_scostamento` e i moltiplicatori sostituiti dalle voci (impianti, livello finiture) si disattivano
- [ ] **MOT-03**: Un listino senza regole ricade sul calcolo €/m² della v1, così una città nuova non resta senza stima
- [ ] **MOT-04**: Nessuna tabella nuova porta il coefficiente impresa; i test anti-leak coprono le nuove route

### Curatela (CUR3)

- [ ] **CUR3-01**: Grandezze, termini, regole, sorgenti, scaglioni, preset e valori-opzione si esportano e reimportano da Excel, con validazione leggibile (driver inesistente, ciclo, voce a corpo con regola al m², percentuale senza sorgenti)

### Taratura (TAR)

- [ ] **TAR-01**: Casi d'oro da computi reali compilati: rimandato finché Riccardo non li ha (decisione 2026-10-21)

## Fuori perimetro v3

- Range per incertezza (banda stretta su quantità risposte): candidato v3.1
- Separazione completa articolo/prezzo in due tabelle: le regole per codice coprono già il secondo listino
