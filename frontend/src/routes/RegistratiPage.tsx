import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { ApiError } from "@/api/client";
import { postSalvaStima, scaricaPdf, type StimaResponse } from "@/api/stima";
import { useAuth } from "@/hooks/useAuth";

const SAVE_CONFIRMATION = "Stima salvata nel tuo account.";
const PDF_ERROR = "Non siamo riusciti a generare il PDF. Riprova tra qualche istante.";

const NOME_ERROR = "Inserisci il tuo nome.";
const EMAIL_ERROR = "Inserisci un indirizzo email valido.";
const PASSWORD_ERROR = "La password deve avere almeno 8 caratteri.";
const EMAIL_ESISTENTE_ERROR =
  "Esiste già un account con questa email. Accedi oppure recupera la password.";
const GENERIC_ERROR = "Non siamo riusciti a completare l'operazione. Riprova tra qualche istante.";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function googleLoginUrl(): string {
  const apiBase = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";
  return `${apiBase}/auth/google/login`;
}

export function RegistratiPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const intent = searchParams.get("intent");
  const { registrazione } = useAuth();

  const pendingStima =
    (location.state as { pendingStima?: StimaResponse } | null)?.pendingStima ?? null;

  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [touched, setTouched] = useState<{ nome?: boolean; email?: boolean; password?: boolean }>(
    {}
  );
  const [postAuthState, setPostAuthState] = useState<"idle" | "saving" | "saved" | "error">(
    "idle"
  );

  const nomeValid = nome.trim().length > 0;
  const emailValid = EMAIL_RE.test(email.trim());
  const passwordValid = password.length >= 8;
  const formValid = nomeValid && emailValid && passwordValid;

  const heading = intent ? "Crea account e salva la stima" : "Crea il tuo account";

  /**
   * Save-at-signup (D-07): dopo la registrazione, se l'intent include
   * "save", congela esattamente il payload gia' mostrato (nessuna chiamata
   * a POST /api/v1/stima, nessun ricalcolo — D-09). Se l'intent include
   * "download", avvia subito il download del PDF appena salvato.
   */
  async function handlePostRegistrazione() {
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
    setTouched({ nome: true, email: true, password: true });
    if (!formValid) return;

    registrazione.mutate(
      { nome: nome.trim(), email: email.trim(), password },
      {
        onSuccess: () => {
          void handlePostRegistrazione();
        },
      }
    );
  }

  const errorMessage =
    registrazione.isError &&
    (registrazione.error instanceof ApiError && registrazione.error.status === 409
      ? EMAIL_ESISTENTE_ERROR
      : GENERIC_ERROR);

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
                  <Link to="/le-mie-stime">Vai a Le mie stime</Link>
                </Button>
                <Button asChild variant="outline" className="h-11 w-full">
                  <Link to="/">Nuova stima</Link>
                </Button>
              </div>
            )}
          </>
        ) : (
          <>
            <h1 className="text-xl font-semibold text-foreground">{heading}</h1>

            {errorMessage && (
              <Alert variant="destructive">
                <AlertDescription>{errorMessage}</AlertDescription>
              </Alert>
            )}

            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="nome">Nome</Label>
                <Input
                  id="nome"
                  value={nome}
                  onChange={(e) => setNome(e.target.value)}
                  onBlur={() => setTouched((t) => ({ ...t, nome: true }))}
                  aria-invalid={touched.nome && !nomeValid}
                />
                {touched.nome && !nomeValid && (
                  <p className="text-sm text-destructive">{NOME_ERROR}</p>
                )}
              </div>

              <div className="flex flex-col gap-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
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
                <Label htmlFor="password">Password</Label>
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
                disabled={registrazione.isPending}
                className="h-11 w-full bg-primary text-base font-semibold text-primary-foreground hover:bg-primary/90"
              >
                {registrazione.isPending ? "Creazione in corso..." : "Crea account"}
              </Button>
            </form>

            <div className="flex items-center gap-3">
              <Separator className="flex-1" />
              <span className="text-sm text-muted-foreground">oppure</span>
              <Separator className="flex-1" />
            </div>

            <Button variant="outline" className="h-11 w-full" asChild>
              <a href={googleLoginUrl()}>Continua con Google</a>
            </Button>

            <p className="text-center text-sm text-muted-foreground">
              Hai già un account?{" "}
              <Link
                to={intent ? `/accedi?intent=${intent}` : "/accedi"}
                state={pendingStima ? { pendingStima } : undefined}
                className="font-medium text-primary underline-offset-4 hover:underline"
              >
                Accedi
              </Link>
            </p>
          </>
        )}
      </div>
    </main>
  );
}
