import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { AdminLayout } from "@/pages/admin/AdminLayout";
import { AdminTable } from "@/components/admin/AdminTable";
import { AdminCrudDialog } from "@/components/admin/AdminCrudDialog";
import { AdminDeleteConfirm } from "@/components/admin/AdminDeleteConfirm";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  listComuni,
  createComune,
  updateComune,
  deleteComune,
  listTipi,
  updateTipo,
  listListiniOptions,
  type ComuneListino,
  type TipoRistrutturazione,
  type ListinoOption,
} from "@/api/admin/citta";
import { listTesti, updateTesto, type Testo } from "@/api/admin/testi";
import { ApiError } from "@/api/client";

const SAVE_TOAST = "Modifica salvata";
const SAVE_ERROR = "Non siamo riusciti a salvare la modifica. Riprova.";
const DELETE_MAPPATURA_COPY =
  "Eliminare questa mappatura città→listino? Le stime già salvate non saranno modificate.";

function extractErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return SAVE_ERROR;
  return SAVE_ERROR;
}

/**
 * Città e testi (UI-SPEC §D, Open Question 5, ADM-03): tre sotto-sezioni sopra
 * il backend 04-03 — mappature città→listino (ComuneListino), tipi di
 * ristrutturazione (TipoRistrutturazione) e testi/disclaimer key/value
 * (Testo). Stesso pattern CRUD condiviso (AdminTable/AdminCrudDialog/
 * AdminDeleteConfirm) usato dalle altre sezioni admin di questa fase.
 */
export function CittaTestiPage() {
  return (
    <AdminLayout>
      <div className="flex flex-col gap-10">
        <h1 className="text-lg font-semibold text-foreground">Città e testi</h1>
        <MappatureSection />
        <TipiSection />
        <TestiSection />
      </div>
    </AdminLayout>
  );
}

/* ------------------------------------------------------------------ */
/* Sezione 1 — Mappature città → listino                              */
/* ------------------------------------------------------------------ */

interface ComuneFormState {
  comune_nome: string;
  codice_istat: string;
  listino_id: string;
}

const EMPTY_COMUNE_FORM: ComuneFormState = { comune_nome: "", codice_istat: "", listino_id: "" };

function MappatureSection() {
  const queryClient = useQueryClient();
  const comuniQuery = useQuery<ComuneListino[]>({ queryKey: ["admin-comuni"], queryFn: listComuni });
  const listiniQuery = useQuery<ListinoOption[]>({
    queryKey: ["admin-listini-options"],
    queryFn: listListiniOptions,
  });

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<ComuneListino | null>(null);
  const [form, setForm] = useState<ComuneFormState>(EMPTY_COMUNE_FORM);
  const [deleteTarget, setDeleteTarget] = useState<ComuneListino | null>(null);

  const saveMutation = useMutation({
    mutationFn: async () => {
      const body = {
        comune_nome: form.comune_nome.trim(),
        codice_istat: form.codice_istat.trim() ? form.codice_istat.trim() : null,
        listino_id: Number(form.listino_id),
      };
      return editing ? updateComune(editing.id, body) : createComune(body);
    },
    onSuccess: () => {
      toast.success(SAVE_TOAST);
      setDialogOpen(false);
      queryClient.invalidateQueries({ queryKey: ["admin-comuni"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteComune(id),
    onSuccess: () => {
      toast.success(SAVE_TOAST);
      setDeleteTarget(null);
      queryClient.invalidateQueries({ queryKey: ["admin-comuni"] });
    },
  });

  function openCreate() {
    setEditing(null);
    setForm(EMPTY_COMUNE_FORM);
    setDialogOpen(true);
  }

  function openEdit(row: ComuneListino) {
    setEditing(row);
    setForm({
      comune_nome: row.comune_nome,
      codice_istat: row.codice_istat ?? "",
      listino_id: String(row.listino_id),
    });
    setDialogOpen(true);
  }

  const listiniById = new Map((listiniQuery.data ?? []).map((l) => [l.id, l.nome]));

  const rows = (comuniQuery.data ?? []).map((row) => [
    row.comune_nome,
    listiniById.get(row.listino_id) ?? `#${row.listino_id}`,
    row.codice_istat ?? "—",
    <div key="actions" className="flex justify-end gap-2">
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="size-8"
        title="Modifica"
        aria-label="Modifica"
        onClick={() => openEdit(row)}
      >
        <Pencil className="size-4" />
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="size-8"
        title="Elimina"
        aria-label="Elimina"
        onClick={() => setDeleteTarget(row)}
      >
        <Trash2 className="size-4" />
      </Button>
    </div>,
  ]);

  return (
    <section className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-foreground">Mappature città → listino</h2>
        <Button
          type="button"
          onClick={openCreate}
          className="bg-primary text-primary-foreground hover:bg-primary/90"
        >
          <Plus className="mr-1 size-4" aria-hidden />
          Aggiungi mappatura
        </Button>
      </div>

      <AdminTable
        columns={["Comune", "Listino mappato", "Codice ISTAT", ""]}
        isLoading={comuniQuery.isLoading}
        rows={rows}
        isEmpty={(comuniQuery.data ?? []).length === 0}
        emptyHeading="Nessun elemento presente"
        emptyBody="Aggiungi il primo elemento con il pulsante qui sopra, oppure carica un file."
      />

      <AdminCrudDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        entityLabel="mappatura"
        title={editing ? "Modifica mappatura" : "Aggiungi mappatura"}
        onSubmit={() => saveMutation.mutate()}
        isSaving={saveMutation.isPending}
        errorMessage={saveMutation.isError ? extractErrorMessage(saveMutation.error) : null}
      >
        <div className="flex flex-col gap-2">
          <Label htmlFor="comune-nome">Comune</Label>
          <Input
            id="comune-nome"
            value={form.comune_nome}
            onChange={(e) => setForm((f) => ({ ...f, comune_nome: e.target.value }))}
            required
          />
        </div>

        <div className="flex flex-col gap-2">
          <Label htmlFor="comune-listino">Listino</Label>
          <Select
            value={form.listino_id}
            onValueChange={(value) => setForm((f) => ({ ...f, listino_id: value }))}
          >
            <SelectTrigger id="comune-listino" className="w-full">
              <SelectValue placeholder="Seleziona un listino" />
            </SelectTrigger>
            <SelectContent>
              {(listiniQuery.data ?? []).map((listino) => (
                <SelectItem key={listino.id} value={String(listino.id)}>
                  {listino.nome} ({listino.citta_riferimento})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex flex-col gap-2">
          <Label htmlFor="comune-istat">Codice ISTAT (facoltativo)</Label>
          <Input
            id="comune-istat"
            value={form.codice_istat}
            onChange={(e) => setForm((f) => ({ ...f, codice_istat: e.target.value }))}
          />
        </div>
      </AdminCrudDialog>

      <AdminDeleteConfirm
        open={deleteTarget !== null}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        entityLabel="mappatura"
        description={DELETE_MAPPATURA_COPY}
        isDeleting={deleteMutation.isPending}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
      />
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* Sezione 2 — Tipi di ristrutturazione                                */
/* ------------------------------------------------------------------ */

interface TipoFormState {
  nome: string;
  ordine: string;
  range_pct: string;
  range_pct_sotto: string;
}

function TipiSection() {
  const queryClient = useQueryClient();
  const tipiQuery = useQuery<TipoRistrutturazione[]>({ queryKey: ["admin-tipi"], queryFn: listTipi });

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<TipoRistrutturazione | null>(null);
  const [form, setForm] = useState<TipoFormState>({
    nome: "",
    ordine: "",
    range_pct: "",
    range_pct_sotto: "",
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (!editing) throw new Error("Nessun tipo selezionato");
      return updateTipo(editing.code, {
        nome: form.nome.trim(),
        ordine: Number(form.ordine),
        range_pct: Number(form.range_pct),
        ...(form.range_pct_sotto.trim() !== "" ? { range_pct_sotto: Number(form.range_pct_sotto) } : {}),
      });
    },
    onSuccess: () => {
      toast.success(SAVE_TOAST);
      setDialogOpen(false);
      queryClient.invalidateQueries({ queryKey: ["admin-tipi"] });
    },
  });

  function openEdit(row: TipoRistrutturazione) {
    setEditing(row);
    setForm({
      nome: row.nome,
      ordine: String(row.ordine),
      range_pct: String(row.range_pct),
      range_pct_sotto: row.range_pct_sotto === null ? "" : String(row.range_pct_sotto),
    });
    setDialogOpen(true);
  }

  const rows = (tipiQuery.data ?? []).map((row) => [
    row.nome,
    <span key="ordine" className="tabular-nums">
      {row.ordine}
    </span>,
    <span key="range" className="tabular-nums">
      −{((row.range_pct_sotto ?? row.range_pct) * 100).toFixed(0)}% / +{(row.range_pct * 100).toFixed(0)}%
    </span>,
    <div key="actions" className="flex justify-end gap-2">
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="size-8"
        title="Modifica"
        aria-label="Modifica"
        onClick={() => openEdit(row)}
      >
        <Pencil className="size-4" />
      </Button>
    </div>,
  ]);

  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-base font-semibold text-foreground">Tipi di ristrutturazione</h2>

      <AdminTable
        columns={["Nome", "Ordine", "Range", ""]}
        isLoading={tipiQuery.isLoading}
        rows={rows}
        isEmpty={(tipiQuery.data ?? []).length === 0}
        emptyHeading="Nessun elemento presente"
        emptyBody="I tipi di ristrutturazione sono seedati dal sistema."
      />

      <AdminCrudDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        entityLabel="tipo"
        title="Modifica tipo"
        onSubmit={() => saveMutation.mutate()}
        isSaving={saveMutation.isPending}
        errorMessage={saveMutation.isError ? extractErrorMessage(saveMutation.error) : null}
      >
        <div className="flex flex-col gap-2">
          <Label htmlFor="tipo-nome">Nome</Label>
          <Input
            id="tipo-nome"
            value={form.nome}
            onChange={(e) => setForm((f) => ({ ...f, nome: e.target.value }))}
            required
          />
        </div>

        <div className="flex flex-col gap-2">
          <Label htmlFor="tipo-ordine">Ordine</Label>
          <Input
            id="tipo-ordine"
            type="number"
            value={form.ordine}
            onChange={(e) => setForm((f) => ({ ...f, ordine: e.target.value }))}
            required
          />
        </div>

        <div className="flex flex-col gap-2">
          <Label htmlFor="tipo-range">Range sopra (0–1, es. 0.15)</Label>
          <Input
            id="tipo-range"
            type="number"
            step="0.01"
            min="0"
            max="1"
            value={form.range_pct}
            onChange={(e) => setForm((f) => ({ ...f, range_pct: e.target.value }))}
            required
          />
        </div>

        <div className="flex flex-col gap-2">
          <Label htmlFor="tipo-range-sotto">Range sotto (0–1, es. 0.10; vuoto = come sopra)</Label>
          <Input
            id="tipo-range-sotto"
            type="number"
            step="0.01"
            min="0"
            max="1"
            value={form.range_pct_sotto}
            onChange={(e) => setForm((f) => ({ ...f, range_pct_sotto: e.target.value }))}
          />
        </div>
      </AdminCrudDialog>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* Sezione 3 — Testi/disclaimer key/value                             */
/* ------------------------------------------------------------------ */

function TestiSection() {
  const queryClient = useQueryClient();
  const testiQuery = useQuery<Testo[]>({ queryKey: ["admin-testi"], queryFn: listTesti });

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Testo | null>(null);
  const [valore, setValore] = useState("");

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (!editing) throw new Error("Nessun testo selezionato");
      return updateTesto(editing.chiave, { valore: valore.trim() });
    },
    onSuccess: () => {
      toast.success(SAVE_TOAST);
      setDialogOpen(false);
      queryClient.invalidateQueries({ queryKey: ["admin-testi"] });
    },
  });

  function openEdit(row: Testo) {
    setEditing(row);
    setValore(row.valore);
    setDialogOpen(true);
  }

  const rows = (testiQuery.data ?? []).map((row) => [
    <span key="chiave" className="font-mono text-sm">
      {row.chiave}
    </span>,
    <span key="valore" className="line-clamp-2 text-sm text-foreground">
      {row.valore}
    </span>,
    <div key="actions" className="flex justify-end gap-2">
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="size-8"
        title="Modifica"
        aria-label="Modifica"
        onClick={() => openEdit(row)}
      >
        <Pencil className="size-4" />
      </Button>
    </div>,
  ]);

  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-base font-semibold text-foreground">Testi e disclaimer</h2>

      <AdminTable
        columns={["Chiave", "Valore", ""]}
        isLoading={testiQuery.isLoading}
        rows={rows}
        isEmpty={(testiQuery.data ?? []).length === 0}
        emptyHeading="Nessun elemento presente"
        emptyBody="I testi sono seedati dal sistema."
      />

      <AdminCrudDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        entityLabel="testo"
        title={editing ? `Modifica testo "${editing.chiave}"` : "Modifica testo"}
        onSubmit={() => saveMutation.mutate()}
        isSaving={saveMutation.isPending}
        errorMessage={saveMutation.isError ? extractErrorMessage(saveMutation.error) : null}
      >
        <div className="flex flex-col gap-2">
          <Label htmlFor="testo-valore">Valore</Label>
          <Textarea
            id="testo-valore"
            rows={4}
            value={valore}
            onChange={(e) => setValore(e.target.value)}
            required
          />
        </div>
      </AdminCrudDialog>
    </section>
  );
}
