import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Trash2, SlidersHorizontal, Plus, ChevronRight } from "lucide-react";
import { toast } from "sonner";
import { AdminLayout } from "@/pages/admin/AdminLayout";
import { AdminCrudDialog } from "@/components/admin/AdminCrudDialog";
import { AdminDeleteConfirm } from "@/components/admin/AdminDeleteConfirm";
import { cn } from "@/lib/utils";
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
import { listListiniForSelect } from "@/api/admin/referenti";
import {
  listSottocategorie,
  createSottocategoria,
  updateSottocategoria,
  deleteSottocategoria,
  listVoci,
  createVoce,
  updateVoce,
  deleteVoce,
  listCoeffVoce,
  upsertCoeffVoce,
  deleteCoeffVoce,
  type SottocategoriaOut,
  type VoceOut,
  type Famiglia,
} from "@/api/admin/dettaglioPro";
import { useAuth } from "@/hooks/useAuth";

const TIPI = [
  { code: "leggera", label: "Leggera" },
  { code: "moderata", label: "Moderata" },
  { code: "totale", label: "Totale" },
];

const CATEGORIE = [
  { code: "A-EDILE", label: "A · Edile" },
  { code: "B-FINITURE", label: "B · Finiture" },
  { code: "C-SERRAMENTI", label: "C · Serramenti" },
  { code: "D-PRODOTTI", label: "D · Prodotti" },
];

interface SottoForm {
  categoria_code: string;
  codice: string;
  nome: string;
  famiglia: Famiglia;
  ordine: string;
}

const EMPTY_SOTTO: SottoForm = {
  categoria_code: "A-EDILE",
  codice: "",
  nome: "",
  famiglia: "gerarchica",
  ordine: "0",
};

interface VoceForm {
  codice: string;
  descrizione: string;
  um: string;
  prezzo: string;
  ordine: string;
}

const EMPTY_VOCE: VoceForm = { codice: "", descrizione: "", um: "", prezzo: "", ordine: "0" };

function sottoLabel(s: SottocategoriaOut): string {
  return s.codice ? `${s.codice} · ${s.nome}` : s.nome;
}

function DettaglioProContent() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const queryClient = useQueryClient();

  const [listinoId, setListinoId] = useState<number | null>(null);
  const [openItems, setOpenItems] = useState<string[]>([]);

  const listiniQuery = useQuery({
    queryKey: ["admin-listini-select"],
    queryFn: listListiniForSelect,
    enabled: isAdmin,
  });

  const sottoQuery = useQuery<SottocategoriaOut[]>({
    queryKey: ["admin-pro-sotto", listinoId],
    queryFn: () => listSottocategorie(listinoId as number),
    enabled: isAdmin && listinoId !== null,
  });

  // --- Sottocategoria dialog/state ---
  const [sottoDialogOpen, setSottoDialogOpen] = useState(false);
  const [editingSotto, setEditingSotto] = useState<SottocategoriaOut | null>(null);
  const [sottoForm, setSottoForm] = useState<SottoForm>(EMPTY_SOTTO);
  const [deletingSotto, setDeletingSotto] = useState<SottocategoriaOut | null>(null);

  useEffect(() => {
    if (sottoDialogOpen) {
      setSottoForm(
        editingSotto
          ? {
              categoria_code: editingSotto.categoria_code,
              codice: editingSotto.codice ?? "",
              nome: editingSotto.nome,
              famiglia: (editingSotto.famiglia as Famiglia) ?? "gerarchica",
              ordine: String(editingSotto.ordine),
            }
          : EMPTY_SOTTO,
      );
    }
  }, [sottoDialogOpen, editingSotto]);

  const saveSotto = useMutation({
    mutationFn: () => {
      const base = {
        categoria_code: sottoForm.categoria_code,
        codice: sottoForm.codice.trim() ? sottoForm.codice.trim() : null,
        nome: sottoForm.nome.trim(),
        famiglia: sottoForm.famiglia,
        ordine: Number(sottoForm.ordine) || 0,
      };
      return editingSotto
        ? updateSottocategoria(editingSotto.id, base)
        : createSottocategoria({ listino_id: listinoId as number, ...base });
    },
    onSuccess: () => {
      toast.success("Sottocategoria salvata");
      void queryClient.invalidateQueries({ queryKey: ["admin-pro-sotto", listinoId] });
      setSottoDialogOpen(false);
      setEditingSotto(null);
    },
  });

  const deleteSotto = useMutation({
    mutationFn: (id: number) => deleteSottocategoria(id),
    onSuccess: () => {
      toast.success("Sottocategoria eliminata");
      void queryClient.invalidateQueries({ queryKey: ["admin-pro-sotto", listinoId] });
      setDeletingSotto(null);
    },
    onError: () => toast.error("Elimina prima le voci di questa sottocategoria."),
  });

  // --- Voce dialog/state ---
  const [voceDialogOpen, setVoceDialogOpen] = useState(false);
  const [editingVoce, setEditingVoce] = useState<VoceOut | null>(null);
  const [voceTargetSottoId, setVoceTargetSottoId] = useState<number | null>(null);
  const [voceForm, setVoceForm] = useState<VoceForm>(EMPTY_VOCE);
  const [deletingVoce, setDeletingVoce] = useState<VoceOut | null>(null);
  const [applVoce, setApplVoce] = useState<VoceOut | null>(null);

  useEffect(() => {
    if (voceDialogOpen) {
      setVoceForm(
        editingVoce
          ? {
              codice: editingVoce.codice ?? "",
              descrizione: editingVoce.descrizione,
              um: editingVoce.um,
              prezzo: String(editingVoce.prezzo_unitario_cliente),
              ordine: String(editingVoce.ordine),
            }
          : EMPTY_VOCE,
      );
    }
  }, [voceDialogOpen, editingVoce]);

  function invalidateVoci(sottoId: number | null | undefined) {
    if (sottoId != null) void queryClient.invalidateQueries({ queryKey: ["admin-pro-voci", sottoId] });
  }

  const saveVoce = useMutation({
    mutationFn: () => {
      const base = {
        codice: voceForm.codice.trim() ? voceForm.codice.trim() : null,
        descrizione: voceForm.descrizione.trim(),
        um: voceForm.um.trim(),
        prezzo_unitario_cliente: Number(voceForm.prezzo),
        ordine: Number(voceForm.ordine) || 0,
      };
      return editingVoce
        ? updateVoce(editingVoce.id, base)
        : createVoce({ sottocategoria_id: voceTargetSottoId as number, ...base });
    },
    onSuccess: () => {
      toast.success("Voce salvata");
      invalidateVoci(editingVoce ? editingVoce.sottocategoria_id : voceTargetSottoId);
      setVoceDialogOpen(false);
      setEditingVoce(null);
    },
  });

  const deleteVoceMut = useMutation({
    mutationFn: (v: VoceOut) => deleteVoce(v.id),
    onSuccess: (_data, v) => {
      toast.success("Voce eliminata");
      invalidateVoci(v.sottocategoria_id);
      setDeletingVoce(null);
    },
  });

  function openAddVoce(sottoId: number) {
    setEditingVoce(null);
    setVoceTargetSottoId(sottoId);
    setVoceDialogOpen(true);
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-lg font-semibold text-foreground">Voci di dettaglio Pro</h1>
        <p className="text-sm text-muted-foreground">
          Sottocategorie e voci che fanno da base al preventivo di dettaglio Pro. Espandi una
          sottocategoria per vedere e gestire le sue voci. Puoi popolare tutto da un file Excel
          (Listini → Carica listino) oppure a mano qui.
        </p>
      </div>

      <div className="flex flex-col gap-2 sm:w-80">
        <Label htmlFor="pro-listino">Listino</Label>
        <Select
          value={listinoId !== null ? String(listinoId) : ""}
          onValueChange={(v) => {
            setListinoId(Number(v));
            setOpenItems([]);
          }}
        >
          <SelectTrigger id="pro-listino" className="w-full">
            <SelectValue placeholder="Seleziona un listino" />
          </SelectTrigger>
          <SelectContent>
            {(listiniQuery.data ?? []).map((l) => (
              <SelectItem key={l.id} value={String(l.id)}>
                {l.nome} ({l.citta_riferimento})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {listinoId !== null && (
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-base font-semibold text-foreground">Sottocategorie</h2>
            <Button type="button" onClick={() => { setEditingSotto(null); setSottoDialogOpen(true); }}>
              <Plus className="mr-1 size-4" /> Sottocategoria
            </Button>
          </div>

          {sottoQuery.isLoading && (
            <p className="text-sm text-muted-foreground">Caricamento…</p>
          )}
          {sottoQuery.isSuccess && (sottoQuery.data?.length ?? 0) === 0 && (
            <div className="rounded-lg border border-border bg-card px-4 py-8 text-center">
              <p className="text-sm font-semibold text-foreground">Nessuna sottocategoria</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Aggiungine una, oppure carica un listino da Excel.
              </p>
            </div>
          )}

          {(sottoQuery.data?.length ?? 0) > 0 && (
            <div className="flex flex-col overflow-hidden rounded-lg border border-border bg-card">
              {(sottoQuery.data ?? []).map((s) => (
                <SottoCollapsible
                  key={s.id}
                  sotto={s}
                  isOpen={openItems.includes(String(s.id))}
                  onToggle={() =>
                    setOpenItems((prev) =>
                      prev.includes(String(s.id))
                        ? prev.filter((x) => x !== String(s.id))
                        : [...prev, String(s.id)],
                    )
                  }
                  onAddVoce={() => openAddVoce(s.id)}
                  onEditVoce={(v) => { setEditingVoce(v); setVoceDialogOpen(true); }}
                  onDeleteVoce={(v) => setDeletingVoce(v)}
                  onApplVoce={(v) => setApplVoce(v)}
                  onEditSotto={() => { setEditingSotto(s); setSottoDialogOpen(true); }}
                  onDeleteSotto={() => setDeletingSotto(s)}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Dialog sottocategoria */}
      <AdminCrudDialog
        open={sottoDialogOpen}
        onOpenChange={(open) => { setSottoDialogOpen(open); if (!open) { saveSotto.reset(); setEditingSotto(null); } }}
        entityLabel="sottocategoria"
        title={editingSotto ? "Modifica sottocategoria" : "Aggiungi sottocategoria"}
        onSubmit={() => { if (sottoForm.nome.trim()) saveSotto.mutate(); }}
        isSaving={saveSotto.isPending}
        errorMessage={saveSotto.isError ? "Non siamo riusciti a salvare. Riprova." : null}
      >
        <div className="flex flex-col gap-2">
          <Label htmlFor="sotto-cat">Categoria</Label>
          <Select value={sottoForm.categoria_code} onValueChange={(v) => setSottoForm((f) => ({ ...f, categoria_code: v }))}>
            <SelectTrigger id="sotto-cat" className="w-full"><SelectValue /></SelectTrigger>
            <SelectContent>
              {CATEGORIE.map((c) => (
                <SelectItem key={c.code} value={c.code}>{c.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="sotto-codice">Codice (opzionale)</Label>
          <Input id="sotto-codice" placeholder="Es. A.1" value={sottoForm.codice} onChange={(e) => setSottoForm((f) => ({ ...f, codice: e.target.value }))} />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="sotto-nome">Nome</Label>
          <Input id="sotto-nome" value={sottoForm.nome} onChange={(e) => setSottoForm((f) => ({ ...f, nome: e.target.value }))} />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="sotto-fam">Famiglia</Label>
          <Select value={sottoForm.famiglia} onValueChange={(v) => setSottoForm((f) => ({ ...f, famiglia: v as Famiglia }))}>
            <SelectTrigger id="sotto-fam" className="w-full"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="gerarchica">Gerarchica (a codici A.n)</SelectItem>
              <SelectItem value="catalogo">Catalogo (elenco piatto)</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="sotto-ordine">Ordine</Label>
          <Input id="sotto-ordine" type="number" min={0} value={sottoForm.ordine} onChange={(e) => setSottoForm((f) => ({ ...f, ordine: e.target.value }))} />
        </div>
      </AdminCrudDialog>

      <AdminDeleteConfirm
        open={deletingSotto !== null}
        onOpenChange={(open) => !open && setDeletingSotto(null)}
        entityLabel="sottocategoria"
        description={`Eliminare "${deletingSotto?.nome ?? ""}"? Possibile solo se non ha voci.`}
        onConfirm={() => deletingSotto && deleteSotto.mutate(deletingSotto.id)}
        isDeleting={deleteSotto.isPending}
      />

      {/* Dialog voce */}
      <AdminCrudDialog
        open={voceDialogOpen}
        onOpenChange={(open) => { setVoceDialogOpen(open); if (!open) { saveVoce.reset(); setEditingVoce(null); } }}
        entityLabel="voce"
        title={editingVoce ? "Modifica voce" : "Aggiungi voce"}
        onSubmit={() => { if (voceForm.descrizione.trim() && voceForm.um.trim() && Number(voceForm.prezzo) > 0) saveVoce.mutate(); }}
        isSaving={saveVoce.isPending}
        errorMessage={saveVoce.isError ? "Non siamo riusciti a salvare. Riprova." : null}
      >
        <div className="flex flex-col gap-2">
          <Label htmlFor="voce-codice">Codice (opzionale)</Label>
          <Input id="voce-codice" value={voceForm.codice} onChange={(e) => setVoceForm((f) => ({ ...f, codice: e.target.value }))} />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="voce-desc">Descrizione</Label>
          <Input id="voce-desc" value={voceForm.descrizione} onChange={(e) => setVoceForm((f) => ({ ...f, descrizione: e.target.value }))} />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="voce-um">Unità di misura</Label>
          <Input id="voce-um" placeholder="Es. m2, cad, ml" value={voceForm.um} onChange={(e) => setVoceForm((f) => ({ ...f, um: e.target.value }))} />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="voce-prezzo">Prezzo unitario cliente (€)</Label>
          <Input id="voce-prezzo" type="number" min={0} step="0.01" value={voceForm.prezzo} onChange={(e) => setVoceForm((f) => ({ ...f, prezzo: e.target.value }))} />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="voce-ordine">Ordine</Label>
          <Input id="voce-ordine" type="number" min={0} value={voceForm.ordine} onChange={(e) => setVoceForm((f) => ({ ...f, ordine: e.target.value }))} />
        </div>
      </AdminCrudDialog>

      <AdminDeleteConfirm
        open={deletingVoce !== null}
        onOpenChange={(open) => !open && setDeletingVoce(null)}
        entityLabel="voce"
        description={`Eliminare "${deletingVoce?.descrizione ?? ""}"?`}
        onConfirm={() => deletingVoce && deleteVoceMut.mutate(deletingVoce)}
        isDeleting={deleteVoceMut.isPending}
      />

      <VoceApplicazioneDialog voce={applVoce} onClose={() => setApplVoce(null)} />
    </div>
  );
}

interface SottoCollapsibleProps {
  sotto: SottocategoriaOut;
  isOpen: boolean;
  onToggle: () => void;
  onAddVoce: () => void;
  onEditVoce: (v: VoceOut) => void;
  onDeleteVoce: (v: VoceOut) => void;
  onApplVoce: (v: VoceOut) => void;
  onEditSotto: () => void;
  onDeleteSotto: () => void;
}

/**
 * Riga-sottocategoria collassabile in FLUSSO normale (niente altezza animata
 * di Radix, che tagliava il contenuto caricato in async): aprendo, le righe
 * sotto scendono davvero. L'elenco voci ha uno scroll interno (max-height)
 * così una sottocategoria molto lunga non allontana troppo le altre.
 */
function SottoCollapsible({
  sotto,
  isOpen,
  onToggle,
  onAddVoce,
  onEditVoce,
  onDeleteVoce,
  onApplVoce,
  onEditSotto,
  onDeleteSotto,
}: SottoCollapsibleProps) {
  const vociQuery = useQuery<VoceOut[]>({
    queryKey: ["admin-pro-voci", sotto.id],
    queryFn: () => listVoci(sotto.id),
    enabled: isOpen,
  });

  return (
    <div className="border-b border-border last:border-b-0">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={isOpen}
        className="flex w-full items-center gap-2 px-4 py-3 text-left hover:bg-muted/50"
      >
        <ChevronRight className={cn("size-4 shrink-0 text-muted-foreground transition-transform", isOpen && "rotate-90")} />
        <span className="text-sm font-medium text-foreground">{sottoLabel(sotto)}</span>
        <span className="ml-1 text-xs font-normal text-muted-foreground">{sotto.categoria_code}</span>
      </button>

      {isOpen && (
        <div className="px-4 pb-4">
          <div className="flex flex-wrap items-center gap-2 pb-3">
            <Button type="button" size="sm" onClick={onAddVoce}>
              <Plus className="mr-1 size-4" /> Aggiungi voce
            </Button>
            <Button type="button" size="sm" variant="outline" onClick={onEditSotto}>
              Modifica sottocategoria
            </Button>
            <Button type="button" size="sm" variant="ghost" onClick={onDeleteSotto}>
              Elimina
            </Button>
          </div>

          {vociQuery.isLoading && <p className="py-2 text-sm text-muted-foreground">Caricamento voci…</p>}
          {vociQuery.isSuccess && (vociQuery.data?.length ?? 0) === 0 && (
            <p className="py-2 text-sm text-muted-foreground">
              Nessuna voce. Aggiungi la prima con il pulsante qui sopra.
            </p>
          )}

          {(vociQuery.data?.length ?? 0) > 0 && (
            <div className="flex max-h-[26rem] flex-col overflow-y-auto rounded-md border border-border">
              {(vociQuery.data ?? []).map((v) => (
                <div key={v.id} className="flex items-start justify-between gap-3 border-b border-border px-3 py-2 last:border-b-0">
                  <div className="min-w-0 flex-1">
                    <p className="whitespace-normal break-words text-sm font-medium text-foreground">
                      {v.codice ? `${v.codice} · ` : ""}
                      {v.descrizione}
                    </p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {v.um} · {v.prezzo_unitario_cliente} € al cliente
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-1">
                    <Button type="button" variant="ghost" size="icon-sm" aria-label="Applicazione per tipo" title="Dove va applicata" onClick={() => onApplVoce(v)}>
                      <SlidersHorizontal className="size-4" />
                    </Button>
                    <Button type="button" variant="ghost" size="icon-sm" aria-label="Modifica" onClick={() => onEditVoce(v)}>
                      <Pencil className="size-4" />
                    </Button>
                    <Button type="button" variant="ghost" size="icon-sm" aria-label="Elimina" onClick={() => onDeleteVoce(v)}>
                      <Trash2 className="size-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

interface TipoAppState {
  incluso: boolean;
  modalita: "mq" | "conteggio";
  valore: string;
}

/**
 * Dialog "Applicazione per tipo" di una voce: per ciascun tipo
 * (leggera/moderata/totale) decide SE la voce è inclusa e con quale quantità
 * — proporzionale ai mq (`coefficiente_qta_per_mq`) o fissa (`default_conteggio`).
 * La quantità × prezzo cliente della voce determina il contributo al dettaglio Pro.
 */
function VoceApplicazioneDialog({ voce, onClose }: { voce: VoceOut | null; onClose: () => void }) {
  const queryClient = useQueryClient();
  const open = voce !== null;

  const coeffQuery = useQuery({
    queryKey: ["admin-pro-coeff", voce?.id],
    queryFn: () => listCoeffVoce(voce!.id),
    enabled: open,
  });

  const [state, setState] = useState<Record<string, TipoAppState>>({});

  useEffect(() => {
    if (open && coeffQuery.data) {
      const next: Record<string, TipoAppState> = {};
      for (const t of TIPI) {
        const row = coeffQuery.data.find((r) => r.tipo_code === t.code);
        if (row && row.coefficiente_qta_per_mq != null) {
          next[t.code] = { incluso: true, modalita: "mq", valore: String(row.coefficiente_qta_per_mq) };
        } else if (row) {
          next[t.code] = { incluso: true, modalita: "conteggio", valore: String(row.default_conteggio ?? 0) };
        } else {
          next[t.code] = { incluso: false, modalita: "mq", valore: "" };
        }
      }
      setState(next);
    }
  }, [open, coeffQuery.data]);

  const save = useMutation({
    mutationFn: async () => {
      const existing = coeffQuery.data ?? [];
      for (const t of TIPI) {
        const s = state[t.code];
        const existed = existing.some((r) => r.tipo_code === t.code);
        if (s?.incluso) {
          const payload =
            s.modalita === "mq"
              ? { coefficiente_qta_per_mq: Number(s.valore) || 0, default_conteggio: null }
              : { coefficiente_qta_per_mq: null, default_conteggio: Math.round(Number(s.valore) || 0) };
          await upsertCoeffVoce(voce!.id, t.code, payload);
        } else if (existed) {
          await deleteCoeffVoce(voce!.id, t.code);
        }
      }
    },
    onSuccess: () => {
      toast.success("Applicazione aggiornata");
      void queryClient.invalidateQueries({ queryKey: ["admin-pro-coeff", voce?.id] });
      onClose();
    },
    onError: () => toast.error("Non siamo riusciti a salvare. Riprova."),
  });

  return (
    <AdminCrudDialog
      open={open}
      onOpenChange={(o) => { if (!o) { save.reset(); onClose(); } }}
      entityLabel="applicazione"
      title={`Applicazione per tipo${voce ? ` — ${voce.descrizione}` : ""}`}
      onSubmit={() => save.mutate()}
      isSaving={save.isPending}
      errorMessage={save.isError ? "Non siamo riusciti a salvare. Riprova." : null}
    >
      <p className="text-sm text-muted-foreground">
        Attiva la voce nei tipi in cui deve entrare e imposta la quantità: per m² (proporzionale alla
        superficie) o fissa (numero di pezzi). La quantità × prezzo cliente forma il contributo al totale.
      </p>
      {TIPI.map((t) => {
        const s = state[t.code] ?? { incluso: false, modalita: "mq" as const, valore: "" };
        return (
          <div key={t.code} className="flex flex-col gap-2 rounded-md border border-border p-3">
            <div className="flex items-center justify-between">
              <Label className="font-medium">{t.label}</Label>
              <Switch
                checked={s.incluso}
                onCheckedChange={(checked) =>
                  setState((prev) => ({ ...prev, [t.code]: { ...s, incluso: checked } }))
                }
                aria-label={`Includi in ${t.label}`}
              />
            </div>
            {s.incluso && (
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
                <div className="flex flex-1 flex-col gap-1">
                  <Label className="text-xs text-muted-foreground">Modalità quantità</Label>
                  <Select
                    value={s.modalita}
                    onValueChange={(v) =>
                      setState((prev) => ({ ...prev, [t.code]: { ...s, modalita: v as "mq" | "conteggio" } }))
                    }
                  >
                    <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="mq">Per m² (× superficie)</SelectItem>
                      <SelectItem value="conteggio">Quantità fissa (pezzi)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex flex-1 flex-col gap-1">
                  <Label className="text-xs text-muted-foreground">
                    {s.modalita === "mq" ? "Quantità per m²" : "Quantità fissa"}
                  </Label>
                  <Input
                    type="number"
                    min={0}
                    step={s.modalita === "mq" ? "0.0001" : "1"}
                    value={s.valore}
                    onChange={(e) =>
                      setState((prev) => ({ ...prev, [t.code]: { ...s, valore: e.target.value } }))
                    }
                  />
                </div>
              </div>
            )}
          </div>
        );
      })}
    </AdminCrudDialog>
  );
}

export function DettaglioProAdminPage() {
  return (
    <AdminLayout>
      <DettaglioProContent />
    </AdminLayout>
  );
}
