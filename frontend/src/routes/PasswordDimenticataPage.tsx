import { useState, type FormEvent } from "react";
import { Link } from "react-router";
import { useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { postPasswordDimenticata } from "@/api/auth";

const EMAIL_ERROR = "Inserisci un indirizzo email valido.";
const GENERIC_ERROR = "Non siamo riusciti a completare l'operazione. Riprova tra qualche istante.";
const CONFERMA_MESSAGE =
  "Ti abbiamo inviato un'email con le istruzioni per reimpostare la password.";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Richiesta reset password (D-04). Il backend risponde SEMPRE con lo stesso
 * 200 indipendentemente dall'esistenza dell'email (anti-enumeration,
 * T-06-01): la UI mostra sempre la stessa conferma amber e non deve mai
 * rivelare, con nessun ramo osservabile, se l'account esiste o meno.
 */
export function PasswordDimenticataPage() {
  const [email, setEmail] = useState("");
  const [touched, setTouched] = useState(false);
  const [inviata, setInviata] = useState(false);

  const emailValid = EMAIL_RE.test(email.trim());

  const richiedi = useMutation({
    mutationFn: () => postPasswordDimenticata({ email: email.trim() }),
    onSuccess: () => setInviata(true),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setTouched(true);
    if (!emailValid) return;
    richiedi.mutate();
  }

  return (
    <main className="mx-auto flex min-h-svh w-full max-w-[400px] flex-col justify-center gap-8 px-4 py-8">
      <div className="flex flex-col gap-6 rounded-lg border border-border bg-card p-6 shadow-xs">
        <h1 className="text-xl font-semibold text-foreground">Password dimenticata</h1>

        {inviata ? (
          <Alert className="border-amber-300 bg-amber-50 text-amber-800">
            <AlertDescription className="text-amber-800">{CONFERMA_MESSAGE}</AlertDescription>
          </Alert>
        ) : (
          <>
            {richiedi.isError && (
              <Alert variant="destructive">
                <AlertDescription>{GENERIC_ERROR}</AlertDescription>
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
                  onBlur={() => setTouched(true)}
                  aria-invalid={touched && !emailValid}
                />
                {touched && !emailValid && (
                  <p className="text-sm text-destructive">{EMAIL_ERROR}</p>
                )}
              </div>

              <Button
                type="submit"
                disabled={richiedi.isPending}
                className="h-11 w-full bg-primary text-base font-semibold text-primary-foreground hover:bg-primary/90"
              >
                {richiedi.isPending ? "Invio in corso..." : "Invia link di reset"}
              </Button>
            </form>
          </>
        )}

        <p className="text-center text-sm text-muted-foreground">
          <Link to="/accedi" className="font-medium text-primary underline-offset-4 hover:underline">
            Torna al login
          </Link>
        </p>
      </div>
    </main>
  );
}
