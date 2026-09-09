import { apiDelete, apiGet, apiPatch, apiPost, apiPostFile, ApiError } from "@/api/client";

export type UserRole = "user" | "consulente" | "admin";

export interface UserOut {
  id: number;
  email: string;
  nome: string;
  cognome: string | null;
  telefono: string | null;
  citta: string | null;
  /**
   * URL pubblico dell'avatar su object storage, o null. SOLA LETTURA: si
   * cambia con postAvatar/deleteAvatar, mai da patchProfilo — il backend non
   * accetta questo campo su PATCH /auth/me.
   */
  avatar_url: string | null;
  role: UserRole;
  /** Stato Pro derivato server-side dalla tessera abbonamento; mai scrivibile dal client. */
  pro: boolean;
  created_at: string;
}

export interface ProfiloUpdateInput {
  nome: string;
  cognome?: string | null;
  telefono?: string | null;
  citta?: string | null;
}

export interface RegistrazioneInput {
  nome: string;
  email: string;
  password: string;
}

export interface LoginInput {
  email: string;
  password: string;
}

export interface PasswordDimenticataInput {
  email: string;
}

export interface ReimpostaPasswordInput {
  token: string;
  password: string;
}

/**
 * POST /auth/registrati — crea l'account e imposta il cookie httpOnly di
 * sessione sulla risposta (credentials:"include" via apiPost).
 */
export async function postRegistrazione(input: RegistrazioneInput): Promise<UserOut> {
  return apiPost<UserOut>("/auth/registrati", input);
}

/**
 * POST /auth/login — verifica le credenziali e imposta il cookie httpOnly
 * di sessione. Il backend risponde con lo stesso messaggio generico sia per
 * email inesistente sia per password errata (anti-enumeration).
 */
export async function postLogin(input: LoginInput): Promise<UserOut> {
  return apiPost<UserOut>("/auth/login", input);
}

/**
 * POST /auth/logout — revoca la sessione server-side (204 No Content).
 */
export async function postLogout(): Promise<void> {
  await apiPost<undefined>("/auth/logout", undefined);
}

/**
 * GET /auth/me — sessione corrente. Un 401 significa "non autenticato": va
 * trattato come stato normale (utente anonimo), non come errore rumoroso.
 */
export async function getMe(): Promise<UserOut | null> {
  try {
    return await apiGet<UserOut>("/auth/me");
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return null;
    }
    throw error;
  }
}

/**
 * POST /auth/password-dimenticata — richiede il link di reset. Il backend
 * risponde sempre con lo stesso 200, che l'email esista o meno
 * (anti-enumeration): la UI mostra sempre la stessa conferma.
 */
export async function postPasswordDimenticata(input: PasswordDimenticataInput): Promise<void> {
  await apiPost<{ detail: string }>("/auth/password-dimenticata", input);
}

/**
 * POST /auth/reimposta-password — imposta la nuova password a partire dal
 * token ricevuto via email. 400 se il token e' invalido/scaduto/gia' usato.
 */
export async function postReimpostaPassword(input: ReimpostaPasswordInput): Promise<void> {
  await apiPost<{ detail: string }>("/auth/reimposta-password", input);
}

/**
 * PATCH /auth/me — aggiorna i dati profilo dell'utente corrente
 * (nome/cognome/telefono/città). email/role/pro non sono modificabili qui.
 */
export async function patchProfilo(input: ProfiloUpdateInput): Promise<UserOut> {
  return apiPatch<UserOut>("/auth/me", input);
}

/**
 * POST /auth/me/avatar — carica la foto profilo (multipart). Il backend
 * valida, ridimensiona e ri-encodifica in WEBP, e risponde con lo `UserOut`
 * aggiornato. 400 = immagine rifiutata, 503 = storage non configurato: in
 * entrambi i casi `ApiError.message` porta il messaggio del backend, da
 * mostrare all'utente cosi' com'e'.
 */
export async function postAvatar(file: File): Promise<UserOut> {
  return apiPostFile<UserOut>("/auth/me/avatar", file);
}

/** DELETE /auth/me/avatar — rimuove la foto profilo. */
export async function deleteAvatar(): Promise<UserOut> {
  return apiDelete<UserOut>("/auth/me/avatar");
}
