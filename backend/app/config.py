"""Application configuration loaded from environment variables (.env).

12-factor style config via pydantic-settings. Phase 1 needed only
DATABASE_URL/CORS_ORIGINS (see 01-RESEARCH.md); Phase 2 (see 02-RESEARCH.md)
adds auth/session, OAuth, transactional email and PDF-related settings.

Secrets (SECRET_KEY, OAUTH_SESSION_SECRET, SMTP_PASSWORD, GOOGLE_CLIENT_SECRET)
default to empty string and must be provided via .env in every real
environment — no real secret is ever hardcoded here. See backend/.env.example
for how to generate them locally.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "sqlite:///./dev.db"
    CORS_ORIGINS: str = "http://localhost:5173"

    # Auth / session (AUTH-01..04)
    # Firma i token itsdangerous (es. reset password). Nessun default reale:
    # generare con `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
    SECRET_KEY: str = ""
    # Segreto DEDICATO per lo Starlette SessionMiddleware usato da Authlib
    # (flusso OAuth state/PKCE) — DEVE restare distinto da SECRET_KEY per
    # evitare cookie-clobbering tra sessione OAuth e sessione applicativa
    # (02-RESEARCH.md Pitfall 1). Generare allo stesso modo di SECRET_KEY.
    OAUTH_SESSION_SECRET: str = ""
    # True in produzione dietro HTTPS (cookie Secure); False in dev locale su http.
    COOKIE_SECURE: bool = False

    # Google OAuth (AUTH-02)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # Email transazionale (reset password D-04, riusata dai lead in Fase 4)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""

    # URL pubblico del frontend (link nelle email, redirect post-login Google)
    FRONTEND_URL: str = "http://localhost:5173"

    # Email del primo admin, promosso a role="admin" da seed/bootstrap (D-03)
    ADMIN_EMAIL: str = ""

    # Object storage S3-compatibile (Cloudflare R2) per gli avatar profilo.
    # Tutti default "" come SMTP/SECRET_KEY: senza credenziali l'app resta
    # importabile e l'endpoint avatar risponde 503, mai un 500.
    R2_ENDPOINT_URL: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET: str = ""
    # Base URL pubblica del bucket (dominio r2.dev o custom domain), senza
    # slash finale: e' il prefisso di `User.avatar_url`.
    R2_PUBLIC_BASE_URL: str = ""

    @property
    def storage_configured(self) -> bool:
        """True solo se TUTTI e cinque i valori sono presenti: una config a
        meta' e' indistinguibile da nessuna config, e fallire al primo upload
        con un 500 di boto3 sarebbe peggio di un 503 esplicito."""
        return all(
            [
                self.R2_ENDPOINT_URL,
                self.R2_ACCESS_KEY_ID,
                self.R2_SECRET_ACCESS_KEY,
                self.R2_BUCKET,
                self.R2_PUBLIC_BASE_URL,
            ]
        )

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
