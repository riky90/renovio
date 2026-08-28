import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { AdminLayout } from "@/pages/admin/AdminLayout";
import { AdminTable } from "@/components/admin/AdminTable";
import { AdminCrudDialog } from "@/components/admin/AdminCrudDialog";
import { AdminDeleteConfirm } from "@/components/admin/AdminDeleteConfirm";
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
  listReferenti,
  createReferente,
  updateReferente,
  deleteReferente,
  listListiniForSelect,
  type ReferenteOut,
} from "@/api/admin/referenti";
import { useAuth } from "@/hooks/useAuth";

interface ReferenteFormState {
  listinoId: string;
  nome: string;
  email: string;
  telefono: string;
  attivo: boolean;
  priorita: string;
}

const EMPTY_FORM: ReferenteFormState = {
  listinoId: "",
  nome: "",
  email: "",
  telefono: "",
  attivo: true,
  priorita: "0",
};

/**
 * CRUD referenti (/admin/referenti, ADM-04/D-15/D-16, UI-SPEC §D): tabella
 * + dialog aggiungi/modifica + conferma distruttiva sull'elimina. Guard di
 * ruolo delegata ad AdminLayout; ogni useQuery qui è comunque gated su
 * `isAdmin` per non far partire il fetch prima del guard (T-04-27).
 */
function ReferentiContent() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const queryClient = useQueryClient();

  const referentiQuery = useQuery<ReferenteOut[]>({
    queryKey: ["admin-referenti"],
    queryFn: listReferenti,
    enabled: isAdmin,
  });

  const listiniQuery = useQuery({
    queryKey: ["admin-listini-select"],
    queryFn: listListiniForSelect,
    enabled: isAdmin,
  });

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<ReferenteOut | null>(null);
  const [form, setForm] = useState<ReferenteFormState>(EMPTY_FORM);
  const [deleting, setDeleting] = useState<ReferenteOut | null>(null);

  useEffect(() => {
    if (dialogOpen) {
      setForm(
        editing
          ? {
              listinoId: String(editing.listino_id),
              nome: editing.nome,
              email: editing.email,
              telefono: editing.telefono ?? "",
              attivo: editing.attivo,
              priorita: String(editing.priorita),
            }
          : EMPTY_FORM
      );
    }
  }, [dialogOpen, editing]);

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ["admin-referenti"] });
  }

  const saveMutation = useMutation({
    mutationFn: () => {
      const payload = {
        listino_id: Number(form.listinoId),
        nome: form.nome.trim(),
        email: form.email.trim(),
        telefono: form.telefono.trim() ? form.telefono.trim() : null,
        attivo: form.attivo,
        priorita: Number(form.priorita) || 0,
      };
      return editing ? updateReferente(editing.id, payload) : createReferente(payload);
    },
    onSuccess: () => {
      toast.success("Modifica salvata");
      invalidate();
      setDialogOpen(false);
      setEditing(null);
    },
  });

  const toggleAttivoMutation = useMutation({
    mutationFn: ({ id, attivo }: { id: number; attivo: boolean }) =>
      updateReferente(id, { attivo }),
    onSuccess: () => {
      toast.success("Modifica salvata");
      invalidate();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteReferente(id),
    onSuccess: () => {
      toast.success("Modifica salvata");
      invalidate();
      setDeleting(null);
    },
  });

  function openCreate() {
    setEditing(null);
    setDialogOpen(true);
  }

  function openEdit(referente: ReferenteOut) {
    setEditing(referente);
    setDialogOpen(true);
  }

  const listinoNameById = new Map(
    (listiniQuery.data ?? []).map((l) => [l.id, l.citta_riferimento])
  );

  const formValid =
    form.listinoId !== "" && form.nome.trim().length > 0 && form.email.trim().length > 0;

  const rows = (referentiQuery.data ?? []).map((referente) => [
    <span key="nome" className="text-sm font-medium">
      {referente.nome}
    </span>,
    <span key="email" className="text-sm">
      {referente.email}
    </span>,
    <span key="telefono" className="text-sm">
      {referente.telefono ?? "—"}
    </span>,
    <span key="listino" className="text-sm">
      {listinoNameById.get(referente.listino_id) ?? `#${referente.listino_id}`}
    </span>,
    <Switch
      key="attivo"
      checked={referente.attivo}
      onCheckedChange={(checked) =>
        toggleAttivoMutation.mutate({ id: referente.id, attivo: checked })
      }
      aria-label={referente.attivo ? "Disattiva referente" : "Attiva referente"}
    />,
    <span key="priorita" className="text-sm tabular-nums">
      {referente.priorita}
    </span>,
    <div key="azioni" className="flex items-center gap-1">
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        aria-label="Modifica"
        title="Modifica"
        onClick={() => openEdit(referente)}
      >
        <Pencil className="size-4" />
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        aria-label="Elimina"
        title="Elimina"
        onClick={() => setDeleting(referente)}
      >
        <Trash2 className="size-4" />
      </Button>
    </div>,
  ]);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-lg font-semibold text-foreground">Referenti</h1>
        <Button
          type="button"
          onClick={openCreate}
          className="bg-primary text-primary-foreground hover:bg-primary/90"
        >
          Aggiungi referente
        </Button>
      </div>

      <AdminTable
        columns={["Nome", "Email", "Telefono", "Città/listino", "Attivo", "Priorità", ""]}
        isLoading={referentiQuery.isLoading}
        rows={rows}
        isEmpty={!referentiQuery.isLoading && (referentiQuery.data?.length ?? 0) === 0}
        emptyHeading="Nessun elemento presente"
        emptyBody="Aggiungi il primo elemento con il pulsante qui sopra, oppure carica un file."
      />

      <AdminCrudDialog
        open={dialogOpen}
        onOpenChange={(open) => {
          setDialogOpen(open);
          if (!open) {
            saveMutation.reset();
            setEditing(null);
          }
        }}
        entityLabel="referente"
        title={editing ? "Modifica referente" : "Aggiungi referente"}
        onSubmit={() => {
          if (!formValid) return;
          saveMutation.mutate();
        }}
        isSaving={saveMutation.isPending}
        errorMessage={
          saveMutation.isError ? "Non siamo riusciti a salvare la modifica. Riprova." : null
        }
      >
        <div className="flex flex-col gap-2">
          <Label htmlFor="referente-listino">Città / listino</Label>
          <Select
            value={form.listinoId}
            onValueChange={(v) => setForm((f) => ({ ...f, listinoId: v }))}
          >
            <SelectTrigger id="referente-listino" className="w-full">
              <SelectValue placeholder="Seleziona una città" />
            </SelectTrigger>
            <SelectContent>
              {(listiniQuery.data ?? []).map((l) => (
                <SelectItem key={l.id} value={String(l.id)}>
                  {l.citta_riferimento}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex flex-col gap-2">
          <Label htmlFor="referente-nome">Nome</Label>
          <Input
            id="referente-nome"
            value={form.nome}
            onChange={(e) => setForm((f) => ({ ...f, nome: e.target.value }))}
          />
        </div>

        <div className="flex flex-col gap-2">
          <Label htmlFor="referente-email">Email</Label>
          <Input
            id="referente-email"
            type="email"
            value={form.email}
            onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
          />
        </div>

        <div className="flex flex-col gap-2">
          <Label htmlFor="referente-telefono">Telefono</Label>
          <Input
            id="referente-telefono"
            inputMode="tel"
            value={form.telefono}
            onChange={(e) => setForm((f) => ({ ...f, telefono: e.target.value }))}
          />
        </div>

        <div className="flex items-center justify-between gap-3">
          <Label htmlFor="referente-attivo">Attivo</Label>
          <Switch
            id="referente-attivo"
            checked={form.attivo}
            onCheckedChange={(checked) => setForm((f) => ({ ...f, attivo: checked }))}
          />
        </div>

        <div className="flex flex-col gap-2">
          <Label htmlFor="referente-priorita">Priorità</Label>
          <Input
            id="referente-priorita"
            type="number"
            min={0}
            value={form.priorita}
            onChange={(e) => setForm((f) => ({ ...f, priorita: e.target.value }))}
          />
        </div>
      </AdminCrudDialog>

      <AdminDeleteConfirm
        open={deleting !== null}
        onOpenChange={(open) => !open && setDeleting(null)}
        entityLabel="referente"
        description={`Eliminare ${deleting?.nome ?? ""}? Non riceverà più i lead di questa città.`}
        onConfirm={() => deleting && deleteMutation.mutate(deleting.id)}
        isDeleting={deleteMutation.isPending}
      />
    </div>
  );
}

export function ReferentiPage() {
  return (
    <AdminLayout>
      <ReferentiContent />
    </AdminLayout>
  );
}
