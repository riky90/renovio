import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { postSalvaStima, scaricaPdf, type StimaResponse } from "@/api/stima";
import { useAuth } from "@/hooks/useAuth";

const EMAIL_ERROR = "Inserisci un indirizzo email valido.";
const PASSWORD_ERROR = "La password deve avere almeno 8 caratteri.";
const CREDENZIALI_ERROR = "Email o password non corretti. Riprova.";
const PASSWORD_REIMPOSTATA_MESSAGE = "Password reimpostata. Accedi con la nuova password.";
const SAVE_CONFIRMATION = "Stima salvata nel tuo account.";
const PDF_ERROR = "Non siamo riusciti a generare il PDF. Riprova tra qualche istante.";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function googleLoginUrl(): string {
  const apiBase = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";
  return `${apiBase}/auth/google/login`;
}

export function AccediPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const intent = searchParams.get("intent");
  const passwordReimpostata = searchParams.get("password_reimpostata") === "1";
  const { login } = useAuth();

  const pendingStima =
    (location.state as { pendingStima?: StimaResponse } | null)?.pendingStima ?? null;

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [touched, setTouched] = useState<{ email?: boolean; password?: boolean }>({});
  const [postAuthState, setPostAuthState] = useState<"idle" | "saving" | "saved" | "error">(
    "idle"
  );

  const emailValid = EMAIL_RE.test(email.trim());
  const passwordValid = password.length >= 8;
  const formValid = emailValid && passwordValid;

  /**
   * Stesso gancio save-at-signup di RegistratiPage.tsx (D-07), applicato
   * anche al login: un utente gia' registrato che clicca "Salva"/"Scarica
   * PDF" da anonimo puo' scegliere di accedere invece di registrarsi.
   */
  async function handlePostLogin() {
    if (!intent || !pendingStima) {
      navigate("/");
      return;
    }

    setPostAuthState("saving");
    try {
      const { id } = await postSalvaStima(pendingStima);
      setPostAuthState("saved");
      if (intent.includes("download")) {
        await scaricaPdf(id);
      }
    } catch {
      setPostAuthState("error");
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setTouched({ email: true, password: true });
    if (!formValid) return;

    login.mutate(
      { email: email.trim(), password },
      {
        onSuccess: () => {
          void handlePostLogin();
        },
      }
    );
  }

  const showConfirmation = postAuthState !== "idle";

  return (
    <main className="mx-auto flex min-h-svh w-full max-w-[400px] flex-col justify-center gap-8 px-4 py-8">
      <div className="flex flex-col gap-6 rounded-lg border border-border bg-card p-6 shadow-xs">
        {showConfirmation ? (
          <>
            <h1 className="text-xl font-semibold text-foreground">
              {postAuthState === "saving" ? "Salvataggio in corso..." : SAVE_CONFIRMATION}
            </h1>
            {postAuthState === "error" && (
              <Alert variant="destructive">
                <AlertDescription>{PDF_ERROR}</AlertDescription>
              </Alert>
            )}
            {postAuthState !== "saving" && (
              <div className="flex flex-col gap-2">
                <Button asChild className="h-11 w-full bg-primary text-base font-semibold text-primary-foreground hover:bg-primary/90">
                  <Link to="/le-mie-stime">Vai a I miei progetti</Link>
                </Button>
                <Button asChild variant="outline" className="h-11 w-full">
                  <Link to="/">Nuova stima</Link>
                </Button>
              </div>
            )}
          </>
        ) : (
          <>
        <h1 className="text-xl font-semibold text-foreground">Accedi</h1>

        {passwordReimpostata && !login.isError && (
          <Alert className="border-amber-300 bg-amber-50 text-amber-800">
            <AlertDescription className="text-amber-800">
              {PASSWORD_REIMPOSTATA_MESSAGE}
            </AlertDescription>
          </Alert>
        )}

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
            state={pendingStima ? { pendingStima } : undefined}
            className="font-medium text-primary underline-offset-4 hover:underline"
          >
            Registrati
          </Link>
        </p>
          </>
        )}
      </div>
    </main>
  );
}
