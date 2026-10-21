import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Download, UploadCloud } from "lucide-react";
import { Button } from "@/components/ui/button";
import { scaricaExcel } from "@/api/admin/exportExcel";
import {
  getValidazioneComputo,
  importaComputo,
  type EsitoImportComputo,
} from "@/api/admin/computo";

/**
 * Computo parametrico (Fase 11, CUR3-01): grandezze, regole per voce e preset
 * si curano su Excel. Il file si scarica, si modifica e si ricarica:
 * l'anteprima elenca gli errori per foglio e riga senza scrivere nulla, e
 * "Applica" sostituisce il computo solo se non ce ne sono.
 */
export function ComputoTab() {
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [esito, setEsito] = useState<EsitoImportComputo | null>(null);

  const validazione = useQuery({
    queryKey: ["admin-computo-validazione"],
    queryFn: getValidazioneComputo,
  });

  const scarica = useMutation({
    mutationFn: () => scaricaExcel("/admin/computo/export.xlsx"),
    onError: (e: Error) => toast.error(e.message),
  });

  const importa = useMutation({
    mutationFn: ({ f, applica }: { f: File; applica: boolean }) => importaComputo(f, applica),
    onSuccess: (risultato) => {
      setEsito(risultato);
      if (risultato.applicato) {
        toast.success("Computo aggiornato");
        setFile(null);
        void queryClient.invalidateQueries({ queryKey: ["admin-computo-validazione"] });
      }
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const erroriDb = validazione.data?.errori ?? [];

  return (
    <div className="flex flex-col gap-4 pt-4">
      <p className="text-sm text-muted-foreground">
        Grandezze della casa, regola di quantità di ogni voce e preset per tipo di
        ristrutturazione. L'import sostituisce tutto il computo ed è tutto o niente.
      </p>

      <div className="flex flex-wrap gap-2">
        <Button variant="outline" onClick={() => scarica.mutate()} disabled={scarica.isPending}>
          <Download className="size-4" />
          {scarica.isPending ? "Generazione…" : "Scarica Excel"}
        </Button>
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx"
          className="hidden"
          onChange={(e) => {
            const scelto = e.target.files?.[0] ?? null;
            setFile(scelto);
            setEsito(null);
            if (scelto) importa.mutate({ f: scelto, applica: false });
            e.target.value = "";
          }}
        />
        <Button variant="outline" onClick={() => inputRef.current?.click()} disabled={importa.isPending}>
          <UploadCloud className="size-4" />
          Carica Excel
        </Button>
        {file && esito && !esito.applicato && esito.errori.length === 0 && (
          <Button onClick={() => importa.mutate({ f: file, applica: true })} disabled={importa.isPending}>
            Applica
          </Button>
        )}
      </div>

      {esito && (
        <div className="rounded-md border p-3 text-sm">
          <p className="font-medium">
            {esito.applicato
              ? "Applicato."
              : esito.errori.length
                ? `${esito.errori.length} errori: il file non è stato applicato.`
                : "Anteprima senza errori: premi Applica per sostituire il computo."}
          </p>
          <p className="text-muted-foreground">
            {Object.entries(esito.conteggi)
              .map(([foglio, n]) => `${foglio}: ${n}`)
              .join(" · ")}
          </p>
          {esito.errori.length > 0 && (
            <ul className="mt-2 list-disc pl-5 text-destructive">
              {esito.errori.map((errore) => (
                <li key={errore}>{errore}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="text-sm">
        <p className="font-medium">Stato del computo a database</p>
        {validazione.isLoading ? (
          <p className="text-muted-foreground">Verifica in corso…</p>
        ) : erroriDb.length === 0 ? (
          <p className="text-muted-foreground">Nessun errore di curatela.</p>
        ) : (
          <ul className="list-disc pl-5 text-destructive">
            {erroriDb.map((errore) => (
              <li key={errore}>{errore}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
