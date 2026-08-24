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

## IVA per categoria
Edile **10%** · Finiture **22%** · Serramenti **22%** *(provvisorio, da confermare)* · Prodotti **10%**.
Extra inclusi nel totale: CSE/CSP ~€800, pratiche ~€1.500 (placeholder, editabili). Finanziamento escluso.

## Verifica di plausibilità (IVA + extra inclusi)
| mq | Leggera | Moderata | Totale |
|---:|---|---|---|
| 60 | €12.140 – €14.838 | €21.259 – €28.763 | €34.136 – €51.204 |
| 85 | €16.146 – €19.734 | €29.124 – €39.402 | €47.424 – €71.136 |
| 110 | €20.153 – €24.631 | €36.988 – €50.042 | €60.712 – €91.068 |

Intensità media: leggera ~210 €/mq · moderata ~400 €/mq · totale ~700 €/mq — coerente col mercato RE.

## Da tarare / confermare (per Riccardo)
- I 4 valori base €/m² e i 12 moltiplicatori (sono la leva principale).
- Aliquota IVA reale sui Serramenti/Porte.
- Importi extra (CSE/CSP, pratiche): fissi o % sui lavori?
- Definizione operativa esatta di leggera/moderata/totale (cosa includono).
