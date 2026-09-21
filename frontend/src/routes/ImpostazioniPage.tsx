import { useState } from "react";
import { Link, Navigate, useNavigate, useParams, useSearchParams } from "react-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Check, Copy, CreditCard, Gift, Mail, Sparkles, User } from "lucide-react";
import { ProfileHeaderCard } from "@/components/ProfileHeaderCard";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { CityAutocomplete } from "@/components/CityAutocomplete";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AUTH_QUERY_KEY, useAuth } from "@/hooks/useAuth";
import { patchProfilo, type UserOut } from "@/api/auth";

/**
 * Le tre tab, nell'ordine in cui compaiono anche nel menu account. Lo slug e'
 * anche il segmento di URL: `/impostazioni/profilo`, `/impostazioni/abbonamento`,
 * `/impostazioni/invita`.
 */
const TAB_VALIDE = ["profilo", "abbonamento", "invita"] as const;

/** Vecchi slug da `?tab=`: solo "referral" ha cambiato nome diventando "invita". */
const TAB_LEGACY: Record<string, string> = { referral: "invita" };

/**
 * `/impostazioni` non ha una pagina propria: serve solo a raccogliere i link
 * vecchi in query string e a mandarli sul path giusto. Un `tab` non
 * riconosciuto arriva dalla barra degli indirizzi, quindi non e' fidato: ricade
 * su Profilo invece di produrre un URL rotto.
 */
export function ImpostazioniRedirect() {
  const [searchParams] = useSearchParams();
  const richiesto = searchParams.get("tab") ?? "";
  const slug = TAB_LEGACY[richiesto] ?? richiesto;
  const destinazione = (TAB_VALIDE as readonly string[]).includes(slug) ? slug : "profilo";
  return <Navigate to={`/impostazioni/${destinazione}`} replace />;
}

export function ImpostazioniPage() {
  const { user, isLoading } = useAuth();
  const { tab: tabParam } = useParams();
  const navigate = useNavigate();

  const tabValida = (TAB_VALIDE as readonly string[]).includes(tabParam ?? "");
  const tab = tabValida ? (tabParam as string) : "profilo";

  if (isLoading) {
    return (
      <PageShell>
        <div className="flex flex-col gap-6">
          <Skeleton className="h-9 w-48" />
          <Skeleton className="h-10 w-full max-w-md" />
          <Skeleton className="h-72 w-full rounded-xl" />
        </div>
      </PageShell>
    );
  }

  if (!user) {
    return <Navigate to="/accedi" replace />;
  }

  // Path inventato a mano: normalizza l'URL invece di mostrare Profilo sotto
  // un indirizzo che dice altro.
  if (!tabValida) {
    return <Navigate to="/impostazioni/profilo" replace />;
  }

  return (
    <PageShell>
      <header className="flex flex-col gap-1">
        <h1 className="text-3xl font-bold text-foreground">Profilo</h1>
        <p className="text-muted-foreground">Gestisci i tuoi dati, l'abbonamento e gli inviti.</p>
      </header>

      <Tabs
        value={tab}
        onValueChange={(value) => navigate(`/impostazioni/${value}`, { replace: true })}
        className="mt-8 gap-6"
      >
        {/* A tutta larghezza: e' la scelta principale della pagina, non un
            accessorio schiacciato a sinistra. I trigger hanno gia' `flex-1`,
            quindi si spartiscono la riga da soli. */}
        <TabsList className="w-full">
          <TabsTrigger value="profilo">
            <User className="size-4" /> Profilo
          </TabsTrigger>
          <TabsTrigger value="abbonamento">
            <CreditCard className="size-4" /> Abbonamento
          </TabsTrigger>
          <TabsTrigger value="invita">
            <Gift className="size-4" /> Invita un amico
          </TabsTrigger>
        </TabsList>

        <TabsContent value="profilo">
          <ProfiloTab user={user} />
        </TabsContent>
        <TabsContent value="abbonamento">
          <AbbonamentoTab user={user} />
        </TabsContent>
        <TabsContent value="invita">
          <ReferralTab nome={user.nome} />
        </TabsContent>
      </Tabs>
    </PageShell>
  );
}

function PageShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-svh flex-col bg-background">
      <SiteHeader />
      <main className="flex-1">
        <div className="mx-auto w-full max-w-3xl px-4 py-10 sm:px-6 sm:py-12">{children}</div>
      </main>
      <SiteFooter />
    </div>
  );
}

/* ---------------------------------------------------------------- Profilo */

function ProfiloTab({ user }: { user: UserOut }) {
  const queryClient = useQueryClient();
  const [nome, setNome] = useState(user.nome ?? "");
  const [cognome, setCognome] = useState(user.cognome ?? "");
  const [telefono, setTelefono] = useState(user.telefono ?? "");
  const [citta, setCitta] = useState(user.citta ?? "");

  const mutation = useMutation({
    mutationFn: patchProfilo,
    onSuccess: (updated) => {
      queryClient.setQueryData(AUTH_QUERY_KEY, updated);
      toast.success("Profilo aggiornato.");
    },
    onError: () => toast.error("Non siamo riusciti a salvare le modifiche. Riprova."),
  });

  const nomeValido = nome.trim().length > 0;
  const dirty =
    nome !== (user.nome ?? "") ||
    cognome !== (user.cognome ?? "") ||
    telefono !== (user.telefono ?? "") ||
    citta !== (user.citta ?? "");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!nomeValido) return;
    mutation.mutate({
      nome: nome.trim(),
      cognome: cognome.trim() || null,
      telefono: telefono.trim() || null,
      citta: citta.trim() || null,
    });
  }

  return (
    <div className="flex flex-col gap-6">
      <ProfileHeaderCard user={user} />
      <Card>
        <CardHeader>
          <CardTitle>I tuoi dati</CardTitle>
          <CardDescription>
            Usiamo questi dati per identificarti e per ricontattarti sulle tue stime.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
              <div className="flex flex-col gap-2">
                <Label htmlFor="nome">Nome</Label>
                <Input
                  id="nome"
                  value={nome}
                  onChange={(e) => setNome(e.target.value)}
                  aria-invalid={!nomeValido}
                  autoComplete="given-name"
                />
                {!nomeValido && <p className="text-sm text-destructive">Il nome è obbligatorio.</p>}
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="cognome">Cognome</Label>
                <Input
                  id="cognome"
                  value={cognome}
                  onChange={(e) => setCognome(e.target.value)}
                  autoComplete="family-name"
                />
              </div>
            </div>
    
            <div className="flex flex-col gap-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" value={user.email} readOnly disabled />
              <p className="text-sm text-muted-foreground">
                L'email di accesso non è modificabile da qui.
              </p>
            </div>
    
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
              <div className="flex flex-col gap-2">
                <Label htmlFor="telefono">Telefono</Label>
                <Input
                  id="telefono"
                  type="tel"
                  inputMode="tel"
                  placeholder="Es. 0522 123456"
                  value={telefono}
                  onChange={(e) => setTelefono(e.target.value)}
                  autoComplete="tel"
                />
              </div>
              <CityAutocomplete value={citta} onChange={setCitta} />
            </div>
    
            <div className="flex items-center gap-3 pt-1">
              <Button type="submit" disabled={!nomeValido || !dirty || mutation.isPending}>
                {mutation.isPending ? "Salvataggio..." : "Salva modifiche"}
              </Button>
              {!dirty && !mutation.isPending && (
                <span className="text-sm text-muted-foreground">Nessuna modifica da salvare.</span>
              )}
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

/* ------------------------------------------------------------ Abbonamento */

function AbbonamentoTab({ user }: { user: UserOut }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Il tuo piano</CardTitle>
        <CardDescription>Stato dell'abbonamento e vantaggi disponibili.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        <div className="flex items-center justify-between rounded-xl border border-border bg-secondary/40 px-5 py-4">
          <div className="flex flex-col gap-0.5">
            <span className="text-sm text-muted-foreground">Piano attuale</span>
            <span className="font-display text-xl font-bold text-foreground">
              {user.pro ? "Pro" : "Free"}
            </span>
          </div>
          {user.pro ? (
            <Badge className="gap-1 bg-primary text-primary-foreground">
              <Sparkles className="size-3.5" /> Attivo
            </Badge>
          ) : (
            <Badge variant="secondary">Gratuito</Badge>
          )}
        </div>

        {user.pro ? (
          <p className="text-sm text-muted-foreground">
            Il tuo abbonamento Pro è attivo: hai accesso al dettaglio voce per voce di ogni stima.
          </p>
        ) : (
          <div className="flex flex-col gap-4">
            <ul className="flex flex-col gap-2 text-sm text-foreground">
              <li className="flex items-start gap-2">
                <Sparkles className="mt-0.5 size-4 shrink-0 text-primary" />
                Dettaglio voce per voce di ogni categoria di lavori.
              </li>
              <li className="flex items-start gap-2">
                <Sparkles className="mt-0.5 size-4 shrink-0 text-primary" />
                Report e preventivi da condividere con i clienti.
              </li>
            </ul>
            <div>
              <Button asChild>
                <Link to="/passa-a-pro">Passa a Pro</Link>
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/* --------------------------------------------------------------- Referral */

function ReferralTab({ nome }: { nome: string }) {
  const [copied, setCopied] = useState(false);
  const link = typeof window !== "undefined" ? window.location.origin : "https://renovio.it";
  const messaggio =
    `Ciao! Sto usando Renovio per farmi un'idea dei costi di ristrutturazione — ` +
    `stima gratuita, a range, senza registrazione. Dai un'occhiata: ${link}`;

  async function copiaLink() {
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
      toast.success("Link copiato.");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Non siamo riusciti a copiare il link.");
    }
  }

  const whatsappHref = `https://wa.me/?text=${encodeURIComponent(messaggio)}`;
  const mailHref =
    `mailto:?subject=${encodeURIComponent("Un'idea per la tua ristrutturazione")}` +
    `&body=${encodeURIComponent(messaggio)}`;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Invita un amico</CardTitle>
        <CardDescription>
          Conosci qualcuno che sta per ristrutturare? Passagli Renovio: una stima onesta in
          trenta secondi, gratis.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <div className="flex flex-col gap-2">
          <Label htmlFor="referral-link">Il tuo link da condividere</Label>
          <div className="flex flex-col gap-2 sm:flex-row">
            <Input id="referral-link" value={link} readOnly className="font-mono text-sm" />
            <Button type="button" variant="outline" onClick={copiaLink} className="shrink-0">
              {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
              {copied ? "Copiato" : "Copia link"}
            </Button>
          </div>
        </div>

        <div className="flex flex-col gap-2 sm:flex-row">
          <Button asChild className="flex-1">
            <a href={whatsappHref} target="_blank" rel="noopener noreferrer">
              <Gift className="size-4" /> Condividi su WhatsApp
            </a>
          </Button>
          <Button asChild variant="outline" className="flex-1">
            <a href={mailHref}>
              <Mail className="size-4" /> Invita via email
            </a>
          </Button>
        </div>

        <p className="text-sm text-muted-foreground">
          Grazie {nome.split(/\s+/)[0]}: ogni persona che aiuti a partire con il piede giusto è un
          passaparola che conta.
        </p>
      </CardContent>
    </Card>
  );
}
