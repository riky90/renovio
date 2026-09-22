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
import { Skeleton } from "@/components/ui/skeleton";
import {
  previewImport,
  confirmImport,
  type DiffPiatto,
  type DiffRigaOut,
  type RigaPiattaIn,
} from "@/api/admin/importExcel";
import { DiffPreviewTable, type DiffPreviewRow } from "@/components/admin/DiffPreviewTable";

const MAX_SIZE_BYTES = 10 * 1024 * 1024;
const INVALID_FILE_MESSAGE = "Il file non è valido. Controlla che sia un .xlsx e non superi i 10 MB.";
const IMPORT_ERROR = "Import non riuscito. Riprova o contatta l'assistenza tecnica.";

interface FlatImportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  risorsa: string;
  titolo: string;
  onImported: () => void;
}

function validateFile(file: File): string | null {
  const isXlsx = file.name.toLowerCase().endsWith(".xlsx");
  if (!isXlsx || file.size > MAX_SIZE_BYTES) {
    return INVALID_FILE_MESSAGE;
  }
  return null;
}

function formatValori(valori: Record<string, unknown>, campi: string[]): string {
  if (campi.length === 0) return "—";
  return campi.map((campo) => `${campo}: ${String(valori[campo] ?? "—")}`).join(", ");
}

function toDiffPreviewRows(rows: DiffRigaOut[]): DiffPreviewRow[] {
  return rows.map((row) => ({
    key: `${row.foglio}-${row.id ?? row.chiave_descr}`,
    label: `${row.foglio} — ${row.chiave_descr}`,
    valorePrecedente: formatValori(row.valori_precedenti, row.campi_modificati),
    valoreNuovo: formatValori(row.valori_nuovi, row.campi_modificati),
  }));
}

/**
 * Round-trip stateless (Fase 4/08-03): il client ricostruisce
 * `RigaPiattaIn` da `DiffRigaOut` — `valori_nuovi` contiene gia' SOLO i
 * campi che cambiano (D-09/CUR-02), pronti per `/confirm`.
 */
function toRigaPiattaIn(row: DiffRigaOut): RigaPiattaIn {
  return { foglio: row.foglio, id: row.id, valori: row.valori_nuovi, campi_da_cancellare: [] };
}

/**
 * Dialog di import del formato piatto (piano 08-06), senza il passo
 * destinazione di `ExcelUploadDialog`: per queste risorse la risorsa
 * stessa e' la destinazione. Flusso a tre passi: dropzone → preview diff
 * (`DiffPreviewTable`, condivisa) → conferma.
 */
export function FlatImportDialog({ open, onOpenChange, risorsa, titolo, onImported }: FlatImportDialogProps) {
  const [fileError, setFileError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [discardOpen, setDiscardOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const previewMutation = useMutation<DiffPiatto, Error, File>({
    mutationFn: (file: File) => previewImport(risorsa, file),
  });

  const confirmMutation = useMutation({
    mutationFn: () => {
      const preview = previewMutation.data!;
      return confirmImport(risorsa, preview.nuove.map(toRigaPiattaIn), preview.modificate.map(toRigaPiattaIn));
    },
    onSuccess: (result) => {
      toast.success(`Import completato: ${result.righe_applicate} righe applicate`);
      onImported();
      resetAndClose();
    },
  });

  function resetAndClose() {
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
            <DialogTitle>{titolo}</DialogTitle>
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
                <DiffPreviewTable
                  nuove={toDiffPreviewRows(preview.nuove)}
                  modificate={toDiffPreviewRows(preview.modificate)}
                  scarti={preview.scarti}
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
