# Seed coefficienti €/m² — Listino Reggio Emilia (BOZZA)

> **DRAFT auto-generato** da `docs/computo-base-reggio-emilia.xlsx`. Sono i valori di partenza del motore Free (Fase 1). **Da tarare** nel pannello admin (Fase 4). Dati grezzi machine-readable in `docs/seed-coefficienti-base.json`.

## Metodo
Il file è un computo bottom-up con quantità a 0, quindi il €/m² non è leggibile direttamente. Questa bozza è costruita **per m² di superficie dell'appartamento** (l'input `mq`), ancorando i valori ai **prezzi unitari del listino RE** e ad assunzioni tipiche di quantità-per-m² per una ristrutturazione **totale** (moltiplicatore 1.0). Moderata e leggera scalano con i moltiplicatori.

## €/m² base per categoria (riferimento = TOTALE, molt. 1.0)
| Categoria | €/m² base | Cosa copre (dal file) |
|---|---:|---|
| A — Edile | 300 | demolizioni (18–45 €/mq), massetti (40–55), intonaci, posa pav./riv. (30–110), impermeabilizzazioni, allestimento cantiere, manodopera idr./elettr. |
| B — Finiture | 130 | materiali finitura: gres/ceramica/parquet/LVT (mediana ~59 €/mq), rivestimenti, pitture |
| C — Serramenti/Porte | 90 | finestre (200–850 €/mq), porte interne (90–412 cad), blindata (~800), tapparelle |
| D — Prodotti | 60 | caldaia (~1500), climatizzazione (610–3852), termosifoni (~350), scaldabagno (~580) |

## Moltiplicatori per tipo
| Categoria | Leggera | Moderata | Totale |
|---|---:|---:|---:|
| A — Edile | 0.25 | 0.60 | 1.00 |
| B — Finiture | 0.45 | 0.60 | 1.00 |
| C — Serramenti | 0.10 | 0.40 | 1.00 |
| D — Prodotti | 0.20 | 0.50 | 1.00 |

## Banda del range (±% per tipo)
Leggera **±10%** · Moderata **±15%** · Totale **±20%** (più incertezza → banda più larga).

**Regola di applicazione (riconciliazione a schermo):** la ±% si applica **solo alle 4 categorie (i lavori)**. Gli **extra restano fissi** (CSE/CSP, pratiche sono costi certi, non oscillano). Il **totale a schermo = somma dei range delle 4 card + extra**, così le card e il totale quadrano sempre (entro ±1 € da arrotondamento). Niente ±% sul totale complessivo.

## IVA per categoria
Edile **10%** · Finiture **22%** · Serramenti **22%** *(provvisorio, da confermare)* · Prodotti **10%**.
Extra inclusi nel totale: CSE/CSP ~€800, pratiche ~€1.500 (placeholder, editabili). Finanziamento escluso.

## Verifica di plausibilità (IVA inclusa; ±% sui lavori, extra fissi €2.806 lordo)
Questi valori sono gli **oracoli di regressione** del motore (test): totale = Σ range 4 categorie + extra fissi.
| mq | Leggera | Moderata | Totale |
|---:|---|---|---|
| 60 | €12.421 – €14.557 | €21.680 – €28.341 | €34.697 – €50.643 |
| 85 | €16.427 – €19.454 | €29.544 – €38.981 | €47.985 – €70.575 |
| 110 | €20.434 – €24.350 | €37.409 – €49.621 | €61.273 – €90.507 |

Intensità media: leggera ~210 €/mq · moderata ~400 €/mq · totale ~700 €/mq — coerente col mercato RE.

## Da tarare / confermare (per Riccardo)
- I 4 valori base €/m² e i 12 moltiplicatori (sono la leva principale).
- Aliquota IVA reale sui Serramenti/Porte.
- Importi extra (CSE/CSP, pratiche): fissi o % sui lavori?
- Definizione operativa esatta di leggera/moderata/totale (cosa includono).
