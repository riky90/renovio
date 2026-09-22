import { Badge } from "@/components/ui/badge";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";

/**
 * Tabella di preview del diff import, condivisa da `ExcelUploadDialog`
 * (formato del computo) e `FlatImportDialog` (formato piatto, 08-06): il
 * piano 08-08 aggiunge il badge "Cambiata dopo l'export" in UN posto solo,
 * non in due copie che divergono. Ogni dialog mappa il proprio formato di
 * riga a `DiffPreviewRow` prima di renderizzare — questo componente non
 * conosce `VoceRiga` né `DiffRigaOut`, solo stringhe già pronte per lo
 * schermo.
 *
 * Token ambra (`bg-amber-bg`/`border-amber-border`/`text-amber-fg`, UI-SPEC
 * §Color) invece dei valori hex cablati che c'erano nell'originale
 * `ExcelUploadDialog` prima di questa estrazione.
 */
export const SCARTI_ACCORDION_THRESHOLD = 10;

export interface DiffPreviewRow {
  key: string;
  label: string;
  valorePrecedente: string;
  valoreNuovo: string;
  /** D-11: true se la riga e' stata modificata a database DOPO il
   * timestamp di generazione del file caricato (`generatoIl`). Informativo
   * — non blocca mai "Conferma import". */
  staleAfterExport?: boolean;
}

export interface DiffPreviewScarto {
  riga: number;
  motivo: string;
}

interface DiffPreviewTableProps {
  nuove: DiffPreviewRow[];
  modificate: DiffPreviewRow[];
  scarti: DiffPreviewScarto[];
  /** D-11: timestamp di generazione del file (`DiffPiatto.generato_il` /
   * `DiffPreview.generato_il`), usato SOLO per il testo del banner —
   * `null` quando il file non lo porta (nessuna riga risultera' mai stale
   * in quel caso). */
  generatoIl?: string | null;
}

export function DiffPreviewTable({ nuove, modificate, scarti, generatoIl = null }: DiffPreviewTableProps) {
  const validRowCount = nuove.length + modificate.length;
  const showScartiAccordion = scarti.length > SCARTI_ACCORDION_THRESHOLD;
  const righeStale = modificate.filter((row) => row.staleAfterExport);

  return (
    <>
      <div className="flex flex-wrap gap-2">
        <Badge className="bg-primary/10 text-primary">{nuove.length} nuove</Badge>
        <Badge className="border-amber-border bg-amber-bg text-amber-fg">{modificate.length} modificate</Badge>
        <Badge variant="destructive">{scarti.length} scartate</Badge>
      </div>

      {righeStale.length > 0 && (
        <div className="rounded-lg border border-amber-border bg-amber-bg px-4 py-3 text-sm text-amber-fg">
          {righeStale.length} righe sono cambiate nel database dopo che hai scaricato questo file
          {generatoIl ? ` (generato il ${new Date(generatoIl).toLocaleDateString("it-IT")})` : ""}.{" "}
          Controllale prima di confermare.
        </div>
      )}

      {validRowCount > 0 && (
        <div className="rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="px-3 py-2 font-semibold">Voce</th>
                <th className="px-3 py-2 font-semibold">Stato</th>
                <th className="px-3 py-2 font-semibold">Valore precedente</th>
                <th className="px-3 py-2 font-semibold">Nuovo valore</th>
              </tr>
            </thead>
            <tbody>
              {modificate.map((row) => (
                <tr key={`mod-${row.key}`} className="h-10 border-b border-border last:border-0">
                  <td className="px-3 py-2">{row.label}</td>
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap items-center gap-1">
                      <Badge className="border-amber-border bg-amber-bg text-amber-fg">Modificata</Badge>
                      {row.staleAfterExport && (
                        <Badge className="border-amber-border bg-amber-bg text-amber-fg">
                          Cambiata dopo l'export
                        </Badge>
                      )}
                    </div>
                  </td>
                  <td className="px-3 py-2 tabular-nums">{row.valorePrecedente}</td>
                  <td className="px-3 py-2 tabular-nums">{row.valoreNuovo}</td>
                </tr>
              ))}
              {nuove.map((row) => (
                <tr key={`new-${row.key}`} className="h-10 border-b border-border last:border-0">
                  <td className="px-3 py-2">{row.label}</td>
                  <td className="px-3 py-2">
                    <Badge className="bg-primary/10 text-primary">Nuova</Badge>
                  </td>
                  <td className="px-3 py-2 tabular-nums">—</td>
                  <td className="px-3 py-2 tabular-nums">{row.valoreNuovo}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div>
        <h3 className="mb-2 text-sm font-semibold text-foreground">Righe scartate</h3>
        {scarti.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nessuna riga scartata.</p>
        ) : showScartiAccordion ? (
          <Accordion type="single" collapsible>
            <AccordionItem value="scarti">
              <AccordionTrigger>{scarti.length} righe scartate</AccordionTrigger>
              <AccordionContent>
                <ul className="flex flex-col gap-1">
                  {scarti.map((s, i) => (
                    <li key={i} className="text-sm text-destructive">
                      Riga {s.riga}: {s.motivo}
                    </li>
                  ))}
                </ul>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        ) : (
          <ul className="flex flex-col gap-1">
            {scarti.map((s, i) => (
              <li key={i} className="text-sm text-destructive">
                Riga {s.riga}: {s.motivo}
              </li>
            ))}
          </ul>
        )}
      </div>

      {validRowCount === 0 && (
        <p className="text-sm text-muted-foreground">
          Nessuna riga verrà importata: tutte le righe sono state scartate.
        </p>
      )}
    </>
  );
}
