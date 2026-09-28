import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Pencil, Trash2, List as ListIcon, Download, UploadCloud } from "lucide-react";
import { Link } from "react-router";
import { AdminLayout } from "@/pages/admin/AdminLayout";
import { AdminTable } from "@/components/admin/AdminTable";
import { AdminCrudDialog } from "@/components/admin/AdminCrudDialog";
import { AdminDeleteConfirm } from "@/components/admin/AdminDeleteConfirm";
import { ExcelUploadDialog } from "@/components/admin/ExcelUploadDialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  getListini,
  createListino,
  updateListino,
  getListinoCategorie,
  createListinoCategoria,
  updateListinoCategoria,
  deleteListinoCategoria,
  getVoci,
  updateVoce,
  deleteVoce,
  type ListinoOut,
  type ListinoCategoriaOut,
  type VoceOut,
} from "@/api/admin/listini";
import { scaricaExcel } from "@/api/admin/exportExcel";

const EXPORT_ERROR = "Non siamo riusciti a generare il file. Riprova.";

/**
 * Listini e prezzi (ADM-01, UI-SPEC §D): CRUD listino/categoria/voce sopra
 * 04-02, con entry-point upload Excel (esistente + nuova città, §E). I
 * campi `base_eur_mq`/`coefficiente_impresa` sono campi normali qui (D-10)
 * — MAI riesportati fuori da questo file/da `api/admin/listini.ts`.
 */
export function ListiniPage() {
  const queryClient = useQueryClient();

  const [selectedListinoId, setSelectedListinoId] = useState<number | null>(null);
  const [selectedCategoriaId, setSelectedCategoriaId] = useState<number | null>(null);

  const [listinoDialogOpen, setListinoDialogOpen] = useState(false);
  const [listinoNome, setListinoNome] = useState("");
  const [listinoCitta, setListinoCitta] = useState("");
  const [listinoIsDefault, setListinoIsDefault] = useState(false);

  const [editListinoDialogOpen, setEditListinoDialogOpen] = useState(false);
  const [editListinoNome, setEditListinoNome] = useState("");
  const [editListinoIsDefault, setEditListinoIsDefault] = useState(false);
  const [editListinoAttivo, setEditListinoAttivo] = useState(true);

  const [categoriaDialogOpen, setCategoriaDialogOpen] = useState(false);
  const [editingCategoria, setEditingCategoria] = useState<ListinoCategoriaOut | null>(null);
  const [categoriaCode, setCategoriaCode] = useState("");
  const [categoriaBase, setCategoriaBase] = useState("");
  const [categoriaCoeff, setCategoriaCoeff] = useState("");
  const [deleteCategoriaTarget, setDeleteCategoriaTarget] = useState<ListinoCategoriaOut | null>(null);

  const [voceDialogOpen, setVoceDialogOpen] = useState(false);
  const [editingVoce, setEditingVoce] = useState<VoceOut | null>(null);
  const [vocePrezzo, setVocePrezzo] = useState("");
  const [voceUm, setVoceUm] = useState("");
  const [deleteVoceTarget, setDeleteVoceTarget] = useState<VoceOut | null>(null);

  const [uploadOpen, setUploadOpen] = useState(false);

  const listiniQuery = useQuery<ListinoOut[]>({ queryKey: ["admin-listini"], queryFn: getListini });

  const scaricaListinoMutation = useMutation({
    mutationFn: () => scaricaExcel(`/admin/listini/${selectedListinoId}/export.xlsx`),
    onError: () => {
      toast.error(EXPORT_ERROR);
    },
  });

  useEffect(() => {
    if (selectedListinoId === null && listiniQuery.data && listiniQuery.data.length > 0) {
      const preferred = listiniQuery.data.find((l) => l.is_default) ?? listiniQuery.data[0];
      setSelectedListinoId(preferred.id);
    }
  }, [listiniQuery.data, selectedListinoId]);

  const categorieQuery = useQuery<ListinoCategoriaOut[]>({
    queryKey: ["admin-listino-categorie", selectedListinoId],
    queryFn: () => getListinoCategorie(selectedListinoId as number),
    enabled: selectedListinoId !== null,
  });

  const vociQuery = useQuery<VoceOut[]>({
    queryKey: ["admin-listino-voci", selectedCategoriaId],
    queryFn: () => getVoci(selectedCategoriaId as number),
    enabled: selectedCategoriaId !== null,
  });

  const createListinoMutation = useMutation({
    mutationFn: createListino,
    onSuccess: (row) => {
      toast.success("Modifica salvata");
      queryClient.invalidateQueries({ queryKey: ["admin-listini"] });
      setSelectedListinoId(row.id);
      setListinoDialogOpen(false);
      setListinoNome("");
      setListinoCitta("");
      setListinoIsDefault(false);
    },
  });

  const updateListinoMutation = useMutation({
    mutationFn: () =>
      updateListino(selectedListinoId as number, {
        nome: editListinoNome.trim(),
        is_default: editListinoIsDefault,
        attivo: editListinoAttivo,
      }),
    onSuccess: () => {
      toast.success("Modifica salvata");
      queryClient.invalidateQueries({ queryKey: ["admin-listini"] });
      setEditListinoDialogOpen(false);
    },
  });

  const createCategoriaMutation = useMutation({
    mutationFn: () =>
      createListinoCategoria(selectedListinoId as number, {
        categoria_code: categoriaCode.trim(),
        base_eur_mq: Number(categoriaBase),
        coefficiente_impresa: Number(categoriaCoeff),
      }),
    onSuccess: () => {
      toast.success("Modifica salvata");
      queryClient.invalidateQueries({ queryKey: ["admin-listino-categorie", selectedListinoId] });
      closeCategoriaDialog();
    },
  });

  const updateCategoriaMutation = useMutation({
    mutationFn: () =>
      updateListinoCategoria(editingCategoria!.id, {
        base_eur_mq: Number(categoriaBase),
        coefficiente_impresa: Number(categoriaCoeff),
      }),
    onSuccess: () => {
      toast.success("Modifica salvata");
      queryClient.invalidateQueries({ queryKey: ["admin-listino-categorie", selectedListinoId] });
      closeCategoriaDialog();
    },
  });

  const deleteCategoriaMutation = useMutation({
    mutationFn: (id: number) => deleteListinoCategoria(id),
    onSuccess: () => {
      toast.success("Modifica salvata");
      queryClient.invalidateQueries({ queryKey: ["admin-listino-categorie", selectedListinoId] });
      setDeleteCategoriaTarget(null);
    },
  });

  const updateVoceMutation = useMutation({
    mutationFn: () =>
      updateVoce(editingVoce!.id, { prezzo_cliente: Number(vocePrezzo), um: voceUm.trim() }),
    onSuccess: () => {
      toast.success("Modifica salvata");
      queryClient.invalidateQueries({ queryKey: ["admin-listino-voci", selectedCategoriaId] });
      setVoceDialogOpen(false);
      setEditingVoce(null);
    },
  });

  const deleteVoceMutation = useMutation({
    mutationFn: (id: number) => deleteVoce(id),
    onSuccess: () => {
      toast.success("Modifica salvata");
      queryClient.invalidateQueries({ queryKey: ["admin-listino-voci", selectedCategoriaId] });
      setDeleteVoceTarget(null);
    },
  });

  function openCreateCategoria() {
    setEditingCategoria(null);
    setCategoriaCode("");
    setCategoriaBase("");
    setCategoriaCoeff("");
    setCategoriaDialogOpen(true);
  }

  function openEditCategoria(row: ListinoCategoriaOut) {
    setEditingCategoria(row);
    setCategoriaCode(row.categoria_code);
    setCategoriaBase(String(row.base_eur_mq));
    setCategoriaCoeff(String(row.coefficiente_impresa));
    setCategoriaDialogOpen(true);
  }

  function closeCategoriaDialog() {
    setCategoriaDialogOpen(false);
    setEditingCategoria(null);
  }

  function openEditVoce(row: VoceOut) {
    setEditingVoce(row);
    setVocePrezzo(String(row.prezzo_cliente));
    setVoceUm(row.um);
    setVoceDialogOpen(true);
  }

  const selectedCategoria = categorieQuery.data?.find((c) => c.id === selectedCategoriaId) ?? null;
  const selectedListino = listiniQuery.data?.find((l) => l.id === selectedListinoId) ?? null;

  function openEditListino() {
    if (!selectedListino) return;
    setEditListinoNome(selectedListino.nome);
    setEditListinoIsDefault(selectedListino.is_default);
    setEditListinoAttivo(selectedListino.attivo);
    setEditListinoDialogOpen(true);
  }

  return (
    <AdminLayout>
      <div className="flex flex-col gap-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-lg font-semibold text-foreground">Listini e prezzi</h1>
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="outline" onClick={() => scaricaListinoMutation.mutate()} disabled={selectedListinoId === null || scaricaListinoMutation.isPending}><Download className="size-4" />{scaricaListinoMutation.isPending ? "Generazione…" : "Scarica listino"}</Button>
            <Button type="button" variant="outline" onClick={() => setUploadOpen(true)}>
              <UploadCloud className="size-4" />
              Carica file
            </Button>
            <Button type="button" variant="outline" onClick={openEditListino} disabled={selectedListino === null}>
              <Pencil className="size-4" />
              Modifica listino
            </Button>
            <Button type="button" onClick={() => setListinoDialogOpen(true)}>
              Aggiungi listino
            </Button>
          </div>
        </div>

        <div className="flex flex-col gap-2 sm:w-80">
          <Label htmlFor="listino-select">Listino</Label>
          <Select
            value={selectedListinoId !== null ? String(selectedListinoId) : ""}
            onValueChange={(value) => {
              setSelectedListinoId(Number(value));
              setSelectedCategoriaId(null);
            }}
          >
            <SelectTrigger id="listino-select" className="w-full">
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

        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-foreground">Categorie</h2>
            <Button type="button" size="sm" variant="outline" onClick={openCreateCategoria} disabled={selectedListinoId === null}>
              Aggiungi categoria
            </Button>
          </div>

          <AdminTable
            columns={["Categoria", "Base €/m²", "Coefficiente impresa", "Azioni"]}
            isLoading={categorieQuery.isLoading}
            isEmpty={(categorieQuery.data ?? []).length === 0}
            emptyHeading="Nessun elemento presente"
            emptyBody="Aggiungi il primo elemento con il pulsante qui sopra, oppure carica un file."
            rows={(categorieQuery.data ?? []).map((row) => [
              row.categoria_code,
              <span className="tabular-nums" key="base">
                {row.base_eur_mq.toLocaleString("it-IT", { style: "currency", currency: "EUR" })}
              </span>,
              <span className="tabular-nums" key="coeff">
                {row.coefficiente_impresa.toLocaleString("it-IT", { maximumFractionDigits: 2 })}
              </span>,
              <div className="flex gap-1" key="azioni">
                <Button
                  type="button"
                  variant="ghost"
                  size="icon-sm"
                  aria-label="Voci"
                  onClick={() => setSelectedCategoriaId(row.id)}
                >
                  <ListIcon className="size-4" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon-sm"
                  aria-label="Modifica"
                  onClick={() => openEditCategoria(row)}
                >
                  <Pencil className="size-4" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon-sm"
                  aria-label="Elimina"
                  onClick={() => setDeleteCategoriaTarget(row)}
                >
                  <Trash2 className="size-4" />
                </Button>
              </div>,
            ])}
          />
        </div>

        {selectedCategoriaId !== null && (
          <div className="flex flex-col gap-3">
            <h2 className="text-base font-semibold text-foreground">
              Voci{selectedCategoria ? ` — ${selectedCategoria.categoria_code}` : ""}
            </h2>

            <AdminTable
              columns={["Codice", "Descrizione", "UM", "Prezzo cliente", "Azioni"]}
              isLoading={vociQuery.isLoading}
              isEmpty={(vociQuery.data ?? []).length === 0}
              emptyHeading="Nessun elemento presente"
              emptyBody="Le voci vengono create tramite il caricamento di un listino Excel."
              rows={(vociQuery.data ?? []).map((row) => [
                row.codice ?? "—",
                row.descrizione,
                row.um,
                <span className="tabular-nums" key="prezzo">
                  {row.prezzo_cliente.toLocaleString("it-IT", { style: "currency", currency: "EUR" })}
                </span>,
                <div className="flex gap-1" key="azioni">
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    aria-label="Modifica"
                    onClick={() => openEditVoce(row)}
                  >
                    <Pencil className="size-4" />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    aria-label="Elimina"
                    onClick={() => setDeleteVoceTarget(row)}
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </div>,
              ])}
            />
          </div>
        )}
      </div>

      {/* Aggiungi listino */}
      <AdminCrudDialog
        open={listinoDialogOpen}
        onOpenChange={setListinoDialogOpen}
        entityLabel="listino"
        title="Aggiungi listino"
        description="Crea un nuovo listino, opzionalmente per una città nuova."
        onSubmit={() => createListinoMutation.mutate()}
        isSaving={createListinoMutation.isPending}
        errorMessage={createListinoMutation.isError ? "Non siamo riusciti a salvare la modifica. Riprova." : null}
      >
        <div className="flex flex-col gap-2">
          <Label htmlFor="listino-nome">Nome</Label>
          <Input id="listino-nome" value={listinoNome} onChange={(e) => setListinoNome(e.target.value)} required />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="listino-citta">Città di riferimento</Label>
          <Input
            id="listino-citta"
            value={listinoCitta}
            onChange={(e) => setListinoCitta(e.target.value)}
            required
          />
        </div>
        <div className="flex items-center gap-2">
          <Switch id="listino-default" checked={listinoIsDefault} onCheckedChange={setListinoIsDefault} />
          <Label htmlFor="listino-default" className="font-normal">
            Listino di default (fallback)
          </Label>
        </div>
      </AdminCrudDialog>

      {/* Modifica listino */}
      <AdminCrudDialog
        open={editListinoDialogOpen}
        onOpenChange={setEditListinoDialogOpen}
        entityLabel="listino"
        title="Modifica listino"
        onSubmit={() => updateListinoMutation.mutate()}
        isSaving={updateListinoMutation.isPending}
        errorMessage={updateListinoMutation.isError ? "Non siamo riusciti a salvare la modifica. Riprova." : null}
      >
        <div className="flex flex-col gap-2">
          <Label htmlFor="edit-listino-nome">Nome</Label>
          <Input
            id="edit-listino-nome"
            value={editListinoNome}
            onChange={(e) => setEditListinoNome(e.target.value)}
            required
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label>Città di riferimento</Label>
          <p className="rounded-md bg-muted px-3 py-2 text-sm text-foreground">
            {selectedListino?.citta_riferimento}
          </p>
          <p className="text-xs text-muted-foreground">
            La città del listino non si cambia: crea un nuovo listino e sposta i comuni da Città e
            testi.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Switch
            id="edit-listino-default"
            checked={editListinoIsDefault}
            onCheckedChange={setEditListinoIsDefault}
          />
          <Label htmlFor="edit-listino-default" className="font-normal">
            Predefinito (fallback)
          </Label>
        </div>
        <div className="flex items-center gap-2">
          <Switch id="edit-listino-attivo" checked={editListinoAttivo} onCheckedChange={setEditListinoAttivo} />
          <Label htmlFor="edit-listino-attivo" className="font-normal">
            Attivo
          </Label>
        </div>
      </AdminCrudDialog>

      {/* Aggiungi/modifica categoria */}
      <AdminCrudDialog
        open={categoriaDialogOpen}
        onOpenChange={closeCategoriaDialog}
        entityLabel="categoria"
        title={editingCategoria ? "Modifica categoria" : "Aggiungi categoria"}
        onSubmit={() => (editingCategoria ? updateCategoriaMutation.mutate() : createCategoriaMutation.mutate())}
        isSaving={createCategoriaMutation.isPending || updateCategoriaMutation.isPending}
        errorMessage={
          createCategoriaMutation.isError || updateCategoriaMutation.isError
            ? "Non siamo riusciti a salvare la modifica. Riprova."
            : null
        }
      >
        <div className="flex flex-col gap-2">
          <Label htmlFor="categoria-code">Codice categoria</Label>
          <Input
            id="categoria-code"
            value={categoriaCode}
            onChange={(e) => setCategoriaCode(e.target.value)}
            disabled={!!editingCategoria}
            required
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="categoria-base">Base €/m²</Label>
          <Input
            id="categoria-base"
            type="number"
            step="0.01"
            min="0"
            value={categoriaBase}
            onChange={(e) => setCategoriaBase(e.target.value)}
            required
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="categoria-coeff">Coefficiente impresa</Label>
          <Input
            id="categoria-coeff"
            type="number"
            step="0.01"
            min="0"
            max="1"
            value={categoriaCoeff}
            onChange={(e) => setCategoriaCoeff(e.target.value)}
            required
          />
        </div>
      </AdminCrudDialog>

      {/* Modifica voce — SOLO prezzo/UM (descrizione read-only) */}
      <AdminCrudDialog
        open={voceDialogOpen}
        onOpenChange={setVoceDialogOpen}
        entityLabel="voce"
        title="Modifica voce"
        onSubmit={() => updateVoceMutation.mutate()}
        isSaving={updateVoceMutation.isPending}
        errorMessage={updateVoceMutation.isError ? "Non siamo riusciti a salvare la modifica. Riprova." : null}
      >
        <div className="flex flex-col gap-2">
          <Label>Codice</Label>
          <p className="rounded-md bg-muted px-3 py-2 text-sm text-foreground">
            {editingVoce?.codice ?? "—"}
          </p>
        </div>
        <div className="flex flex-col gap-2">
          <Label>Descrizione</Label>
          <p className="text-sm text-muted-foreground">{editingVoce?.descrizione}</p>
          <p className="text-xs text-muted-foreground">
            Codice e descrizione identificano la voce nel computo: si cambiano da{" "}
            <Link to="/admin/dettaglio-pro" className="underline">
              Voci dettaglio Pro
            </Link>
            .
          </p>
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="voce-prezzo">Prezzo cliente</Label>
          <Input
            id="voce-prezzo"
            type="number"
            step="0.01"
            min="0"
            value={vocePrezzo}
            onChange={(e) => setVocePrezzo(e.target.value)}
            required
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="voce-um">UM</Label>
          <Input id="voce-um" value={voceUm} onChange={(e) => setVoceUm(e.target.value)} required />
        </div>
      </AdminCrudDialog>

      <AdminDeleteConfirm
        open={deleteCategoriaTarget !== null}
        onOpenChange={(open) => !open && setDeleteCategoriaTarget(null)}
        entityLabel="categoria"
        description="Eliminare questa categoria dal listino? L'operazione non è reversibile."
        isDeleting={deleteCategoriaMutation.isPending}
        onConfirm={() => deleteCategoriaTarget && deleteCategoriaMutation.mutate(deleteCategoriaTarget.id)}
      />

      <AdminDeleteConfirm
        open={deleteVoceTarget !== null}
        onOpenChange={(open) => !open && setDeleteVoceTarget(null)}
        entityLabel="voce"
        description="Eliminare questa voce dal listino? L'operazione non è reversibile."
        isDeleting={deleteVoceMutation.isPending}
        onConfirm={() => deleteVoceTarget && deleteVoceMutation.mutate(deleteVoceTarget.id)}
      />

      <ExcelUploadDialog
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        listini={listiniQuery.data ?? []}
        defaultListinoId={selectedListinoId}
        onImported={(listinoId) => {
          queryClient.invalidateQueries({ queryKey: ["admin-listini"] });
          queryClient.invalidateQueries({ queryKey: ["admin-listino-categorie", listinoId] });
          setSelectedListinoId(listinoId);
        }}
      />
    </AdminLayout>
  );
}
