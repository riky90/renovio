import { useRef, useState, useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Camera, Trash2 } from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { AUTH_QUERY_KEY } from "@/hooks/useAuth";
import { deleteAvatar, postAvatar, type UserOut } from "@/api/auth";
import { ApiError } from "@/api/client";
import { getStoricoStime, type StimaSalvataListItem } from "@/api/stima";

/** Iniziali del nome, come fallback quando non c'è (ancora) una foto. */
export function iniziali(nome: string, cognome?: string | null): string {
  const parti = [nome, cognome ?? ""].join(" ").trim().split(/\s+/).filter(Boolean);
  if (parti.length === 0) return "?";
  if (parti.length === 1) return parti[0].slice(0, 2).toUpperCase();
  return (parti[0][0] + parti[1][0]).toUpperCase();
}

function membroDa(isoDate: string): string {
  const data = new Date(isoDate);
  if (Number.isNaN(data.getTime())) return "";
  return data.toLocaleDateString("it-IT", { month: "long", year: "numeric" });
}

const ERRORE_GENERICO = "Non siamo riusciti a caricare la foto. Riprova.";

export function ProfileHeaderCard({ user }: { user: UserOut }) {
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  // Anteprima locale (object URL): l'immagine si vede subito, senza attendere
  // il round trip verso lo storage.
  const [anteprima, setAnteprima] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      if (anteprima) URL.revokeObjectURL(anteprima);
    };
  }, [anteprima]);

  const storicoQuery = useQuery<StimaSalvataListItem[]>({
    queryKey: ["storico-stime"],
    queryFn: getStoricoStime,
  });

  const uploadMutation = useMutation({
    mutationFn: postAvatar,
    onSuccess: (updated) => {
      queryClient.setQueryData(AUTH_QUERY_KEY, updated);
      toast.success("Foto profilo aggiornata.");
    },
    onError: (error) => {
      // Il backend distingue 400 (immagine rifiutata) da 503 (storage non
      // configurato) e scrive un messaggio comprensibile in entrambi i casi:
      // riscriverlo qui lo peggiorerebbe.
      toast.error(error instanceof ApiError ? error.message : ERRORE_GENERICO);
      setAnteprima(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteAvatar,
    onSuccess: (updated) => {
      queryClient.setQueryData(AUTH_QUERY_KEY, updated);
      setAnteprima(null);
      toast.success("Foto profilo rimossa.");
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : ERRORE_GENERICO),
  });

  function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    // Il campo si azzera SEMPRE: senza, ricaricare lo stesso file due volte di
    // fila non emette un secondo change event.
    e.target.value = "";
    if (!file) return;
    setAnteprima(URL.createObjectURL(file));
    uploadMutation.mutate(file);
  }

  const nomeCompleto = [user.nome, user.cognome].filter(Boolean).join(" ");
  const roleBadge =
    user.role === "admin" ? "Admin" : user.role === "consulente" ? "Consulente" : null;
  const progetti = storicoQuery.data?.length;
  const inCorso = uploadMutation.isPending || deleteMutation.isPending;

  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-5 py-6 sm:flex-row sm:items-center sm:gap-6">
        <Avatar size="lg" className="size-20">
          {(anteprima ?? user.avatar_url) && (
            <AvatarImage src={anteprima ?? user.avatar_url ?? ""} alt={nomeCompleto} />
          )}
          <AvatarFallback className="text-xl">
            {iniziali(user.nome, user.cognome)}
          </AvatarFallback>
        </Avatar>

        <div className="flex flex-1 flex-col items-center gap-1.5 sm:items-start">
          <div className="flex flex-wrap items-center justify-center gap-2 sm:justify-start">
            <span className="text-lg font-semibold text-foreground">{nomeCompleto}</span>
            {roleBadge && <Badge variant="secondary">{roleBadge}</Badge>}
            {user.pro && <Badge className="bg-primary text-primary-foreground">Pro</Badge>}
          </div>
          <span className="text-sm text-muted-foreground">{user.email}</span>
          <span className="text-sm text-muted-foreground">
            Membro da {membroDa(user.created_at)}
            {progetti !== undefined &&
              ` · ${progetti} ${progetti === 1 ? "progetto" : "progetti"}`}
          </span>
        </div>

        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            onChange={handleFile}
            className="hidden"
          />
          <Button
            type="button"
            variant="outline"
            disabled={inCorso}
            onClick={() => inputRef.current?.click()}
          >
            <Camera className="size-4" />
            {uploadMutation.isPending ? "Caricamento..." : "Cambia foto"}
          </Button>
          {user.avatar_url && (
            <Button
              type="button"
              variant="ghost"
              disabled={inCorso}
              onClick={() => deleteMutation.mutate()}
            >
              <Trash2 className="size-4" />
              Rimuovi
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
