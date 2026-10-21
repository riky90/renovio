import { useEffect, useMemo, useState } from "react";
import { Check } from "lucide-react";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Popover, PopoverAnchor, PopoverContent } from "@/components/ui/popover";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
interface Comune {
  nome: string;
  provincia: string;
}

/** Parole normalizzate: minuscole, senza accenti, apostrofi come separatori. */
function parole(testo: string): string[] {
  return testo
    .toLocaleLowerCase("it")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .split(/[\s'’-]+/)
    .filter(Boolean);
}

// I ~8.000 comuni ISTAT pesano ~300 kB: si scaricano alla prima digitazione,
// non con la pagina. Una sola promessa condivisa fra tutte le istanze.
let caricamento: Promise<Comune[]> | null = null;
function caricaComuni(): Promise<Comune[]> {
  caricamento ??= import("@/data/comuni.json").then((m) => m.default as Comune[]);
  return caricamento;
}

/**
 * Suggerimenti in ordine di pertinenza: prima il nome che comincia con il
 * testo digitato, poi i nomi in cui ogni parola digitata e' l'inizio di una
 * parola del nome ("reggio emilia" trova "Reggio nell'Emilia").
 */
function suggerisci(comuni: Comune[], query: string): Comune[] {
  const testo = query.trim().toLocaleLowerCase("it");
  if (testo.length < 2) return [];
  const cercate = parole(testo);
  const iniziano: Comune[] = [];
  const perParole: Comune[] = [];
  for (const c of comuni) {
    const nome = c.nome.toLocaleLowerCase("it");
    if (nome.startsWith(testo)) {
      iniziano.push(c);
      continue;
    }
    const delNome = parole(c.nome);
    if (cercate.every((p) => delNome.some((n) => n.startsWith(p)))) perParole.push(c);
  }
  const perLunghezza = (a: Comune, b: Comune) => a.nome.length - b.nome.length || a.nome.localeCompare(b.nome, "it");
  return [...iniziano.sort(perLunghezza), ...perParole.sort(perLunghezza)].slice(0, 8);
}

interface CityAutocompleteProps {
  value: string;
  onChange: (value: string) => void;
  error?: string;
}

/**
 * Free-text città input with a suggestion popover backed by a bundled
 * ISTAT comuni dataset. The user may type any text and submit — the
 * autocomplete is UX sugar only (D-06): città is never validated against
 * this list before submit.
 */
export function CityAutocomplete({ value, onChange, error }: CityAutocompleteProps) {
  const [open, setOpen] = useState(false);
  const [comuni, setComuni] = useState<Comune[]>([]);

  useEffect(() => {
    if (comuni.length || value.trim().length < 2) return;
    let attivo = true;
    void caricaComuni().then((dati) => {
      if (attivo) setComuni(dati);
    });
    return () => {
      attivo = false;
    };
  }, [value, comuni.length]);

  const suggestions = useMemo(() => suggerisci(comuni, value), [comuni, value]);

  const showList = open && suggestions.length > 0;

  function selectCity(nome: string) {
    onChange(nome);
    setOpen(false);
  }

  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor="citta">Città</Label>
      <Popover open={showList} onOpenChange={setOpen}>
        <PopoverAnchor asChild>
          <Command shouldFilter={false} className="overflow-visible bg-transparent p-0">
            <CommandInput
              id="citta"
              placeholder="Es. Reggio Emilia"
              value={value}
              onValueChange={(next) => {
                onChange(next);
                setOpen(true);
              }}
              onKeyDown={(e) => {
                // Esc closes the suggestion list without clearing the typed text.
                if (e.key === "Escape") setOpen(false);
              }}
              className={cn(error && "text-destructive")}
            />
            {/*
             * IMPORTANT: no onBlur-driven close here. Clicking a suggestion
             * fires a native "click" (mousedown -> blur -> mouseup -> click)
             * on the CommandItem — cmdk selects on "click", not "mousedown".
             * Closing on blur would unmount the popover content before that
             * click event ever reaches the item, so the selection is lost.
             * Closing is instead handled by:
             *  - onSelect below (explicit, on successful selection)
             *  - Escape (onKeyDown above)
             *  - Radix's own outside-pointerdown dismissal on PopoverContent
             */}
            {showList && (
              <PopoverContent
                className="w-(--radix-popover-trigger-width) p-0"
                onOpenAutoFocus={(e) => e.preventDefault()}
                align="start"
              >
                <CommandList>
                  <CommandEmpty>Nessun comune trovato.</CommandEmpty>
                  <CommandGroup>
                    {suggestions.map((c) => (
                      <CommandItem
                        key={`${c.nome}-${c.provincia}`}
                        value={c.nome}
                        onSelect={selectCity}
                      >
                        <Check
                          className={cn(
                            "size-4",
                            value === c.nome ? "opacity-100" : "opacity-0"
                          )}
                        />
                        {c.nome}{" "}
                        <span className="text-muted-foreground">({c.provincia})</span>
                      </CommandItem>
                    ))}
                  </CommandGroup>
                </CommandList>
              </PopoverContent>
            )}
          </Command>
        </PopoverAnchor>
      </Popover>
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  );
}
