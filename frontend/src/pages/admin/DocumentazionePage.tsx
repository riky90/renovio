import type { ReactNode } from "react";
import { Link } from "react-router";
import { AdminLayout } from "@/pages/admin/AdminLayout";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

/**
 * Manuale d'uso del pannello admin: a cosa serve ogni pagina, cosa vuol dire
 * ogni campo, come le tabelle si collegano e cosa metterci dentro.
 *
 * E' testo statico e non dati di business: nessun prezzo, coefficiente o
 * aliquota compare qui (regola #3), solo la spiegazione di dove stanno e di
 * come il motore li legge. Quando cambia uno schema o una regola del motore
 * (`backend/app/services/effetti.py`, `estimation.py`, `dettaglio_pro.py`),
 * questa pagina va aggiornata insieme.
 */

interface Campo {
  nome: string;
  significato: string;
  cosaMettere: string;
}

interface Tabella {
  titolo: string;
  descrizione?: string;
  campi: Campo[];
}

interface SezionePagina {
  id: string;
  path: string;
  label: string;
  aCosaServe: ReactNode;
  tabelle: Tabella[];
  attenzione?: ReactNode[];
}

const SEZIONI: SezionePagina[] = [
  {
    id: "lead",
    path: "/admin/lead",
    label: "Lead",
    aCosaServe: (
      <>
        Le richieste di contatto arrivate dal sito: chi ha chiesto di essere ricontattato dopo
        una stima. Ogni lead porta con sé la fotografia della stima (a range) com'era nel
        momento dell'invio. È l'unica pagina visibile anche al ruolo <em>consulente</em>.
      </>
    ),
    tabelle: [
      {
        titolo: "Lead",
        campi: [
          { nome: "Città", significato: "Comune della stima che ha generato il lead.", cosaMettere: "Solo lettura; si usa come filtro." },
          { nome: "Stato", significato: "Nuovo = nessuno l'ha ancora gestito; Gestito = preso in carico.", cosaMettere: "Passalo a Gestito quando hai ricontattato il cliente." },
          { nome: "Nota", significato: "Appunto interno, non visibile al cliente.", cosaMettere: "Esito della chiamata, prossimo passo." },
        ],
      },
    ],
    attenzione: [
      <>
        <strong>Scarica lead</strong> produce un Excel con dati personali: ogni download viene
        registrato in <em>Download registrati</em>. Scaricalo solo quando serve.
      </>,
    ],
  },
  {
    id: "listini",
    path: "/admin/listini",
    label: "Listini e prezzi",
    aCosaServe: (
      <>
        Il listino è l'insieme dei prezzi di una città (oggi Reggio Emilia). Qui definisci i
        listini e, per ciascuno, il <strong>costo base €/m²</strong> di ogni categoria: è il
        numero da cui parte la stima gratuita.
      </>
    ),
    tabelle: [
      {
        titolo: "Listino",
        campi: [
          { nome: "Nome", significato: "Nome leggibile del listino.", cosaMettere: "Es. «Listino Reggio Emilia 2026»." },
          { nome: "Città di riferimento", significato: "La città i cui prezzi descrive.", cosaMettere: "Il comune da cui vengono i prezzi." },
          { nome: "Default", significato: "Il listino usato per le città che non ne hanno uno proprio (fallback, con disclaimer).", cosaMettere: "Uno solo deve essere default." },
          { nome: "Attivo", significato: "Un listino spento non viene usato per le stime.", cosaMettere: "Spegni invece di cancellare." },
        ],
      },
      {
        titolo: "Categorie del listino",
        descrizione: "Una riga per ciascuna delle 4 categorie (A Edile, B Finiture, C Serramenti, D Prodotti).",
        campi: [
          { nome: "Base €/m²", significato: "Prezzo CLIENTE per m² della categoria, IVA esclusa, per una ristrutturazione con moltiplicatore 1.", cosaMettere: "Euro al m². Il moltiplicatore per tipo (Coefficienti) lo scala poi per leggera/moderata/totale." },
          { nome: "Coefficiente impresa", significato: "Margine interno: prezzo impresa = prezzo cliente × coefficiente. Resta sul server, non arriva mai al cliente né nel PDF.", cosaMettere: "Un numero tra 0 e 1 (es. 0.6). Non influenza la stima mostrata al cliente." },
        ],
      },
    ],
    attenzione: [
      <>Il file Excel <strong>Scarica listino</strong> contiene le voci del dettaglio Pro del listino selezionato: modificalo e ricaricalo per cambiare molte voci insieme.</>,
    ],
  },
  {
    id: "dettaglio-pro",
    path: "/admin/dettaglio-pro",
    label: "Voci dettaglio Pro",
    aCosaServe: (
      <>
        Il computo metrico usato dalla stima Pro: per ogni categoria, le sottocategorie e le
        singole voci con unità di misura e prezzo unitario. Il motore Pro stima una quantità per
        ogni voce e la moltiplica per il prezzo.
      </>
    ),
    tabelle: [
      {
        titolo: "Sottocategoria",
        campi: [
          { nome: "Codice", significato: "Codice gerarchico (A.1…A.12). Obbligatorio solo per A Edile.", cosaMettere: "Per B/C/D lascialo vuoto." },
          { nome: "Nome", significato: "Titolo del gruppo di voci.", cosaMettere: "Es. «Demolizioni», «Pavimenti»." },
          { nome: "Famiglia", significato: "gerarchica = le voci si SOMMANO (A Edile). catalogo = le voci sono ALTERNATIVE: il motore ne sceglie una per livello di finitura (B/C/D).", cosaMettere: "gerarchica per A, catalogo per B/C/D." },
          { nome: "Ordine", significato: "Posizione nell'elenco.", cosaMettere: "Numero crescente." },
        ],
      },
      {
        titolo: "Voce",
        campi: [
          { nome: "Codice", significato: "Codice della voce (A.n.m) per A Edile.", cosaMettere: "Vuoto per B/C/D." },
          { nome: "Descrizione", significato: "Cosa è la lavorazione o il prodotto.", cosaMettere: "Testo come nel computo." },
          { nome: "UM", significato: "Unità di misura del prezzo.", cosaMettere: "m², ml, cad, piano…" },
          { nome: "Prezzo unitario cliente (€)", significato: "Prezzo al cliente per unità, IVA esclusa.", cosaMettere: "Euro. Nessun margine impresa qui." },
          { nome: "Livello di finitura", significato: "base / medio / alto: in una sottocategoria catalogo il motore tiene solo le voci del livello scelto. Vuoto = voce comune a tutti i livelli, sempre inclusa.", cosaMettere: "Vuoto per posa, consumo, montaggio; un livello per i prodotti alternativi." },
        ],
      },
      {
        titolo: "Coefficiente quantità (voce × tipo)",
        descrizione: "Dice al motore Pro QUANTO di una voce serve, per ciascun tipo di ristrutturazione. Si modifica da Coefficienti → Coefficienti Pro.",
        campi: [
          { nome: "Quantità per m²", significato: "Quantità = coefficiente × m² dell'immobile.", cosaMettere: "Es. 1.0 per un pavimento, 0.03 per una voce a corpo ogni 30 m²." },
          { nome: "Domanda mirata", significato: "La quantità è la risposta dell'utente a una domanda (es. numero di bagni).", cosaMettere: "La chiave della domanda; in alternativa alla quantità per m²." },
          { nome: "Default conteggio", significato: "Quantità fissa, o valore usato se l'utente non risponde alla domanda mirata.", cosaMettere: "Un intero (es. 1 bagno)." },
        ],
      },
    ],
    attenzione: [
      <>Se tutte le colonne di quantità sono vuote la voce vale 0 e non compare nel dettaglio.</>,
    ],
  },
  {
    id: "domande",
    path: "/admin/domande",
    label: "Domande",
    aCosaServe: (
      <>
        Il catalogo delle domande del wizard. Ogni domanda ha delle <strong>opzioni</strong>
        (le risposte possibili) e ogni opzione ha degli <strong>effetti</strong> (cosa cambia
        nel calcolo se l'utente la sceglie). Aggiungere o cambiare una domanda qui non richiede
        un deploy. La pagina si apre a tre livelli: Domande → Opzioni → Effetti.
      </>
    ),
    tabelle: [
      {
        titolo: "Domanda",
        campi: [
          { nome: "Codice", significato: "Identificativo stabile, usato dagli altri collegamenti.", cosaMettere: "minuscolo_con_underscore. Non cambiarlo dopo che è in uso." },
          { nome: "Testo / Help", significato: "La domanda come la legge il cliente, e il suggerimento sotto.", cosaMettere: "Frase breve e chiara; help facoltativo." },
          { nome: "Tipo controllo", significato: "stepper / numero = l'utente scrive un numero; scelta_singola / toggle = una risposta; scelta_multipla = più risposte.", cosaMettere: "Stepper per contatori (bagni, finestre); scelta_singola per alternative." },
          { nome: "Gruppo / Ordine", significato: "In quale blocco del wizard compare e in che posizione.", cosaMettere: "Stesso gruppo per domande affini." },
          { nome: "Tier minimo", significato: "free = nel wizard pubblico; pro = solo nel configuratore Pro.", cosaMettere: "È la linea Free/Pro: spostala solo con una decisione." },
          { nome: "Attributo", significato: "Collega uno stepper alla sua baseline in «attese» (quanti bagni ha normalmente un immobile di X m²).", cosaMettere: "Il codice attributo; senza una riga di attesa per quei m² la correzione non si applica." },
          { nome: "Visibile solo se — Domanda / Risposta", significato: "La domanda compare solo se un'altra domanda ha una certa risposta.", cosaMettere: "Vuoti = sempre visibile." },
          { nome: "Obbligatoria / Attiva", significato: "L'utente deve rispondere / la domanda compare nel wizard.", cosaMettere: "Disattiva invece di cancellare." },
        ],
      },
      {
        titolo: "Opzione",
        campi: [
          { nome: "Codice / Etichetta", significato: "Identificativo e testo mostrato.", cosaMettere: "Per stepper e numero c'è una sola opzione con codice «valore»." },
          { nome: "Descrizione / Immagine", significato: "Spiegazione e foto facoltative (utili per i livelli di finitura).", cosaMettere: "URL immagine facoltativo." },
          { nome: "Default", significato: "La risposta preselezionata.", cosaMettere: "Una sola per domanda, e deve essere attiva." },
          { nome: "Attiva", significato: "Un'opzione spenta sparisce dal wizard e i suoi effetti non scattano più.", cosaMettere: "Non si può spegnere un'opzione in uso (default della domanda, condizione di visibilità, derivazione): il pannello elenca tutti i motivi." },
        ],
      },
      {
        titolo: "Effetto",
        descrizione: "Otto tipi, nessuno di più. I primi quattro agiscono sulla stima gratuita, gli altri quattro sul computo Pro.",
        campi: [
          { nome: "moltiplicatore_categoria (Free)", significato: "Moltiplica il costo della categoria. 1.08 = +8%; 0 = categoria azzerata.", cosaMettere: "Bersaglio: categoria. Valore: fattore." },
          { nome: "eur_mq_categoria (Free)", significato: "Aggiunge euro al m² alla categoria.", cosaMettere: "Bersaglio: categoria. Valore: €/m²." },
          { nome: "eur_fisso_categoria (Free)", significato: "Aggiunge un importo una tantum alla categoria.", cosaMettere: "Bersaglio: categoria. Valore: €." },
          { nome: "eur_per_scostamento (Free)", significato: "Euro per ogni unità di differenza tra la risposta e il valore atteso (es. un bagno in più del normale).", cosaMettere: "Su uno stepper con attributo. Valore: € per unità." },
          { nome: "includi (Pro)", significato: "La voce o sottocategoria entra nel computo.", cosaMettere: "Bersaglio: sottocategoria o voce. Nessun valore." },
          { nome: "escludi (Pro)", significato: "La voce, sottocategoria o categoria esce dal computo.", cosaMettere: "Nessun valore." },
          { nome: "fattore_quantita (Pro)", significato: "Moltiplica la quantità stimata.", cosaMettere: "Bersaglio: sottocategoria o voce. Valore: fattore." },
          { nome: "quantita_per_unita (Pro)", significato: "Quantità = risposta numerica × valore.", cosaMettere: "Bersaglio: voce. Valore: quantità per unità." },
          { nome: "Tipo di ristrutturazione", significato: "Se vuoto l'effetto vale per tutti i tipi.", cosaMettere: "Compilalo solo se l'effetto deve pesare diversamente su leggera/moderata/totale." },
        ],
      },
      {
        titolo: "Attese e derivazioni (solo da file Excel)",
        descrizione: "Nel file «Scarica catalogo domande» ci sono due fogli in più che non hanno una schermata.",
        campi: [
          { nome: "attese", significato: "Quanti bagni/finestre/porte ha normalmente un immobile in una fascia di m². Serve sia come valore iniziale dello stepper sia come baseline dello scostamento.", cosaMettere: "Fasce chiuse (min–max) che non si sovrappongono." },
          { nome: "derivazioni", significato: "Una risposta dedotta da un'altra: «se la classe energetica è Non so, deducila dall'anno di costruzione».", cosaMettere: "Domanda, opzione «quando», domanda sorgente, opzione sorgente, opzione dedotta." },
        ],
      },
    ],
  },
  {
    id: "coefficienti",
    path: "/admin/coefficienti",
    label: "Coefficienti",
    aCosaServe: <>I numeri che trasformano i prezzi base in una stima, divisi in schede.</>,
    tabelle: [
      {
        titolo: "Schede",
        campi: [
          { nome: "Moltiplicatori", significato: "Per ogni coppia tipo × categoria, quanto pesa la categoria su una ristrutturazione leggera, moderata o totale.", cosaMettere: "Fattore: 0 = categoria assente per quel tipo, 1 = costo base pieno." },
          { nome: "Base €/m²", significato: "Gli stessi valori di Listini e prezzi, in vista tabellare.", cosaMettere: "Vedi Listini." },
          { nome: "IVA", significato: "Aliquota per categoria (Edile 10%, Finiture 22%…).", cosaMettere: "Frazione: 0.10 = 10%." },
          { nome: "Extra", significato: "Costi fissi sempre inclusi nel totale (CSE/CSP, pratiche).", cosaMettere: "Importo netto e IVA; spegni un extra invece di cancellarlo." },
          { nome: "Coefficienti Pro", significato: "Le quantità per voce × tipo del motore Pro (vedi Voci dettaglio Pro).", cosaMettere: "Quantità per m², domanda mirata o conteggio." },
          { nome: "Anteprima", significato: "Calcola una stima con i valori attuali, senza salvarla.", cosaMettere: "Usala dopo ogni modifica per controllare l'effetto." },
        ],
      },
    ],
    attenzione: [
      <><strong>Scarica parametri</strong> esporta moltiplicatori, base, extra, coefficienti Pro e forfait arredo. «Scarica con margine» include anche il coefficiente impresa: è riservato, non inoltrarlo.</>,
      <>Il foglio <strong>forfait_arredo</strong> esiste solo nel file: per ogni ambiente × livello di finitura un range in euro IVA inclusa. L'arredo viaggia accanto al totale lavori, mai dentro.</>,
    ],
  },
  {
    id: "bonus",
    path: "/admin/bonus",
    label: "Bonus fiscali",
    aCosaServe: <>Le detrazioni mostrate sotto la stima. Le aliquote cambiano per legge a data certa, quindi hanno un periodo di validità.</>,
    tabelle: [
      {
        titolo: "Tabelle",
        campi: [
          { nome: "Bonus", significato: "Ristrutturazione, Ecobonus, Mobili, Sismabonus.", cosaMettere: "Attivo solo se il wizard raccoglie l'input che serve." },
          { nome: "Aliquote per periodo", significato: "Aliquota, tetto di spesa, rate annuali per destinazione (prima casa / altro) e periodo (valida dal – fino al).", cosaMettere: "Una riga nuova per ogni cambio di legge; «fino al» vuoto = ancora valida." },
          { nome: "Categorie detraibili", significato: "Quali categorie di spesa alimentano un bonus e per quale quota.", cosaMettere: "Quota 1 = tutta. Per ogni categoria la somma delle quote sui bonus attivi non può superare 1." },
          { nome: "Extra detraibili", significato: "Come sopra, per gli extra (CSE/CSP, pratiche).", cosaMettere: "Stessa regola: somma quote ≤ 1." },
        ],
      },
    ],
  },
  {
    id: "citta-testi",
    path: "/admin/citta-testi",
    label: "Città e testi",
    aCosaServe: <>Quale listino usa ogni comune, i tipi di ristrutturazione e i testi del server (disclaimer, oggetti email).</>,
    tabelle: [
      {
        titolo: "Tabelle",
        campi: [
          { nome: "Mappature città → listino", significato: "Un comune punta a un listino. Un comune assente usa il listino default e mostra il disclaimer.", cosaMettere: "Comune, listino, codice ISTAT facoltativo." },
          { nome: "Tipi di ristrutturazione — Range %", significato: "Ampiezza della forchetta min–max attorno al valore centrale.", cosaMettere: "Frazione: 0.15 = ±15%." },
          { nome: "Testi e disclaimer", significato: "Testi mostrati dal server, per chiave.", cosaMettere: "Modifica il testo, non la chiave." },
        ],
      },
    ],
  },
  {
    id: "referenti",
    path: "/admin/referenti",
    label: "Referenti",
    aCosaServe: <>Chi riceve i lead di un listino/città. Pronto per più referenti per città.</>,
    tabelle: [
      {
        titolo: "Referente",
        campi: [
          { nome: "Listino", significato: "La città di competenza.", cosaMettere: "Il listino della città." },
          { nome: "Nome / Email / Telefono", significato: "Contatto che riceve il lead.", cosaMettere: "Email obbligatoria." },
          { nome: "Priorità", significato: "Se ci sono più referenti attivi, riceve il lead quello con il numero più basso.", cosaMettere: "0 = primo." },
          { nome: "Attivo", significato: "Un referente spento non riceve lead. Se nessuno è attivo si usa il referente del listino default.", cosaMettere: "Spegni durante ferie o cambi." },
        ],
      },
    ],
  },
  {
    id: "utenti",
    path: "/admin/utenti",
    label: "Utenti",
    aCosaServe: <>Gli account registrati e il loro ruolo.</>,
    tabelle: [
      {
        titolo: "Ruoli",
        campi: [
          { nome: "user", significato: "Cliente: fa stime, vede le proprie.", cosaMettere: "Il default." },
          { nome: "consulente", significato: "Vede solo la pagina Lead.", cosaMettere: "Per chi gestisce i contatti." },
          { nome: "admin", significato: "Vede e modifica tutto il pannello.", cosaMettere: "Il minor numero possibile di persone." },
        ],
      },
    ],
  },
];

function TabellaCampi({ tabella }: { tabella: Tabella }) {
  return (
    <div className="flex flex-col gap-2">
      <h4 className="text-sm font-semibold text-foreground">{tabella.titolo}</h4>
      {tabella.descrizione && (
        <p className="text-sm text-muted-foreground">{tabella.descrizione}</p>
      )}
      <div className="overflow-x-auto rounded-lg border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[22%]">Campo</TableHead>
              <TableHead>A cosa serve</TableHead>
              <TableHead className="w-[34%]">Cosa mettere</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tabella.campi.map((campo) => (
              <TableRow key={campo.nome}>
                <TableCell className="align-top font-medium whitespace-normal">{campo.nome}</TableCell>
                <TableCell className="align-top whitespace-normal text-muted-foreground">{campo.significato}</TableCell>
                <TableCell className="align-top whitespace-normal">{campo.cosaMettere}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

function DocumentazioneContent() {
  return (
    <div className="flex max-w-4xl flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-lg font-semibold text-foreground">Documentazione</h1>
        <p className="text-sm text-muted-foreground">
          Cosa fa ogni pagina del pannello, cosa vuol dire ogni campo e cosa metterci. Apri la
          sezione della pagina su cui devi intervenire.
        </p>
      </div>

      <section className="flex flex-col gap-3 rounded-xl border border-border p-4">
        <h2 className="text-base font-semibold text-foreground">Come ragiona la stima</h2>
        <ol className="list-decimal space-y-1.5 pl-5 text-sm">
          <li>La <strong>città</strong> sceglie il listino (Città e testi); senza mappatura si usa il listino default con disclaimer.</li>
          <li>Per ogni categoria: <strong>base €/m²</strong> (Listini) × <strong>moltiplicatore</strong> del tipo di ristrutturazione (Coefficienti) × m².</li>
          <li>Le risposte al wizard applicano gli <strong>effetti</strong> (Domande): prima i moltiplicatori, poi gli euro al m², gli importi fissi e gli scostamenti dall'atteso.</li>
          <li>Si aggiunge l'<strong>IVA</strong> della categoria e si apre la forchetta con il <strong>Range %</strong> del tipo.</li>
          <li>Si sommano gli <strong>extra</strong> fissi. L'arredo e i bonus fiscali si mostrano accanto al totale, non dentro.</li>
          <li>Nella stima <strong>Pro</strong> ogni voce del computo ha una quantità (Coefficienti Pro, effetti Pro) moltiplicata per il prezzo unitario; nelle sottocategorie «catalogo» conta solo il livello di finitura scelto.</li>
        </ol>
        <p className="text-sm text-muted-foreground">
          Il coefficiente impresa non entra mai nella stima mostrata al cliente: serve solo
          internamente.
        </p>
      </section>

      <section className="flex flex-col gap-3 rounded-xl border border-border p-4">
        <h2 className="text-base font-semibold text-foreground">Come sono collegate le tabelle</h2>
        <ul className="list-disc space-y-1.5 pl-5 text-sm">
          <li><strong>Listino</strong> → categorie del listino (base €/m²) → sottocategorie → voci → coefficienti quantità.</li>
          <li><strong>Comune</strong> → listino; <strong>referente</strong> → listino.</li>
          <li><strong>Domanda</strong> → opzioni → effetti; ogni effetto punta a una categoria, sottocategoria o voce.</li>
          <li><strong>Domanda</strong> (stepper) → attributo → attese per fascia di m².</li>
          <li><strong>Opzione</strong> di un ambiente → forfait arredo per livello di finitura.</li>
          <li><strong>Bonus</strong> → aliquote per periodo; categorie ed extra → bonus con una quota.</li>
        </ul>
        <p className="text-sm text-muted-foreground">
          Per questo si disattiva invece di cancellare: cancellare una domanda porta via le sue
          opzioni e i loro effetti.
        </p>
      </section>

      <section className="flex flex-col gap-3 rounded-xl border border-border p-4">
        <h2 className="text-base font-semibold text-foreground">Modificare tanti valori con Excel</h2>
        <ul className="list-disc space-y-1.5 pl-5 text-sm">
          <li>Scarica il file dalla pagina (listino, parametri, catalogo domande), modificalo, ricaricalo: prima di applicare vedi l'elenco delle differenze.</li>
          <li>Non toccare la colonna <code>id</code>: è ciò che collega la riga al database. Una riga senza id è una riga nuova.</li>
          <li>Una cella <strong>vuota</strong> significa «non cambiare». Per svuotare davvero un campo scrivi <code>#CANCELLA#</code>.</li>
          <li>Se qualcuno ha modificato una riga dal pannello dopo il tuo download, l'import te lo segnala: riscarica il file.</li>
          <li>Il foglio <code>ISTRUZIONI</code> del file riassume queste regole.</li>
          <li>I testi e le opzioni già a database non vengono più sovrascritti dal seed al deploy: le correzioni si fanno da qui.</li>
        </ul>
      </section>

      <Accordion type="multiple" className="rounded-xl border border-border">
        {SEZIONI.map((sezione) => (
          <AccordionItem key={sezione.id} value={sezione.id} className="px-4">
            <AccordionTrigger className="text-base font-semibold">{sezione.label}</AccordionTrigger>
            <AccordionContent>
              <div className="flex flex-col gap-4 pb-2">
                <p className="text-sm">
                  {sezione.aCosaServe}{" "}
                  <Link to={sezione.path} className="font-semibold text-primary underline-offset-4 hover:underline">
                    Apri la pagina
                  </Link>
                </p>
                {sezione.tabelle.map((tabella) => (
                  <TabellaCampi key={tabella.titolo} tabella={tabella} />
                ))}
                {sezione.attenzione && (
                  <ul className="list-disc space-y-1 rounded-lg bg-muted/50 py-3 pr-3 pl-8 text-sm">
                    {sezione.attenzione.map((nota, i) => (
                      <li key={i}>{nota}</li>
                    ))}
                  </ul>
                )}
              </div>
            </AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </div>
  );
}

export function DocumentazionePage() {
  return (
    <AdminLayout>
      <DocumentazioneContent />
    </AdminLayout>
  );
}
