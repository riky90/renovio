import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Pencil, Power } from "lucide-react";
import { AdminTable } from "@/components/admin/AdminTable";
import { AdminCrudDialog } from "@/components/admin/AdminCrudDialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { ApiError } from "@/api/admin/client";
import { EMPTY_HEADING } from "@/lib/adminCopy";
import {
  DOMANDE_QUERY_KEY,
  chiaveOpzioni,
  chiaveEffetti,
  getOpzioni,
  getEffetti,
  createOpzione,
  updateOpzione,
  type DomandaOut,
  type OpzioneOut,
  type EffettoOut,
  type OpzioneCreateInput,
  type OpzionePatchInput,
} from "@/api/admin/domande";

const SAVE_ERROR = "Non siamo riusciti a salvare la modifica. Riprova.";
const EMPTY_BODY_OPZIONI =
  "Aggiungi la prima opzione con il pulsante qui sopra, oppure carica un file.";

interface OpzioniSezioneProps {
  domanda: DomandaOut;
  selectedOpzioneId: number | null;
  onSelectOpzione: (id: number) => void;
  onChiudi: () => void;
}

interface OpzioneFormState {
  code: string;
  etichetta: string;
  descrizione: string;
  immagineUrl: string;
  isDefault: boolean;
  ordine: string;
  attiva: boolean;
}

const FORM_VUOTO: OpzioneFormState = {
  code: "",
  etichetta: "",
  descrizione: "",
  immagineUrl: "",
  isDefault: false,
  ordine: "0",
  attiva: true,
};

/**
 * Secondo livello del master-detail (D-24): sotto la domanda scelta, le sue
 * opzioni. Il toggle Attiva puo' essere rifiutato dal backend (D-27/D-28) —
 * il `detail` arriva verbatim nel toast, mai riformulato. Nessun dialog di
 * conferma eliminazione, nessuna icona da cestino (D-39): questa pagina non
 * elimina.
 *
 * Non viene mai renderizzato per una domanda `stepper`/`numero` (D-35): lo
 * decide `DomandePage.tsx` con `isNumerico()`, non un filtro qui sulla lista
 * delle opzioni.
 */
export function OpzioniSezione({
  domanda,
  selectedOpzioneId,
  onSelectOpzione,
  onChiudi,
}: OpzioniSezioneProps) {
  const queryClient = useQueryClient();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<OpzioneOut | null>(null);
  const [form, setForm] = useState<OpzioneFormState>(FORM_VUOTO);
  const [imgError, setImgError] = useState(false);

  const opzioniQuery = useQuery<OpzioneOut[]>({
    queryKey: chiaveOpzioni(domanda.code),
    queryFn: () => getOpzioni(domanda.code),
  });

  // Stessa chiave di EffettiSezione (chiaveEffetti(domanda.code)): cache
  // condivisa, nessun fetch in piu' per mostrare il conteggio "Effetti (n)".
  const effettiQuery = useQuery<EffettoOut[]>({
    queryKey: chiaveEffetti(domanda.code),
    queryFn: () => getEffetti(domanda.code),
  });

  function contaEffetti(opzioneId: number): number {
    return (effettiQuery.data ?? []).filter((e) => e.opzione_id === opzioneId).length;
  }

  const toggleMutation = useMutation({
    mutationFn: (row: OpzioneOut) => updateOpzione(row.id, { attiva: !row.attiva }),
    onSuccess: () => {
      toast.success("Modifica salvata");
      queryClient.invalidateQueries({ queryKey: DOMANDE_QUERY_KEY });
    },
    onError: (err) => {
      toast.error(err instanceof ApiError && err.detail ? err.detail : SAVE_ERROR);
    },
  });

  const createMutation = useMutation({
    mutationFn: (payload: OpzioneCreateInput) => createOpzione(payload),
    onSuccess: () => {
      toast.success("Modifica salvata");
      queryClient.invalidateQueries({ queryKey: DOMANDE_QUERY_KEY });
      closeDialog();
    },
  });

  const updateMutation = useMutation({
    mutationFn: (payload: OpzionePatchInput) => updateOpzione(editing!.id, payload),
    onSuccess: () => {
      toast.success("Modifica salvata");
      queryClient.invalidateQueries({ queryKey: DOMANDE_QUERY_KEY });
      closeDialog();
    },
  });

  function openCreate() {
    setEditing(null);
    setForm(FORM_VUOTO);
    setImgError(false);
    setDialogOpen(true);
  }

  function openEdit(row: OpzioneOut) {
    setEditing(row);
    setForm({
      code: row.code,
      etichetta: row.etichetta,
      descrizione: row.descrizione ?? "",
      immagineUrl: row.immagine_url ?? "",
      isDefault: row.is_default,
      ordine: String(row.ordine),
      attiva: row.attiva,
    });
    setImgError(false);
    setDialogOpen(true);
  }

  function closeDialog() {
    setDialogOpen(false);
    setEditing(null);
  }

  function onImmagineChange(value: string) {
    setForm((prev) => ({ ...prev, immagineUrl: value }));
    setImgError(false);
  }

  function handleSubmit() {
    const ordineNum = Number(form.ordine);
    const base = {
      etichetta: form.etichetta.trim(),
      descrizione: form.descrizione.trim() === "" ? null : form.descrizione.trim(),
      immagine_url: form.immagineUrl.trim() === "" ? null : form.immagineUrl.trim(),
      is_default: form.isDefault,
      ordine: ordineNum,
      attiva: form.attiva,
    };

    if (editing) {
      updateMutation.mutate(base);
    } else {
      createMutation.mutate({ domanda_code: domanda.code, code: form.code.trim(), ...base });
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-foreground">Opzioni — {domanda.testo}</h2>
        <div className="flex items-center gap-2">
          <Button type="button" size="sm" variant="outline" onClick={openCreate}>
            Aggiungi opzione
          </Button>
          <Button type="button" size="sm" variant="ghost" onClick={onChiudi}>
            Chiudi
          </Button>
        </div>
      </div>

      <AdminTable
        columns={["Codice", "Etichetta", "Default", "Attiva", "Azioni"]}
        isLoading={opzioniQuery.isLoading}
        isEmpty={(opzioniQuery.data ?? []).length === 0}
        emptyHeading={EMPTY_HEADING}
        emptyBody={EMPTY_BODY_OPZIONI}
        rows={(opzioniQuery.data ?? []).map((row) => {
          const selected = row.id === selectedOpzioneId;
          const selezionaRiga = () => onSelectOpzione(row.id);
          return [
            <button
              type="button"
              key="codice"
              onClick={selezionaRiga}
              aria-expanded={selected}
              className={`block w-full text-left ${selected ? "rounded-md bg-secondary px-1 -mx-1" : ""}`}
            >
              {row.code}
            </button>,
            <button
              type="button"
              key="etichetta"
              onClick={selezionaRiga}
              className={`block w-full text-left ${selected ? "rounded-md bg-secondary px-1 -mx-1" : ""}`}
            >
              {row.etichetta}
            </button>,
            row.is_default ? "Sì" : "",
            <Badge key="attiva" variant={row.attiva ? "default" : "secondary"}>
              {row.attiva ? "Attiva" : "Non attiva"}
            </Badge>,
            <div className="flex gap-1" key="azioni">
              <Button
                type="button"
                size="sm"
                variant="outline"
                aria-expanded={selected}
                onClick={selezionaRiga}
              >
                {effettiQuery.isLoading ? "Effetti" : `Effetti (${contaEffetti(row.id)})`}
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                aria-label="Modifica"
                onClick={() => openEdit(row)}
              >
                <Pencil className="size-4" />
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                aria-label={row.attiva ? "Disattiva opzione" : "Riattiva opzione"}
                onClick={() => toggleMutation.mutate(row)}
              >
                <Power className="size-4" />
              </Button>
            </div>,
          ];
        })}
      />

      <AdminCrudDialog
        open={dialogOpen}
        onOpenChange={closeDialog}
        entityLabel="opzione"
        title={editing ? "Modifica opzione" : "Aggiungi opzione"}
        onSubmit={handleSubmit}
        isSaving={createMutation.isPending || updateMutation.isPending}
        errorMessage={
          createMutation.isError || updateMutation.isError
            ? (() => {
                const err = createMutation.error ?? updateMutation.error;
                return err instanceof ApiError && err.detail ? err.detail : SAVE_ERROR;
              })()
            : null
        }
      >
        <div className="flex flex-col gap-1 rounded-md bg-secondary p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Domanda
          </p>
          <p className="text-sm text-foreground">
            {domanda.code} — {domanda.testo}
          </p>
        </div>

        <div className="flex flex-col gap-2">
          <Label htmlFor="opzione-code">Codice</Label>
          <Input
            id="opzione-code"
            value={form.code}
            onChange={(e) => setForm((prev) => ({ ...prev, code: e.target.value }))}
            disabled={!!editing}
            required
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="opzione-etichetta">Etichetta</Label>
          <Input
            id="opzione-etichetta"
            value={form.etichetta}
            onChange={(e) => setForm((prev) => ({ ...prev, etichetta: e.target.value }))}
            required
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="opzione-descrizione">Descrizione</Label>
          <Textarea
            id="opzione-descrizione"
            value={form.descrizione}
            onChange={(e) => setForm((prev) => ({ ...prev, descrizione: e.target.value }))}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="opzione-immagine">Immagine</Label>
          <Input
            id="opzione-immagine"
            value={form.immagineUrl}
            onChange={(e) => onImmagineChange(e.target.value)}
            placeholder="https://…"
          />
          {form.immagineUrl.trim() !== "" && !imgError && (
            <img
              src={form.immagineUrl}
              alt=""
              className="h-16 w-16 rounded-md border border-border object-cover"
              onError={() => setImgError(true)}
            />
          )}
        </div>
        <div className="flex items-center gap-2">
          <Switch
            id="opzione-default"
            checked={form.isDefault}
            onCheckedChange={(checked) => setForm((prev) => ({ ...prev, isDefault: checked }))}
          />
          <Label htmlFor="opzione-default" className="font-normal">
            Predefinita
          </Label>
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="opzione-ordine">Ordine</Label>
          <Input
            id="opzione-ordine"
            type="number"
            min={0}
            max={10000}
            value={form.ordine}
            onChange={(e) => setForm((prev) => ({ ...prev, ordine: e.target.value }))}
            required
          />
        </div>
        <div className="flex items-center gap-2">
          <Switch
            id="opzione-attiva"
            checked={form.attiva}
            onCheckedChange={(checked) => setForm((prev) => ({ ...prev, attiva: checked }))}
          />
          <Label htmlFor="opzione-attiva" className="font-normal">
            Attiva
          </Label>
        </div>
      </AdminCrudDialog>
    </div>
  );
}
