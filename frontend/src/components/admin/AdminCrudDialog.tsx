import type { ReactNode } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

interface AdminCrudDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Nome entità, es. "referente" — usato per titolare le CTA. */
  entityLabel: string;
  /** Titolo del dialog, es. "Aggiungi referente" / "Modifica referente". */
  title: string;
  description?: string;
  /** Form iniettato dalla pagina chiamante. */
  children: ReactNode;
  onSubmit: () => void;
  isSaving?: boolean;
  errorMessage?: string | null;
}

/**
 * Shell dialog CRUD condivisa (UI-SPEC §D): form iniettato dalla pagina,
 * un'unica primary CTA "Salva {entità}" + secondaria "Annulla modifica".
 * Toast "Modifica salvata" è responsabilità della pagina chiamante al
 * successo della mutation (qui solo lo shell).
 */
export function AdminCrudDialog({
  open,
  onOpenChange,
  entityLabel,
  title,
  description,
  children,
  onSubmit,
  isSaving = false,
  errorMessage,
}: AdminCrudDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>

        <form
          onSubmit={(event) => {
            event.preventDefault();
            onSubmit();
          }}
          className="flex flex-col gap-4"
        >
          {children}

          {errorMessage && (
            <p className="text-sm text-destructive">{errorMessage}</p>
          )}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Annulla modifica
            </Button>
            <Button
              type="submit"
              disabled={isSaving}
              className="bg-primary text-primary-foreground hover:bg-primary/90"
            >
              Salva {entityLabel}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
