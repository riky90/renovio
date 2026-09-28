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
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  getBonus,
  createBonus,
  updateBonus,
  deleteBonus,
  getAliquote,
  createAliquota,
  updateAliquota,
  deleteAliquota,
  getBonusCategorie,
  createBonusCategoria,
  updateBonusCategoria,
  deleteBonusCategoria,
  getBonusExtra,
  createBonusExtra,
  updateBonusExtra,
  deleteBonusExtra,
  type AliquotaOut,
  type BonusCategoriaOut,
  type BonusExtraOut,
  type BonusOut,
  type Destinazione,
} from "@/api/admin/bonus";
import { getIva, listExtra } from "@/api/admin/coefficienti";
import { ApiError } from "@/api/client";

const SAVE_TOAST = "Modifica salvata";
const SAVE_ERROR = "Non siamo riusciti a salvare la modifica. Riprova.";

/**
 * Il 409 di questa sezione non è rumore: è l'unico avviso che una curatela sta
 * per far detrarre due volte la stessa spesa. `ApiError` non porta il `detail`
 * del server, quindi il messaggio si ricostruisce dallo status — meglio una
 * frase giusta e generica del "Riprova" di default, che qui manderebbe l'admin
 * a ripetere lo stesso errore.
 */
function extractErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 409) {
      return "Le quote sui bonus attivi supererebbero il 100% per una categoria o un extra: la stessa spesa verrebbe detratta due volte. Riduci la quota, oppure disattiva l'altro bonus.";
    }
    if (error.status === 404) return "Il bonus, la categoria o l'extra indicato non esiste.";
  }
  return SAVE_ERROR;
}

const DESTINAZIONE_LABELS: Record<Destinazione, string> = {
  prima_casa: "Abitazione principale",
  altro: "Altro immobile",
};

/** 0.5 <-> "50": in tabella si ragiona in percentuale, sul filo in frazione. */
function pctToInput(frazione: number): string {
  return String(Math.round(frazione * 10000) / 100);
}

function inputToPct(percentuale: string): number {
  return Number(percentuale) / 100;
}

function formatPct(frazione: number): string {
  return `${Math.round(frazione * 10000) / 100}%`;
}

function formatTetto(value: number | null): string {
  return value === null ? "nessun tetto" : `${value.toLocaleString("it-IT")} €`;
}

function actionButtons(onEdit: () => void, onDelete: () => void) {
  return (
    <div key="actions" className="flex justify-end gap-2">
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="size-8"
        title="Modifica"
        aria-label="Modifica"
        onClick={onEdit}
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
        onClick={onDelete}
      >
        <Trash2 className="size-4" />
      </Button>
    </div>
  );
}

/**
 * Bonus fiscali: bonus, aliquote per periodo, e i due mapping che dicono quale
 * spesa alimenta quale bonus — categorie ed extra.
 *
 * È il pannello che rende vera la promessa del modello dati: quando l'aliquota
 * cambia per legge non serve un deploy, si aggiunge una riga con la nuova
 * finestra di validità. Nessun edit fatto qui tocca le stime già salvate: il
 * bonus è congelato dentro il loro snapshot.
 */
export function BonusPage() {
  return (
    <AdminLayout>
      <div className="flex flex-col gap-10">
        <h1 className="text-lg font-semibold text-foreground">Bonus fiscali</h1>
        <BonusSection />
        <AliquoteSection />
        <MappingCategorieSection />
        <MappingExtraSection />
      </div>
    </AdminLayout>
  );
}

/* ------------------------------------------------------------------ */
/* Sezione 1 — Bonus                                                   */
/* ------------------------------------------------------------------ */

interface BonusFormState {
  code: string;
  nome: string;
  descrizione: string;
  ordine: string;
  attivo: boolean;
}

const EMPTY_BONUS_FORM: BonusFormState = {
  code: "",
  nome: "",
  descrizione: "",
  ordine: "0",
  attivo: true,
};

function BonusSection() {
  const queryClient = useQueryClient();
  const bonusQuery = useQuery<BonusOut[]>({ queryKey: ["admin-bonus"], queryFn: getBonus });

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<BonusOut | null>(null);
  const [form, setForm] = useState<BonusFormState>(EMPTY_BONUS_FORM);
  const [deleteTarget, setDeleteTarget] = useState<BonusOut | null>(null);

  function invalidate() {
    // Riaccendere un bonus cambia le quote che vedono le altre sezioni.
    queryClient.invalidateQueries({ queryKey: ["admin-bonus"] });
    queryClient.invalidateQueries({ queryKey: ["admin-bonus-aliquote"] });
  }

  const saveMutation = useMutation({
    mutationFn: async () => {
      const body = {
        nome: form.nome.trim(),
        descrizione: form.descrizione.trim() ? form.descrizione.trim() : null,
        ordine: Number(form.ordine) || 0,
        attivo: form.attivo,
      };
      return editing
        ? updateBonus(editing.code, body)
        : createBonus({ code: form.code.trim(), ...body });
    },
    onSuccess: () => {
      toast.success(SAVE_TOAST);
      setDialogOpen(false);
      invalidate();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (code: string) => deleteBonus(code),
    onSuccess: () => {
      toast.success(SAVE_TOAST);
      setDeleteTarget(null);
      invalidate();
    },
    onError: (error) => toast.error(extractErrorMessage(error)),
  });

  function openCreate() {
    setEditing(null);
    setForm(EMPTY_BONUS_FORM);
    setDialogOpen(true);
  }

  function openEdit(row: BonusOut) {
    setEditing(row);
    setForm({
      code: row.code,
      nome: row.nome,
      descrizione: row.descrizione ?? "",
      ordine: String(row.ordine),
      attivo: row.attivo,
    });
    setDialogOpen(true);
  }

  const rows = (bonusQuery.data ?? []).map((row) => [
    row.code,
    row.nome,
    row.attivo ? "Attivo" : "Spento",
    row.ordine,
    actionButtons(
      () => openEdit(row),
      () => setDeleteTarget(row)
    ),
  ]);

  return (
    <section className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-foreground">Bonus</h2>
        <Button
          type="button"
          onClick={openCreate}
          className="bg-primary text-primary-foreground hover:bg-primary/90"
        >
          <Plus className="mr-1 size-4" aria-hidden />
          Aggiungi bonus
        </Button>
      </div>

      <p className="text-sm text-muted-foreground">
        Un bonus spento resta in tabella ma sparisce dalle stime: è così che si tiene pronto un
        bonus che richiede un dato che il form non raccoglie ancora.
      </p>

      <AdminTable
        columns={["Codice", "Nome", "Stato", "Ordine", ""]}
        isLoading={bonusQuery.isLoading}
        rows={rows}
        isEmpty={(bonusQuery.data ?? []).length === 0}
        emptyHeading="Nessun bonus presente"
        emptyBody="Aggiungi il primo bonus con il pulsante qui sopra."
      />

      <AdminCrudDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        entityLabel="bonus"
        title={editing ? "Modifica bonus" : "Aggiungi bonus"}
        onSubmit={() => saveMutation.mutate()}
        isSaving={saveMutation.isPending}
        errorMessage={saveMutation.isError ? extractErrorMessage(saveMutation.error) : null}
      >
        <div className="flex flex-col gap-2">
          <Label htmlFor="bonus-code">Codice</Label>
          <Input
            id="bonus-code"
            value={form.code}
            placeholder="Es. RISTRUTTURAZIONE"
            disabled={!!editing}
            onChange={(e) => setForm((f) => ({ ...f, code: e.target.value }))}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="bonus-nome">Nome</Label>
          <Input
            id="bonus-nome"
            value={form.nome}
            onChange={(e) => setForm((f) => ({ ...f, nome: e.target.value }))}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="bonus-descrizione">Descrizione</Label>
          <Textarea
            id="bonus-descrizione"
            value={form.descrizione}
            onChange={(e) => setForm((f) => ({ ...f, descrizione: e.target.value }))}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="bonus-ordine">Ordine</Label>
          <Input
            id="bonus-ordine"
            inputMode="numeric"
            value={form.ordine}
            onChange={(e) => setForm((f) => ({ ...f, ordine: e.target.value }))}
          />
        </div>
        <div className="flex items-center justify-between gap-3">
          <Label htmlFor="bonus-attivo">Attivo</Label>
          <Switch
            id="bonus-attivo"
            checked={form.attivo}
            onCheckedChange={(attivo) => setForm((f) => ({ ...f, attivo }))}
          />
        </div>
      </AdminCrudDialog>

      <AdminDeleteConfirm
        open={deleteTarget !== null}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        entityLabel="bonus"
        description={`Eliminare ${deleteTarget?.nome ?? ""}? Vanno prima eliminate le aliquote e i mapping collegati. Le stime già salvate non saranno modificate.`}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.code)}
        isDeleting={deleteMutation.isPending}
      />
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* Sezione 2 — Aliquote per periodo                                    */
/* ------------------------------------------------------------------ */

interface AliquotaFormState {
  bonus_code: string;
  destinazione: Destinazione;
  aliquota_pct: string;
  tetto_spesa_eur: string;
  tetto_modalita: string;
  rate_annuali: string;
  valido_dal: string;
  valido_al: string;
  note: string;
}

const EMPTY_ALIQUOTA_FORM: AliquotaFormState = {
  bonus_code: "",
  destinazione: "prima_casa",
  aliquota_pct: "50",
  tetto_spesa_eur: "",
  tetto_modalita: "",
  rate_annuali: "10",
  valido_dal: "",
  valido_al: "",
  note: "",
};

function AliquoteSection() {
  const queryClient = useQueryClient();
  const aliquoteQuery = useQuery<AliquotaOut[]>({
    queryKey: ["admin-bonus-aliquote"],
    queryFn: () => getAliquote(),
  });
  const bonusQuery = useQuery<BonusOut[]>({ queryKey: ["admin-bonus"], queryFn: getBonus });

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<AliquotaOut | null>(null);
  const [form, setForm] = useState<AliquotaFormState>(EMPTY_ALIQUOTA_FORM);
  const [deleteTarget, setDeleteTarget] = useState<AliquotaOut | null>(null);

  const saveMutation = useMutation({
    mutationFn: async () => {
      const comune = {
        aliquota_pct: inputToPct(form.aliquota_pct),
        tetto_spesa_eur: form.tetto_spesa_eur.trim() ? Number(form.tetto_spesa_eur) : null,
        tetto_modalita: form.tetto_modalita.trim() ? form.tetto_modalita.trim() : null,
        rate_annuali: Number(form.rate_annuali) || 10,
        valido_dal: form.valido_dal,
        valido_al: form.valido_al.trim() ? form.valido_al : null,
        note: form.note.trim() ? form.note.trim() : null,
      };
      return editing
        ? updateAliquota(editing.id, comune)
        : createAliquota({
            bonus_code: form.bonus_code,
            destinazione: form.destinazione,
            ...comune,
          });
    },
    onSuccess: () => {
      toast.success(SAVE_TOAST);
      setDialogOpen(false);
      queryClient.invalidateQueries({ queryKey: ["admin-bonus-aliquote"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteAliquota(id),
    onSuccess: () => {
      toast.success(SAVE_TOAST);
      setDeleteTarget(null);
      queryClient.invalidateQueries({ queryKey: ["admin-bonus-aliquote"] });
    },
  });

  function openCreate() {
    setEditing(null);
    setForm({ ...EMPTY_ALIQUOTA_FORM, bonus_code: bonusQuery.data?.[0]?.code ?? "" });
    setDialogOpen(true);
  }

  function openEdit(row: AliquotaOut) {
    setEditing(row);
    setForm({
      bonus_code: row.bonus_code,
      destinazione: row.destinazione,
      aliquota_pct: pctToInput(row.aliquota_pct),
      tetto_spesa_eur: row.tetto_spesa_eur === null ? "" : String(row.tetto_spesa_eur),
      tetto_modalita: row.tetto_modalita ?? "",
      rate_annuali: String(row.rate_annuali),
      valido_dal: row.valido_dal,
      valido_al: row.valido_al ?? "",
      note: row.note ?? "",
    });
    setDialogOpen(true);
  }

  const rows = (aliquoteQuery.data ?? []).map((row) => [
    row.bonus_code,
    DESTINAZIONE_LABELS[row.destinazione] ?? row.destinazione,
    formatPct(row.aliquota_pct),
    formatTetto(row.tetto_spesa_eur),
    `${row.valido_dal} → ${row.valido_al ?? "aperta"}`,
    row.rate_annuali,
    actionButtons(
      () => openEdit(row),
      () => setDeleteTarget(row)
    ),
  ]);

  return (
    <section className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-foreground">Aliquote per periodo</h2>
        <Button
          type="button"
          onClick={openCreate}
          className="bg-primary text-primary-foreground hover:bg-primary/90"
        >
          <Plus className="mr-1 size-4" aria-hidden />
          Aggiungi aliquota
        </Button>
      </div>

      <p className="text-sm text-muted-foreground">
        Quando un'aliquota cambia per legge non si modifica la riga esistente: si chiude la sua
        finestra e se ne aggiunge una nuova con la data di decorrenza. Il calcolo sceglie da sé la
        riga valida alla data della stima.
      </p>

      <AdminTable
        columns={["Bonus", "Destinazione", "Aliquota", "Tetto di spesa", "Validità", "Rate", ""]}
        isLoading={aliquoteQuery.isLoading}
        rows={rows}
        isEmpty={(aliquoteQuery.data ?? []).length === 0}
        emptyHeading="Nessuna aliquota presente"
        emptyBody="Senza aliquota valida il bonus viene escluso dalle stime, non calcolato a zero."
      />

      <AdminCrudDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        entityLabel="aliquota"
        title={editing ? "Modifica aliquota" : "Aggiungi aliquota"}
        onSubmit={() => saveMutation.mutate()}
        isSaving={saveMutation.isPending}
        errorMessage={saveMutation.isError ? extractErrorMessage(saveMutation.error) : null}
      >
        {editing ? (
          <>
            <div className="flex flex-col gap-2">
              <Label>Bonus</Label>
              <p className="rounded-md bg-muted px-3 py-2 text-sm text-foreground">
                {bonusQuery.data?.find((b) => b.code === editing.bonus_code)?.nome ?? editing.bonus_code}
              </p>
            </div>
            <div className="flex flex-col gap-2">
              <Label>Destinazione</Label>
              <p className="rounded-md bg-muted px-3 py-2 text-sm text-foreground">
                {DESTINAZIONE_LABELS[editing.destinazione]}
              </p>
              <p className="text-xs text-muted-foreground">
                Per un altro bonus o destinazione crea una nuova aliquota.
              </p>
            </div>
          </>
        ) : (
          <>
            <div className="flex flex-col gap-2">
              <Label htmlFor="aliquota-bonus">Bonus</Label>
              <Select
                value={form.bonus_code}
                onValueChange={(bonus_code) => setForm((f) => ({ ...f, bonus_code }))}
              >
                <SelectTrigger id="aliquota-bonus">
                  <SelectValue placeholder="Seleziona un bonus" />
                </SelectTrigger>
                <SelectContent>
                  {(bonusQuery.data ?? []).map((b) => (
                    <SelectItem key={b.code} value={b.code}>
                      {b.nome}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="aliquota-destinazione">Destinazione</Label>
              <Select
                value={form.destinazione}
                onValueChange={(destinazione) =>
                  setForm((f) => ({ ...f, destinazione: destinazione as Destinazione }))
                }
              >
                <SelectTrigger id="aliquota-destinazione">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="prima_casa">{DESTINAZIONE_LABELS.prima_casa}</SelectItem>
                  <SelectItem value="altro">{DESTINAZIONE_LABELS.altro}</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </>
        )}
        <div className="flex flex-col gap-2">
          <Label htmlFor="aliquota-pct">Aliquota (%)</Label>
          <Input
            id="aliquota-pct"
            inputMode="decimal"
            value={form.aliquota_pct}
            onChange={(e) => setForm((f) => ({ ...f, aliquota_pct: e.target.value }))}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="aliquota-tetto">Tetto di spesa (€)</Label>
          <Input
            id="aliquota-tetto"
            inputMode="numeric"
            placeholder="Vuoto = nessun tetto"
            value={form.tetto_spesa_eur}
            onChange={(e) => setForm((f) => ({ ...f, tetto_spesa_eur: e.target.value }))}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="aliquota-tetto-modalita">Modalità del tetto</Label>
          <Input
            id="aliquota-tetto-modalita"
            placeholder="Es. per_unita_immobiliare"
            value={form.tetto_modalita}
            onChange={(e) => setForm((f) => ({ ...f, tetto_modalita: e.target.value }))}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="aliquota-rate">Rate annuali</Label>
          <Input
            id="aliquota-rate"
            inputMode="numeric"
            value={form.rate_annuali}
            onChange={(e) => setForm((f) => ({ ...f, rate_annuali: e.target.value }))}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="aliquota-dal">Valida dal</Label>
          <Input
            id="aliquota-dal"
            type="date"
            value={form.valido_dal}
            onChange={(e) => setForm((f) => ({ ...f, valido_dal: e.target.value }))}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="aliquota-al">Valida fino al</Label>
          <Input
            id="aliquota-al"
            type="date"
            value={form.valido_al}
            onChange={(e) => setForm((f) => ({ ...f, valido_al: e.target.value }))}
          />
          <p className="text-sm text-muted-foreground">Vuoto = finestra ancora aperta.</p>
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="aliquota-note">Note</Label>
          <Textarea
            id="aliquota-note"
            value={form.note}
            onChange={(e) => setForm((f) => ({ ...f, note: e.target.value }))}
          />
        </div>
      </AdminCrudDialog>

      <AdminDeleteConfirm
        open={deleteTarget !== null}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        entityLabel="aliquota"
        description="Eliminare questa aliquota? Le stime già salvate non saranno modificate."
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
        isDeleting={deleteMutation.isPending}
      />
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* Sezione 3 — Quale categoria alimenta quale bonus                    */
/* ------------------------------------------------------------------ */

function MappingCategorieSection() {
  const queryClient = useQueryClient();
  const mappingQuery = useQuery<BonusCategoriaOut[]>({
    queryKey: ["admin-bonus-categorie"],
    queryFn: getBonusCategorie,
  });
  const bonusQuery = useQuery<BonusOut[]>({ queryKey: ["admin-bonus"], queryFn: getBonus });
  const categorieQuery = useQuery({ queryKey: ["admin-iva"], queryFn: getIva });

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<BonusCategoriaOut | null>(null);
  const [bonusCode, setBonusCode] = useState("");
  const [categoriaCode, setCategoriaCode] = useState("");
  const [quota, setQuota] = useState("100");
  const [deleteTarget, setDeleteTarget] = useState<BonusCategoriaOut | null>(null);

  const saveMutation = useMutation({
    mutationFn: async () =>
      editing
        ? updateBonusCategoria(editing.id, inputToPct(quota))
        : createBonusCategoria({
            bonus_code: bonusCode,
            categoria_code: categoriaCode,
            quota_ammissibile_pct: inputToPct(quota),
          }),
    onSuccess: () => {
      toast.success(SAVE_TOAST);
      setDialogOpen(false);
      queryClient.invalidateQueries({ queryKey: ["admin-bonus-categorie"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteBonusCategoria(id),
    onSuccess: () => {
      toast.success(SAVE_TOAST);
      setDeleteTarget(null);
      queryClient.invalidateQueries({ queryKey: ["admin-bonus-categorie"] });
    },
  });

  function openCreate() {
    setEditing(null);
    setBonusCode(bonusQuery.data?.[0]?.code ?? "");
    setCategoriaCode(categorieQuery.data?.[0]?.code ?? "");
    setQuota("100");
    setDialogOpen(true);
  }

  function openEdit(row: BonusCategoriaOut) {
    setEditing(row);
    setBonusCode(row.bonus_code);
    setCategoriaCode(row.categoria_code);
    setQuota(pctToInput(row.quota_ammissibile_pct));
    setDialogOpen(true);
  }

  const nomiCategoria = new Map((categorieQuery.data ?? []).map((c) => [c.code, c.nome]));

  const rows = (mappingQuery.data ?? []).map((row) => [
    row.bonus_code,
    nomiCategoria.get(row.categoria_code) ?? row.categoria_code,
    formatPct(row.quota_ammissibile_pct),
    actionButtons(
      () => openEdit(row),
      () => setDeleteTarget(row)
    ),
  ]);

  return (
    <section className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-foreground">Categorie detraibili</h2>
        <Button
          type="button"
          onClick={openCreate}
          className="bg-primary text-primary-foreground hover:bg-primary/90"
        >
          <Plus className="mr-1 size-4" aria-hidden />
          Aggiungi categoria
        </Button>
      </div>

      <p className="text-sm text-muted-foreground">
        Per ogni categoria la somma delle quote sui bonus attivi non può superare il 100%: oltre
        quella soglia la stessa spesa verrebbe detratta due volte.
      </p>

      <AdminTable
        columns={["Bonus", "Categoria", "Quota detraibile", ""]}
        isLoading={mappingQuery.isLoading}
        rows={rows}
        isEmpty={(mappingQuery.data ?? []).length === 0}
        emptyHeading="Nessuna categoria mappata"
        emptyBody="Senza mappature nessuna spesa alimenta i bonus e la sezione detrazioni sparisce dalle stime."
      />

      <AdminCrudDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        entityLabel="categoria"
        title={editing ? "Modifica quota" : "Aggiungi categoria detraibile"}
        onSubmit={() => saveMutation.mutate()}
        isSaving={saveMutation.isPending}
        errorMessage={saveMutation.isError ? extractErrorMessage(saveMutation.error) : null}
      >
        {editing ? (
          <>
            <div className="flex flex-col gap-2">
              <Label>Bonus</Label>
              <p className="rounded-md bg-muted px-3 py-2 text-sm text-foreground">
                {bonusQuery.data?.find((b) => b.code === bonusCode)?.nome ?? bonusCode}
              </p>
            </div>
            <div className="flex flex-col gap-2">
              <Label>Categoria</Label>
              <p className="rounded-md bg-muted px-3 py-2 text-sm text-foreground">
                {nomiCategoria.get(categoriaCode) ?? categoriaCode}
              </p>
              <p className="text-xs text-muted-foreground">
                Per un altro bonus o categoria crea una nuova mappatura.
              </p>
            </div>
          </>
        ) : (
          <>
            <div className="flex flex-col gap-2">
              <Label htmlFor="mapcat-bonus">Bonus</Label>
              <Select value={bonusCode} onValueChange={setBonusCode}>
                <SelectTrigger id="mapcat-bonus">
                  <SelectValue placeholder="Seleziona un bonus" />
                </SelectTrigger>
                <SelectContent>
                  {(bonusQuery.data ?? []).map((b) => (
                    <SelectItem key={b.code} value={b.code}>
                      {b.nome}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="mapcat-categoria">Categoria</Label>
              <Select value={categoriaCode} onValueChange={setCategoriaCode}>
                <SelectTrigger id="mapcat-categoria">
                  <SelectValue placeholder="Seleziona una categoria" />
                </SelectTrigger>
                <SelectContent>
                  {(categorieQuery.data ?? []).map((c) => (
                    <SelectItem key={c.code} value={c.code}>
                      {c.nome}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </>
        )}
        <div className="flex flex-col gap-2">
          <Label htmlFor="mapcat-quota">Quota detraibile (%)</Label>
          <Input
            id="mapcat-quota"
            inputMode="decimal"
            value={quota}
            onChange={(e) => setQuota(e.target.value)}
          />
        </div>
      </AdminCrudDialog>

      <AdminDeleteConfirm
        open={deleteTarget !== null}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        entityLabel="mappatura"
        description="Eliminare questa mappatura? La categoria smetterà di alimentare il bonus nelle nuove stime; quelle già salvate non cambiano."
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
        isDeleting={deleteMutation.isPending}
      />
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* Sezione 4 — Quale extra alimenta quale bonus                        */
/* ------------------------------------------------------------------ */

function MappingExtraSection() {
  const queryClient = useQueryClient();
  const mappingQuery = useQuery<BonusExtraOut[]>({
    queryKey: ["admin-bonus-extra"],
    queryFn: getBonusExtra,
  });
  const bonusQuery = useQuery<BonusOut[]>({ queryKey: ["admin-bonus"], queryFn: getBonus });
  const extraQuery = useQuery({ queryKey: ["admin-extra"], queryFn: listExtra });

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<BonusExtraOut | null>(null);
  const [bonusCode, setBonusCode] = useState("");
  const [extraCode, setExtraCode] = useState("");
  const [quota, setQuota] = useState("100");
  const [deleteTarget, setDeleteTarget] = useState<BonusExtraOut | null>(null);

  const saveMutation = useMutation({
    mutationFn: async () =>
      editing
        ? updateBonusExtra(editing.id, inputToPct(quota))
        : createBonusExtra({
            bonus_code: bonusCode,
            extra_code: extraCode,
            quota_ammissibile_pct: inputToPct(quota),
          }),
    onSuccess: () => {
      toast.success(SAVE_TOAST);
      setDialogOpen(false);
      queryClient.invalidateQueries({ queryKey: ["admin-bonus-extra"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteBonusExtra(id),
    onSuccess: () => {
      toast.success(SAVE_TOAST);
      setDeleteTarget(null);
      queryClient.invalidateQueries({ queryKey: ["admin-bonus-extra"] });
    },
  });

  function openCreate() {
    setEditing(null);
    setBonusCode(bonusQuery.data?.[0]?.code ?? "");
    setExtraCode(extraQuery.data?.[0]?.code ?? "");
    setQuota("100");
    setDialogOpen(true);
  }

  function openEdit(row: BonusExtraOut) {
    setEditing(row);
    setBonusCode(row.bonus_code);
    setExtraCode(row.extra_code);
    setQuota(pctToInput(row.quota_ammissibile_pct));
    setDialogOpen(true);
  }

  const nomiExtra = new Map((extraQuery.data ?? []).map((e) => [e.code, e.nome]));
  const mappati = new Set((mappingQuery.data ?? []).map((m) => m.extra_code));
  const nonMappati = (extraQuery.data ?? []).filter((e) => e.attivo && !mappati.has(e.code));

  const rows = (mappingQuery.data ?? []).map((row) => [
    row.bonus_code,
    nomiExtra.get(row.extra_code) ?? row.extra_code,
    formatPct(row.quota_ammissibile_pct),
    actionButtons(
      () => openEdit(row),
      () => setDeleteTarget(row)
    ),
  ]);

  return (
    <section className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-foreground">Extra detraibili</h2>
        <Button
          type="button"
          onClick={openCreate}
          className="bg-primary text-primary-foreground hover:bg-primary/90"
        >
          <Plus className="mr-1 size-4" aria-hidden />
          Aggiungi extra
        </Button>
      </div>

      <p className="text-sm text-muted-foreground">
        Sicurezza in cantiere e pratiche amministrative sono spesa detraibile come le categorie. Un
        extra che resta fuori da questa tabella non abbassa la stima: abbassa la detrazione, senza
        dirlo.
      </p>

      {nonMappati.length > 0 && (
        <p className="rounded-lg border border-gold bg-gold-soft px-4 py-3 text-sm text-gold-foreground">
          Non mappati su nessun bonus: {nonMappati.map((e) => e.nome).join(", ")}. Se sono spese
          detraibili, la detrazione mostrata è più bassa del vero.
        </p>
      )}

      <AdminTable
        columns={["Bonus", "Extra", "Quota detraibile", ""]}
        isLoading={mappingQuery.isLoading}
        rows={rows}
        isEmpty={(mappingQuery.data ?? []).length === 0}
        emptyHeading="Nessun extra mappato"
        emptyBody="Gli extra non alimentano nessun bonus: la detrazione stimata esce più bassa del vero."
      />

      <AdminCrudDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        entityLabel="extra"
        title={editing ? "Modifica quota" : "Aggiungi extra detraibile"}
        onSubmit={() => saveMutation.mutate()}
        isSaving={saveMutation.isPending}
        errorMessage={saveMutation.isError ? extractErrorMessage(saveMutation.error) : null}
      >
        {editing ? (
          <>
            <div className="flex flex-col gap-2">
              <Label>Bonus</Label>
              <p className="rounded-md bg-muted px-3 py-2 text-sm text-foreground">
                {bonusQuery.data?.find((b) => b.code === bonusCode)?.nome ?? bonusCode}
              </p>
            </div>
            <div className="flex flex-col gap-2">
              <Label>Extra</Label>
              <p className="rounded-md bg-muted px-3 py-2 text-sm text-foreground">
                {nomiExtra.get(extraCode) ?? extraCode}
              </p>
              <p className="text-xs text-muted-foreground">
                Per un altro bonus o extra crea una nuova mappatura.
              </p>
            </div>
          </>
        ) : (
          <>
            <div className="flex flex-col gap-2">
              <Label htmlFor="mapextra-bonus">Bonus</Label>
              <Select value={bonusCode} onValueChange={setBonusCode}>
                <SelectTrigger id="mapextra-bonus">
                  <SelectValue placeholder="Seleziona un bonus" />
                </SelectTrigger>
                <SelectContent>
                  {(bonusQuery.data ?? []).map((b) => (
                    <SelectItem key={b.code} value={b.code}>
                      {b.nome}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="mapextra-extra">Extra</Label>
              <Select value={extraCode} onValueChange={setExtraCode}>
                <SelectTrigger id="mapextra-extra">
                  <SelectValue placeholder="Seleziona un extra" />
                </SelectTrigger>
                <SelectContent>
                  {(extraQuery.data ?? []).map((e) => (
                    <SelectItem key={e.code} value={e.code}>
                      {e.nome}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </>
        )}
        <div className="flex flex-col gap-2">
          <Label htmlFor="mapextra-quota">Quota detraibile (%)</Label>
          <Input
            id="mapextra-quota"
            inputMode="decimal"
            value={quota}
            onChange={(e) => setQuota(e.target.value)}
          />
        </div>
      </AdminCrudDialog>

      <AdminDeleteConfirm
        open={deleteTarget !== null}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        entityLabel="mappatura"
        description="Eliminare questa mappatura? L'extra smetterà di alimentare il bonus nelle nuove stime; quelle già salvate non cambiano."
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
        isDeleting={deleteMutation.isPending}
      />
    </section>
  );
}
