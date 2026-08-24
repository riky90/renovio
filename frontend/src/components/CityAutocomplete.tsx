import { useMemo, useState } from "react";
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
import comuniData from "@/data/comuni.json";

interface Comune {
  nome: string;
  provincia: string;
}

const comuni = comuniData as Comune[];

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

  const suggestions = useMemo(() => {
    const query = value.trim().toLocaleLowerCase("it");
    if (query.length < 2) return [];
    return comuni
      .filter((c) => c.nome.toLocaleLowerCase("it").startsWith(query))
      .slice(0, 8);
  }, [value]);

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
