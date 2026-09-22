import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Pencil, Trash2, Download, Lock } from "lucide-react";
import { AdminLayout } from "@/pages/admin/AdminLayout";
import { AdminTable } from "@/components/admin/AdminTable";
import { AdminCrudDialog } from "@/components/admin/AdminCrudDialog";
import { AdminDeleteConfirm } from "@/components/admin/AdminDeleteConfirm";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { AnteprimaTab } from "@/components/admin/AnteprimaTab";
import { EMPTY_HEADING, EMPTY_BODY } from "@/lib/adminCopy";
import { scaricaExcel } from "@/api/admin/exportExcel";
import {
  getMoltiplicatori,
  updateMoltiplicatore,
  getIva,
  updateIva,
  listExtra,
  createExtra,
  updateExtra,
  deleteExtra,
  getCoeffPro,
  updateCoeffPro,
  getBaseEurMq,
  type MoltiplicatoreOut,
  type CategoriaIvaOut,
  type ExtraOut,
  type CoeffProOut,
} from "@/api/admin/coefficienti";

const SAVE_ERROR = "Non siamo riusciti a salvare la modifica. Riprova.";
const EXPORT_ERROR = "Non siamo riusciti a generare il file. Riprova.";

function pct(value: number): string {
  return (value * 100).toLocaleString("it-IT", { maximumFractionDigits: 1 }) + "%";
}

/**
 * Coefficienti (ADM-02, D-12, UI-SPEC §D Open Question 6): le famiglie del
 * modello come sotto-sezioni a `tabs`, ognuna con lo stesso pattern
 * `AdminTable` + edit `AdminCrudDialog` di §D. `base_eur_mq` è in sola
 * lettura qui (la scrittura resta nel CRUD categoria di Listini e prezzi).
 */
export function CoefficientiPage() {
  const [margineDialogOpen, setMargineDialogOpen] = useState(false);

  const scaricaMutation = useMutation({
    mutationFn: () => scaricaExcel("/admin/coefficienti/export.xlsx"),
    onError: () => {
      toast.error(EXPORT_ERROR);
    },
  });

  const scaricaMargineMutation = useMutation({
    mutationFn: () => scaricaExcel("/admin/coefficienti/export.xlsx?margine=true"),
    onSuccess: () => {
      setMargineDialogOpen(false);
    },
    onError: () => {
      toast.error(EXPORT_ERROR);
    },
  });

  return (
    <AdminLayout>
      <div className="flex flex-col gap-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-lg font-semibold text-foreground">Coefficienti</h1>
          <div className="flex flex-wrap gap-2">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  type="button"
                  variant="outline"
                  disabled={scaricaMutation.isPending}
                >
                  <Download className="size-4" />
                  {scaricaMutation.isPending ? "Generazione…" : "Scarica parametri"}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start">
                <DropdownMenuItem onSelect={() => scaricaMutation.mutate()}>
                  Scarica
                </DropdownMenuItem>
                <DropdownMenuItem onSelect={() => setMargineDialogOpen(true)}>
                  <Lock className="size-3.5" />
                  <span className="text-muted-foreground">Scarica con margine (riservato)</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        <AlertDialog open={margineDialogOpen} onOpenChange={setMargineDialogOpen}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Scaricare il file con il margine?</AlertDialogTitle>
              <AlertDialogDescription>
                Questo file contiene il coefficiente impresa: non condividerlo con clienti o
                consulenti esterni. Il download viene registrato con il tuo nome.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel autoFocus>Annulla</AlertDialogCancel>
              <AlertDialogAction
                variant="outline"
                className="border border-amber-border bg-amber-bg text-amber-fg hover:bg-amber-border/40"
                disabled={scaricaMargineMutation.isPending}
                onClick={(event) => {
                  event.preventDefault();
                  scaricaMargineMutation.mutate();
                }}
              >
                <Lock className="size-4" />
                {scaricaMargineMutation.isPending ? "Generazione…" : "Scarica con margine"}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>

        <Tabs defaultValue="moltiplicatori">
          <TabsList className="w-full">
            <TabsTrigger value="moltiplicatori">Moltiplicatori</TabsTrigger>
            <TabsTrigger value="base">Base €/m²</TabsTrigger>
            <TabsTrigger value="iva">IVA</TabsTrigger>
            <TabsTrigger value="extra">Extra</TabsTrigger>
            <TabsTrigger value="coeff-pro">Coefficienti Pro</TabsTrigger>
            <TabsTrigger value="anteprima">Anteprima</TabsTrigger>
          </TabsList>

          <TabsContent value="moltiplicatori">
            <MoltiplicatoriTab />
          </TabsContent>
          <TabsContent value="base">
            <BaseTab />
          </TabsContent>
          <TabsContent value="iva">
            <IvaTab />
          </TabsContent>
          <TabsContent value="extra">
            <ExtraTab />
          </TabsContent>
          <TabsContent value="coeff-pro">
            <CoeffProTab />
          </TabsContent>
          <TabsContent value="anteprima">
            <AnteprimaTab />
          </TabsContent>
        </Tabs>
      </div>
    </AdminLayout>
  );
}

function MoltiplicatoriTab() {
  const queryClient = useQueryClient();
  const query = useQuery<MoltiplicatoreOut[]>({ queryKey: ["admin-moltiplicatori"], queryFn: getMoltiplicatori });
  const [editing, setEditing] = useState<MoltiplicatoreOut | null>(null);
  const [valore, setValore] = useState("");

  const mutation = useMutation({
    mutationFn: () => updateMoltiplicatore(editing!.id, Number(valore)),
    onSuccess: () => {
      toast.success("Modifica salvata");
      queryClient.invalidateQueries({ queryKey: ["admin-moltiplicatori"] });
      setEditing(null);
    },
  });

  return (
    <div className="flex flex-col gap-3 pt-4">
      <AdminTable
        columns={["Tipo", "Categoria", "Moltiplicatore", "Azioni"]}
        isLoading={query.isLoading}
        isEmpty={(query.data ?? []).length === 0}
        emptyHeading={EMPTY_HEADING}
        emptyBody={EMPTY_BODY}
        rows={(query.data ?? []).map((row) => [
          row.tipo_code,
          row.categoria_code,
          <span className="tabular-nums" key="valore">
            {row.valore.toLocaleString("it-IT", { maximumFractionDigits: 3 })}
          </span>,
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-label="Modifica"
            key="azioni"
            onClick={() => {
              setEditing(row);
              setValore(String(row.valore));
            }}
          >
            <Pencil className="size-4" />
          </Button>,
        ])}
      />

      <AdminCrudDialog
        open={editing !== null}
        onOpenChange={(open) => !open && setEditing(null)}
        entityLabel="coefficiente"
        title="Modifica coefficiente"
        onSubmit={() => mutation.mutate()}
        isSaving={mutation.isPending}
        errorMessage={mutation.isError ? SAVE_ERROR : null}
      >
        <div className="flex flex-col gap-2">
          <Label>Tipo × categoria</Label>
          <p className="text-sm text-muted-foreground">
            {editing?.tipo_code} × {editing?.categoria_code}
          </p>
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="molt-valore">Moltiplicatore</Label>
          <Input
            id="molt-valore"
            type="number"
            step="0.001"
            min="0"
            value={valore}
            onChange={(e) => setValore(e.target.value)}
            required
          />
        </div>
      </AdminCrudDialog>
    </div>
  );
}

function BaseTab() {
  const query = useQuery({ queryKey: ["admin-base-eur-mq"], queryFn: getBaseEurMq });

  return (
    <div className="flex flex-col gap-3 pt-4">
      <p className="text-sm text-muted-foreground">
        Sola lettura — per modificare la base €/m² usa la sezione Listini e prezzi (categoria del listino).
      </p>
      <AdminTable
        columns={["Listino", "Categoria", "Base €/m²"]}
        isLoading={query.isLoading}
        isEmpty={(query.data ?? []).length === 0}
        emptyHeading={EMPTY_HEADING}
        emptyBody="I valori compaiono qui dopo aver creato almeno una categoria in un listino."
        rows={(query.data ?? []).map((row) => [
          String(row.listino_id),
          row.categoria_code,
          <span className="tabular-nums" key="base">
            {row.base_eur_mq.toLocaleString("it-IT", { style: "currency", currency: "EUR" })}
          </span>,
        ])}
      />
    </div>
  );
}

function IvaTab() {
  const queryClient = useQueryClient();
  const query = useQuery<CategoriaIvaOut[]>({ queryKey: ["admin-iva"], queryFn: getIva });
  const [editing, setEditing] = useState<CategoriaIvaOut | null>(null);
  const [ivaPct, setIvaPct] = useState("");

  const mutation = useMutation({
    mutationFn: () => updateIva(editing!.code, Number(ivaPct) / 100),
    onSuccess: () => {
      toast.success("Modifica salvata");
      queryClient.invalidateQueries({ queryKey: ["admin-iva"] });
      setEditing(null);
    },
  });

  return (
    <div className="flex flex-col gap-3 pt-4">
      <AdminTable
        columns={["Categoria", "Nome", "IVA", "Azioni"]}
        isLoading={query.isLoading}
        isEmpty={(query.data ?? []).length === 0}
        emptyHeading={EMPTY_HEADING}
        emptyBody={EMPTY_BODY}
        rows={(query.data ?? []).map((row) => [
          row.code,
          row.nome,
          <span className="tabular-nums" key="iva">
            {pct(row.iva_pct)}
          </span>,
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-label="Modifica"
            key="azioni"
            onClick={() => {
              setEditing(row);
              setIvaPct(String(row.iva_pct * 100));
            }}
          >
            <Pencil className="size-4" />
          </Button>,
        ])}
      />

      <AdminCrudDialog
        open={editing !== null}
        onOpenChange={(open) => !open && setEditing(null)}
        entityLabel="IVA"
        title="Modifica IVA"
        onSubmit={() => mutation.mutate()}
        isSaving={mutation.isPending}
        errorMessage={mutation.isError ? SAVE_ERROR : null}
      >
        <div className="flex flex-col gap-2">
          <Label>Categoria</Label>
          <p className="text-sm text-muted-foreground">{editing?.nome}</p>
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="iva-pct">IVA (%)</Label>
          <Input
            id="iva-pct"
            type="number"
            step="0.1"
            min="0"
            max="99"
            value={ivaPct}
            onChange={(e) => setIvaPct(e.target.value)}
            required
          />
        </div>
      </AdminCrudDialog>
    </div>
  );
}

function ExtraTab() {
  const queryClient = useQueryClient();
  const query = useQuery<ExtraOut[]>({ queryKey: ["admin-extra"], queryFn: listExtra });

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<ExtraOut | null>(null);
  const [code, setCode] = useState("");
  const [nome, setNome] = useState("");
  const [importo, setImporto] = useState("");
  const [ivaPct, setIvaPct] = useState("");
  const [attivo, setAttivo] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState<ExtraOut | null>(null);

  const createMutation = useMutation({
    mutationFn: () =>
      createExtra({
        code: code.trim(),
        nome: nome.trim(),
        importo: Number(importo),
        iva_pct: Number(ivaPct) / 100,
        attivo,
      }),
    onSuccess: () => {
      toast.success("Modifica salvata");
      queryClient.invalidateQueries({ queryKey: ["admin-extra"] });
      closeDialog();
    },
  });

  const updateMutation = useMutation({
    mutationFn: () =>
      updateExtra(editing!.code, {
        nome: nome.trim(),
        importo: Number(importo),
        iva_pct: Number(ivaPct) / 100,
        attivo,
      }),
    onSuccess: () => {
      toast.success("Modifica salvata");
      queryClient.invalidateQueries({ queryKey: ["admin-extra"] });
      closeDialog();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (deleteCode: string) => deleteExtra(deleteCode),
    onSuccess: () => {
      toast.success("Modifica salvata");
      queryClient.invalidateQueries({ queryKey: ["admin-extra"] });
      setDeleteTarget(null);
    },
  });

  function openCreate() {
    setEditing(null);
    setCode("");
    setNome("");
    setImporto("");
    setIvaPct("");
    setAttivo(true);
    setDialogOpen(true);
  }

  function openEdit(row: ExtraOut) {
    setEditing(row);
    setCode(row.code);
    setNome(row.nome);
    setImporto(String(row.importo));
    setIvaPct(String(row.iva_pct * 100));
    setAttivo(row.attivo);
    setDialogOpen(true);
  }

  function closeDialog() {
    setDialogOpen(false);
    setEditing(null);
  }

  return (
    <div className="flex flex-col gap-3 pt-4">
      <div className="flex justify-end">
        <Button type="button" size="sm" variant="outline" onClick={openCreate}>
          Aggiungi extra
        </Button>
      </div>

      <AdminTable
        columns={["Codice", "Nome", "Importo", "IVA", "Attivo", "Azioni"]}
        isLoading={query.isLoading}
        isEmpty={(query.data ?? []).length === 0}
        emptyHeading={EMPTY_HEADING}
        emptyBody={EMPTY_BODY}
        rows={(query.data ?? []).map((row) => [
          row.code,
          row.nome,
          <span className="tabular-nums" key="importo">
            {row.importo.toLocaleString("it-IT", { style: "currency", currency: "EUR" })}
          </span>,
          <span className="tabular-nums" key="iva">
            {pct(row.iva_pct)}
          </span>,
          <Badge key="attivo" variant={row.attivo ? "default" : "secondary"}>
            {row.attivo ? "Attivo" : "Non attivo"}
          </Badge>,
          <div className="flex gap-1" key="azioni">
            <Button type="button" variant="ghost" size="icon-sm" aria-label="Modifica" onClick={() => openEdit(row)}>
              <Pencil className="size-4" />
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              aria-label="Elimina"
              onClick={() => setDeleteTarget(row)}
            >
              <Trash2 className="size-4" />
            </Button>
          </div>,
        ])}
      />

      <AdminCrudDialog
        open={dialogOpen}
        onOpenChange={closeDialog}
        entityLabel="extra"
        title={editing ? "Modifica extra" : "Aggiungi extra"}
        onSubmit={() => (editing ? updateMutation.mutate() : createMutation.mutate())}
        isSaving={createMutation.isPending || updateMutation.isPending}
        errorMessage={createMutation.isError || updateMutation.isError ? SAVE_ERROR : null}
      >
        <div className="flex flex-col gap-2">
          <Label htmlFor="extra-code">Codice</Label>
          <Input
            id="extra-code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            disabled={!!editing}
            required
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="extra-nome">Nome</Label>
          <Input id="extra-nome" value={nome} onChange={(e) => setNome(e.target.value)} required />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="extra-importo">Importo</Label>
          <Input
            id="extra-importo"
            type="number"
            step="0.01"
            min="0"
            value={importo}
            onChange={(e) => setImporto(e.target.value)}
            required
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="extra-iva">IVA (%)</Label>
          <Input
            id="extra-iva"
            type="number"
            step="0.1"
            min="0"
            max="99"
            value={ivaPct}
            onChange={(e) => setIvaPct(e.target.value)}
            required
          />
        </div>
        <div className="flex items-center gap-2">
          <Switch id="extra-attivo" checked={attivo} onCheckedChange={setAttivo} />
          <Label htmlFor="extra-attivo" className="font-normal">
            Attivo
          </Label>
        </div>
      </AdminCrudDialog>

      <AdminDeleteConfirm
        open={deleteTarget !== null}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        entityLabel="extra"
        description="Eliminare questo extra? L'operazione non è reversibile."
        isDeleting={deleteMutation.isPending}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.code)}
      />
    </div>
  );
}

function CoeffProTab() {
  const queryClient = useQueryClient();
  const query = useQuery<CoeffProOut[]>({ queryKey: ["admin-coeff-pro"], queryFn: getCoeffPro });
  const [editing, setEditing] = useState<CoeffProOut | null>(null);
  const [valore, setValore] = useState("");

  const mutation = useMutation({
    mutationFn: () => updateCoeffPro(editing!.id, Number(valore)),
    onSuccess: () => {
      toast.success("Modifica salvata");
      queryClient.invalidateQueries({ queryKey: ["admin-coeff-pro"] });
      setEditing(null);
    },
  });

  return (
    <div className="flex flex-col gap-3 pt-4">
      <AdminTable
        columns={["Voce", "Tipo", "Quantità per m²", "Domanda mirata", "Azioni"]}
        isLoading={query.isLoading}
        isEmpty={(query.data ?? []).length === 0}
        emptyHeading={EMPTY_HEADING}
        emptyBody={EMPTY_BODY}
        rows={(query.data ?? []).map((row) => [
          String(row.voce_id),
          row.tipo_code,
          <span className="tabular-nums" key="valore">
            {row.valore !== null ? row.valore.toLocaleString("it-IT", { maximumFractionDigits: 4 }) : "—"}
          </span>,
          row.domanda_mirata_key ?? "—",
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-label="Modifica"
            key="azioni"
            onClick={() => {
              setEditing(row);
              setValore(row.valore !== null ? String(row.valore) : "");
            }}
          >
            <Pencil className="size-4" />
          </Button>,
        ])}
      />

      <AdminCrudDialog
        open={editing !== null}
        onOpenChange={(open) => !open && setEditing(null)}
        entityLabel="coefficiente"
        title="Modifica coefficiente Pro"
        onSubmit={() => mutation.mutate()}
        isSaving={mutation.isPending}
        errorMessage={mutation.isError ? SAVE_ERROR : null}
      >
        <div className="flex flex-col gap-2">
          <Label>Voce × tipo</Label>
          <p className="text-sm text-muted-foreground">
            {editing?.voce_id} × {editing?.tipo_code}
          </p>
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="coeff-pro-valore">Quantità per m²</Label>
          <Input
            id="coeff-pro-valore"
            type="number"
            step="0.0001"
            min="0"
            value={valore}
            onChange={(e) => setValore(e.target.value)}
            required
          />
        </div>
      </AdminCrudDialog>
    </div>
  );
}
