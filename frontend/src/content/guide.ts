/**
 * Le guide pubbliche ai costi di ristrutturazione.
 *
 * Ogni guida e' una funzione dei DATI DEL MOTORE (`DatiGuide`): nessuna cifra
 * e' scritta qui. La struttura segue cio' che premiano sia i motori di
 * ricerca sia gli assistenti AI: risposta diretta in apertura, tabelle con
 * numeri e unita', fattori che spostano il prezzo, metodo dichiarato con data
 * di aggiornamento, domande frequenti.
 */

import { formatEur, formatEurRange, formatRangeEurMq } from "@/lib/currency";
import {
  anno,
  fasciaDi,
  meseAnno,
  scenario,
  type DatiGuide,
  type Fascia,
  type FasciaScenario,
} from "@/lib/guideCosti";

export type Blocco =
  | { tipo: "h2"; testo: string; id?: string }
  | { tipo: "p"; testo: string }
  | { tipo: "elenco"; voci: string[] }
  | { tipo: "tabella"; didascalia: string; colonne: string[]; righe: string[][] };

export interface Faq {
  domanda: string;
  risposta: string;
}

export interface Guida {
  slug: string;
  /** Voce di menu e titolo delle card. */
  nome: string;
  /** Riga sotto il nome nelle card. */
  sottotitolo: string;
  titolo: (d: DatiGuide) => string;
  h1: (d: DatiGuide) => string;
  descrizione: (d: DatiGuide) => string;
  /** La risposta in due righe: la prima cosa che si legge. */
  sintesi: (d: DatiGuide) => string;
  blocchi: (d: DatiGuide) => Blocco[];
  faq: (d: DatiGuide) => Faq[];
}

export const PATH_GUIDE = "/costi-ristrutturazione";

const r = (min: number, max: number) => formatEurRange(min, max);
const mqLabel = (mq: number) => `${mq} m²`;

function extraTesto(d: DatiGuide): string {
  const totale = d.extra.reduce((s, e) => s + e.importo_ivato, 0);
  if (!d.extra.length) return "";
  const voci = d.extra.map((e, i) => (i ? e.nome.charAt(0).toLowerCase() + e.nome.slice(1) : e.nome));
  return `Restano fuori ${voci.join(" e ")}, circa ${formatEur(Math.round(totale / 100) * 100)} in tutto, che la stima gratuita aggiunge al totale.`;
}

function metodo(d: DatiGuide): Blocco[] {
  return [
    { tipo: "h2", testo: "Come sono calcolate queste cifre", id: "metodo" },
    {
      tipo: "p",
      testo: `Le fasce vengono dallo stesso motore della stima gratuita: un computo metrico voce per voce (demolizioni, massetti, impianti, posa, forniture) con i prezzi del listino di ${d.citta_listino}, aggiornato a ${meseAnno(d.aggiornato_il)}. Le quantità si ricavano dalla superficie e dagli interventi scelti; il risultato è sempre un intervallo minimo–massimo, IVA inclusa, perché prima del sopralluogo nessuna cifra secca è onesta.`,
    },
    {
      tipo: "p",
      testo: `Gli importi sono arrotondati alle centinaia di euro e comprendono l'allestimento del cantiere e gli oneri della sicurezza. ${extraTesto(d)} Il prezzo finale dipende dallo stato dell'immobile e dai materiali scelti: per una cifra sulla tua casa usa la stima gratuita.`,
    },
  ];
}

function tabellaScenari(didascalia: string, scenari: FasciaScenario[], conMq = false): Blocco {
  return {
    tipo: "tabella",
    didascalia,
    colonne: conMq ? ["Intervento", "Superficie", "Costo IVA inclusa"] : ["Intervento", "Costo IVA inclusa"],
    righe: scenari.map((s) => (conMq ? [s.etichetta, mqLabel(s.mq), r(s.min, s.max)] : [s.etichetta, r(s.min, s.max)])),
  };
}

function righePerTipo(d: DatiGuide, mqs: number[]): string[][] {
  return mqs.flatMap((mq) => {
    const celle = (["leggera", "moderata", "totale"] as const).map((t) => {
      const f = fasciaDi(d, t, mq);
      return f ? `${r(f.min, f.max)} (${formatRangeEurMq(f.eur_mq_min, f.eur_mq_max)})` : "—";
    });
    return [[mqLabel(mq), ...celle]];
  });
}

function totale85(d: DatiGuide): Fascia {
  return fasciaDi(d, "totale", d.mq_riferimento) ?? d.per_tipo.totale[0];
}

const COSA_COMPRENDE: Blocco = {
  tipo: "elenco",
  voci: [
    "Leggera: pavimenti posati sopra quelli esistenti, impianto elettrico modificato, tinteggiatura di pareti e soffitti.",
    "Moderata: pavimenti demoliti e rifatti con il massetto, un bagno nuovo, impianti della cucina, impianto elettrico rifatto, radiatori smontati e rimontati, porte interne nuove.",
    "Totale: tutto quello della moderata, più tutti i bagni, impianto idrico a collettore, radiatori e caldaia nuovi, climatizzazione a split, finestre e tapparelle nuove.",
  ],
};

const FATTORI_GENERALI: Blocco = {
  tipo: "elenco",
  voci: [
    "Quanto si demolisce: posare sopra il pavimento esistente costa molto meno che demolire e rifare il massetto.",
    "Il numero di bagni: ogni bagno rifatto porta sanitari, rivestimenti, impianto idrico e impermeabilizzazione.",
    "Gli impianti: rifare l'impianto elettrico o il riscaldamento pesa più di qualunque finitura.",
    "Il livello delle finiture: tra finiture base e di pregio la differenza è sui materiali, non sulla manodopera.",
    "Piano e accesso al cantiere: senza ascensore o con un accesso difficile la movimentazione dei materiali costa di più.",
    "Età e stato dell'immobile: impianti datati o murature da risanare spostano la stima verso il massimo.",
  ],
};

const guidaGenerale: Guida = {
  slug: "",
  nome: "Prezzi al metro quadro",
  sottotitolo: "Ristrutturazione leggera, moderata e totale, da 50 a 150 m²",
  titolo: (d) => `Quanto costa ristrutturare casa nel ${anno(d.aggiornato_il)}: prezzi al m²`,
  h1: (d) => `Quanto costa ristrutturare casa nel ${anno(d.aggiornato_il)}`,
  descrizione: (d) => {
    const t = totale85(d);
    return `Ristrutturare un appartamento di ${d.mq_riferimento} m² costa tra ${formatEur(t.min)} e ${formatEur(t.max)} IVA inclusa per una ristrutturazione totale. Prezzi al m² per tipo di lavori, cosa comprendono e cosa fa variare il costo.`;
  },
  sintesi: (d) => {
    const mq = d.mq_riferimento;
    const [l, m, t] = (["leggera", "moderata", "totale"] as const).map((tipo) => fasciaDi(d, tipo, mq)!);
    return `Per un appartamento di ${mq} m² una ristrutturazione totale costa tra ${formatEur(t.min)} e ${formatEur(t.max)} IVA inclusa (${formatRangeEurMq(t.eur_mq_min, t.eur_mq_max)}). Una moderata costa tra ${formatEur(m.min)} e ${formatEur(m.max)}, una leggera tra ${formatEur(l.min)} e ${formatEur(l.max)}. Prezzi del listino di ${d.citta_listino}, ${meseAnno(d.aggiornato_il)}.`;
  },
  blocchi: (d) => {
    const t = totale85(d);
    return [
      { tipo: "h2", testo: "Prezzi per superficie e tipo di ristrutturazione", id: "prezzi" },
      {
        tipo: "tabella",
        didascalia: `Costo dei lavori IVA inclusa e incidenza al m², listino di ${d.citta_listino}`,
        colonne: ["Superficie", "Leggera", "Moderata", "Totale"],
        righe: righePerTipo(d, d.per_tipo.totale.map((f) => f.mq)),
      },
      {
        tipo: "p",
        testo: "Il costo al metro quadro scende con la superficie perché le voci fisse (cantiere, quadro elettrico, sicurezza) si dividono su più metri; sale invece quando la casa più grande ha un bagno in più da rifare.",
      },
      { tipo: "h2", testo: "Cosa comprende ogni tipo di ristrutturazione", id: "tipi" },
      COSA_COMPRENDE,
      { tipo: "h2", testo: "Quanto pesano le finiture", id: "finiture" },
      {
        tipo: "tabella",
        didascalia: `Ristrutturazione totale di ${d.mq_riferimento} m², IVA inclusa`,
        colonne: ["Livello di finiture", "Costo IVA inclusa"],
        righe: [
          ["Base", r(d.per_livello.base.min, d.per_livello.base.max)],
          ["Medio", r(d.per_livello.medio.min, d.per_livello.medio.max)],
          ["Alto", r(d.per_livello.alto.min, d.per_livello.alto.max)],
        ],
      },
      { tipo: "h2", testo: "Come si divide la spesa", id: "categorie" },
      {
        tipo: "tabella",
        didascalia: `Ristrutturazione totale di ${d.mq_riferimento} m², per categoria di lavori`,
        colonne: ["Categoria", "Costo IVA inclusa"],
        righe: t.categorie.map((c) => [c.nome, r(c.min, c.max)]),
      },
      { tipo: "h2", testo: "Cosa fa salire o scendere il prezzo", id: "fattori" },
      FATTORI_GENERALI,
      ...metodo(d),
    ];
  },
  faq: (d) => {
    const t = totale85(d);
    const m = fasciaDi(d, "moderata", d.mq_riferimento)!;
    return [
      {
        domanda: "Quanto costa al metro quadro ristrutturare casa?",
        risposta: `Per ${d.mq_riferimento} m² una ristrutturazione totale costa ${formatRangeEurMq(t.eur_mq_min, t.eur_mq_max)} IVA inclusa, una moderata ${formatRangeEurMq(m.eur_mq_min, m.eur_mq_max)}. Il costo al m² scende sulle superfici più grandi e sale con il numero di bagni.`,
      },
      {
        domanda: "Cosa è compreso nel prezzo?",
        risposta: `Demolizioni, massetti, murature, impianti, posa, forniture di pavimenti, sanitari, porte e serramenti quando previsti, cantiere e sicurezza, IVA inclusa. ${extraTesto(d)}`,
      },
      {
        domanda: "Perché la stima è un intervallo e non un prezzo preciso?",
        risposta: "Prima del sopralluogo non si conoscono lo stato degli impianti, delle murature e dei sottofondi. Un intervallo minimo–massimo è l'unica cifra onesta; il sopralluogo la trasforma in un preventivo.",
      },
      {
        domanda: "Come ottengo una stima sulla mia casa?",
        risposta: "Con la stima gratuita di Renovio: inserisci città e superficie, scegli il tipo di lavori e ottieni la fascia di prezzo divisa per categoria, senza registrazione.",
      },
    ];
  },
};

const guidaReggioEmilia: Guida = {
  slug: "reggio-emilia",
  nome: "Reggio Emilia",
  sottotitolo: "Prezzi del listino locale, interventi per interventi",
  titolo: (d) => `Ristrutturazione casa a Reggio Emilia: prezzi ${anno(d.aggiornato_il)}`,
  h1: (d) => `Quanto costa ristrutturare casa a Reggio Emilia nel ${anno(d.aggiornato_il)}`,
  descrizione: (d) => {
    const t = totale85(d);
    return `Prezzi di ristrutturazione a Reggio Emilia dal listino locale: ${formatEur(t.min)}–${formatEur(t.max)} per una ristrutturazione totale di ${d.mq_riferimento} m², più bagno, cucina, impianto elettrico, pavimenti e serramenti.`;
  },
  sintesi: (d) => {
    const t = totale85(d);
    const bagno = scenario(d, "bagno", "bagno_medio");
    return `A Reggio Emilia ristrutturare completamente un appartamento di ${d.mq_riferimento} m² costa tra ${formatEur(t.min)} e ${formatEur(t.max)} IVA inclusa${bagno ? `; rifare solo il bagno costa tra ${formatEur(bagno.min)} e ${formatEur(bagno.max)}` : ""}. Cifre dal listino delle imprese di Reggio Emilia, ${meseAnno(d.aggiornato_il)}.`;
  },
  blocchi: (d) => {
    const voci: [string, FasciaScenario | undefined][] = [
      ["Rifacimento bagno, finiture medie", scenario(d, "bagno", "bagno_medio")],
      ["Impianti della cucina", scenario(d, "cucina", "cucina_induzione")],
      [`Impianto elettrico nuovo, ${d.mq_riferimento} m²`, scenario(d, "impianto-elettrico", `elettrico_rifacimento_${d.mq_riferimento}`)],
      [`Pavimenti in gres demoliti e rifatti, ${d.mq_riferimento} m²`, scenario(d, "pavimenti", "pavimenti_rifai_gres")],
      ["Finestre e tapparelle in PVC (5 finestre, 1 portafinestra)", scenario(d, "serramenti", "serramenti_tapparelle_pvc")],
      ["Radiatori nuovi e caldaia", scenario(d, "riscaldamento", "riscaldamento_radiatori")],
    ];
    return [
      { tipo: "h2", testo: "Prezzi per superficie", id: "prezzi" },
      {
        tipo: "tabella",
        didascalia: "Costo dei lavori a Reggio Emilia, IVA inclusa, e incidenza al m²",
        colonne: ["Superficie", "Leggera", "Moderata", "Totale"],
        righe: righePerTipo(d, [50, 70, 85, 100, 120]),
      },
      { tipo: "h2", testo: "Singoli interventi", id: "interventi" },
      {
        tipo: "tabella",
        didascalia: "Lavori singoli a Reggio Emilia, IVA inclusa, cantiere e sicurezza compresi",
        colonne: ["Intervento", "Costo IVA inclusa"],
        righe: voci.filter(([, s]) => s).map(([nome, s]) => [nome, r(s!.min, s!.max)]),
      },
      { tipo: "h2", testo: "Cosa comprende ogni tipo di ristrutturazione", id: "tipi" },
      COSA_COMPRENDE,
      ...metodo(d),
    ];
  },
  faq: (d) => {
    const t = totale85(d);
    return [
      {
        domanda: "Quanto costa ristrutturare un appartamento a Reggio Emilia?",
        risposta: `Per ${d.mq_riferimento} m² tra ${formatEur(t.min)} e ${formatEur(t.max)} IVA inclusa per una ristrutturazione totale, cioè ${formatRangeEurMq(t.eur_mq_min, t.eur_mq_max)}.`,
      },
      {
        domanda: "Da dove vengono i prezzi?",
        risposta: "Dal listino delle imprese di Reggio Emilia usato dal motore di stima di Renovio, voce per voce. Per le città senza un listino proprio la stima usa il listino più vicino e lo dichiara.",
      },
    ];
  },
};

const guidaBagno: Guida = {
  slug: "bagno",
  nome: "Rifare il bagno",
  sottotitolo: "Demolizione, impianti, sanitari e rivestimenti",
  titolo: (d) => `Quanto costa rifare il bagno nel ${anno(d.aggiornato_il)}`,
  h1: (d) => `Quanto costa rifare il bagno nel ${anno(d.aggiornato_il)}`,
  descrizione: (d) => {
    const m = scenario(d, "bagno", "bagno_medio");
    return m
      ? `Rifare completamente un bagno costa tra ${formatEur(m.min)} e ${formatEur(m.max)} IVA inclusa con finiture medie. Cosa comprende il prezzo e come cambia con le finiture.`
      : "Quanto costa rifare il bagno: prezzi e cosa comprendono.";
  },
  sintesi: (d) => {
    const [b, m, a] = ["bagno_base", "bagno_medio", "bagno_alto"].map((c) => scenario(d, "bagno", c)!);
    return `Rifare completamente un bagno costa tra ${formatEur(m.min)} e ${formatEur(m.max)} IVA inclusa con finiture medie: da ${formatEur(b.min)} con finiture base fino a ${formatEur(a.max)} con finiture di pregio. Il prezzo comprende demolizioni, impianto idrico, impermeabilizzazione, rivestimenti, sanitari e montaggio.`;
  },
  blocchi: (d) => [
    { tipo: "h2", testo: "Prezzi per livello di finiture", id: "prezzi" },
    tabellaScenari("Rifacimento completo di un bagno, IVA inclusa", d.guide.bagno ?? []),
    { tipo: "h2", testo: "Cosa comprende il rifacimento", id: "comprende" },
    {
      tipo: "elenco",
      voci: [
        "Rimozione di sanitari, linee idriche, pavimento e rivestimenti esistenti, con smaltimento.",
        "Nuova rete idrica e di scarico: un punto acqua per ogni apparecchio.",
        "Impermeabilizzazione della zona doccia.",
        "Posa di pavimento e rivestimenti, con colle e stucchi.",
        "Sanitari, rubinetteria, piatto e box doccia, montaggio e collaudo.",
        "Assistenza muraria per aprire e chiudere le tracce degli impianti.",
      ],
    },
    { tipo: "h2", testo: "Cosa fa variare il prezzo", id: "fattori" },
    {
      tipo: "elenco",
      voci: [
        "Sanitari sospesi o a terra: i sospesi richiedono cassetta d'incasso e costano di più.",
        "Formato dei rivestimenti: le grandi lastre costano di più da posare.",
        "Doccia o vasca, e la cabina doccia in cristallo.",
        "Spostare gli scarichi rispetto alla posizione attuale.",
        "Bagno cieco: serve l'aerazione forzata con foro di uscita.",
      ],
    },
    ...metodo(d),
  ],
  faq: (d) => {
    const m = scenario(d, "bagno", "bagno_medio");
    return [
      {
        domanda: "Quanto costa rifare un bagno completo?",
        risposta: m
          ? `Tra ${formatEur(m.min)} e ${formatEur(m.max)} IVA inclusa con finiture medie, compresi impianti, rivestimenti, sanitari, cantiere e sicurezza.`
          : "Dipende dalle finiture e dagli impianti: usa la stima gratuita.",
      },
      {
        domanda: "Si può rifare il bagno senza rifare gli impianti?",
        risposta: "Si può sostituire solo sanitari e rivestimenti, ma con impianti datati di solito conviene rifarli: aprire le pareti una seconda volta costa più che farlo subito.",
      },
    ];
  },
};

const guidaCucina: Guida = {
  slug: "cucina",
  nome: "Impianti della cucina",
  sottotitolo: "Acqua, scarichi, linee elettriche e gas",
  titolo: (d) => `Quanto costa rifare gli impianti della cucina nel ${anno(d.aggiornato_il)}`,
  h1: (d) => `Quanto costa rifare gli impianti della cucina nel ${anno(d.aggiornato_il)}`,
  descrizione: (d) => {
    const s = scenario(d, "cucina", "cucina_induzione");
    return s
      ? `Rifare gli impianti della cucina costa tra ${formatEur(s.min)} e ${formatEur(s.max)} IVA inclusa con piano a induzione. Differenze con il gas e cosa comprende il prezzo.`
      : "Quanto costa rifare gli impianti della cucina.";
  },
  sintesi: (d) => {
    const i = scenario(d, "cucina", "cucina_induzione")!;
    const g = scenario(d, "cucina", "cucina_gas")!;
    return `Rifare gli impianti della cucina costa tra ${formatEur(i.min)} e ${formatEur(i.max)} IVA inclusa con un piano a induzione e tra ${formatEur(g.min)} e ${formatEur(g.max)} con il piano a gas. I mobili e gli elettrodomestici sono esclusi.`;
  },
  blocchi: (d) => [
    { tipo: "h2", testo: "Prezzi", id: "prezzi" },
    tabellaScenari("Impianti della cucina, IVA inclusa", d.guide.cucina ?? []),
    { tipo: "h2", testo: "Cosa comprende", id: "comprende" },
    {
      tipo: "elenco",
      voci: [
        "Punti acqua e scarico per lavello e lavastoviglie, allaccio compreso.",
        "Rivestimento della parete attrezzata.",
        "Foro per la cappa aspirante.",
        "Con l'induzione: una linea elettrica dedicata al quadro. Con il gas: impianto gas a norma e allaccio del piano cottura.",
      ],
    },
    ...metodo(d),
  ],
  faq: () => [
    {
      domanda: "Conviene il piano a induzione o a gas?",
      risposta: "Dal punto di vista dell'impianto l'induzione costa meno: serve una linea elettrica dedicata invece dell'impianto gas a norma.",
    },
  ],
};

const guidaElettrico: Guida = {
  slug: "impianto-elettrico",
  nome: "Impianto elettrico",
  sottotitolo: "Rifacimento completo o modifica, per superficie",
  titolo: (d) => `Quanto costa rifare l'impianto elettrico nel ${anno(d.aggiornato_il)}`,
  h1: () => "Quanto costa rifare l'impianto elettrico",
  descrizione: (d) => {
    const s = scenario(d, "impianto-elettrico", `elettrico_rifacimento_${d.mq_riferimento}`);
    return s
      ? `Rifare l'impianto elettrico di ${d.mq_riferimento} m² costa tra ${formatEur(s.min)} e ${formatEur(s.max)} IVA inclusa, con quadro, punti luce, certificazione e assistenza muraria.`
      : "Quanto costa rifare l'impianto elettrico.";
  },
  sintesi: (d) => {
    const s = scenario(d, "impianto-elettrico", `elettrico_rifacimento_${d.mq_riferimento}`)!;
    const m = scenario(d, "impianto-elettrico", `elettrico_modifica_${d.mq_riferimento}`)!;
    return `Rifare da zero l'impianto elettrico di un appartamento di ${d.mq_riferimento} m² costa tra ${formatEur(s.min)} e ${formatEur(s.max)} IVA inclusa; modificarne una parte costa tra ${formatEur(m.min)} e ${formatEur(m.max)}. Il prezzo comprende quadro, punti luce, certificazione e la riapertura delle tracce.`;
  },
  blocchi: (d) => [
    { tipo: "h2", testo: "Prezzi per superficie", id: "prezzi" },
    tabellaScenari("Impianto elettrico, IVA inclusa", d.guide["impianto-elettrico"] ?? [], true),
    { tipo: "h2", testo: "Cosa comprende il rifacimento", id: "comprende" },
    {
      tipo: "elenco",
      voci: [
        "Punti luce e prese (circa uno ogni 2 m²), con placche e frutti.",
        "Quadro elettrico a norma, dimensionato sulla superficie.",
        "Linee dedicate per induzione e climatizzazione, quando servono.",
        "Certificazione di conformità.",
        "Assistenza muraria per aprire e chiudere le tracce.",
      ],
    },
    ...metodo(d),
  ],
  faq: () => [
    {
      domanda: "Quando conviene rifare l'impianto invece di modificarlo?",
      risposta: "Quando l'impianto è datato, senza differenziali o non certificabile: una modifica non permette di rilasciare la certificazione senza verificare l'impianto esistente.",
    },
  ],
};

const guidaPavimenti: Guida = {
  slug: "pavimenti",
  nome: "Pavimenti",
  sottotitolo: "Gres, parquet, laminato e vinilico, posa sopra o rifacimento",
  titolo: (d) => `Quanto costa rifare i pavimenti nel ${anno(d.aggiornato_il)}`,
  h1: () => "Quanto costa rifare i pavimenti di casa",
  descrizione: (d) => {
    const s = scenario(d, "pavimenti", "pavimenti_rifai_gres");
    return s
      ? `Rifare i pavimenti di ${d.mq_riferimento} m² in gres costa tra ${formatEur(s.min)} e ${formatEur(s.max)} IVA inclusa con demolizione e massetto. Prezzi per gres, parquet, laminato e vinilico.`
      : "Quanto costa rifare i pavimenti.";
  },
  sintesi: (d) => {
    const sov = scenario(d, "pavimenti", "pavimenti_sovrapponi_gres")!;
    const rif = scenario(d, "pavimenti", "pavimenti_rifai_gres")!;
    const par = scenario(d, "pavimenti", "pavimenti_rifai_parquet")!;
    return `Per una casa di ${d.mq_riferimento} m² posare il gres sopra il pavimento esistente costa tra ${formatEur(sov.min)} e ${formatEur(sov.max)} IVA inclusa; demolire, rifare il massetto e posare il gres costa tra ${formatEur(rif.min)} e ${formatEur(rif.max)}. Con il parquet si sale a ${formatEurRange(par.min, par.max)}.`;
  },
  blocchi: (d) => [
    { tipo: "h2", testo: "Prezzi per tipo di pavimento", id: "prezzi" },
    tabellaScenari(`Pavimenti di una casa di ${d.mq_riferimento} m², fornitura e posa, IVA inclusa`, d.guide.pavimenti ?? []),
    { tipo: "h2", testo: "Posa sopra o demolizione?", id: "posa" },
    {
      tipo: "p",
      testo: "Posare sopra l'esistente evita demolizione, smaltimento e massetto, ma richiede un autolivellante e alza la quota del pavimento: le porte vanno spesso rifilate. Demolire costa di più ma permette di rifare gli impianti a pavimento e il massetto.",
    },
    ...metodo(d),
  ],
  faq: () => [
    {
      domanda: "Il parquet costa molto più del gres?",
      risposta: "Sì: la differenza è soprattutto nella fornitura. La posa costa poco di più, la materia prima molto di più.",
    },
  ],
};

const guidaSerramenti: Guida = {
  slug: "serramenti",
  nome: "Finestre e serramenti",
  sottotitolo: "Infissi in PVC, tapparelle e cassonetti",
  titolo: (d) => `Quanto costa cambiare le finestre nel ${anno(d.aggiornato_il)}`,
  h1: () => "Quanto costa cambiare finestre e tapparelle",
  descrizione: (d) => {
    const s = scenario(d, "serramenti", "serramenti_senza_tapparelle");
    return s
      ? `Sostituire 5 finestre e una portafinestra in PVC costa tra ${formatEur(s.min)} e ${formatEur(s.max)} IVA inclusa. Prezzi con tapparelle in PVC o alluminio e cassonetti.`
      : "Quanto costa cambiare le finestre.";
  },
  sintesi: (d) => {
    const s = scenario(d, "serramenti", "serramenti_senza_tapparelle")!;
    const t = scenario(d, "serramenti", "serramenti_tapparelle_pvc")!;
    return `Sostituire 5 finestre e una portafinestra in PVC costa tra ${formatEur(s.min)} e ${formatEur(s.max)} IVA inclusa; con tapparelle in PVC e cassonetti coibentati tra ${formatEur(t.min)} e ${formatEur(t.max)}. Il prezzo comprende fornitura, montaggio sul controtelaio esistente e smaltimento dei vecchi infissi.`;
  },
  blocchi: (d) => [
    { tipo: "h2", testo: "Prezzi", id: "prezzi" },
    tabellaScenari("Cinque finestre e una portafinestra, IVA inclusa", d.guide.serramenti ?? []),
    {
      tipo: "p",
      testo: "Ogni finestra si conta almeno 2 m², anche se più piccola: è la quadratura minima con cui i serramentisti prezzano. Il prezzo va confermato dal serramentista dopo il sopralluogo.",
    },
    ...metodo(d),
  ],
  faq: () => [
    {
      domanda: "Il prezzo comprende la rimozione delle vecchie finestre?",
      risposta: "Sì: smontaggio, carico e smaltimento sono compresi, con il nuovo infisso montato sul controtelaio esistente.",
    },
  ],
};

const guidaRiscaldamento: Guida = {
  slug: "riscaldamento-climatizzazione",
  nome: "Riscaldamento e clima",
  sottotitolo: "Radiatori, caldaia, pavimento radiante, split",
  titolo: (d) => `Quanto costa rifare il riscaldamento nel ${anno(d.aggiornato_il)}`,
  h1: () => "Quanto costa rifare riscaldamento e climatizzazione",
  descrizione: (d) => {
    const s = scenario(d, "riscaldamento", "riscaldamento_radiatori");
    return s
      ? `Radiatori nuovi e caldaia per ${d.mq_riferimento} m² costano tra ${formatEur(s.min)} e ${formatEur(s.max)} IVA inclusa. Prezzi del riscaldamento a pavimento e della climatizzazione a split.`
      : "Quanto costa rifare il riscaldamento.";
  },
  sintesi: (d) => {
    const rad = scenario(d, "riscaldamento", "riscaldamento_radiatori")!;
    const pav = scenario(d, "riscaldamento", "riscaldamento_pavimento")!;
    const cli = scenario(d, "riscaldamento", "climatizzazione_split")!;
    return `In una casa di ${d.mq_riferimento} m² radiatori nuovi e caldaia costano tra ${formatEur(rad.min)} e ${formatEur(rad.max)} IVA inclusa; il riscaldamento a pavimento, con demolizione e rifacimento dei pavimenti, tra ${formatEur(pav.min)} e ${formatEur(pav.max)}. Due split per la climatizzazione costano tra ${formatEur(cli.min)} e ${formatEur(cli.max)}.`;
  },
  blocchi: (d) => [
    { tipo: "h2", testo: "Prezzi", id: "prezzi" },
    tabellaScenari(`Casa di ${d.mq_riferimento} m², IVA inclusa`, d.guide.riscaldamento ?? []),
    {
      tipo: "p",
      testo: "Il riscaldamento a pavimento costa di più perché richiede di demolire i pavimenti e rifare massetto e posa: conviene quando si rifanno comunque i pavimenti.",
    },
    ...metodo(d),
  ],
  faq: () => [
    {
      domanda: "Conviene il riscaldamento a pavimento?",
      risposta: "Conviene quando si demoliscono comunque i pavimenti: il costo aggiuntivo rispetto ai radiatori è soprattutto nella posa della serpentina e nel collettore.",
    },
  ],
};

export const GUIDA_GENERALE = guidaGenerale;

/** Le guide figlie, nell'ordine delle card. */
export const GUIDE: Guida[] = [
  guidaReggioEmilia,
  guidaBagno,
  guidaCucina,
  guidaElettrico,
  guidaPavimenti,
  guidaSerramenti,
  guidaRiscaldamento,
];

export function pathGuida(g: Guida): string {
  return g.slug ? `${PATH_GUIDE}/${g.slug}` : PATH_GUIDE;
}

export function guidaPerSlug(slug: string | undefined): Guida | undefined {
  if (!slug) return guidaGenerale;
  return GUIDE.find((g) => g.slug === slug);
}

/** Per la home: la fascia della totale al m² di riferimento. */
export function fasciaRiferimento(d: DatiGuide): Fascia {
  return totale85(d);
}
