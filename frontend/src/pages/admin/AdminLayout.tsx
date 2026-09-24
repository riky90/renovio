import type { ReactNode } from "react";
import { Link, useLocation } from "react-router";
import {
  Inbox,
  Tags,
  SlidersHorizontal,
  MapPin,
  Users,
  ShieldCheck,
  Layers,
  Percent,
  HelpCircle,
  type LucideIcon,
} from "lucide-react";
import { AccountMenu } from "@/components/AccountMenu";
import { BrandMark } from "@/components/BrandMark";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/useAuth";

type Ruolo = "user" | "consulente" | "admin";

interface AdminNavItem {
  path: string;
  label: string;
  icon: LucideIcon;
  roles: Ruolo[];
}

// Ogni voce dichiara i ruoli che possono vederla. Il consulente vede SOLO la
// dashboard lead; tutta la config di business e la gestione utenti restano
// all'admin. Il gate reale è comunque server-side (require_admin/require_staff).
const NAV_ITEMS: AdminNavItem[] = [
  { path: "/admin/lead", label: "Lead", icon: Inbox, roles: ["admin", "consulente"] },
  { path: "/admin/listini", label: "Listini e prezzi", icon: Tags, roles: ["admin"] },
  { path: "/admin/dettaglio-pro", label: "Voci dettaglio Pro", icon: Layers, roles: ["admin"] },
  { path: "/admin/domande", label: "Domande", icon: HelpCircle, roles: ["admin"] },
  { path: "/admin/coefficienti", label: "Coefficienti", icon: SlidersHorizontal, roles: ["admin"] },
  { path: "/admin/bonus", label: "Bonus fiscali", icon: Percent, roles: ["admin"] },
  { path: "/admin/citta-testi", label: "Città e testi", icon: MapPin, roles: ["admin"] },
  { path: "/admin/referenti", label: "Referenti", icon: Users, roles: ["admin"] },
  { path: "/admin/utenti", label: "Utenti", icon: ShieldCheck, roles: ["admin"] },
];

/**
 * Shell dell'area /admin (D-21, UI-SPEC §B): guard client-side PRIMA di ogni
 * fetch (T-04-27) + sidebar (desktop) / tabs (mobile). `allow` definisce i
 * ruoli ammessi alla SINGOLA pagina (default: solo admin); la dashboard lead
 * passa `allow={["admin","consulente"]}`. Il gate reale resta server-side
 * (require_admin/require_staff) — qui non si fa mai fetch prima del guard,
 * così né un non-staff né un consulente su una pagina admin vede un flash.
 */
export function AdminLayout({
  children,
  allow = ["admin"],
}: {
  children: ReactNode;
  allow?: Ruolo[];
}) {
  const { user, isLoading } = useAuth();
  const location = useLocation();
  const navItems = NAV_ITEMS.filter((item) => user && item.roles.includes(user.role as Ruolo));

  if (isLoading) {
    return (
      <main className="mx-auto flex min-h-svh w-full max-w-[480px] flex-col gap-4 px-4 py-8">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-64 w-full" />
      </main>
    );
  }

  if (!user || !allow.includes(user.role as Ruolo)) {
    return (
      <main className="mx-auto flex min-h-svh w-full max-w-[480px] flex-col items-center justify-center gap-4 px-4 py-8 text-center">
        <h1 className="text-lg font-semibold text-foreground">Accesso negato</h1>
        <p className="text-sm text-muted-foreground">Non hai accesso a questa sezione.</p>
        <Button asChild variant="outline">
          <Link to="/">Torna alla home</Link>
        </Button>
      </main>
    );
  }

  return (
    <div className="flex min-h-svh flex-col bg-background">
      <header className="sticky top-0 z-40 flex items-center justify-between gap-3 border-b border-border bg-background/85 px-4 py-3 backdrop-blur-md md:px-6">
        <div className="flex items-center gap-3">
          <Link to="/" aria-label="Renovio — home" className="rounded-md">
            <BrandMark />
          </Link>
          <Badge
            variant="secondary"
            className="border border-primary/20 bg-accent text-accent-foreground"
          >
            {user.role === "admin" ? "Admin" : "Consulente"}
          </Badge>
        </div>
        <AccountMenu user={user} />
      </header>

      {/* Mobile (<768px): tabs orizzontali al posto della sidebar */}
      <div className="border-b border-border px-4 py-2 md:hidden">
        <Tabs value={location.pathname}>
          <TabsList className="w-full overflow-x-auto">
            {navItems.map((item) => (
              <TabsTrigger key={item.path} value={item.path} asChild>
                <Link to={item.path}>{item.label}</Link>
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>

      <div className="flex flex-1 md:flex-row">
        {/* Desktop/tablet (>=768px): sidebar persistente */}
        <nav className="hidden w-64 shrink-0 flex-col gap-1 border-r border-border p-4 md:flex">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={cn(
                  "flex min-h-11 items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-semibold transition-colors",
                  isActive
                    ? "bg-accent text-accent-foreground"
                    : "text-foreground hover:bg-muted",
                )}
              >
                <Icon
                  className={cn("size-4", isActive ? "text-primary" : "text-muted-foreground")}
                />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="mx-auto w-full max-w-5xl flex-1 p-4 lg:p-6">{children}</div>
      </div>
    </div>
  );
}
