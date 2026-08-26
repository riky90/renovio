# Struttura del computo di dettaglio (fonte del motore Pro)

> Riferimento estratto da `docs/computo-base-reggio-emilia.xlsx`
> (identico a `2025_Computo Base_ER_PREZZI IMPRESE DEFINITI (2).xlsx`, 543.287 byte).
> Prezzi = **Reggio Emilia**. Questo file mappa la fonte dati del **motore Pro (Fase 3)**.
> Estratto il 2026-08-26 durante `/gsd-discuss-phase 3`.

## A cosa serve

Il motore **Free** (Fase 1) usa solo `base_eur_mq` a livello di **categoria** (4 valori).
Il motore **Pro** (Fase 3) deve invece ricostruire il **dettaglio per sottocategorie e voci**,
e la sua fonte è **il massimo dettaglio di questo Excel**. Decisione utente (discuss Fase 3):
il Pro **non deve riconciliare** col totale Free — è una misura diversa e **più precisa**.

## Inventario fogli

| Foglio | Ruolo |
|---|---|
| `Analisi preliminareTOTALI` | Totali/IVA per categoria, extra (già usato in Fase 1) |
| `A-EDILE` | **Dettaglio lavorazioni edili** — gerarchia a codici (vedi sotto) |
| `B-FINITURE` | **Catalogo materiali di finitura** — lista piatta a gruppi |
| `C- SERRAMENTI PORTE ` | **Catalogo serramenti/porte** — lista piatta a gruppi |
| `D- PRODOTTI` | **Catalogo prodotti** (condizionatori, caldaie, termo…) — lista piatta |
| `listini` | Coefficienti impresa 0.65/0.6/0.55/0.5 (SEGRETO, mai esposto) |
| `Importi`, `scheda cantiere_*` | Fogli di lavoro interni — non sorgente diretta |

## ⚠️ Due layout diversi (non uniformi tra categorie)

### Famiglia 1 — A-EDILE (gerarchia a codici)
Colonne: `B`=codice · `C`=descrizione · `D`=UM · `E`=**Qta** · `F`=Prezzo Unitario (cliente) · `G`=Totale · `J`=coeff. impresa (0.65).

Gerarchia a 3 livelli:
- **Sezione** (es. `A` = ALLESTIMENTO DI CANTIERE)
- **Sottocategoria** (es. `A.1` = DEMOLIZIONI-RIMOZIONI, `A.2` = MASSETTI…) ← le "sottocategorie a.1/a.2"
- **Voce** (es. `A.1.1` = Demolizione muratura) con UM e prezzo unitario; alcune voci hanno varianti `a/b/c`.

**11 macro-sottocategorie, 91 voci, 111 righe con prezzo:**

| Cod | Sottocategoria | Voci |
|---|---|---|
| A.1 | Demolizioni - Rimozioni - Trasporto | 16 |
| A.2 | Massetti | 5 |
| A.3 | Opere murarie | 8 |
| A.4 | Intonaci | 2 |
| A.5 | Controsoffitti e soppalchi | 4 |
| A.6 | Pavimenti e rivestimenti | 11 |
| A.7 | Impermeabilizzazioni | 2 |
| A.8 | Impianti | 18 |
| A.9 | Assistenza muraria | 6 |
| A.10 | Montaggi e allacci | 13 |
| A.11 | Opere da pittore | 6 |
| A.12 | Sicurezza cantiere | — |

(Più un blocco iniziale `A.1…A.8` di "Allestimento cantiere": rimozioni sanitari, porte, radiatori, ecc.)

### Famiglia 2 — B-FINITURE / C-SERRAMENTI / D-PRODOTTI (cataloghi piatti)
Colonne: `A`=descrizione · `B`=UM · `C`=**Qta** · `D`=Prezzo Unitario · `E`=Totale.
Nessun codice numerico: sono **liste di materiali/prodotti** raggruppate da righe-intestazione
(es. B-FINITURE → "MATERIALI DI FINITURA" → "PAVIMENTI E RIVESTIMENTI" → decine di tipi di gres…).
Qui il "dettaglio Pro" è **scelta prodotto + quantità**, non una struttura a sotto-codici.

## 🔑 Fatto centrale per il motore: le QUANTITÀ sono a 0

In tutti i fogli la colonna Qta è **vuota/0**: nel file la riempie il tecnico per il singolo cantiere.
L'app parte invece da `(città, mq, tipo)`. Quindi il motore Pro deve **stimare le quantità** per voce
in funzione di mq (ed eventualmente del tipo di intervento). I **prezzi unitari esistono già**; mancano
solo le quantità. Da qui la decisione aperta (vedi CONTEXT.md): quantità **chieste all'utente** con
poche domande mirate, oppure **pre-settate da admin** come quantità-per-m², o un ibrido.

## Regole ereditate (non negoziabili)
- Il coefficiente impresa (colonna J / foglio `listini`, 0.65/0.6/0.55/0.5) è **margine interno**:
  mai esposto in API né nel PDF Pro.
- Output sempre a **range**.
- Questi prezzi sono di **Reggio Emilia**. Le altre città verranno caricate dall'admin (Fase 4)
  via **upload Excel** o creazione manuale di voci — stesso schema dati.
