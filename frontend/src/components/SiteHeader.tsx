import { useEffect, useState } from "react";
import { Link, NavLink } from "react-router";
import { Menu } from "lucide-react";
import { BrandMark } from "@/components/BrandMark";
import { AccountMenu } from "@/components/AccountMenu";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import { PATH_GUIDE } from "@/content/guide";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/useAuth";

const VOCI = [
  { to: PATH_GUIDE, label: "Guide ai costi" },
  { to: "/supporto", label: "Domande frequenti" },
];

/**
 * Header di sito: brand, navigazione verso le guide e le FAQ, invito alla
 * stima e accesso/account. Su mobile la navigazione sta in un menu.
 */
export function SiteHeader() {
  const { user, isLoading } = useAuth();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <>
      <a
        href="#contenuto"
        className="sr-only z-50 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground focus:not-sr-only focus:fixed focus:left-4 focus:top-3"
      >
        Vai al contenuto
      </a>
      <header
        className={cn(
          "sticky top-0 z-40 border-b bg-background/80 backdrop-blur-md transition-shadow",
          scrolled ? "border-border shadow-sm" : "border-transparent",
        )}
      >
        <div className="mx-auto flex h-16 w-full max-w-5xl items-center justify-between gap-4 px-4 sm:px-6">
          <Link to="/" aria-label="Renovio — home" className="rounded-md">
            <BrandMark />
          </Link>

          <nav aria-label="Principale" className="hidden items-center gap-1 md:flex">
            {VOCI.map((v) => (
              <NavLink
                key={v.to}
                to={v.to}
                className={({ isActive }) =>
                  cn(
                    "rounded-md px-3 py-2 text-sm font-medium transition-colors hover:text-primary",
                    isActive ? "text-primary" : "text-foreground/80",
                  )
                }
              >
                {v.label}
              </NavLink>
            ))}
          </nav>

          <div className="flex items-center gap-2">
            <Button size="sm" asChild className="hidden sm:inline-flex">
              <Link to="/#stima">Calcola la stima</Link>
            </Button>
            {isLoading ? (
              <Skeleton className="size-9 rounded-full" />
            ) : user ? (
              <AccountMenu user={user} />
            ) : (
              <Button variant="outline" size="sm" asChild>
                <Link to="/accedi">Accedi</Link>
              </Button>
            )}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="md:hidden" aria-label="Apri il menu">
                  <Menu className="size-5" aria-hidden />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuItem asChild>
                  <Link to="/#stima">Calcola la stima</Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                {VOCI.map((v) => (
                  <DropdownMenuItem key={v.to} asChild>
                    <Link to={v.to}>{v.label}</Link>
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </header>
    </>
  );
}
