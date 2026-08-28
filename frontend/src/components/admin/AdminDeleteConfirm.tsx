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

interface AdminDeleteConfirmProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Nome entità, es. "referente" — usato per titolare il pulsante distruttivo. */
  entityLabel: string;
  /** Copy specifica della conferma (UI-SPEC copy table), es. "Eliminare {nome}? ...". */
  description: string;
  onConfirm: () => void;
  isDeleting?: boolean;
}

/**
 * Conferma distruttiva condivisa (UI-SPEC §D.4): alert-dialog con titolo +
 * corpo + "Elimina {entità}" (destructive) / "Annulla" (bare, 1:1-paired
 * nella stessa dialog per contratto copy).
 */
export function AdminDeleteConfirm({
  open,
  onOpenChange,
  entityLabel,
  description,
  onConfirm,
  isDeleting = false,
}: AdminDeleteConfirmProps) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Eliminare {entityLabel}?</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Annulla</AlertDialogCancel>
          <AlertDialogAction
            variant="destructive"
            disabled={isDeleting}
            onClick={(event) => {
              event.preventDefault();
              onConfirm();
            }}
          >
            Elimina {entityLabel}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
