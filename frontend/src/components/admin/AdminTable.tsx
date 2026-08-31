import type { ReactNode } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";

interface AdminTableProps {
  /** Etichette colonne, sinistra a destra. */
  columns: string[];
  /** true durante il fetch: mostra righe skeleton alla row-height 40px. */
  isLoading: boolean;
  /** Righe da renderizzare quando isLoading=false e rows.length>0. */
  rows: ReactNode[][];
  /** true quando la lista è vuota (nessun filtro applicato o dopo filtro). */
  isEmpty: boolean;
  emptyHeading: string;
  emptyBody?: ReactNode;
}

/**
 * Tabella admin generica riusabile (UI-SPEC §C/§D): container secondary
 * surface, skeleton rows in caricamento, empty-state testuale. Nessun campo
 * dati hardcoded — generica per costruzione (T-04-28), l'anti-leak sta nelle
 * pagine/API concrete.
 */
export function AdminTable({
  columns,
  isLoading,
  rows,
  isEmpty,
  emptyHeading,
  emptyBody,
}: AdminTableProps) {
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((col) => (
              <TableHead key={col}>{col}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading &&
            Array.from({ length: 5 }).map((_, i) => (
              <TableRow key={i} className="h-10">
                {columns.map((col, j) => (
                  <TableCell key={`${col}-${j}`}>
                    <Skeleton className="h-4 w-full" />
                  </TableCell>
                ))}
              </TableRow>
            ))}

          {!isLoading &&
            !isEmpty &&
            rows.map((row, i) => (
              <TableRow key={i} className="h-10">
                {row.map((cell, j) => (
                  <TableCell key={j}>{cell}</TableCell>
                ))}
              </TableRow>
            ))}
        </TableBody>
      </Table>

      {!isLoading && isEmpty && (
        <div className="flex flex-col items-center gap-2 px-4 py-12 text-center">
          <h3 className="text-base font-semibold text-foreground">{emptyHeading}</h3>
          {emptyBody && <p className="max-w-sm text-sm text-muted-foreground">{emptyBody}</p>}
        </div>
      )}
    </div>
  );
}
