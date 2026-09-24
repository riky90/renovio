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
import { Switch } from "@/components/ui/switch";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ApiError } from "@/api/admin/client";
import { EMPTY_HEADING } from "@/lib/adminCopy";
import { TIPO_LABELS } from "@/lib/tipoRistrutturazione";
import { isNumerico } from "@/api/domande";
import {
  DOMANDE_QUERY_KEY,
  chiaveEffetti,
  getEffetti,
  createEffetto,
  updateEffetto,
  type DomandaOut,
  type OpzioneOut,
  type EffettoOut,
  type EffettoCreateInput,
  type EffettoPatchInput,
  type TipoEffetto,
} from "@/api/admin/domande";
import { getListini, getListinoCategorie, type ListinoOut, type ListinoCategoriaOut } from "@/api/admin/listini";
import {
  listSottocategorie,
  listVoci,
  type SottocategoriaOut,
  type VoceOut,
} from "@/api/admin/dettaglioPro";
import {
  TIPI_EFFETTO,
  ETICHETTE_TIPO_EFFETTO,
  BERSAGLI_AMMESSI,
  TIPI_SENZA_VALORE,
  TIPI_VALORE_NON_NEGATIVO,
  formattaValore,
  type Livello,
} from "@/pages/admin/domande/effetti";

const SAVE_ERROR = "Non siamo riusciti a salvare la modifica. Riprova.";
const EMPTY_BODY_EFFETTI =
  "Aggiungi il primo effetto con il pulsante qui sopra, oppure carica un file.";
const NESSUNA = "__nessuna__";

const LIVELLO_LABELS: Record<Livello, string> = {
  categoria: "Categoria",
  sottocategoria: "Sottocategoria",
  voce: "Voce",
};

type TipoRistrutturazioneCode = EffettoOut["tipo_code"];

interface EffettiSezioneProps {
  domanda: DomandaOut;
  opzione: OpzioneOut;
  onChiudi: () => void;
}

interface EffettoFormState {
  tipoEffetto: TipoEffetto;
  livello: Livello;
  categoriaCode: string;
  sottocategoriaId: string;
  voceId: string;
  tipoCode: string;
  valore: string;
  attivo: boolean;
}

function livelloIniziale(tipo: TipoEffetto): Livello {
  return BERSAGLI_AMMESSI[tipo][0];
}

function formVuoto(): EffettoFormState {
  const tipoEffetto = TIPI_EFFETTO[0];
  return {
    tipoEffetto,
    livello: livelloIniziale(tipoEffetto),
    categoriaCode: "",
    sottocategoriaId: "",
    voceId: "",
    tipoCode: NESSUNA,
    valore: "",
    attivo: true,
  };
}

function bersaglioReso(bersaglio: string) {
  const segmenti = bersaglio.split(" › ");
  return segmenti.map((segmento, i) => (
    <span key={i}>
      {segmento}
      {i < segmenti.length - 1 && <span className="text-muted-foreground"> › </span>}
    </span>
  ));
}

function sottocategoriaLabel(s: SottocategoriaOut): string {
  return s.codice ? `${s.codice} ${s.nome}` : s.nome;
}

function voceLabel(v: VoceOut): string {
  return v.codice ? `${v.codice} ${v.descrizione}` : v.descrizione;
}

/**
 * Terzo livello del master-detail (D-24): cosa fa al calcolo la risposta
 * scelta. Per le domande a scelta il titolo nomina l'opzione; per le
 * domande stepper/numero nomina direttamente la domanda (D-35), perche' li'
 * il livello Opzioni non compare mai e questa sezione si apre sull'opzione
 * implicita `valore`. Nessun dialog di conferma eliminazione, nessuna icona
 * da cestino: questa pagina non elimina.
 */
export function EffettiSezione({ domanda, opzione, onChiudi }: EffettiSezioneProps) {
  const queryClient = useQueryClient();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<EffettoOut | null>(null);
  const [form, setForm] = useState<EffettoFormState>(formVuoto());

  const effettiQuery = useQuery<EffettoOut[]>({
    queryKey: chiaveEffetti(domanda.code),
    queryFn: () => getEffetti(domanda.code),
  });

  const effetti = (effettiQuery.data ?? []).filter((e) => e.opzione_id === opzione.id);

  // Cascata del bersaglio (D-32), sempre sul listino di default — vedi
  // "Dipendenze tecniche" di UI-SPEC punto 3. Le query sono attive solo in
  // creazione (in modifica tipo/bersaglio sono testo statico).
  const listiniQuery = useQuery<ListinoOut[]>({
    queryKey: ["admin-listini"],
    queryFn: getListini,
    enabled: dialogOpen && !editing,
  });
  const listinoDefault = (listiniQuery.data ?? []).find((l) => l.is_default) ?? null;

  const categorieQuery = useQuery<ListinoCategoriaOut[]>({
    queryKey: ["admin-listino-categorie", listinoDefault?.id ?? null],
    queryFn: () => getListinoCategorie(listinoDefault!.id),
    enabled: dialogOpen && !editing && listinoDefault !== null,
  });

  const sottocategorieVisibili = form.livello === "sottocategoria" || form.livello === "voce";

  const sottocategorieQuery = useQuery<SottocategoriaOut[]>({
    queryKey: ["admin-pro-sotto", listinoDefault?.id ?? null],
    queryFn: () => listSottocategorie(listinoDefault!.id),
    enabled: dialogOpen && !editing && listinoDefault !== null && sottocategorieVisibili,
  });
  const sottocategorieFiltrate = (sottocategorieQuery.data ?? []).filter(
    (s) => s.categoria_code === form.categoriaCode,
  );

  const vociQuery = useQuery<VoceOut[]>({
    queryKey: ["admin-pro-voci", form.sottocategoriaId],
    queryFn: () => listVoci(Number(form.sottocategoriaId)),
    enabled: dialogOpen && !editing && form.livello === "voce" && form.sottocategoriaId !== "",
  });

  const toggleMutation = useMutation({
    mutationFn: (row: EffettoOut) => updateEffetto(row.id, { attivo: !row.attivo }),
    onSuccess: () => {
      toast.success("Modifica salvata");
      queryClient.invalidateQueries({ queryKey: DOMANDE_QUERY_KEY });
    },
    onError: (err) => {
      toast.error(err instanceof ApiError && err.detail ? err.detail : SAVE_ERROR);
    },
  });

  const createMutation = useMutation({
    mutationFn: (payload: EffettoCreateInput) => createEffetto(payload),
    onSuccess: () => {
      toast.success("Modifica salvata");
      queryClient.invalidateQueries({ queryKey: DOMANDE_QUERY_KEY });
      closeDialog();
    },
  });

  const updateMutation = useMutation({
    mutationFn: (payload: EffettoPatchInput) => updateEffetto(editing!.id, payload),
    onSuccess: () => {
      toast.success("Modifica salvata");
      queryClient.invalidateQueries({ queryKey: DOMANDE_QUERY_KEY });
      closeDialog();
    },
  });

  function openCreate() {
    setEditing(null);
    setForm(formVuoto());
    setDialogOpen(true);
  }

  function openEdit(row: EffettoOut) {
    setEditing(row);
    setForm({
      ...formVuoto(),
      tipoCode: row.tipo_code ?? NESSUNA,
      valore: row.valore === null ? "" : String(row.valore),
      attivo: row.attivo,
    });
    setDialogOpen(true);
  }

  function closeDialog() {
    setDialogOpen(false);
    setEditing(null);
  }

  function onTipoEffettoChange(value: string) {
    const tipoEffetto = value as TipoEffetto;
    setForm((prev) => ({
      ...prev,
      tipoEffetto,
      livello: livelloIniziale(tipoEffetto),
      categoriaCode: "",
      sottocategoriaId: "",
      voceId: "",
    }));
  }

  function onLivelloChange(value: string) {
    setForm((prev) => ({
      ...prev,
      livello: value as Livello,
      categoriaCode: "",
      sottocategoriaId: "",
      voceId: "",
    }));
  }

  function onCategoriaChange(value: string) {
    setForm((prev) => ({ ...prev, categoriaCode: value, sottocategoriaId: "", voceId: "" }));
  }

  function onSottocategoriaChange(value: string) {
    setForm((prev) => ({ ...prev, sottocategoriaId: value, voceId: "" }));
  }

  function handleSubmit() {
    const tipoCode: TipoRistrutturazioneCode =
      form.tipoCode === NESSUNA ? null : (form.tipoCode as Exclude<TipoRistrutturazioneCode, null>);

    if (editing) {
      const payload: EffettoPatchInput = { tipo_code: tipoCode, attivo: form.attivo };
      if (!TIPI_SENZA_VALORE.includes(editing.tipo_effetto)) {
        payload.valore = form.valore.trim() === "" ? null : Number(form.valore);
      }
      updateMutation.mutate(payload);
      return;
    }

    const target: Pick<
      EffettoCreateInput,
      "target_categoria_code" | "target_sottocategoria_id" | "target_voce_id"
    > =
      form.livello === "categoria"
        ? { target_categoria_code: form.categoriaCode }
        : form.livello === "sottocategoria"
          ? { target_sottocategoria_id: Number(form.sottocategoriaId) }
          : { target_voce_id: Number(form.voceId) };

    const payload: EffettoCreateInput = {
      opzione_id: opzione.id,
      tipo_effetto: form.tipoEffetto,
      tipo_code: tipoCode,
      attivo: form.attivo,
      ...target,
    };
    if (!TIPI_SENZA_VALORE.includes(form.tipoEffetto)) {
      payload.valore = form.valore.trim() === "" ? null : Number(form.valore);
    }
    createMutation.mutate(payload);
  }

  const titolo = isNumerico(domanda.tipo_controllo)
    ? `Effetti — ${domanda.testo}`
    : `Effetti — ${opzione.etichetta}`;

  const bersagliAmmessi = BERSAGLI_AMMESSI[form.tipoEffetto];
  const tipoCorrente = editing ? editing.tipo_effetto : form.tipoEffetto;
  const nascondiValore = TIPI_SENZA_VALORE.includes(tipoCorrente);
  const valoreNonNegativo = TIPI_VALORE_NON_NEGATIVO.includes(tipoCorrente);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-foreground">{titolo}</h2>
        <div className="flex items-center gap-2">
          <Button type="button" size="sm" variant="outline" onClick={openCreate}>
            Aggiungi effetto
          </Button>
          <Button type="button" size="sm" variant="ghost" onClick={onChiudi}>
            Chiudi
          </Button>
        </div>
      </div>

      <AdminTable
        columns={["Tipo effetto", "Bersaglio", "Tipo", "Valore", "Attivo", "Azioni"]}
        isLoading={effettiQuery.isLoading}
        isEmpty={effetti.length === 0}
        emptyHeading={EMPTY_HEADING}
        emptyBody={EMPTY_BODY_EFFETTI}
        rows={effetti.map((row) => [
          ETICHETTE_TIPO_EFFETTO[row.tipo_effetto],
          <span key="bersaglio">{bersaglioReso(row.bersaglio)}</span>,
          row.tipo_code ? TIPO_LABELS[row.tipo_code] : "Tutti i tipi",
          <span
            key="valore"
            className={row.valore === null ? "text-muted-foreground" : undefined}
          >
            {formattaValore(row.tipo_effetto, row.valore)}
          </span>,
          <Badge key="attivo" variant={row.attivo ? "default" : "secondary"}>
            {row.attivo ? "Attivo" : "Non attivo"}
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
              aria-label={row.attivo ? "Disattiva effetto" : "Riattiva effetto"}
              onClick={() => toggleMutation.mutate(row)}
            >
              <Power className="size-4" />
            </Button>
          </div>,
        ])}
      />

      <AdminCrudDialog
        open={dialogOpen}
        onOpenChange={closeDialog}
        entityLabel="effetto"
        title={editing ? "Modifica effetto" : "Aggiungi effetto"}
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
            Contesto
          </p>
          <p className="text-sm text-foreground">
            {domanda.testo} › {opzione.etichetta}
          </p>
        </div>

        {editing ? (
          <>
            <div className="flex flex-col gap-2">
              <Label>Tipo effetto</Label>
              <p className="text-sm text-foreground">{ETICHETTE_TIPO_EFFETTO[editing.tipo_effetto]}</p>
            </div>
            <div className="flex flex-col gap-2">
              <Label>Bersaglio</Label>
              <p className="text-sm text-foreground">{bersaglioReso(editing.bersaglio)}</p>
            </div>
          </>
        ) : (
          <>
            <div className="flex flex-col gap-2">
              <Label htmlFor="effetto-tipo">Tipo effetto</Label>
              <Select value={form.tipoEffetto} onValueChange={onTipoEffettoChange}>
                <SelectTrigger id="effetto-tipo" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TIPI_EFFETTO.map((tipo) => (
                    <SelectItem key={tipo} value={tipo}>
                      {ETICHETTE_TIPO_EFFETTO[tipo]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {bersagliAmmessi.length > 1 && (
              <div className="flex flex-col gap-2">
                <Label>Livello bersaglio</Label>
                <RadioGroup
                  value={form.livello}
                  onValueChange={onLivelloChange}
                  className="flex flex-row gap-4"
                >
                  {bersagliAmmessi.map((l) => (
                    <div className="flex items-center gap-2" key={l}>
                      <RadioGroupItem value={l} id={`effetto-livello-${l}`} />
                      <Label htmlFor={`effetto-livello-${l}`} className="font-normal">
                        {LIVELLO_LABELS[l]}
                      </Label>
                    </div>
                  ))}
                </RadioGroup>
              </div>
            )}

            <div className="flex flex-col gap-2">
              <Label htmlFor="effetto-categoria">Categoria</Label>
              <Select value={form.categoriaCode} onValueChange={onCategoriaChange}>
                <SelectTrigger id="effetto-categoria" className="w-full">
                  <SelectValue placeholder="Seleziona una categoria" />
                </SelectTrigger>
                <SelectContent>
                  {(categorieQuery.data ?? []).map((c) => (
                    <SelectItem key={c.categoria_code} value={c.categoria_code}>
                      {c.categoria_code}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {sottocategorieVisibili && (
              <div className="flex flex-col gap-2">
                <Label htmlFor="effetto-sottocategoria">Sottocategoria</Label>
                <Select
                  value={form.sottocategoriaId}
                  onValueChange={onSottocategoriaChange}
                  disabled={form.categoriaCode === ""}
                >
                  <SelectTrigger id="effetto-sottocategoria" className="w-full">
                    <SelectValue placeholder="Seleziona una sottocategoria" />
                  </SelectTrigger>
                  <SelectContent>
                    {sottocategorieFiltrate.map((s) => (
                      <SelectItem key={s.id} value={String(s.id)}>
                        {sottocategoriaLabel(s)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {form.livello === "voce" && (
              <div className="flex flex-col gap-2">
                <Label htmlFor="effetto-voce">Voce</Label>
                <Select
                  value={form.voceId}
                  onValueChange={(value) => setForm((prev) => ({ ...prev, voceId: value }))}
                  disabled={form.sottocategoriaId === ""}
                >
                  <SelectTrigger id="effetto-voce" className="w-full">
                    <SelectValue placeholder="Seleziona una voce" />
                  </SelectTrigger>
                  <SelectContent>
                    {(vociQuery.data ?? []).map((v) => (
                      <SelectItem key={v.id} value={String(v.id)}>
                        {voceLabel(v)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
          </>
        )}

        <div className="flex flex-col gap-2">
          <Label htmlFor="effetto-tipo-ristrutturazione">Tipo di ristrutturazione</Label>
          <Select
            value={form.tipoCode}
            onValueChange={(value) => setForm((prev) => ({ ...prev, tipoCode: value }))}
          >
            <SelectTrigger id="effetto-tipo-ristrutturazione" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={NESSUNA}>Tutti i tipi</SelectItem>
              {Object.entries(TIPO_LABELS).map(([code, label]) => (
                <SelectItem key={code} value={code}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {!nascondiValore && (
          <div className="flex flex-col gap-2">
            <Label htmlFor="effetto-valore">Valore</Label>
            <Input
              id="effetto-valore"
              type="number"
              step="0.01"
              min={valoreNonNegativo ? "0" : undefined}
              value={form.valore}
              onChange={(e) => setForm((prev) => ({ ...prev, valore: e.target.value }))}
              required
            />
          </div>
        )}

        <div className="flex items-center gap-2">
          <Switch
            id="effetto-attivo"
            checked={form.attivo}
            onCheckedChange={(checked) => setForm((prev) => ({ ...prev, attivo: checked }))}
          />
          <Label htmlFor="effetto-attivo" className="font-normal">
            Attivo
          </Label>
        </div>
      </AdminCrudDialog>
    </div>
  );
}
