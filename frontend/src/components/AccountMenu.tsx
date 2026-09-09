import { useNavigate } from "react-router";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/hooks/useAuth";
import { iniziali } from "@/components/ProfileHeaderCard";
import type { UserOut } from "@/api/auth";

interface AccountMenuProps {
  user: UserOut;
}

export function AccountMenu({ user }: AccountMenuProps) {
  const navigate = useNavigate();
  const { logout } = useAuth();

  const isStaff = user.role === "admin" || user.role === "consulente";
  const areaLabel = user.role === "admin" ? "Pannello amministratore" : "Area consulente";
  const roleBadge = user.role === "admin" ? "Admin" : user.role === "consulente" ? "Consulente" : null;

  function handleLogout() {
    logout.mutate(undefined, {
      onSuccess: () => navigate("/"),
    });
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger className="rounded-full outline-none focus-visible:ring-3 focus-visible:ring-ring/50 data-[state=open]:ring-2 data-[state=open]:ring-primary">
        <Avatar>
          {user.avatar_url && <AvatarImage src={user.avatar_url} alt={user.nome} />}
          <AvatarFallback>{iniziali(user.nome, user.cognome)}</AvatarFallback>
        </Avatar>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {/* Il blocco col nome NON e' piu' una semplice etichetta: e' la porta
            d'ingresso alla pagina utente, che e' la cosa che ci si aspetta di
            poter cliccare quando si apre il proprio menu account. */}
        <DropdownMenuItem
          onSelect={() => navigate("/impostazioni")}
          className="flex flex-col items-start gap-0.5 py-2"
        >
          <span className="flex items-center gap-2 text-sm font-medium text-foreground">
            {user.nome}
            {roleBadge && <Badge variant="secondary">{roleBadge}</Badge>}
            {user.pro && <Badge className="bg-primary text-primary-foreground">Pro</Badge>}
          </span>
          <span className="text-xs text-muted-foreground">{user.email}</span>
        </DropdownMenuItem>
        <DropdownMenuSeparator />

        {/* Le tre sezioni della pagina utente in cima, ognuna sulla propria
            tab: sono le voci che si cercano piu' spesso. */}
        <DropdownMenuItem onSelect={() => navigate("/impostazioni?tab=profilo")}>
          Profilo
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => navigate("/impostazioni?tab=abbonamento")}>
          Abbonamento
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => navigate("/impostazioni?tab=referral")}>
          Invita un amico
        </DropdownMenuItem>
        <DropdownMenuSeparator />

        {/* In cima: e' l'azione piu' frequente. Per un Pro punta al flusso a
            due step su /nuova-stima, per tutti gli altri alla home. */}
        <DropdownMenuItem onSelect={() => navigate(user.pro ? "/nuova-stima" : "/")}>
          Nuova stima
        </DropdownMenuItem>
        {isStaff && (
          <DropdownMenuItem onSelect={() => navigate("/admin")}>{areaLabel}</DropdownMenuItem>
        )}
        <DropdownMenuItem onSelect={() => navigate("/le-mie-stime")}>I miei progetti</DropdownMenuItem>
        {!user.pro && (
          <DropdownMenuItem onSelect={() => navigate("/passa-a-pro")}>Passa a Pro</DropdownMenuItem>
        )}

        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={handleLogout}>Esci</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
