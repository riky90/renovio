import type { ReactNode } from "react";
import { Link, useLocation } from "react-router";
import {
  Inbox,
  Tags,
  SlidersHorizontal,
  MapPin,
  Users,
  type LucideIcon,
} from "lucide-react";
import { AccountMenu } from "@/components/AccountMenu";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/useAuth";

interface AdminNavItem {
  path: string;
  label: string;
  icon: LucideIcon;
}

const NAV_ITEMS: AdminNavItem[] = [
  { path: "/admin/lead", label: "Lead", icon: Inbox },
  { path: "/admin/listini", label: "Listini e prezzi", icon: Tags },
  { path: "/admin/coefficienti", label: "Coefficienti", icon: SlidersHorizontal },
  { path: "/admin/citta-testi", label: "Città e testi", icon: MapPin },
  { path: "/admin/referenti", label: "Referenti", icon: Users },
];

/**
 * Shell dell'area /admin (D-21, UI-SPEC §B): guard client-side role="admin"
 * PRIMA di ogni fetch (T-04-27) + sidebar (desktop) / tabs (mobile) sulle 5
 * sezioni. Il gate reale resta server-side (require_admin, 04-04) — questo
 * componente non fa mai fetch di dati admin prima del guard, così un
 * non-admin non vede mai un flash di dati reali.
 */
export function AdminLayout({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <main className="mx-auto flex min-h-svh w-full max-w-[480px] flex-col gap-4 px-4 py-8">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-64 w-full" />
      </main>
    );
  }

  if (!user || user.role !== "admin") {
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
      <header className="flex items-center justify-between gap-3 border-b border-border px-4 py-3 md:px-6">
        <div className="flex items-center gap-2">
          <span className="text-lg font-semibold text-foreground">ristruttura-stima</span>
          <Badge variant="secondary">Admin</Badge>
        </div>
        <AccountMenu user={user} />
      </header>

      {/* Mobile (<768px): tabs orizzontali al posto della sidebar */}
      <div className="border-b border-border px-4 py-2 md:hidden">
        <Tabs value={location.pathname}>
          <TabsList className="w-full overflow-x-auto">
            {NAV_ITEMS.map((item) => (
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
          {NAV_ITEMS.map((item) => {
            const isActive = location.pathname === item.path;
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={cn(
                  "flex min-h-11 items-center gap-2 rounded-md border-l-[3px] px-3 py-2 text-sm font-semibold transition-colors",
                  isActive
                    ? "border-l-primary text-primary"
                    : "border-l-transparent text-foreground hover:bg-muted",
                )}
              >
                <Icon className="size-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex-1 p-4 lg:p-6">{children}</div>
      </div>
    </div>
  );
}
