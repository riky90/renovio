import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { DomandaField } from "@/components/DomandaField";
import {
  CAMPI_BASE_INIZIALI,
  CittaField,
  DestinazioneField,
  MqField,
  OptionCard,
  TipoField,
  toEstimateFormValues,
  validaCampiBase,
  type CampiBase,
  type EstimateFormValues,
} from "@/components/EstimateFormFields";
import { ImportoField } from "@/components/ImportoField";
import { cn } from "@/lib/utils";
import { risposteDopoCatalogo, soloVisibili } from "@/lib/richiestaStima";
import {
  domandeVisibili,
  getCatalogoDomande,
  isNumerico,
  risposteIniziali,
  type CatalogoDomande,
  type Domanda,
  type Risposte,
  type ValoreRisposta,
} from "@/api/domande";
import { getOpzioniPro, type OpzioniProOut, type PreferenzePro } from "@/api/stima";

export interface EstimateWizardSubmit {
  values: EstimateFormValues;
  risposte: Risposte;
  /** Solo in tier Pro: livelli di finitura e domande mirate del motore Pro. */
  preferenze?: PreferenzePro;
  /** Budget dichiarato (facoltativo, IVA inclusa). Non e' una risposta di catalogo. */
  budget?: number | null;
}

interface EstimateWizardProps {
  tier: "free" | "pro";
  onSubmit: (payload: EstimateWizardSubmit) => void;
  isSubmitting?: boolean;
  /** Valori iniziali del "Rifai in versione Pro" (query param). */
  iniziali?: Partial<CampiBase>;
  /**
   * Risposte gia' note da cui ripartire (09-12, "Vai alla stima Pro" da una
   * stima non salvata): le chiavi con valore diverso dal default del primo
   * catalogo contano come toccate e i default non le sovrascrivono.
   */
  risposteDiPartenza?: Risposte;
  /**
   * Step da cui aprire il wizard. Solo di presentazione (T-09-50): il server
   * rivalida tutto al salvataggio, non e' un modo per saltare la validazione.
   * Ignorato se `iniziali` non basta a superare lo step 1, o se fuori dal
   * range degli step del tier.
   */
  stepIniziale?: number;
  /** Budget da cui ripartire (es. "Modifica" dalla pagina risultato). */
  budgetIniziale?: number | null;
}

/**
 * Il wizard unico: un solo form per Free e Pro, con gli step che cambiano.
 *
 * Prima erano due componenti -- `EstimateForm` (uno step) e `EstimateFormPro`
 * (due) -- e le domande erano una costante dentro il secondo. Il motivo per cui
 * collassano qui non e' la duplicazione del markup: e' che il catalogo domande
 * rende i due form lo stesso form con un filtro diverso sul tier. Tenerli
 * separati avrebbe significato due posti in cui montare le stesse domande.
 *
 * Gli step sono di presentazione, non di dominio: raggruppano le domande per
 * `gruppo`, e un gruppo che il wizard non conosce finisce nello step 3 invece
 * di sparire. Una domanda nuova in un gruppo nuovo resta visibile anche senza
 * un deploy del frontend -- che e' tutto il punto della fase.
 */
export function EstimateWizard({
  tier,
  onSubmit,
  isSubmitting,
  iniziali,
  risposteDiPartenza,
  stepIniziale,
  budgetIniziale,
}: EstimateWizardProps) {
  const [campi, setCampi] = useState<CampiBase>({ ...CAMPI_BASE_INIZIALI, ...iniziali });
  const [step, setStep] = useState(() => {
    // `stepIniziale` parte SOLO se i campi base sono gia' validi: altrimenti
    // l'utente si troverebbe su uno step avanzato senza citta'/mq compilati.
    const ultimoStepDelTier = tier === "pro" ? 4 : 3;
    if (
      stepIniziale !== undefined &&
      stepIniziale >= 1 &&
      stepIniziale <= ultimoStepDelTier &&
      validaCampiBase({ ...CAMPI_BASE_INIZIALI, ...iniziali }).valid
    ) {
      return stepIniziale;
    }
    return 1;
  });
  const [touched, setTouched] = useState(false);
  const [budget, setBudget] = useState<number | null>(budgetIniziale ?? null);
  const [budgetErrore, setBudgetErrore] = useState(false);
  const [risposte, setRisposte] = useState<Risposte>(risposteDiPartenza ?? {});
  // Codici delle risposte date davvero dall'utente (G3, 10-11). Per-codice e non
  // un flag globale: al cambio di m2 i default della nuova fascia (bagni, porte,
  // finestre...) vanno riapplicati alle domande lasciate al default, altrimenti
  // due stime con gli stessi input visibili partono da risposte diverse.
  // Per `risposteDiPartenza` contano come toccate solo le chiavi con valore
  // diverso dal default del primo catalogo caricato (la richiesta ripassata da
  // "Modifica" porta il valore di ogni domanda, default compresi).
  const risposteToccate = useRef<Set<string>>(new Set());
  const primoCatalogoGestito = useRef(false);
  const [livelli, setLivelli] = useState<Record<string, string>>({});
  const [scelte, setScelte] = useState<Record<string, string>>({});
  const [scelteToccate, setScelteToccate] = useState<Set<string>>(new Set());

  const { mq, valid: baseValid, cittaValid, mqValid } = validaCampiBase(campi);
  const step1Valid = cittaValid && mqValid;

  // Il catalogo si ricarica quando cambiano i m2: i default degli stepper
  // dipendono dalla fascia, e servirli per una superficie diversa da quella
  // digitata farebbe partire lo scostamento da una baseline sbagliata.
  // E quando cambia il tipo (Fase 11): il tipo e' un preset delle risposte
  // sugli interventi, e i suoi default si riapplicano alle domande non
  // toccate. `keepPreviousData` evita lo scheletro a ogni cambio di tipo.
  const tipoScelto = campi.tipo ?? undefined;
  const catalogoQuery = useQuery<CatalogoDomande>({
    queryKey: ["catalogo-domande", tier, step1Valid ? mq : null, tipoScelto ?? null],
    queryFn: () =>
      getCatalogoDomande({ tier, mq: step1Valid ? mq : undefined, tipo: tipoScelto }),
    enabled: step1Valid,
    placeholderData: keepPreviousData,
  });

  const opzioniProQuery = useQuery<OpzioniProOut>({
    queryKey: ["opzioni-pro"],
    queryFn: getOpzioniPro,
    enabled: tier === "pro",
  });

  const catalogo = catalogoQuery.data;

  // I default arrivano dal server, quindi si applicano quando il catalogo
  // arriva -- e di nuovo a ogni cambio di m2. `risposteToccate` protegge le
  // risposte gia' date: chi ha messo 3 bagni e poi corregge i m2 non se li
  // vede riportare al valore standard.
  useEffect(() => {
    if (!catalogo) return;
    const defaults = risposteIniziali(catalogo);
    const primo = !primoCatalogoGestito.current;
    primoCatalogoGestito.current = true;
    setRisposte((precedenti) =>
      risposteDopoCatalogo(defaults, precedenti, risposteToccate.current, risposteDiPartenza, primo)
    );
    // risposteDiPartenza si legge solo al primo catalogo: e' un valore iniziale.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [catalogo]);

  // Stesso pattern delle risposte del catalogo Free: il default (D-07) arriva
  // gia' risolto dal server in `opzioni.domande[].valore`, si applica quando
  // le opzioni arrivano, e non sovrascrive le scelte che l'utente ha gia'
  // fatto (`scelteToccate`).
  useEffect(() => {
    const opzioni = opzioniProQuery.data;
    if (!opzioni) return;
    setScelte((precedenti) => {
      let cambiato = false;
      const aggiornate = { ...precedenti };
      for (const domanda of opzioni.domande) {
        if (scelteToccate.has(domanda.code)) continue;
        if (typeof domanda.valore === "string" && aggiornate[domanda.code] !== domanda.valore) {
          aggiornate[domanda.code] = domanda.valore;
          cambiato = true;
        }
      }
      return cambiato ? aggiornate : precedenti;
    });
  }, [opzioniProQuery.data, scelteToccate]);

  const visibili = useMemo(
    () => (catalogo ? domandeVisibili(catalogo.domande, risposte) : []),
    [catalogo, risposte]
  );

  const steps = useMemo(() => costruisciStep(visibili, tier), [visibili, tier]);
  const ultimoStep = steps.length;

  function handleChange(patch: Partial<CampiBase>) {
    setCampi((prev) => ({ ...prev, ...patch }));
  }

  function handleRisposta(code: string, valore: ValoreRisposta) {
    risposteToccate.current.add(code);
    setRisposte((prev) => ({ ...prev, [code]: valore }));
  }

  function handleScelta(code: string, valore: string) {
    setScelteToccate((prev) => new Set(prev).add(code));
    setScelte((prev) => ({ ...prev, [code]: valore }));
  }

  function applicaValoriStandard() {
    if (!catalogo) return;
    risposteToccate.current.clear();
    setRisposte(risposteIniziali(catalogo));
  }

  function avanti(e: FormEvent) {
    e.preventDefault();
    setTouched(true);
    if (step === 1 && !step1Valid) return;
    if (step === 3 && !baseValid) return;
    // `touched` si azzera passando allo step successivo: e' "hai gia' provato a
    // mandare QUESTO step", non "hai gia' provato a mandare qualcosa". Senza
    // questa riga, chi arriva allo step 3 ci trova gia' scritto "seleziona il
    // tipo" — un errore su un campo che non ha ancora avuto modo di compilare.
    setTouched(false);
    setStep((s) => Math.min(ultimoStep, s + 1));
  }

  function invia(e: FormEvent) {
    e.preventDefault();
    setTouched(true);
    const values = toEstimateFormValues(campi);
    if (values === null) {
      // Un campo base invalido vive allo step 1 o allo step 3: ci si torna,
      // invece di lasciare un bottone che non fa niente.
      setStep(step1Valid ? 3 : 1);
      return;
    }
    // Le risposte vanno SEMPRE, anche identiche ai default: `{}` accende il
    // layer con tutte le domande sui loro default, `undefined` lo spegne -- e
    // spegnerlo qui vorrebbe dire buttare via quello che l'utente ha appena
    // compilato.
    onSubmit({
      values,
      risposte: soloVisibili(risposte, visibili),
      budget: budgetErrore ? null : budget,
      ...(tier === "pro" ? { preferenze: preferenzePro(livelli, risposte, scelte) } : {}),
    });
  }

  const stepCorrente = steps[step - 1];

  // Al cambio di step si riparte dall'inizio del wizard, con il focus sul
  // titolo dello step: chi preme "Continua" in fondo a uno step lungo non deve
  // ritrovarsi a meta' del successivo, e un lettore di schermo annuncia dove si
  // trova. Non al primo render: la pagina non deve saltare all'apertura.
  const titoloStepRef = useRef<HTMLHeadingElement>(null);
  const primoRender = useRef(true);
  useEffect(() => {
    if (primoRender.current) {
      primoRender.current = false;
      return;
    }
    const titolo = titoloStepRef.current;
    if (!titolo) return;
    titolo.focus({ preventScroll: true });
    const top = titolo.getBoundingClientRect().top + window.scrollY - 96;
    if (top < window.scrollY) window.scrollTo({ top, behavior: "smooth" });
  }, [step]);

  return (
    <form onSubmit={step === ultimoStep ? invia : avanti} className="flex w-full flex-col gap-6">
      <StepIndicator steps={steps} corrente={step} />
      <h2 ref={titoloStepRef} tabIndex={-1} className="sr-only">
        Passaggio {step} di {steps.length}: {stepCorrente?.titolo}
      </h2>

      {step === 1 && (
        <>
          <CittaField values={campi} onChange={handleChange} touched={touched} />
          <MqField values={campi} onChange={handleChange} touched={touched} />
          <p className="text-sm text-muted-foreground">
            La superficie serve subito: da quella dipendono i valori standard che ti
            proponiamo nei passaggi successivi.
          </p>
        </>
      )}

      {step > 1 && catalogoQuery.isLoading && <Skeleton className="h-64 w-full rounded-xl" />}

      {step > 1 && catalogoQuery.isError && (
        <Alert variant="destructive">
          <AlertDescription>
            Non siamo riusciti a caricare le domande. Torna indietro e riprova.
          </AlertDescription>
        </Alert>
      )}

      {step === 2 && stepCorrente && (
        <>
          <ValoriStandardHint onApplica={applicaValoriStandard} domande={stepCorrente.domande} />
          {stepCorrente.domande.map((domanda) => (
            <DomandaField
              key={domanda.code}
              domanda={domanda}
              valore={risposte[domanda.code]}
              onChange={(valore) => handleRisposta(domanda.code, valore)}
            />
          ))}
        </>
      )}

      {step === 3 && (
        <>
          <TipoField values={campi} onChange={handleChange} touched={touched} />
          <StepLavori
            domande={stepCorrente?.domande ?? []}
            risposte={risposte}
            onRisposta={handleRisposta}
            tipoScelto={!!campi.tipo}
          />
          <DestinazioneField values={campi} onChange={handleChange} />
          <div className="flex flex-col gap-2">
            <Label htmlFor="budget-importo" className="text-sm font-semibold">
              Qual è il tuo budget per la ristrutturazione?
            </Label>
            <p id="budget-help" className="text-sm text-muted-foreground">
              Facoltativo. Scrivi la cifra che hai in mente, IVA inclusa: non cambia la stima, ci
              serve per dirti se ci rientri.
            </p>
            <ImportoField
              id="budget-importo"
              valore={budget}
              describedBy="budget-help"
              onChange={(v, errore) => {
                setBudget(v);
                setBudgetErrore(errore);
              }}
            />
          </div>
        </>
      )}

      {step === 4 && (
        <FinitureStep
          opzioni={opzioniProQuery.data}
          isLoading={opzioniProQuery.isLoading}
          livelli={livelli}
          onLivello={(categoria, livello) =>
            setLivelli((prev) => ({ ...prev, [categoria]: livello }))
          }
          domande={stepCorrente?.domande ?? []}
          risposte={risposte}
          onRisposta={handleRisposta}
          scelte={scelte}
          onScelta={handleScelta}
        />
      )}

      <Navigazione
        step={step}
        ultimoStep={ultimoStep}
        indietro={() => setStep((s) => Math.max(1, s - 1))}
        avantiDisabilitato={step === 1 ? !step1Valid : step === 3 ? !baseValid : false}
        isSubmitting={isSubmitting}
        tier={tier}
      />
    </form>
  );
}

// --- composizione degli step ------------------------------------------------

interface StepDef {
  numero: number;
  titolo: string;
  domande: Domanda[];
}

/**
 * Quali gruppi del catalogo finiscono in quale step.
 *
 * E' una mappa di PRESENTAZIONE e non di dominio: dice dove si disegna una
 * domanda, mai cosa fa. Un gruppo assente da questa mappa non sparisce -- cade
 * nello step 3 -- perche' il modo in cui questa fase puo' fallire in silenzio
 * e' proprio quello: l'admin crea un gruppo nuovo, il wizard non lo riconosce,
 * e la domanda non viene mai posta pur restando attiva in tabella.
 */
const GRUPPI_PER_STEP: Record<string, number> = {
  immobile: 2,
  ambienti: 2,
  ristrutturazione: 3,
  energia: 3,
  // L'arredo cadrebbe qui comunque per ripiego. E' elencato per SCELTA:
  // sta nello step della ristrutturazione perche' e' li' che l'utente
  // ragiona su cosa vuole ottenere, non su com'e' fatta la casa.
  arredo: 3,
};

const STEP_DI_RIPIEGO = 3;

function costruisciStep(domande: Domanda[], tier: "free" | "pro"): StepDef[] {
  const perStep = new Map<number, Domanda[]>();

  for (const domanda of domande) {
    // Le domande Pro hanno il loro step; le Free restano dove il gruppo dice,
    // anche per un utente Pro, cosi' il wizard e' lo stesso per entrambi.
    const numero =
      domanda.tier_minimo === "pro" ? 4 : (GRUPPI_PER_STEP[domanda.gruppo] ?? STEP_DI_RIPIEGO);
    perStep.set(numero, [...(perStep.get(numero) ?? []), domanda]);
  }

  const steps: StepDef[] = [
    { numero: 1, titolo: "Dove", domande: [] },
    { numero: 2, titolo: "La casa", domande: perStep.get(2) ?? [] },
    { numero: 3, titolo: "I lavori", domande: perStep.get(3) ?? [] },
  ];

  if (tier === "pro") {
    steps.push({ numero: 4, titolo: "Finiture", domande: perStep.get(4) ?? [] });
  }

  return steps;
}

/**
 * Le tre domande mirate del motore Pro (`coefficiente_qta_voce.domanda_mirata_key`).
 *
 * NON e' il catalogo: e' il contratto che il motore Pro si aspetta ancora, e
 * che la Fase 09 sostituisce quando anche il configuratore Pro passera' dal
 * catalogo. Fino ad allora tutte e tre le chiavi esistono come domande del
 * catalogo (`bagni`, `porte`, `condizionatori`) e si leggono da li' invece di
 * chiederle una seconda volta. Quello che resta da sciogliere non e' piu' una
 * domanda mancante: e' che questo oggetto ha tre campi fissi, mentre una
 * quarta chiave mirata creata dal pannello admin non avrebbe dove entrare.
 */
function preferenzePro(
  livelli: Record<string, string>,
  risposte: Risposte,
  scelte: Record<string, string>
): PreferenzePro {
  const numero = (code: string): number => {
    const valore = risposte[code];
    return typeof valore === "number" ? valore : 0;
  };

  return {
    ...(Object.keys(livelli).length > 0 ? { livelli } : {}),
    risposte: {
      bagni: numero("bagni"),
      porte: numero("porte"),
      condizionatori: numero("condizionatori"),
    },
    ...(Object.keys(scelte).length > 0 ? { scelte } : {}),
  };
}

// --- pezzi di UI ------------------------------------------------------------

function ValoriStandardHint({
  onApplica,
  domande,
}: {
  onApplica: () => void;
  domande: Domanda[];
}) {
  // Il suggerimento ha senso solo se in questo step c'e' qualcosa di numerico
  // da riportare allo standard.
  if (!domande.some((d) => isNumerico(d.tipo_controllo))) return null;

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-border bg-accent/30 p-4 sm:flex-row sm:items-center sm:justify-between">
      <p className="text-sm text-muted-foreground">
        Abbiamo gia' compilato i valori tipici per la tua superficie. Puoi cambiarli anche
        dopo.
      </p>
      <Button type="button" variant="outline" size="sm" onClick={onApplica} className="shrink-0">
        Vai avanti con i valori standard
      </Button>
    </div>
  );
}

function FinitureStep({
  opzioni,
  isLoading,
  livelli,
  onLivello,
  domande,
  risposte,
  onRisposta,
  scelte,
  onScelta,
}: {
  opzioni: OpzioniProOut | undefined;
  isLoading: boolean;
  livelli: Record<string, string>;
  onLivello: (categoria: string, livello: string) => void;
  domande: Domanda[];
  risposte: Risposte;
  onRisposta: (code: string, valore: ValoreRisposta) => void;
  scelte: Record<string, string>;
  onScelta: (code: string, valore: string) => void;
}) {
  // Il livello scelto allo step 3 (`livello_finiture`) e' il punto di partenza
  // di ogni categoria: il motore Pro fa lo stesso ponte, cosi' la card
  // selezionata qui e' quella che il dettaglio calcolera'.
  const livelloWizard = risposte.livello_finiture;
  const defaultLivello =
    opzioni?.livelli.find((l) => l.code === livelloWizard)?.code ??
    opzioni?.livelli.find((l) => l.is_default)?.code;

  return (
    <>
      {isLoading && <Skeleton className="h-40 w-full rounded-xl" />}

      {opzioni?.categorie.map((categoria) => (
        <div key={categoria.code} className="flex flex-col gap-2">
          <Label>Livello di finitura · {categoria.nome}</Label>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {opzioni.livelli.map((livello) => (
              <OptionCard
                key={livello.code}
                nome={livello.nome}
                descrizione={livello.descrizione ?? ""}
                selected={(livelli[categoria.code] ?? defaultLivello) === livello.code}
                onSelect={() => onLivello(categoria.code, livello.code)}
              />
            ))}
          </div>
        </div>
      ))}

      {/* Domande a scelta del configuratore (09-11, es. "Che pavimento vuoi per
          casa?"): DOPO i livelli per categoria, stesso ordine dell'UI-SPEC.
          Titolo/aiuto vengono dal catalogo (CFG-01/QST-05), nessuna etichetta
          cablata qui. */}
      {opzioni?.domande.map((domanda) => (
        <DomandaField
          key={domanda.code}
          domanda={domanda}
          valore={scelte[domanda.code]}
          onChange={(valore) => {
            if (typeof valore === "string") onScelta(domanda.code, valore);
          }}
        />
      ))}

      {domande.map((domanda) => (
        <DomandaField
          key={domanda.code}
          domanda={domanda}
          valore={risposte[domanda.code]}
          onChange={(valore) => onRisposta(domanda.code, valore)}
        />
      ))}
    </>
  );
}

function Navigazione({
  step,
  ultimoStep,
  indietro,
  avantiDisabilitato,
  isSubmitting,
  tier,
}: {
  step: number;
  ultimoStep: number;
  indietro: () => void;
  avantiDisabilitato: boolean;
  isSubmitting?: boolean;
  tier: "free" | "pro";
}) {
  const ultimo = step === ultimoStep;

  return (
    <div className="flex flex-col gap-3 sm:flex-row">
      {step > 1 && (
        <Button type="button" variant="outline" onClick={indietro} className="h-12 sm:w-40">
          <ArrowLeft className="size-4" />
          Indietro
        </Button>
      )}
      <Button
        type="submit"
        disabled={avantiDisabilitato || (ultimo && isSubmitting)}
        className="group h-12 flex-1 bg-primary text-base font-semibold text-primary-foreground shadow-sm hover:bg-primary/90"
      >
        {ultimo && isSubmitting ? (
          "Calcolo in corso..."
        ) : (
          <>
            {ultimo ? (tier === "pro" ? "Calcola la stima Pro" : "Calcola la stima") : "Continua"}
            <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
          </>
        )}
      </Button>
    </div>
  );
}

function StepIndicator({ steps, corrente }: { steps: StepDef[]; corrente: number }) {
  return (
    <ol className="flex items-center gap-3" aria-label="Avanzamento">
      {steps.map((step) => (
        <li
          key={step.numero}
          className="flex flex-1 flex-col gap-1.5"
          aria-current={step.numero === corrente ? "step" : undefined}
        >
          <span
            className={cn("h-1 rounded-full", step.numero <= corrente ? "bg-primary" : "bg-border")}
          />
          <span
            className={cn(
              "text-xs font-medium",
              step.numero <= corrente ? "text-foreground" : "text-muted-foreground"
            )}
          >
            {step.numero}. {step.titolo}
          </span>
        </li>
      ))}
    </ol>
  );
}

/**
 * Le domande che restano SEMPRE in vista nello step dei lavori: le altre del
 * gruppo `ristrutturazione` sono gli interventi, gia' precompilati dal preset
 * del tipo e riassunti, da aprire solo se serve. Mappe di PRESENTAZIONE come
 * `GRUPPI_PER_STEP`: una domanda nuova creata dal pannello finisce comunque
 * fra gli interventi, mai fuori dal wizard.
 */
const DOMANDE_IN_EVIDENZA = new Set(["livello_finiture"]);

/** Gruppi resi come sezioni facoltative, chiuse di default. */
const SEZIONI_FACOLTATIVE: { gruppo: string; titolo: string; descrizione: string }[] = [
  {
    gruppo: "energia",
    titolo: "Risparmio energetico",
    descrizione: "Classe energetica e interventi di efficientamento.",
  },
  {
    gruppo: "arredo",
    titolo: "Arredo",
    descrizione: "Una stima dell'arredo, mostrata accanto al totale dei lavori.",
  },
];

/** Etichette brevi per il riepilogo degli interventi. */
const RIEPILOGO: Record<string, string> = {
  interv_pavimenti: "Pavimenti",
  interv_bagni: "Bagni",
  interv_cucina: "Impianti cucina",
  interv_elettrico: "Impianto elettrico",
  interv_riscaldamento: "Riscaldamento",
  interv_clima: "Climatizzazione",
  interv_caldaia: "Caldaia nuova",
  interv_porte: "Porte interne",
  interv_serramenti: "Finestre",
  tinteggiatura: "Tinteggiatura",
  controsoffitti_mq: "Controsoffitti (m²)",
};

function etichettaRisposta(domanda: Domanda, valore: ValoreRisposta | undefined): string | null {
  if (valore === undefined || valore === null) return null;
  if (isNumerico(domanda.tipo_controllo)) return String(valore);
  const codici = Array.isArray(valore) ? valore : [valore];
  const etichette = codici
    .map((c) => domanda.opzioni.find((o) => o.code === c)?.etichetta)
    .filter((e): e is string => !!e);
  return etichette.length ? etichette.join(", ") : null;
}

function StepLavori({
  domande,
  risposte,
  onRisposta,
  tipoScelto,
}: {
  domande: Domanda[];
  risposte: Risposte;
  onRisposta: (code: string, valore: ValoreRisposta) => void;
  tipoScelto: boolean;
}) {
  const campo = (domanda: Domanda) => (
    <DomandaField
      key={domanda.code}
      domanda={domanda}
      valore={risposte[domanda.code]}
      onChange={(valore) => onRisposta(domanda.code, valore)}
    />
  );
  const facoltativi = new Set(SEZIONI_FACOLTATIVE.map((s) => s.gruppo));
  const inEvidenza = domande.filter((d) => DOMANDE_IN_EVIDENZA.has(d.code));
  const interventi = domande.filter((d) => !DOMANDE_IN_EVIDENZA.has(d.code) && !facoltativi.has(d.gruppo));
  const riepilogo = interventi
    .filter((d) => RIEPILOGO[d.code])
    .map((d) => ({ code: d.code, nome: RIEPILOGO[d.code], valore: etichettaRisposta(d, risposte[d.code]) }))
    .filter((r) => r.valore);

  return (
    <>
      {inEvidenza.map(campo)}
      {interventi.length > 0 && (
        <SezioneComprimibile
          id="lavori-inclusi"
          titolo="I lavori inclusi"
          descrizione={
            tipoScelto
              ? "Li abbiamo precompilati in base al tipo di ristrutturazione: cambia solo quello che non torna."
              : "Scegli il tipo di ristrutturazione: precompiliamo i lavori di conseguenza."
          }
          etichettaApri="Personalizza i lavori"
          riepilogo={
            riepilogo.length > 0 && (
              <dl className="grid grid-cols-1 gap-x-4 gap-y-1.5 text-sm sm:grid-cols-2">
                {riepilogo.map((r) => (
                  <div key={r.code} className="flex justify-between gap-3 border-b border-border/60 pb-1.5">
                    <dt className="text-muted-foreground">{r.nome}</dt>
                    <dd className="text-right font-medium text-foreground">{r.valore}</dd>
                  </div>
                ))}
              </dl>
            )
          }
        >
          {interventi.map(campo)}
        </SezioneComprimibile>
      )}
      {SEZIONI_FACOLTATIVE.map((sezione) => {
        const delGruppo = domande.filter((d) => d.gruppo === sezione.gruppo);
        if (!delGruppo.length) return null;
        return (
          <SezioneComprimibile
            key={sezione.gruppo}
            id={`sezione-${sezione.gruppo}`}
            titolo={sezione.titolo}
            descrizione={sezione.descrizione}
            facoltativa
            etichettaApri="Aggiungi"
          >
            {delGruppo.map(campo)}
          </SezioneComprimibile>
        );
      })}
    </>
  );
}

/**
 * Sezione richiudibile del wizard. Il contenuto resta montato anche chiuso
 * (`hidden`): le risposte e lo stato dei campi non si perdono aprendo e
 * chiudendo, e il riepilogo legge sempre i valori correnti.
 */
function SezioneComprimibile({
  id,
  titolo,
  descrizione,
  riepilogo,
  facoltativa,
  etichettaApri,
  children,
}: {
  id: string;
  titolo: string;
  descrizione: string;
  riepilogo?: React.ReactNode;
  facoltativa?: boolean;
  etichettaApri: string;
  children: React.ReactNode;
}) {
  const [aperta, setAperta] = useState(false);
  const idContenuto = `${id}-contenuto`;
  return (
    <section aria-labelledby={`${id}-titolo`} className="rounded-xl border border-border bg-secondary/30 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h3 id={`${id}-titolo`} className="font-sans text-sm font-semibold text-foreground">
            {titolo}
            {facoltativa && <span className="ml-2 text-xs font-normal text-muted-foreground">facoltativo</span>}
          </h3>
          <p className="mt-0.5 text-sm text-muted-foreground">{descrizione}</p>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="self-start sm:shrink-0"
          aria-expanded={aperta}
          aria-controls={idContenuto}
          onClick={() => setAperta((a) => !a)}
        >
          {aperta ? "Chiudi" : etichettaApri}
          <ChevronDown className={cn("size-4 transition-transform", aperta && "rotate-180")} aria-hidden />
        </Button>
      </div>
      {!aperta && riepilogo && <div className="mt-3">{riepilogo}</div>}
      <div id={idContenuto} hidden={!aperta} className="mt-4 flex flex-col gap-6">
        {children}
      </div>
    </section>
  );
}
