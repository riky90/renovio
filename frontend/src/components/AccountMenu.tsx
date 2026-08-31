import { useNavigate } from "react-router";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/hooks/useAuth";
import type { UserOut } from "@/api/auth";

function iniziali(nome: string): string {
  const parti = nome.trim().split(/\s+/).filter(Boolean);
  if (parti.length === 0) return "?";
  if (parti.length === 1) return parti[0].slice(0, 2).toUpperCase();
  return (parti[0][0] + parti[1][0]).toUpperCase();
}

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
          <AvatarFallback>{iniziali(user.nome)}</AvatarFallback>
        </Avatar>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel className="flex flex-col gap-0.5 font-normal">
          <span className="flex items-center gap-2 text-sm font-medium text-foreground">
            {user.nome}
            {roleBadge && <Badge variant="secondary">{roleBadge}</Badge>}
            {user.pro && <Badge className="bg-primary text-primary-foreground">Pro</Badge>}
          </span>
          <span className="text-xs text-muted-foreground">{user.email}</span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />

        {isStaff && (
          <DropdownMenuItem onSelect={() => navigate("/admin")}>{areaLabel}</DropdownMenuItem>
        )}
        <DropdownMenuItem onSelect={() => navigate("/le-mie-stime")}>I miei progetti</DropdownMenuItem>
        <DropdownMenuItem onSelect={() => navigate("/impostazioni")}>Impostazioni</DropdownMenuItem>
        {!user.pro && (
          <DropdownMenuItem onSelect={() => navigate("/passa-a-pro")}>Passa a Pro</DropdownMenuItem>
        )}

        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={handleLogout}>Esci</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
