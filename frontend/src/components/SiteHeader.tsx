import { useEffect, useState } from "react";
import { Link } from "react-router";
import { BrandMark } from "@/components/BrandMark";
import { AccountMenu } from "@/components/AccountMenu";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/useAuth";

/** Header di sito: brand a sinistra, accesso/account a destra. Ombra al scroll. */
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
    <header
      className={cn(
        "sticky top-0 z-40 border-b bg-background/80 backdrop-blur-md transition-shadow",
        scrolled ? "border-border shadow-sm" : "border-transparent",
      )}
    >
      <div className="mx-auto flex h-16 w-full max-w-5xl items-center justify-between px-4 sm:px-6">
        <Link to="/" aria-label="Renovio — home" className="rounded-md">
          <BrandMark />
        </Link>
        {isLoading ? (
          <Skeleton className="size-9 rounded-full" />
        ) : user ? (
          <AccountMenu user={user} />
        ) : (
          <Button variant="outline" size="sm" asChild>
            <Link to="/accedi">Accedi</Link>
          </Button>
        )}
      </div>
    </header>
  );
}
