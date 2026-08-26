import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { useMutation } from "@tanstack/react-query";
import { Eye, EyeOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from "@/components/ui/input-group";
import { postReimpostaPassword } from "@/api/auth";

const PASSWORD_ERROR = "La password deve avere almeno 8 caratteri.";
const TOKEN_INVALIDO_MESSAGE = "Il link non e' piu' valido. Richiedine uno nuovo.";
const GENERIC_ERROR = "Non siamo riusciti a completare l'operazione. Riprova tra qualche istante.";

/**
 * Conferma reset password (D-04). Legge `token` dai query param; il token
 * invalido/scaduto/gia' usato non mostra il form — solo l'alert destructive
 * con link per richiederne uno nuovo (nessun tentativo di sottomissione
 * possibile su un link gia' morto).
 */
export function ReimpostaPasswordPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");

  const [password, setPassword] = useState("");
  const [touched, setTouched] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const passwordValid = password.length >= 8;

  const reimposta = useMutation({
    mutationFn: () => postReimpostaPassword({ token: token ?? "", password }),
    onSuccess: () => navigate("/accedi?password_reimpostata=1"),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setTouched(true);
    if (!passwordValid || !token) return;
    reimposta.mutate();
  }

  const tokenInvalido = !token || reimposta.isError;

  return (
    <main className="mx-auto flex min-h-svh w-full max-w-[400px] flex-col justify-center gap-8 px-4 py-8">
      <div className="flex flex-col gap-6 rounded-lg border border-border bg-card p-6 shadow-xs">
        <h1 className="text-xl font-semibold text-foreground">Reimposta la password</h1>

        {tokenInvalido ? (
          <>
            <Alert variant="destructive">
              <AlertDescription>{token ? GENERIC_ERROR : TOKEN_INVALIDO_MESSAGE}</AlertDescription>
            </Alert>
            {token && reimposta.isError && (
              <p className="text-sm text-destructive">{TOKEN_INVALIDO_MESSAGE}</p>
            )}
            <p className="text-center text-sm text-muted-foreground">
              <Link
                to="/password-dimenticata"
                className="font-medium text-primary underline-offset-4 hover:underline"
              >
                Richiedi un nuovo link
              </Link>
            </p>
          </>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="password">Nuova password</Label>
              <InputGroup>
                <InputGroupInput
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoFocus
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onBlur={() => setTouched(true)}
                  aria-invalid={touched && !passwordValid}
                />
                <InputGroupAddon align="inline-end">
                  <InputGroupButton
                    aria-label={showPassword ? "Nascondi password" : "Mostra password"}
                    onClick={() => setShowPassword((v) => !v)}
                  >
                    {showPassword ? <EyeOff /> : <Eye />}
                  </InputGroupButton>
                </InputGroupAddon>
              </InputGroup>
              {touched && !passwordValid && (
                <p className="text-sm text-destructive">{PASSWORD_ERROR}</p>
              )}
            </div>

            <Button
              type="submit"
              disabled={reimposta.isPending}
              className="h-11 w-full bg-primary text-base font-semibold text-primary-foreground hover:bg-primary/90"
            >
              {reimposta.isPending ? "Aggiornamento in corso..." : "Imposta nuova password"}
            </Button>
          </form>
        )}
      </div>
    </main>
  );
}
