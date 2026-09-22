import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Download } from "lucide-react";
import { AdminLayout } from "@/pages/admin/AdminLayout";
import { AdminTable } from "@/components/admin/AdminTable";
import { AdminCrudDialog } from "@/components/admin/AdminCrudDialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { formatEurRange } from "@/lib/currency";
import { TIPO_LABELS } from "@/lib/tipoRistrutturazione";
import { getAdminLeads, getAdminLead, updateAdminLead, type LeadOut } from "@/api/admin/lead";
import { listListiniForSelect } from "@/api/admin/referenti";
import { scaricaExcel } from "@/api/admin/exportExcel";
import { getExportLog, type ExportLogRow } from "@/api/admin/exportLog";
import { useAuth } from "@/hooks/useAuth";

const PREFERENZA_LABELS: Record<string, string> = {
  email: "Email",
  telefono: "Telefono",
};

const FASCIA_LABELS: Record<string, string> = {
  mattina: "Mattina",
  pomeriggio: "Pomeriggio",
  sera: "Sera",
};

const RISORSA_LABELS: Record<string, string> = {
  listino: "Listino",
  domande: "Catalogo domande",
  parametri: "Parametri",
  lead: "Lead",
};

const EXPORT_ERROR = "Non siamo riusciti a generare il file. Riprova.";

const ALL_VALUE = "__tutte__";

function formatData(iso: string): string {
  return new Date(iso).toLocaleDateString("it-IT");
}

function StatoBadge({ stato }: { stato: string }) {
  return (
    <Badge
      className={
        stato === "nuovo"
          ? "bg-primary/10 text-primary"
          : "bg-muted text-muted-foreground"
      }
    >
      {stato === "nuovo" ? "Nuovo" : "Gestito"}
    </Badge>
  );
}

/**
 * Dashboard lead (/admin/lead, ADM-04/D-17, UI-SPEC §C): lista con filtri
 * città/stato, dettaglio con snapshot a range e aggiornamento stato/nota.
 * Guard di ruolo delegata ad AdminLayout; ogni useQuery qui è comunque
 * gated su `isAdmin` per non far partire il fetch prima del guard
 * (T-04-27), coerente con l'analog LeMieStimePage.
 */
function LeadDashboardContent() {
  const { user } = useAuth();
  // Staff = admin O consulente: entrambi vedono/lavorano i lead. Il dropdown
  // città (listini) resta admin-only: il consulente non accede a /admin/listini
  // (403), quindi per lui il filtro città non ha opzioni preimpostate.
  const isStaff = user?.role === "admin" || user?.role === "consulente";
  const isAdmin = user?.role === "admin";
  const queryClient = useQueryClient();

  const [cittaFilter, setCittaFilter] = useState("");
  const [statoFilter, setStatoFilter] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [notaValue, setNotaValue] = useState("");
  const [statoValue, setStatoValue] = useState("nuovo");

  const leadsQuery = useQuery<LeadOut[]>({
    queryKey: ["admin-leads", cittaFilter, statoFilter],
    queryFn: () =>
      getAdminLeads({
        citta: cittaFilter || undefined,
        stato: statoFilter || undefined,
      }),
    enabled: isStaff,
  });

  const listiniQuery = useQuery({
    queryKey: ["admin-listini-select"],
    queryFn: listListiniForSelect,
    enabled: isAdmin,
  });

  const detailQuery = useQuery({
    queryKey: ["admin-lead-detail", selectedId],
    queryFn: () => getAdminLead(selectedId as number),
    enabled: isStaff && selectedId !== null,
  });

  const exportLogQuery = useQuery<ExportLogRow[]>({
    queryKey: ["admin-export-log"],
    queryFn: getExportLog,
    enabled: isStaff,
  });

  const scaricaLeadMutation = useMutation({
    mutationFn: () => scaricaExcel("/admin/lead/export.xlsx"),
    onError: () => {
      toast.error(EXPORT_ERROR);
    },
  });

  useEffect(() => {
    if (detailQuery.data) {
      setNotaValue(detailQuery.data.nota ?? "");
      setStatoValue(detailQuery.data.stato);
    }
  }, [detailQuery.data]);

  const updateMutation = useMutation({
    mutationFn: (input: { stato: string; nota: string | null }) =>
      updateAdminLead(selectedId as number, input),
    onSuccess: () => {
      toast.success("Lead aggiornato");
      void queryClient.invalidateQueries({ queryKey: ["admin-leads"] });
      void queryClient.invalidateQueries({ queryKey: ["admin-lead-detail", selectedId] });
    },
  });

  const cities = Array.from(
    new Set((listiniQuery.data ?? []).map((l) => l.citta_riferimento))
  ).sort((a, b) => a.localeCompare(b));

  const filtersActive = !!cittaFilter || !!statoFilter;

  function resetFilters() {
    setCittaFilter("");
    setStatoFilter("");
  }

  function handleSaveNotaStato() {
    updateMutation.mutate({ stato: statoValue, nota: notaValue.trim() ? notaValue.trim() : null });
  }

  const rows = (leadsQuery.data ?? []).map((item) => [
    <div key="data" className="cursor-pointer text-sm" onClick={() => setSelectedId(item.id)}>
      {formatData(item.created_at)}
    </div>,
    <div key="citta" className="cursor-pointer text-sm" onClick={() => setSelectedId(item.id)}>
      {item.citta}
    </div>,
    <div key="nome" className="cursor-pointer text-sm font-medium" onClick={() => setSelectedId(item.id)}>
      {item.nome}
    </div>,
    <div key="contatti" className="cursor-pointer flex flex-col text-sm" onClick={() => setSelectedId(item.id)}>
      <span>{item.email}</span>
      {item.telefono && <span className="text-muted-foreground">{item.telefono}</span>}
    </div>,
    <div
      key="totale"
      className="cursor-pointer text-right text-sm tabular-nums font-medium"
      onClick={() => setSelectedId(item.id)}
    >
      {formatEurRange(item.totale_min, item.totale_max)}
    </div>,
    <div key="stato" className="cursor-pointer" onClick={() => setSelectedId(item.id)}>
      <StatoBadge stato={item.stato} />
    </div>,
  ]);

  const exportLogRows = (exportLogQuery.data ?? []).map((item) => [
    <div key="data" className="text-sm">
      {formatData(item.created_at)}
    </div>,
    <div key="utente" className="text-sm">
      {item.user_label}
    </div>,
    <div key="risorsa" className="text-sm">
      {RISORSA_LABELS[item.risorsa] ?? item.risorsa}
    </div>,
    <div key="righe" className="text-right text-sm tabular-nums">
      {item.righe}
    </div>,
    <div key="margine">
      {item.include_margine ? (
        <Badge className="bg-amber-bg text-amber-fg">Sì</Badge>
      ) : (
        <span className="text-sm text-muted-foreground">—</span>
      )}
    </div>,
  ]);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-semibold text-foreground">Lead</h1>
        <Button
          type="button"
          variant="outline"
          onClick={() => scaricaLeadMutation.mutate()}
          disabled={scaricaLeadMutation.isPending}
        >
          <Download className="size-4" />
          {scaricaLeadMutation.isPending ? "Generazione…" : "Scarica lead"}
        </Button>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Select
          value={cittaFilter || ALL_VALUE}
          onValueChange={(v) => setCittaFilter(v === ALL_VALUE ? "" : v)}
        >
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Filtra per città" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL_VALUE}>Tutte le città</SelectItem>
            {cities.map((c) => (
              <SelectItem key={c} value={c}>
                {c}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={statoFilter || ALL_VALUE}
          onValueChange={(v) => setStatoFilter(v === ALL_VALUE ? "" : v)}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Filtra per stato" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL_VALUE}>Tutti gli stati</SelectItem>
            <SelectItem value="nuovo">Nuovo</SelectItem>
            <SelectItem value="gestito">Gestito</SelectItem>
          </SelectContent>
        </Select>

        {filtersActive && (
          <button
            type="button"
            onClick={resetFilters}
            className="text-sm font-medium text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
          >
            Rimuovi filtri
          </button>
        )}
      </div>

      <AdminTable
        columns={["Data", "Città", "Nome", "Contatti", "Totale stima", "Stato"]}
        isLoading={leadsQuery.isLoading}
        rows={rows}
        isEmpty={!leadsQuery.isLoading && (leadsQuery.data?.length ?? 0) === 0}
        emptyHeading={
          filtersActive ? "Nessun lead corrisponde ai filtri selezionati." : "Nessun lead ricevuto"
        }
        emptyBody={
          filtersActive ? (
            <button
              type="button"
              onClick={resetFilters}
              className="text-sm font-medium text-primary underline-offset-4 hover:underline"
            >
              Rimuovi filtri
            </button>
          ) : (
            "Le richieste di contatto degli utenti compariranno qui."
          )
        }
      />

      <AdminCrudDialog
        open={selectedId !== null}
        onOpenChange={(open) => {
          if (!open) {
            setSelectedId(null);
            updateMutation.reset();
          }
        }}
        entityLabel="nota e stato"
        title={detailQuery.data?.nome ?? "Dettaglio lead"}
        onSubmit={handleSaveNotaStato}
        isSaving={updateMutation.isPending}
        errorMessage={
          updateMutation.isError ? "Non siamo riusciti a salvare la modifica. Riprova." : null
        }
      >
        {detailQuery.isLoading && (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        )}

        {detailQuery.isSuccess && detailQuery.data && (
          <div className="flex flex-col gap-4">
            <p className="text-sm text-muted-foreground">
              {formatData(detailQuery.data.created_at)} · {detailQuery.data.citta}
            </p>

            <div className="flex flex-col gap-2">
              <h3 className="text-sm font-semibold text-foreground">Dati di contatto</h3>
              <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
                <dt className="text-muted-foreground">Email</dt>
                <dd className="text-foreground">{detailQuery.data.email}</dd>
                <dt className="text-muted-foreground">Telefono</dt>
                <dd className="text-foreground">{detailQuery.data.telefono ?? "—"}</dd>
                <dt className="text-muted-foreground">Preferenza</dt>
                <dd className="text-foreground">
                  {PREFERENZA_LABELS[detailQuery.data.preferenza_contatto] ??
                    detailQuery.data.preferenza_contatto}
                </dd>
                <dt className="text-muted-foreground">Fascia oraria</dt>
                <dd className="text-foreground">
                  {detailQuery.data.fascia_oraria
                    ? FASCIA_LABELS[detailQuery.data.fascia_oraria] ?? detailQuery.data.fascia_oraria
                    : "—"}
                </dd>
                {detailQuery.data.messaggio && (
                  <>
                    <dt className="text-muted-foreground">Messaggio</dt>
                    <dd className="text-foreground">{detailQuery.data.messaggio}</dd>
                  </>
                )}
              </dl>
            </div>

            <div className="flex flex-col gap-2">
              <h3 className="text-sm font-semibold text-foreground">Stima allegata</h3>
              <div className="rounded-lg border border-border bg-secondary px-4 py-3 text-sm text-muted-foreground">
                {detailQuery.data.citta} · {detailQuery.data.mq} m² ·{" "}
                {TIPO_LABELS[detailQuery.data.tipo] ?? detailQuery.data.tipo} ·{" "}
                <span className="font-semibold text-foreground tabular-nums">
                  {formatEurRange(detailQuery.data.totale_min, detailQuery.data.totale_max)}
                </span>
              </div>
            </div>

            <div className="flex flex-col gap-2">
              <h3 className="text-sm font-semibold text-foreground">Nota interna</h3>
              <Select value={statoValue} onValueChange={setStatoValue}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="nuovo">Nuovo</SelectItem>
                  <SelectItem value="gestito">Gestito</SelectItem>
                </SelectContent>
              </Select>
              <Textarea
                rows={3}
                placeholder="Aggiungi una nota (es. esito della chiamata)…"
                value={notaValue}
                onChange={(e) => setNotaValue(e.target.value)}
              />
            </div>
          </div>
        )}
      </AdminCrudDialog>

      <div className="flex flex-col gap-3">
        <h2 className="text-base font-semibold text-foreground">Download registrati</h2>
        <AdminTable
          columns={["Data", "Utente", "Risorsa", "Righe", "Margine"]}
          isLoading={exportLogQuery.isLoading}
          rows={exportLogRows}
          isEmpty={!exportLogQuery.isLoading && (exportLogQuery.data?.length ?? 0) === 0}
          emptyHeading="Nessun download registrato"
          emptyBody="I download di questa pagina compariranno qui."
        />
      </div>
    </div>
  );
}

export function LeadDashboardPage() {
  return (
    <AdminLayout allow={["admin", "consulente"]}>
      <LeadDashboardContent />
    </AdminLayout>
  );
}
