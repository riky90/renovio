import { useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { UploadCloud } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { previewUpload, confirmUpload, type DiffPreview, type DiffRow, type UploadTarget } from "@/api/admin/uploadListino";
import type { ListinoOut } from "@/api/admin/listini";
import { DiffPreviewTable, type DiffPreviewRow } from "@/components/admin/DiffPreviewTable";

const MAX_SIZE_BYTES = 10 * 1024 * 1024;
const INVALID_FILE_MESSAGE = "Il file non è valido. Controlla che sia un .xlsx e non superi i 10 MB.";
const IMPORT_ERROR = "Import non riuscito. Riprova o contatta l'assistenza tecnica.";

interface ExcelUploadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  listini: ListinoOut[];
  defaultListinoId: number | null;
  /** Invocato dopo un import riuscito, con l'id del listino destinazione (nuovo o esistente). */
  onImported: (listinoId: number) => void;
}

const EURO = { style: "currency", currency: "EUR" } as const;

function toDiffPreviewRows(rows: DiffRow[]): DiffPreviewRow[] {
  return rows.map((row, i) => ({
    key: String(i),
    label: row.riga.descrizione,
    valorePrecedente:
      row.valore_precedente !== null ? row.valore_precedente.toLocaleString("it-IT", EURO) : "—",
    // `row.prezzoNuovo`, non `row.riga.prezzo_unitario_cliente`: quello e'
    // una stringa (pydantic serializza Decimal come stringa JSON) e
    // `String.prototype.toLocaleString` ignora gli argomenti, restituendo
    // `12.50` invece di `12,50 €`.
    valoreNuovo: row.prezzoNuovo !== null ? row.prezzoNuovo.toLocaleString("it-IT", EURO) : "—",
    staleAfterExport: row.riga_modificata_dopo_export,
  }));
}

function validateFile(file: File): string | null {
  const isXlsx = file.name.toLowerCase().endsWith(".xlsx");
  if (!isXlsx || file.size > MAX_SIZE_BYTES) {
    return INVALID_FILE_MESSAGE;
  }
  return null;
}

/**
 * Upload Excel a due passi (UI-SPEC §E, D-18/D-19/D-20): Step 0
 * destinazione (listino esistente OPPURE nuova città, D-13/Success
 * Criterion #3) → Step 1 dropzone con pre-check client → Step 2 anteprima
 * diff → Step 3 conferma. Il preview NON scrive nulla; il ramo nuova città
 * crea Listino+voci solo alla conferma.
 */
export function ExcelUploadDialog({
  open,
  onOpenChange,
  listini,
  defaultListinoId,
  onImported,
}: ExcelUploadDialogProps) {
  const [destKind, setDestKind] = useState<"esistente" | "nuova_citta">("esistente");
  const [destListinoId, setDestListinoId] = useState<number | null>(defaultListinoId);
  const [destCitta, setDestCitta] = useState("");
  const [destIsDefault, setDestIsDefault] = useState(false);
  const [destComuniExtra, setDestComuniExtra] = useState("");
  const [fileError, setFileError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [discardOpen, setDiscardOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const previewMutation = useMutation<DiffPreview, Error, File>({
    mutationFn: (file: File) => previewUpload(file, buildTarget()),
  });

  const confirmMutation = useMutation({
    mutationFn: () => {
      const preview = previewMutation.data!;
      const comuniExtra = destComuniExtra
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      return confirmUpload(
        buildTarget(),
        preview.nuove.map((r) => r.riga),
        preview.modificate.map((r) => r.riga),
        comuniExtra,
      );
    },
    onSuccess: (result) => {
      toast.success(`Import completato: ${result.righe_importate} righe importate`);
      onImported(result.listino_id);
      resetAndClose();
    },
  });

  function buildTarget(): UploadTarget {
    if (destKind === "esistente") {
      return { kind: "esistente", listino_id: destListinoId as number };
    }
    return { kind: "nuova_citta", citta: destCitta.trim(), is_default: destIsDefault };
  }

  function resetAndClose() {
    setDestKind("esistente");
    setDestListinoId(defaultListinoId);
    setDestCitta("");
    setDestIsDefault(false);
    setDestComuniExtra("");
    setFileError(null);
    setFileName(null);
    setDiscardOpen(false);
    previewMutation.reset();
    confirmMutation.reset();
    if (fileInputRef.current) fileInputRef.current.value = "";
    onOpenChange(false);
  }

  function handleFileSelected(file: File) {
    setFileName(file.name);
    const error = validateFile(file);
    if (error) {
      setFileError(error);
      return;
    }
    setFileError(null);
    previewMutation.mutate(file);
  }

  function handleDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    const file = event.dataTransfer.files?.[0];
    if (file) handleFileSelected(file);
  }

  const destinationValid = destKind === "esistente" ? destListinoId !== null : destCitta.trim().length > 0;

  const preview = previewMutation.data ?? null;
  const validRowCount = preview ? preview.nuove.length + preview.modificate.length : 0;

  return (
    <>
      <Dialog
        open={open}
        onOpenChange={(next) => {
          if (!next) resetAndClose();
          else onOpenChange(next);
        }}
      >
        <DialogContent className="sm:max-w-[720px]">
          <DialogHeader>
            <DialogTitle>Carica listino da Excel</DialogTitle>
            {!preview && (
              <DialogDescription>
                Trascina qui il file .xlsx oppure sfoglia i file. Solo file .xlsx, dimensione massima 10 MB.
              </DialogDescription>
            )}
            {preview && (
              <DialogDescription>
                Anteprima modifiche — Controlla le modifiche prima di confermare. Le righe scartate non verranno
                importate.
              </DialogDescription>
            )}
          </DialogHeader>

          <div className="flex max-h-[60vh] flex-col gap-4 overflow-y-auto">
            {!preview && (
              <>
                <div className="flex flex-col gap-3">
                  <Label>Destinazione</Label>
                  <RadioGroup
                    value={destKind}
                    onValueChange={(value) => setDestKind(value as "esistente" | "nuova_citta")}
                    className="grid-cols-1 gap-3 sm:grid-cols-2"
                  >
                    <Label className="flex items-center gap-2 font-normal">
                      <RadioGroupItem value="esistente" />
                      Listino esistente
                    </Label>
                    <Label className="flex items-center gap-2 font-normal">
                      <RadioGroupItem value="nuova_citta" />
                      Nuova città / Nuovo listino
                    </Label>
                  </RadioGroup>

                  {destKind === "esistente" ? (
                    <Select
                      value={destListinoId !== null ? String(destListinoId) : ""}
                      onValueChange={(value) => setDestListinoId(Number(value))}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Seleziona un listino" />
                      </SelectTrigger>
                      <SelectContent>
                        {listini.map((listino) => (
                          <SelectItem key={listino.id} value={String(listino.id)}>
                            {listino.nome} ({listino.citta_riferimento})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : (
                    <div className="flex flex-col gap-2">
                      <Input
                        placeholder="Nome della città"
                        value={destCitta}
                        onChange={(e) => setDestCitta(e.target.value)}
                      />
                      <label className="flex items-center gap-2 text-sm text-muted-foreground">
                        <input
                          type="checkbox"
                          checked={destIsDefault}
                          onChange={(e) => setDestIsDefault(e.target.checked)}
                        />
                        Imposta come listino di default (fallback)
                      </label>
                    </div>
                  )}

                  <div className="flex flex-col gap-1.5">
                    <Label htmlFor="comuni-extra" className="font-normal">
                      Mappa anche questi comuni (facoltativo)
                    </Label>
                    <Input
                      id="comuni-extra"
                      placeholder="Es. Carpi, Sassuolo, Formigine"
                      value={destComuniExtra}
                      onChange={(e) => setDestComuniExtra(e.target.value)}
                    />
                    <p className="text-xs text-muted-foreground">
                      Separati da virgola: verranno associati a questo listino in un unico passaggio.
                    </p>
                  </div>
                </div>

                <div
                  className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border px-6 py-10 text-center"
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={handleDrop}
                >
                  <UploadCloud className="size-8 text-muted-foreground" aria-hidden />
                  <p className="text-sm text-foreground">
                    Trascina qui il file .xlsx oppure{" "}
                    <button
                      type="button"
                      className="text-primary underline underline-offset-4"
                      onClick={() => fileInputRef.current?.click()}
                      disabled={!destinationValid}
                    >
                      sfoglia i file
                    </button>
                  </p>
                  <p className="text-sm text-muted-foreground">Solo file .xlsx, dimensione massima 10 MB.</p>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".xlsx"
                    className="hidden"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) handleFileSelected(file);
                    }}
                  />
                </div>

                {fileName && !fileError && previewMutation.isPending && (
                  <div className="flex flex-col gap-2">
                    <p className="text-sm text-muted-foreground">Verifica del file in corso…</p>
                    <Skeleton className="h-10 w-full" />
                  </div>
                )}

                {fileError && <p className="text-sm text-destructive">{fileError}</p>}
                {previewMutation.isError && <p className="text-sm text-destructive">{IMPORT_ERROR}</p>}
              </>
            )}

            {preview && (
              <>
                <p className="text-sm text-muted-foreground">Destinazione: {preview.target_descr}</p>

                <DiffPreviewTable
                  nuove={toDiffPreviewRows(preview.nuove)}
                  modificate={toDiffPreviewRows(preview.modificate)}
                  scarti={preview.scarti}
                  generatoIl={preview.generato_il}
                />

                {confirmMutation.isError && <p className="text-sm text-destructive">{IMPORT_ERROR}</p>}
              </>
            )}
          </div>

          {preview && (
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDiscardOpen(true)}>
                Annulla import
              </Button>
              <Button
                type="button"
                disabled={validRowCount === 0 || confirmMutation.isPending}
                onClick={() => confirmMutation.mutate()}
                className="bg-primary text-primary-foreground hover:bg-primary/90"
              >
                {confirmMutation.isPending ? "Import in corso…" : "Conferma import"}
              </Button>
            </DialogFooter>
          )}
        </DialogContent>
      </Dialog>

      <AlertDialog open={discardOpen} onOpenChange={setDiscardOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Annullare l'import?</AlertDialogTitle>
            <AlertDialogDescription>Nessuna modifica verrà applicata.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDiscardOpen(false)}>Torna alla preview</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={(event) => {
                event.preventDefault();
                setDiscardOpen(false);
                resetAndClose();
              }}
            >
              Annulla import
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
