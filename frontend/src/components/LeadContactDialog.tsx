import { PATH_PRIVACY } from "@/content/legale";
import { Link } from "react-router";
import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { formatEurRange } from "@/lib/currency";
import { postLead, type FasciaOraria, type PreferenzaContatto } from "@/api/lead";
import { useAuth } from "@/hooks/useAuth";
import { tipoMostrato, type StimaResponse } from "@/api/stima";

const TIPO_LABELS: Record<StimaResponse["input"]["tipo"], string> = {
  leggera: "Leggera",
  moderata: "Moderata",
  totale: "Totale",
};

const FASCIA_LABELS: Record<FasciaOraria, string> = {
  mattina: "Mattina",
  pomeriggio: "Pomeriggio",
  sera: "Sera",
};

const HEADING = "Contatta un professionista";
const SUBHEADING =
  "Un consulente ti ricontatterà per affinare la stima e organizzare un sopralluogo.";
const TELEFONO_ERROR = "Inserisci un numero di telefono valido.";
const SUCCESS_TITLE = "Richiesta inviata";
const SUCCESS_BODY = "Richiesta inviata. Un professionista ti contatterà a breve.";
const SUCCESS_TOAST = "Richiesta inviata con successo";
const ERROR_COPY = "Non siamo riusciti a inviare la richiesta. Riprova tra qualche istante.";

const TELEFONO_RE = /^[0-9+\s().-]{6,20}$/;

interface LeadContactDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Stima corrente gia' calcolata: lo snapshot allegato e' esattamente questa, mai ricalcolata. */
  result: StimaResponse;
}

/**
 * Form contatto in dialog (UI-SPEC §A). GUARDIA DOMINIO (D-22): payload e
 * snapshot render costruiti SOLO dai campi a range gia' su schermo
 * (citta/mq/tipo/totale_min/totale_max) — mai i campi riservati lato
 * server relativi al margine impresa.
 */
export function LeadContactDialog({ open, onOpenChange, result }: LeadContactDialogProps) {
  const { user } = useAuth();

  const [nome, setNome] = useState(user?.nome ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [telefono, setTelefono] = useState("");
  const [messaggio, setMessaggio] = useState("");
  const [preferenza, setPreferenza] = useState<PreferenzaContatto | "">("");
  const [fasciaOraria, setFasciaOraria] = useState<FasciaOraria | "">("");
  const [touched, setTouched] = useState<{ telefono?: boolean; preferenza?: boolean }>({});

  const mutation = useMutation({ mutationFn: postLead });

  // Riprecompila nome/email quando il dialog si riapre con un account diverso.
  useEffect(() => {
    if (open) {
      setNome(user?.nome ?? "");
      setEmail(user?.email ?? "");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const telefonoValid = TELEFONO_RE.test(telefono.trim());
  const preferenzaValid = preferenza !== "";
  const formValid = nome.trim().length > 0 && email.trim().length > 0 && telefonoValid && preferenzaValid;

  function handleOpenChange(next: boolean) {
    if (!next) {
      mutation.reset();
      setTelefono("");
      setMessaggio("");
      setPreferenza("");
      setFasciaOraria("");
      setTouched({});
    }
    onOpenChange(next);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setTouched({ telefono: true, preferenza: true });
    if (!formValid) return;

    mutation.mutate(
      {
        nome: nome.trim(),
        email: email.trim(),
        telefono: telefono.trim(),
        messaggio: messaggio.trim() ? messaggio.trim() : undefined,
        preferenza_contatto: preferenza,
        fascia_oraria: fasciaOraria === "" ? undefined : fasciaOraria,
        citta: result.input.citta,
        mq: result.input.mq,
        tipo: tipoMostrato(result),
        totale_min: result.totale.totale_min,
        totale_max: result.totale.totale_max,
      },
      {
        onSuccess: () => {
          toast.success(SUCCESS_TOAST);
        },
      }
    );
  }

  const showSuccess = mutation.isSuccess;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[480px]">
        {showSuccess ? (
          <>
            <DialogHeader>
              <DialogTitle>{SUCCESS_TITLE}</DialogTitle>
            </DialogHeader>
            <p className="text-sm text-foreground">{SUCCESS_BODY}</p>
            <Button type="button" variant="outline" onClick={() => handleOpenChange(false)}>
              Chiudi
            </Button>
          </>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>{HEADING}</DialogTitle>
              <DialogDescription>{SUBHEADING}</DialogDescription>
            </DialogHeader>

            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="lead-nome">Nome</Label>
                <Input
                  id="lead-nome"
                  value={nome}
                  onChange={(e) => setNome(e.target.value)}
                />
              </div>

              <div className="flex flex-col gap-2">
                <Label htmlFor="lead-email">Email</Label>
                <Input
                  id="lead-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>

              <div className="flex flex-col gap-2">
                <Label htmlFor="lead-telefono">Telefono</Label>
                <Input
                  id="lead-telefono"
                  inputMode="tel"
                  value={telefono}
                  onChange={(e) => setTelefono(e.target.value)}
                  onBlur={() => setTouched((t) => ({ ...t, telefono: true }))}
                  aria-invalid={touched.telefono && !telefonoValid}
                />
                {touched.telefono && !telefonoValid && (
                  <p className="text-sm text-destructive">{TELEFONO_ERROR}</p>
                )}
              </div>

              <div className="flex flex-col gap-2">
                <Label>Come preferisci essere ricontattato?</Label>
                <RadioGroup
                  value={preferenza}
                  onValueChange={(value) => setPreferenza(value as PreferenzaContatto)}
                  onBlur={() => setTouched((t) => ({ ...t, preferenza: true }))}
                  className="grid-cols-2"
                >
                  <Label className="flex items-center gap-2 font-normal">
                    <RadioGroupItem value="email" />
                    Email
                  </Label>
                  <Label className="flex items-center gap-2 font-normal">
                    <RadioGroupItem value="telefono" />
                    Telefono
                  </Label>
                </RadioGroup>
              </div>

              <div className="flex flex-col gap-2">
                <Label htmlFor="lead-fascia">Fascia oraria preferita (facoltativo)</Label>
                <Select
                  value={fasciaOraria}
                  onValueChange={(value) => setFasciaOraria(value as FasciaOraria)}
                >
                  <SelectTrigger id="lead-fascia" className="w-full">
                    <SelectValue placeholder="Seleziona una fascia oraria" />
                  </SelectTrigger>
                  <SelectContent>
                    {(Object.keys(FASCIA_LABELS) as FasciaOraria[]).map((value) => (
                      <SelectItem key={value} value={value}>
                        {FASCIA_LABELS[value]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="flex flex-col gap-2">
                <Label htmlFor="lead-messaggio">Messaggio (facoltativo)</Label>
                <Textarea
                  id="lead-messaggio"
                  rows={3}
                  value={messaggio}
                  onChange={(e) => setMessaggio(e.target.value)}
                />
              </div>

              <div className="rounded-lg border border-border bg-secondary px-4 py-3 text-sm text-muted-foreground">
                Alleghiamo alla richiesta la stima che stai visualizzando: {result.input.citta} ·{" "}
                {result.input.mq} m² · {TIPO_LABELS[tipoMostrato(result)]} ·{" "}
                <span className="font-semibold text-foreground">
                  {formatEurRange(result.totale.totale_min, result.totale.totale_max)}
                </span>
                .
              </div>

              <Button
                type="submit"
                disabled={mutation.isPending}
                className="h-11 w-full bg-primary text-base font-semibold text-primary-foreground hover:bg-primary/90"
              >
                {mutation.isPending ? (
                  <span className="flex items-center justify-center gap-2">
                    <Loader2 className="size-4 animate-spin" aria-hidden />
                    Invio in corso...
                  </span>
                ) : (
                  "Invia richiesta"
                )}
              </Button>
              <p className="text-xs leading-relaxed text-muted-foreground">
                Inviamo la tua richiesta e la stima al professionista che segue la tua zona, che ti
                ricontatterà per un preventivo. Dettagli nell'
                <Link to={PATH_PRIVACY} target="_blank" className="font-medium text-primary underline underline-offset-4">
                  informativa privacy
                </Link>
                .
              </p>

              {mutation.isError && (
                <p className="text-center text-sm text-destructive">{ERROR_COPY}</p>
              )}
            </form>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
