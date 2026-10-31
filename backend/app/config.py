"""Application configuration loaded from environment variables (.env).

12-factor style config via pydantic-settings. Phase 1 needed only
DATABASE_URL/CORS_ORIGINS (see 01-RESEARCH.md); Phase 2 (see 02-RESEARCH.md)
adds auth/session, OAuth, transactional email and PDF-related settings.

Secrets (SECRET_KEY, OAUTH_SESSION_SECRET, SMTP_PASSWORD, GOOGLE_CLIENT_SECRET)
default to empty string and must be provided via .env in every real
environment — no real secret is ever hardcoded here. See backend/.env.example
for how to generate them locally.
"""

from pydantic import field_validator
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

    # URL pubblico di QUESTO backend, senza slash finale. Serve solo al
    # backend di storage "db": un avatar servito da noi ha bisogno di un URL
    # assoluto in `User.avatar_url`, perche' quel campo finisce in un `<img
    # src>` renderizzato dal frontend, che gira su un'altra origine.
    BACKEND_PUBLIC_URL: str = "http://localhost:8000"

    # Pagamenti Pro con Stripe (abbonamento mensile e annuale). Senza
    # STRIPE_SECRET_KEY i pagamenti sono spenti: la pagina "Passa a Pro" usa
    # l'attivazione dimostrativa gratuita, che si spegne da sola appena la
    # chiave c'e'. Chiavi di test (`sk_test_...`) e live (`sk_live_...`)
    # vanno solo nelle variabili d'ambiente, mai nel codice.
    STRIPE_SECRET_KEY: str = ""
    # Segreto di firma del webhook (`whsec_...`), dalla pagina del webhook.
    STRIPE_WEBHOOK_SECRET: str = ""
    # I prezzi si cercano per `lookup_key`: importi e valuta stanno solo su
    # Stripe, e cambiarli non richiede un deploy.
    STRIPE_LOOKUP_KEY_MENSILE: str = "renovio_pro_mensile"
    STRIPE_LOOKUP_KEY_ANNUALE: str = "renovio_pro_annuale"

    @field_validator("DATABASE_URL")
    @classmethod
    def _use_psycopg3(cls, url: str) -> str:
        """Instrada gli URL Postgres "nudi" su psycopg 3.

        I provider (Neon, Render, Supabase) danno `postgresql://` o
        `postgres://`, che SQLAlchemy risolverebbe su psycopg2 — non
        installato. Riscrivere qui permette di incollare la stringa del
        provider cosi' com'e', e vale anche per Alembic, che legge da qui.
        """
        for prefix in ("postgresql://", "postgres://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix):]
        return url

    @property
    def storage_configured(self) -> bool:
        """True solo se TUTTI e cinque i valori R2 sono presenti: una config a
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
    def storage_backend(self) -> str:
        """Quale backend serve gli avatar: `"r2"` o `"db"`.

        R2 ha la precedenza quando e' configurato per intero — e' la strada
        maestra, serve le immagini da una CDN e non appesantisce il database.
        Senza R2 si usa `avatar_blob`, che e' l'unico posto durevole che l'app
        ha gia': il filesystem di Render e' effimero.

        Non esiste piu' uno stato "nessuno storage": la proprieta' ritorna
        sempre un backend funzionante, ed e' per questo che l'upload avatar ha
        smesso di rispondere 503. `StorageNotConfigured` resta nel codice
        perche' il backend "db" puo' comunque fallire il suo prerequisito
        (vedi `services/storage_service.py`).
        """
        return "r2" if self.storage_configured else "db"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
