import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Pencil, Power } from "lucide-react";
import { AdminLayout } from "@/pages/admin/AdminLayout";
import { AdminTable } from "@/components/admin/AdminTable";
import { AdminCrudDialog } from "@/components/admin/AdminCrudDialog";
import { ToolbarCatalogo } from "@/pages/admin/domande/ToolbarCatalogo";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ApiError } from "@/api/admin/client";
import { EMPTY_HEADING } from "@/lib/adminCopy";
import type { TipoControllo } from "@/api/domande";
import {
  DOMANDE_QUERY_KEY,
  chiaveOpzioni,
  getDomande,
  createDomanda,
  updateDomanda,
  getOpzioni,
  type DomandaOut,
  type DomandaCreateInput,
  type DomandaPatchInput,
} from "@/api/admin/domande";

const SAVE_ERROR = "Non siamo riusciti a salvare la modifica. Riprova.";
const EMPTY_BODY_DOMANDE =
  "Aggiungi la prima domanda con il pulsante qui sopra, oppure carica un file.";
const NESSUNA = "__nessuna__";

const TIPO_CONTROLLO_LABELS: Record<TipoControllo, string> = {
  scelta_singola: "Scelta singola",
  scelta_multipla: "Scelta multipla",
  toggle: "Interruttore",
  stepper: "Contatore (stepper)",
  numero: "Numero",
};

const TIPI_CONTROLLO: TipoControllo[] = [
  "scelta_singola",
  "scelta_multipla",
  "toggle",
  "stepper",
  "numero",
];

interface FormState {
  code: string;
  testo: string;
  help: string;
  tipoControllo: TipoControllo;
  tierMinimo: "free" | "pro";
  obbligatoria: boolean;
  gruppo: string;
  ordine: string;
  attributoCode: string;
  visibileSeDomandaCode: string;
  visibileSeOpzioneCode: string;
}

const FORM_VUOTO: FormState = {
  code: "",
  testo: "",
  help: "",
  tipoControllo: "scelta_singola",
  tierMinimo: "free",
  obbligatoria: false,
  gruppo: "",
  ordine: "0",
  attributoCode: "",
  visibileSeDomandaCode: NESSUNA,
  visibileSeOpzioneCode: NESSUNA,
};

function sectionLabel(children: string) {
  return (
    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
      {children}
    </p>
  );
}

/**
 * `/admin/domande` (D-21), primo livello: la tabella delle domande con il
 * form completo a tre sezioni (D-36). Il click su una riga non rivela ancora
 * nulla — il livello opzioni lo aggiunge il piano 04.
 */
export function DomandePage() {
  const queryClient = useQueryClient();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<DomandaOut | null>(null);
  const [form, setForm] = useState<FormState>(FORM_VUOTO);

  const domandeQuery = useQuery<DomandaOut[]>({
    queryKey: DOMANDE_QUERY_KEY,
    queryFn: getDomande,
  });

  const domandaGateSelezionata = form.visibileSeDomandaCode !== NESSUNA ? form.visibileSeDomandaCode : null;

  const opzioniGateQuery = useQuery({
    queryKey: domandaGateSelezionata ? chiaveOpzioni(domandaGateSelezionata) : chiaveOpzioni("__none__"),
    queryFn: () => getOpzioni(domandaGateSelezionata as string),
    enabled: domandaGateSelezionata !== null,
  });

  const createMutation = useMutation({
    mutationFn: (payload: DomandaCreateInput) => createDomanda(payload),
    onSuccess: () => {
      toast.success("Modifica salvata");
      queryClient.invalidateQueries({ queryKey: DOMANDE_QUERY_KEY });
      closeDialog();
    },
  });

  const updateMutation = useMutation({
    mutationFn: (payload: DomandaPatchInput) => updateDomanda(editing!.code, payload),
    onSuccess: () => {
      toast.success("Modifica salvata");
      queryClient.invalidateQueries({ queryKey: DOMANDE_QUERY_KEY });
      closeDialog();
    },
  });

  const toggleMutation = useMutation({
    mutationFn: (row: DomandaOut) => updateDomanda(row.code, { attiva: !row.attiva }),
    onSuccess: () => {
      toast.success("Modifica salvata");
      queryClient.invalidateQueries({ queryKey: DOMANDE_QUERY_KEY });
    },
    onError: (err) => {
      toast.error(err instanceof ApiError && err.detail ? err.detail : SAVE_ERROR);
    },
  });

  function openCreate() {
    setEditing(null);
    setForm(FORM_VUOTO);
    setDialogOpen(true);
  }

  function openEdit(row: DomandaOut) {
    setEditing(row);
    setForm({
      code: row.code,
      testo: row.testo,
      help: row.help ?? "",
      tipoControllo: row.tipo_controllo,
      tierMinimo: row.tier_minimo,
      obbligatoria: row.obbligatoria,
      gruppo: row.gruppo,
      ordine: String(row.ordine),
      attributoCode: row.attributo_code ?? "",
      visibileSeDomandaCode: row.visibile_se_domanda_code ?? NESSUNA,
      visibileSeOpzioneCode: row.visibile_se_opzione_code ?? NESSUNA,
    });
    setDialogOpen(true);
  }

  function closeDialog() {
    setDialogOpen(false);
    setEditing(null);
  }

  function onDomandaGateChange(value: string) {
    setForm((prev) => ({
      ...prev,
      visibileSeDomandaCode: value,
      // Cambiare (o azzerare) la domanda gate invalida sempre la risposta
      // scelta finora, che apparterrebbe a un'altra domanda.
      visibileSeOpzioneCode: NESSUNA,
    }));
  }

  function handleSubmit() {
    const ordineNum = Number(form.ordine);
    const base = {
      testo: form.testo.trim(),
      help: form.help.trim() === "" ? null : form.help.trim(),
      tipo_controllo: form.tipoControllo,
      gruppo: form.gruppo.trim(),
      ordine: ordineNum,
      tier_minimo: form.tierMinimo,
      attributo_code: form.attributoCode.trim() === "" ? null : form.attributoCode.trim(),
      obbligatoria: form.obbligatoria,
      visibile_se_domanda_code: domandaGateSelezionata,
      visibile_se_opzione_code:
        domandaGateSelezionata !== null && form.visibileSeOpzioneCode !== NESSUNA
          ? form.visibileSeOpzioneCode
          : null,
    };

    if (editing) {
      updateMutation.mutate(base);
    } else {
      createMutation.mutate({ code: form.code.trim(), ...base });
    }
  }

  const domandeAttiveGate = (domandeQuery.data ?? []).filter(
    (d) => d.attiva && d.code !== editing?.code,
  );
  const opzioniAttiveGate = (opzioniGateQuery.data ?? []).filter((o) => o.attiva);

  return (
    <AdminLayout>
      <div className="flex flex-col gap-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-lg font-semibold text-foreground">Domande</h1>
          <ToolbarCatalogo onAggiungiDomanda={openCreate} />
        </div>

        <AdminTable
          columns={["Codice", "Testo", "Attributo", "Tipo controllo", "Tier", "Attiva", "Azioni"]}
          isLoading={domandeQuery.isLoading}
          isEmpty={(domandeQuery.data ?? []).length === 0}
          emptyHeading={EMPTY_HEADING}
          emptyBody={EMPTY_BODY_DOMANDE}
          rows={(domandeQuery.data ?? []).map((row) => [
            row.code,
            row.testo,
            row.attributo_code ?? "—",
            TIPO_CONTROLLO_LABELS[row.tipo_controllo],
            row.tier_minimo === "pro" ? "Pro" : "Free",
            <Badge key="attiva" variant={row.attiva ? "default" : "secondary"}>
              {row.attiva ? "Attiva" : "Non attiva"}
            </Badge>,
            <div className="flex gap-1" key="azioni">
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
                aria-label={row.attiva ? "Disattiva domanda" : "Riattiva domanda"}
                onClick={() => toggleMutation.mutate(row)}
              >
                <Power className="size-4" />
              </Button>
            </div>,
          ])}
        />
      </div>

      <AdminCrudDialog
        open={dialogOpen}
        onOpenChange={closeDialog}
        entityLabel="domanda"
        title={editing ? "Modifica domanda" : "Aggiungi domanda"}
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
        {sectionLabel("Base")}
        <div className="flex flex-col gap-2">
          <Label htmlFor="domanda-code">Codice</Label>
          <Input
            id="domanda-code"
            value={form.code}
            onChange={(e) => setForm((prev) => ({ ...prev, code: e.target.value }))}
            disabled={!!editing}
            required
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="domanda-testo">Testo</Label>
          <Input
            id="domanda-testo"
            value={form.testo}
            onChange={(e) => setForm((prev) => ({ ...prev, testo: e.target.value }))}
            required
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="domanda-help">Help</Label>
          <Textarea
            id="domanda-help"
            value={form.help}
            onChange={(e) => setForm((prev) => ({ ...prev, help: e.target.value }))}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="domanda-tipo-controllo">Tipo controllo</Label>
          <Select
            value={form.tipoControllo}
            onValueChange={(value) =>
              setForm((prev) => ({ ...prev, tipoControllo: value as TipoControllo }))
            }
          >
            <SelectTrigger id="domanda-tipo-controllo" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TIPI_CONTROLLO.map((tipo) => (
                <SelectItem key={tipo} value={tipo}>
                  {TIPO_CONTROLLO_LABELS[tipo]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <Separator />
        {sectionLabel("Pubblico")}
        <div className="flex flex-col gap-2">
          <Label htmlFor="domanda-tier">Tier minimo</Label>
          <Select
            value={form.tierMinimo}
            onValueChange={(value) =>
              setForm((prev) => ({ ...prev, tierMinimo: value as "free" | "pro" }))
            }
          >
            <SelectTrigger id="domanda-tier" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="free">Free</SelectItem>
              <SelectItem value="pro">Pro</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-2">
          <Switch
            id="domanda-obbligatoria"
            checked={form.obbligatoria}
            onCheckedChange={(checked) => setForm((prev) => ({ ...prev, obbligatoria: checked }))}
          />
          <Label htmlFor="domanda-obbligatoria" className="font-normal">
            Obbligatoria
          </Label>
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="domanda-gruppo">Gruppo</Label>
          <Input
            id="domanda-gruppo"
            value={form.gruppo}
            onChange={(e) => setForm((prev) => ({ ...prev, gruppo: e.target.value }))}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="domanda-ordine">Ordine</Label>
          <Input
            id="domanda-ordine"
            type="number"
            min={0}
            max={10000}
            value={form.ordine}
            onChange={(e) => setForm((prev) => ({ ...prev, ordine: e.target.value }))}
            required
          />
        </div>

        <Separator />
        {sectionLabel("Logica")}
        <div className="flex flex-col gap-2">
          <Label htmlFor="domanda-attributo">Attributo</Label>
          <Input
            id="domanda-attributo"
            value={form.attributoCode}
            onChange={(e) => setForm((prev) => ({ ...prev, attributoCode: e.target.value }))}
          />
          <p className="text-sm text-muted-foreground">
            Collega questa domanda alla sua baseline per m² (Attese). Lascia vuoto se la domanda
            non ha una correzione per scostamento.
          </p>
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="domanda-visibile-se-domanda">Visibile solo se — Domanda</Label>
          <Select value={form.visibileSeDomandaCode} onValueChange={onDomandaGateChange}>
            <SelectTrigger id="domanda-visibile-se-domanda" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={NESSUNA}>Nessuna</SelectItem>
              {domandeAttiveGate.map((d) => (
                <SelectItem key={d.code} value={d.code}>
                  {d.testo}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="domanda-visibile-se-opzione">Visibile solo se — Risposta</Label>
          <Select
            value={form.visibileSeOpzioneCode}
            onValueChange={(value) =>
              setForm((prev) => ({ ...prev, visibileSeOpzioneCode: value }))
            }
            disabled={domandaGateSelezionata === null}
          >
            <SelectTrigger id="domanda-visibile-se-opzione" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={NESSUNA}>Nessuna</SelectItem>
              {opzioniAttiveGate.map((o) => (
                <SelectItem key={o.code} value={o.code}>
                  {o.etichetta}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </AdminCrudDialog>
    </AdminLayout>
  );
}
