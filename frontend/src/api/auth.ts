import { apiGet, apiPost, ApiError } from "@/api/client";

export type UserRole = "user" | "admin";

export interface UserOut {
  id: number;
  email: string;
  nome: string;
  role: UserRole;
  created_at: string;
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
