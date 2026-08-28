import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AdminLayout } from "@/pages/admin/AdminLayout";
import { AdminTable } from "@/components/admin/AdminTable";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { listUtenti, updateRuolo, type UtenteOut, type Ruolo } from "@/api/admin/utenti";
import { useAuth } from "@/hooks/useAuth";

const RUOLO_LABEL: Record<Ruolo, string> = {
  user: "Utente",
  consulente: "Consulente",
  admin: "Admin",
};

function formatData(iso: string): string {
  return new Date(iso).toLocaleDateString("it-IT");
}

/**
 * Gestione utenti/ruoli (/admin/utenti): l'admin assegna a ciascun utente il
 * ruolo user / consulente / admin. Il consulente vede i lead ma non la config
 * di business; l'admin ha pieno accesso. La riga dell'admin corrente è
 * bloccata (non può cambiare il proprio ruolo — anche il server rifiuta, 403).
 * Guard di ruolo (solo admin) delegata ad AdminLayout; il fetch è gated su
 * `isAdmin` per non partire prima del guard.
 */
function UtentiContent() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const queryClient = useQueryClient();

  const utentiQuery = useQuery<UtenteOut[]>({
    queryKey: ["admin-utenti"],
    queryFn: listUtenti,
    enabled: isAdmin,
  });

  const roleMutation = useMutation({
    mutationFn: ({ id, role }: { id: number; role: Ruolo }) => updateRuolo(id, role),
    onSuccess: (updated) => {
      toast.success(`Ruolo di ${updated.nome} aggiornato a "${RUOLO_LABEL[updated.role]}"`);
      void queryClient.invalidateQueries({ queryKey: ["admin-utenti"] });
    },
    onError: () => {
      toast.error("Non è stato possibile cambiare il ruolo. Riprova.");
    },
  });

  const rows = (utentiQuery.data ?? []).map((u) => {
    const isSelf = u.id === user?.id;
    return [
      <span key="nome" className="text-sm font-medium">
        {u.nome}
        {isSelf && <span className="ml-2 text-xs text-muted-foreground">(tu)</span>}
      </span>,
      <span key="email" className="text-sm">
        {u.email}
      </span>,
      <span key="registrato" className="text-sm text-muted-foreground">
        {formatData(u.created_at)}
      </span>,
      isSelf ? (
        <Badge key="ruolo" variant="secondary">
          {RUOLO_LABEL[u.role]}
        </Badge>
      ) : (
        <Select
          key="ruolo"
          value={u.role}
          onValueChange={(value) => roleMutation.mutate({ id: u.id, role: value as Ruolo })}
          disabled={roleMutation.isPending}
        >
          <SelectTrigger className="w-[160px]" aria-label={`Ruolo di ${u.nome}`}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="user">Utente</SelectItem>
            <SelectItem value="consulente">Consulente</SelectItem>
            <SelectItem value="admin">Admin</SelectItem>
          </SelectContent>
        </Select>
      ),
    ];
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-lg font-semibold text-foreground">Utenti</h1>
        <p className="text-sm text-muted-foreground">
          Assegna i ruoli. Un <strong>consulente</strong> vede e gestisce i lead; un{" "}
          <strong>admin</strong> ha pieno accesso e può gestire gli utenti.
        </p>
      </div>

      <AdminTable
        columns={["Nome", "Email", "Registrato", "Ruolo"]}
        isLoading={utentiQuery.isLoading}
        rows={rows}
        isEmpty={!utentiQuery.isLoading && (utentiQuery.data?.length ?? 0) === 0}
        emptyHeading="Nessun utente presente"
        emptyBody="Gli utenti registrati compariranno qui."
      />
    </div>
  );
}

export function UtentiPage() {
  return (
    <AdminLayout>
      <UtentiContent />
    </AdminLayout>
  );
}
