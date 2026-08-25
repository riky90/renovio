import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useAuth } from "@/hooks/useAuth";

const EMAIL_ERROR = "Inserisci un indirizzo email valido.";
const PASSWORD_ERROR = "La password deve avere almeno 8 caratteri.";
const CREDENZIALI_ERROR = "Email o password non corretti. Riprova.";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function googleLoginUrl(): string {
  const apiBase = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";
  return `${apiBase}/auth/google/login`;
}

export function AccediPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const intent = searchParams.get("intent");
  const { login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [touched, setTouched] = useState<{ email?: boolean; password?: boolean }>({});

  const emailValid = EMAIL_RE.test(email.trim());
  const passwordValid = password.length >= 8;
  const formValid = emailValid && passwordValid;

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setTouched({ email: true, password: true });
    if (!formValid) return;

    login.mutate(
      { email: email.trim(), password },
      {
        onSuccess: () => navigate("/"),
      }
    );
  }

  return (
    <main className="mx-auto flex min-h-svh w-full max-w-[400px] flex-col justify-center gap-8 px-4 py-8">
      <div className="flex flex-col gap-6 rounded-lg border border-border bg-card p-6 shadow-xs">
        <h1 className="text-xl font-semibold text-foreground">Accedi</h1>

        {login.isError && (
          <Alert variant="destructive">
            <AlertDescription>{CREDENZIALI_ERROR}</AlertDescription>
          </Alert>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onBlur={() => setTouched((t) => ({ ...t, email: true }))}
              aria-invalid={touched.email && !emailValid}
            />
            {touched.email && !emailValid && (
              <p className="text-sm text-destructive">{EMAIL_ERROR}</p>
            )}
          </div>

          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="password">Password</Label>
              <Link
                to="/password-dimenticata"
                className="text-sm font-medium text-primary underline-offset-4 hover:underline"
              >
                Password dimenticata?
              </Link>
            </div>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onBlur={() => setTouched((t) => ({ ...t, password: true }))}
              aria-invalid={touched.password && !passwordValid}
            />
            {touched.password && !passwordValid && (
              <p className="text-sm text-destructive">{PASSWORD_ERROR}</p>
            )}
          </div>

          <Button
            type="submit"
            disabled={login.isPending}
            className="h-11 w-full bg-primary text-base font-semibold text-primary-foreground hover:bg-primary/90"
          >
            {login.isPending ? "Accesso in corso..." : "Accedi"}
          </Button>
        </form>

        <div className="flex items-center gap-3">
          <Separator className="flex-1" />
          <span className="text-sm text-muted-foreground">oppure</span>
          <Separator className="flex-1" />
        </div>

        <Button variant="outline" className="h-11 w-full" asChild>
          <a href={googleLoginUrl()}>Accedi con Google</a>
        </Button>

        <p className="text-center text-sm text-muted-foreground">
          Non hai un account?{" "}
          <Link
            to={intent ? `/registrati?intent=${intent}` : "/registrati"}
            className="font-medium text-primary underline-offset-4 hover:underline"
          >
            Registrati
          </Link>
        </p>
      </div>
    </main>
  );
}
