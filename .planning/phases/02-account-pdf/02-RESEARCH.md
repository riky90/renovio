# Phase 2: Account & PDF - Research

**Researched:** 2026-08-25
**Domain:** Auth self-hosted (FastAPI + Postgres) con OAuth Google, sessione cookie httpOnly, snapshot immutabile, PDF server-side
**Confidence:** MEDIUM (stack chiaro e verificato su registry; alcune scelte di libreria [ASSUMED] perché slopcheck non ha potuto verificare in questa sessione — vedi Package Legitimacy Audit)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Strategia auth & sessione (AUTH-01/02/03/04)**
- **D-01:** Auth self-hosted nel backend FastAPI. Tabella `user` nel Postgres del progetto. Password con hashing forte (bcrypt/argon2), Google OAuth via Authlib. Motivo: tutti i dati (utenti, stime, futuri lead/referenti di Fase 4) in un solo DB, nessun lock-in né costo, controllo totale sull'invariante anti-leak impresa. Niente provider gestito (Supabase/Auth0/Clerk).
- **D-02:** Sessione via cookie httpOnly (JWT o session id in cookie httpOnly + SameSite), invisibile al JS del frontend. Immune al furto via XSS, logout server-side pulito, il frontend non maneggia token. Standard per SPA + API sullo stesso deploy/dominio.
- **D-03:** Ruolo su `user` con valori `user` / `admin` (AUTH-04). Il primo admin è promosso via seed o variabile d'ambiente (es. `ADMIN_EMAIL`). In Fase 2 il ruolo esiste e le route riservate sono protette; nessuna interfaccia admin ancora (Fase 4).
- **D-04:** Verifica email: NO in v1 (attrito minimo alla registrazione). Reset password: SÌ via link email. Serve un'utility di email transazionale già in Fase 2 (SMTP/provider) — sarà riusata dai lead in Fase 4. Motivo: senza reset, una password dimenticata = account bloccato, e Google non è un percorso di recupero garantito.
- **D-05:** Un solo account per email (l'email è la chiave identità). Se la stessa email arriva sia da password sia da "Accedi con Google", confluisce nello stesso account (l'email di Google è già verificata da Google), con possibilità di aggiungere la password in seguito. Nessun doppione, nessun blocco.
- **D-06:** Campi registrazione: email + password + nome. Il nome serve al PDF brandizzato e al lead (Fase 4); chiederlo ora evita una migrazione dopo. (Un campo `nome`, eventuale cognome opzionale.)

**Salvataggio stima ↔ account (onora D-10 della Fase 1)**
- **D-07:** Salva-al-signup della stima corrente. L'utente fa la stima da anonimo (tenuta nel browser); quando si registra/accede da una CTA soft-wall, quella stima viene salvata e associata al nuovo account. Poi, da loggato, ogni nuova stima si salva automaticamente. Nessuna persistenza anonima con "reclamo" successivo, nessuna riga anonima da gestire/pulire.

**Storico stime & snapshot (data model `stima`)**
- **D-08:** Storico "Le mie stime": ogni stima salvata resta in una lista consultabile (città, mq, tipo, data, totale). Basso costo, utile per rientrare su una stima, e la Fase 3 (upgrade Pro su una stima) ci si appoggia.
- **D-09:** Snapshot — numeri congelati. Al salvataggio si congelano input + risultato completo (i 4 range di categoria, totale, IVA, disclaimer/fallback) come snapshot immutabile. Una stima salvata non cambia mai, anche quando l'admin aggiornerà i listini (Fase 4): è riproducibile, difendibile legalmente e coerente col PDF scaricato. Si conservano anche gli input per un eventuale ricalcolo Pro esplicito.

**PDF Free (PDF-01)**
- **D-10:** Gate: solo utente loggato. Il PDF è dietro l'account, coerente con la soft-wall già scelta in Fase 1 (D-09/D-10): "Scarica PDF" è una delle ragioni per registrarsi e rafforza il funnel. Da anonimo la CTA porta alla registrazione, poi il download.
- **D-11:** Generazione server-side (FastAPI, es. WeasyPrint/reportlab) a partire dallo snapshot salvato. Anti-leak garantito lato server (mai coefficiente/prezzo impresa nel PDF), branding coerente, e stesso motore riusabile per il PDF dettagliato Pro (Fase 3). Niente generazione client-side.
- **D-12:** Contenuto PDF (1 pagina): intestazione con branding + nome utente; riepilogo input (città, mq, tipo); le 4 card di categoria a range; totale IVA inclusa; disclaimer (incl. disclaimer fallback città se attivo); data della stima + nota "stima indicativa". Nome file tipo `stima-ristrutturazione-<citta>-<data>.pdf`. Mai dati impresa.

**Regole di dominio (portate avanti — non ri-discusse)**
- **D-13:** L'invariante anti-leak vale anche qui: `coefficiente_impresa`/`base_eur_mq`/moltiplicatori/`prezzo_impresa` restano server-side e non compaiono in risposta API, nello snapshot esposto al client, né nel PDF.
- **D-14:** L'output resta sempre a range (categorie e totale), anche nello snapshot e nel PDF.

### Claude's Discretion

- Scelta esatta della libreria auth/OAuth (Authlib vs alternative), della libreria PDF (WeasyPrint vs reportlab vs template HTML→PDF) e del provider email transazionale — delegata a researcher/planner, purché rispetti D-01..D-12.
- Struttura precisa dello snapshot (colonne dedicate vs JSON) e schema di `user`/`stima`, purché: snapshot immutabile, storico per utente, anti-leak, e predisposizione all'upgrade Pro (Fase 3) e ai lead (Fase 4).
- Asset di branding del PDF (logo/colori): base = palette Slate/blue-600 già definita in `01-UI-SPEC.md`; placeholder logo accettabile se non fornito.
- Meccanica UI del gate soft-wall → registrazione → download (modale vs pagina), coerente con `SoftWallCta` esistente.

### Deferred Ideas (OUT OF SCOPE)

- Apertura sottocategorie Pro + paywall + PDF dettagliato → Fase 3 (lo snapshot conserva gli input proprio per abilitare l'upgrade Pro).
- Invio lead / contatto professionista + pannello admin CRUD (listini, coefficienti, città, referenti, testi) → Fase 4. Qui nascono solo il ruolo admin e l'utility email (riusata dai lead).
- Verifica email obbligatoria → eventuale hardening post-v1 (in v1 esclusa per attrito).
- Gestione pagamenti / prezzo abbonamento Pro → Fase 3 / post-v1.
- Moltiplicatori prezzo per zona geografica → fase di prodotto post-v1.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-------------------|
| AUTH-01 | L'utente può registrarsi con email e password | Pattern 1 (sessione), Code Examples (argon2-cffi hash/verify), Standard Stack (argon2-cffi) |
| AUTH-02 | L'utente può accedere con Google (OAuth) | Pattern 2 (Authlib + SessionMiddleware isolato), Pitfall 1, Open Question 3 (credenziali Google Cloud) |
| AUTH-03 | L'utente resta autenticato tra le sessioni e può fare logout | Pattern 1 (sessione DB-backed `user_session`), Pitfall 4 (cookie cross-origin dev), Security Domain V3 |
| AUTH-04 | Esiste un ruolo admin distinto dall'utente finale | Pattern 1 (`require_admin` dependency), Security Domain V4 |
| PDF-01 | L'utente Free può scaricare un PDF sintetico brandizzato della stima | Standard Stack (WeasyPrint+Jinja2), Pattern 3 (snapshot ibrido come sorgente), Pitfall 3 (WeasyPrint su Windows dev), Pitfall 5 (mai ricalcolare), Code Examples (render_pdf) |
</phase_requirements>

## Summary

La Fase 2 aggiunge auth self-hosted, storico stime con snapshot immutabile e PDF server-side sopra uno stack già collaudato in Fase 1 (FastAPI + SQLAlchemy 2.0 + Alembic + Postgres/SQLite-dev; React 19 + Vite + react-query + Tailwind/shadcn). Nessuna di queste feature esiste ancora nel codice: 0 router auth, 0 modelli `User`/`Stima`, 0 router client-side (SPA a singola pagina oggi).

Le aree davvero rischiose sono tre. Primo, la **sessione**: D-02 lascia scegliere JWT vs session-id in cookie httpOnly, ma D-02 chiede anche "logout server-side pulito" — un JWT stateless non si può revocare senza una blocklist, quindi la raccomandazione è una **sessione opaca in DB** (tabella `user_session`, id casuale in cookie httpOnly, nessuna libreria JWT necessaria per la sessione). Secondo, **Authlib + Google OAuth** richiede `SessionMiddleware` di Starlette per lo scambio state/PKCE — una sessione *diversa* dal cookie di sessione applicativo, e le due vanno tenute ben distinte per non confondersi (pitfall #1). Terzo, **WeasyPrint** (scelto per fedeltà di branding via CSS, coerente con UI-SPEC §Open Questions #4) ha una dipendenza di sistema nativa (Pango/Cairo/GDK-PixBuf via GTK) che **non è banale su Windows** (l'ambiente di sviluppo di questo progetto) mentre è naturale su Railway/Debian in produzione — va documentato come rischio locale con mitigazione esplicita.

**Primary recommendation:** auth self-hosted con `argon2-cffi` per l'hashing password (non `passlib`, deprecato/rotto con bcrypt≥4.1), sessione applicativa via tabella `user_session` + cookie httpOnly opaco (no JWT), Authlib per Google OAuth con `SessionMiddleware` isolato, snapshot `stima` ibrido (colonne scalari per lo storico + JSONB per il congelato completo), PDF server-side con WeasyPrint da template Jinja2 con gli stessi token Slate/blue-600, email transazionale via SMTP astratto dietro un'utility riusabile in Fase 4 (nessun provider specifico deciso — SMTP generico, sostituibile).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Registrazione/login email+password | API/Backend | — | Hashing, validazione, unicità email: logica server-side, mai nel client |
| Login Google OAuth | API/Backend | Browser (redirect) | Il browser fa solo il redirect verso Google; token exchange e verifica id_token avvengono server-side (Authlib) |
| Sessione (cookie httpOnly) | API/Backend | Browser (invio automatico cookie) | Cookie invisibile a JS; creazione/validazione/revoca in `user_session` lato server |
| Guard admin (route protette) | API/Backend | — | Dependency FastAPI su `current_user.role == "admin"`; nessuna logica di autorizzazione nel client |
| Salvataggio stima + storico | API/Backend | Database/Storage | Scrittura su `stima` al signup/auto-save; lettura per "Le mie stime" |
| Snapshot immutabile | Database/Storage | API/Backend | Il congelamento è una scrittura una-tantum; il backend non ricalcola mai una stima salvata |
| Generazione PDF | API/Backend | — | Deve leggere solo dallo snapshot salvato, mai ricalcolare/ricontattare il motore di stima |
| Routing client (auth screens, storico) | Browser/Client (SSR non presente) | — | SPA React con client-side routing (react-router); nessun server-rendering in questo stack |
| Invio email reset password | API/Backend | External Service (SMTP) | Backend genera token + chiama SMTP; nessuna logica email nel frontend |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `argon2-cffi` | 25.1.0 [VERIFIED: PyPI, pip index] | Hashing password (Argon2id) | Raccomandato OWASP come prima scelta 2024+; niente wrapper `passlib` (deprecato/rotto, vedi Pitfall #2) |
| `authlib` | 1.7.2 [VERIFIED: PyPI, pip index] | Client OAuth Google (authorization code flow) | Già indicato in D-01; libreria matura, integrazione FastAPI/Starlette documentata ufficialmente [CITED: docs.authlib.org] |
| `itsdangerous` | 2.2.0 [VERIFIED: PyPI, pip index] | Firma/scadenza dei token monouso (reset password) | Già dipendenza indiretta dell'ecosistema Starlette; `URLSafeTimedSerializer` copre expiry + tamper-proofing senza bisogno di JWT |
| `weasyprint` | 69.0 [VERIFIED: PyPI, pip index] | Generazione PDF server-side da HTML/CSS | Riusa i token Tailwind Slate/blue-600 via foglio di stile per la stampa (fedeltà di branding, D-11/D-12); scelta esplicitamente indicata in UI-SPEC §Open Questions #4 |
| `jinja2` | (dipendenza di WeasyPrint, già transitiva via FastAPI/Starlette in molti setup, ma va aggiunta esplicitamente) | Template HTML del PDF | Standard de-facto per templating Python, integra bene con WeasyPrint |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `python-multipart` | verificare a install-time | Necessaria se si useranno form OAuth2 `Depends(OAuth2PasswordRequestForm)` | Solo se si sceglie il pattern form-based di FastAPI per login; **non necessaria** se login è JSON puro (raccomandato qui, coerente con `StimaRequest` JSON esistente) |
| SMTP client (stdlib `smtplib`/`aiosmtplib`, wrappato in un modulo `app/services/email.py`) | — | Invio email reset password (D-04) | Nessun provider gestito ancora deciso: usare un'astrazione minimale dietro variabili d'ambiente (`SMTP_HOST/PORT/USER/PASSWORD/FROM`) così la Fase 4 (lead) la riusa senza refactor |
| `react-router` | 8.3.0 [VERIFIED: npm, npm view] | Routing client-side per le nuove schermate (`/registrati`, `/accedi`, `/le-mie-stime`, ecc.) | Net-new, esplicitamente richiesta da UI-SPEC (oggi il frontend è single-page, nessun router installato) |
| `react-hook-form` + `zod` | verificare a install-time | Validazione form auth (registrazione/login/reset) tramite il primitivo shadcn `form` | UI-SPEC lo raccomanda ma lo rende non vincolante — la pattern hand-rolled già in `EstimateForm.tsx` è un'alternativa accettabile |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Sessione DB-backed (`user_session`) | JWT stateless (httpOnly cookie con `pyjwt`) | JWT evita una query DB per richiesta, ma non si può revocare senza blocklist — in contrasto con "logout server-side pulito" (D-02); più adatto a sistemi multi-servizio senza DB condiviso, non il caso qui (un solo backend, un solo Postgres) |
| `argon2-cffi` diretto | `passlib[bcrypt]` | `passlib` è **non manutenuto** (nessun rilascio dal 2020) e rotto con `bcrypt>=4.1` (`AttributeError: module 'bcrypt' has no attribute '__about__'`) — problema noto e diffuso [CITED: github.com/pyca/bcrypt/issues/684, github.com/fastapi/fastapi/discussions/11773] |
| WeasyPrint | `reportlab` (puro Python, nessuna dipendenza nativa) | reportlab non ha dipendenze di sistema (più semplice su Windows dev) ma richiede di ridichiarare manualmente colori/spaziature invece di riusare CSS — meno fedele al branding Slate/blue-600 richiesto da D-12/UI-SPEC §H |
| WeasyPrint | Headless Chromium (Playwright `page.pdf()`) | Fedeltà CSS massima (stesso motore del browser), ma introduce una dipendenza pesante (download Chromium ~300MB) per generare un solo PDF a una pagina — sproporzionato per questo scope |
| Auth self-hosted custom | `fastapi-users` | Libreria matura e batterie incluse (registrazione, OAuth, reset password) ma opinionata sullo schema `User` e sul flusso cookie; la convergenza email/Google (D-05) e lo snapshot legato a `user.id` sono più semplici da controllare con un modello scritto a mano data la ridotta superficie (4 endpoint auth + 1 guard) |

**Installation:**
```bash
# backend (uv, coerente con pyproject.toml esistente)
uv add argon2-cffi authlib itsdangerous weasyprint jinja2 aiosmtplib

# frontend
npm install react-router
# se si adotta il primitivo shadcn `form`:
npm install react-hook-form zod @hookform/resolvers
```

**Version verification:** eseguita in questa sessione via `pip index versions <pkg>` (registro PyPI) e `npm view react-router version` (registro npm) — vedi tabella sopra. `python-multipart` e `react-hook-form`/`zod` non fissati a una versione specifica perché la loro necessità dipende da scelte implementative del planner (form JSON vs form-encoded; validazione hand-rolled vs `form` shadcn).

## Package Legitimacy Audit

`slopcheck` (v0.6.1, installato in questa sessione) è disponibile ma **interroga di default il registro npm**, non PyPI/pip — con questi pacchetti Python ha prodotto solo errori di rete (proxy aziendale, certificato self-signed) invece di un verdetto utile. Non essendoci un flag ecosistema-specifico verificato per Python in questa sessione, applico la **degradazione controllata**: tutti i pacchetti Python sotto sono tag `[ASSUMED]` nonostante l'esistenza confermata su PyPI via `pip index versions` — l'esistenza sul registro da sola non equivale a `[VERIFIED]` per la regola di provenienza pacchetti. `react-router` è verificato solo su npm (`npm view`), stesso discorso.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| argon2-cffi | PyPI | >10 anni (dal 2015) | alto (milioni/mese, dipendenza comune) | github.com/hynek/argon2-cffi | non eseguibile (registro sbagliato) | [ASSUMED] — Approvato con checkpoint |
| authlib | PyPI | >8 anni | alto | github.com/authlib/authlib | non eseguibile | [ASSUMED] — Approvato con checkpoint |
| itsdangerous | PyPI | >12 anni (progetto Pallets) | molto alto | github.com/pallets/itsdangerous | non eseguibile | [ASSUMED] — Approvato con checkpoint |
| weasyprint | PyPI | >13 anni | alto | github.com/Kozea/WeasyPrint | non eseguibile | [ASSUMED] — Approvato con checkpoint |
| jinja2 | PyPI | >15 anni (progetto Pallets) | molto alto | github.com/pallets/jinja | non eseguibile | [ASSUMED] — Approvato con checkpoint |
| aiosmtplib | PyPI | anni, libreria SMTP async consolidata | medio-alto | github.com/cole/aiosmtplib | non eseguibile | [ASSUMED] — Approvato con checkpoint |
| react-router | npm | >10 anni | molto alto | github.com/remix-run/react-router | non eseguibile (proxy) | [ASSUMED] — Approvato con checkpoint |

**Packages removed due to slopcheck [SLOP] verdict:** nessuno.
**Packages flagged as suspicious [SUS]:** nessuno.

*slopcheck non ha potuto verificare l'ecosistema Python in questa sessione (interroga npm di default, e la rete aziendale ha bloccato anche quella query via proxy/cert self-signed). Tutti i pacchetti sopra sono quindi `[ASSUMED]`: il planner deve inserire un task `checkpoint:human-verify` prima di ciascun `uv add`/`npm install`, anche se si tratta di librerie estremamente note (tutte con >8 anni di storia e adozione di massa nel proprio ecosistema — rischio di slopsquat basso ma non verificato meccanicamente).*

## Architecture Patterns

### System Architecture Diagram

```
Browser (SPA React + react-router)
  │
  │ 1. POST /api/v1/auth/registrati {email, password, nome}
  │    oppure GET /api/v1/auth/google/login → redirect Google
  ▼
FastAPI backend
  ├─ router auth (registrazione, login, logout, google callback, reset password)
  │     → argon2-cffi (hash/verify password)
  │     → Authlib OAuth client (Google) — usa Starlette SessionMiddleware
  │            SEPARATA dal cookie di sessione applicativo (pitfall #1)
  │     → su successo: crea riga in `user_session`, imposta cookie httpOnly
  │            (session_id opaco, SameSite=Lax, Secure in prod)
  │
  ├─ dependency `get_current_user(request)`
  │     → legge cookie → query `user_session` (join `user`) → 401 se assente/scaduta
  ├─ dependency `require_admin(user=Depends(get_current_user))`
  │     → 403 se `user.role != "admin"`
  │
  ├─ router stima (esistente, Fase 1) — INVARIATO nella logica di calcolo
  │     → POST /api/v1/stima resta anonimo/pubblico (nessun gate qui)
  │
  ├─ router stima-salvate (net-new)
  │     → POST /api/v1/me/stime {snapshot} — richiede get_current_user
  │         (chiamato dal frontend con il risultato GIÀ calcolato,
  │          mai un ricalcolo server-side — D-07/D-09)
  │     → GET /api/v1/me/stime — storico (colonne scalari, no JOIN pesanti)
  │     → GET /api/v1/me/stime/{id} — dettaglio snapshot completo (JSONB)
  │
  ├─ router pdf (net-new)
  │     → GET /api/v1/me/stime/{id}/pdf — richiede get_current_user
  │         legge SOLO lo snapshot salvato (mai l'engine Fase 1) →
  │         render Jinja2 → WeasyPrint HTML→PDF → StreamingResponse
  │
  └─ Postgres (via SQLAlchemy 2.0 + Alembic)
        user, user_session, password_reset_token, stima (net-new)
        + le 8 tabelle di dominio Fase 1 (invariate)

External: SMTP (reset password, D-04) — chiamato solo dal router auth
External: Google OAuth (login, D-01/D-02) — chiamato solo dal router auth
```

### Recommended Project Structure

```
backend/app/
├── models/
│   ├── user.py              # User, UserSession, PasswordResetToken (net-new)
│   └── stima_salvata.py     # StimaSalvata (net-new, evita clash col modulo services/estimation)
├── schemas/
│   ├── auth.py               # RegistrazioneRequest, LoginRequest, UserOut (campi chiusi, mai password_hash)
│   └── stima_salvata.py      # StimaSalvataCreate/Out — stesso pattern anti-leak di schemas/stima.py
├── services/
│   ├── auth_service.py       # hash/verify password, create/validate session, google convergence (D-05)
│   ├── email_service.py      # invio email transazionale (astrazione SMTP, riusata Fase 4)
│   └── pdf_service.py        # render Jinja2 + WeasyPrint da uno snapshot
├── routers/
│   ├── auth.py                # /auth/registrati /auth/login /auth/logout /auth/google/* /auth/reset-password/*
│   └── stime_salvate.py       # /me/stime /me/stime/{id} /me/stime/{id}/pdf
├── dependencies/
│   └── auth.py                # get_current_user, require_admin
└── templates/
    └── pdf_stima.html         # template Jinja2, CSS inline con token Slate/blue-600

frontend/src/
├── routes/                    # nuove pagine react-router
│   ├── RegistratiPage.tsx
│   ├── AccediPage.tsx
│   ├── PasswordDimenticataPage.tsx
│   ├── ReimpostaPasswordPage.tsx
│   └── LeMieStimePage.tsx
├── api/
│   └── auth.ts                 # postRegistrazione/postLogin/postLogout/getMe — tutte con credentials:"include"
├── hooks/
│   └── useAuth.ts               # react-query useQuery('me') + mutations login/logout
└── components/
    ├── AccountMenu.tsx          # avatar + dropdown-menu (header §E)
    └── SoftWallCta.tsx          # MODIFICATO: 2 dei 4 bottoni ora navigano invece di soft-wall
```

### Pattern 1: Sessione DB-backed via cookie httpOnly opaco

**What:** al login riuscito, il backend genera un id casuale (`secrets.token_urlsafe(32)`), lo salva (o il suo hash) in `user_session` con `expires_at`, e lo imposta come cookie httpOnly/SameSite/Secure. Ogni richiesta autenticata legge il cookie, cerca la sessione in DB, la joina a `user`.

**When to use:** quando serve revoca pulita (logout) senza gestire una blocklist JWT — esattamente il caso D-02.

**Example:**
```python
# Source: pattern standard sessione DB-backed, ASSUMED (nessuna doc ufficiale
# unica citata: composizione di FastAPI Depends + SQLAlchemy, non specifica
# di una libreria)
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Cookie, Depends, HTTPException, Response

SESSION_COOKIE_NAME = "session_id"
SESSION_TTL = timedelta(days=30)


def create_session(session: Session, user: User, response: Response) -> None:
    session_id = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + SESSION_TTL
    session.add(UserSession(id=session_id, user_id=user.id, expires_at=expires_at))
    session.commit()
    response.set_cookie(
        SESSION_COOKIE_NAME,
        session_id,
        httponly=True,
        samesite="lax",
        secure=True,  # solo in prod (dietro HTTPS); False in dev locale su http
        max_age=int(SESSION_TTL.total_seconds()),
    )


def get_current_user(
    session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> User:
    if not session_id:
        raise HTTPException(401, "Non autenticato")
    row = db.query(UserSession).filter_by(id=session_id).one_or_none()
    if not row or row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(401, "Sessione scaduta")
    return row.user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Accesso riservato")
    return user
```

### Pattern 2: Google OAuth con Authlib — SessionMiddleware isolato

**What:** Authlib usa `request.session` (Starlette `SessionMiddleware`, cookie firmato separato) per tenere `state`/PKCE tra `authorize_redirect` e il callback. Questo NON è il cookie di sessione applicativo del Pattern 1 — sono due cookie diversi con scopi diversi.

**When to use:** sempre, quando si integra Authlib in FastAPI/Starlette.

**Example:**
```python
# Source: docs.authlib.org/en/latest/client/fastapi.html [CITED]
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware

app.add_middleware(SessionMiddleware, secret_key=settings.OAUTH_SESSION_SECRET)  # cookie DIVERSO da session_id

oauth = OAuth()
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    client_kwargs={"scope": "openid email profile"},
)


@router.get("/auth/google/login")
async def google_login(request: Request):
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/auth/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    token = await oauth.google.authorize_access_token(request)
    userinfo = token["userinfo"]  # email GIÀ verificata da Google
    user = get_or_create_user_by_email(db, email=userinfo["email"], nome=userinfo.get("given_name", ""))
    # D-05: se esiste già uno user con questa email (via password), converge
    # sullo stesso record — nessun duplicato.
    response = RedirectResponse(url=settings.FRONTEND_URL)
    create_session(db, user, response)  # Pattern 1
    return response
```

### Pattern 3: Snapshot storage ibrido (colonne scalari + JSONB)

**What:** la tabella `stima` tiene colonne scalari (`citta`, `mq`, `tipo`, `totale_min`, `totale_max`, `fallback`, `created_at`) per rendere veloce ed economica la query dello storico (nessun parsing JSON per riga di lista), PIÙ una colonna `risultato_json` (JSONB) col payload completo congelato (identico nella forma a `StimaResponse`, incluse le 4 categorie e gli extra) usato da dettaglio e PDF.

**When to use:** sempre per `stima` in questa fase — bilancia query economiche (storico) e fedeltà totale del congelato (dettaglio/PDF), senza dover normalizzare in tabelle figlie `stima_categoria`/`stima_extra` che aggiungerebbero complessità senza benefici (lo snapshot non si aggiorna mai riga per riga).

**Example:**
```python
# Source: ASSUMED — pattern comune "snapshot ibrido", non da una doc specifica
class StimaSalvata(Base):
    __tablename__ = "stima"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False, index=True)

    # Input congelati (anche per eventuale ricalcolo Pro esplicito in Fase 3)
    citta: Mapped[str] = mapped_column(String(200), nullable=False)
    mq: Mapped[int] = mapped_column(nullable=False)
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)

    # Colonne scalari duplicate per lo storico (evitano JSON parsing su ogni riga lista)
    totale_min: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    totale_max: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    fallback: Mapped[bool] = mapped_column(nullable=False, default=False)

    # Risultato COMPLETO congelato — stessa forma di StimaResponse (Fase 1)
    risultato_json: Mapped[dict] = mapped_column(JSONB, nullable=False)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
```

### Anti-Patterns to Avoid

- **JWT stateless per la sessione applicativa:** rende il logout un'illusione lato client (il token resta valido finché non scade) — in contrasto diretto con D-02 "logout server-side pulito". Usare solo per casi che qui non esistono (microservizi senza DB condiviso).
- **`model_validate` diretto su `User`/`StimaSalvata` verso il client:** stesso rischio anti-leak di Fase 1 — mai serializzare `password_hash` o campi interni. Replicare lo schema a campi chiusi già usato in `schemas/stima.py`.
- **Ricalcolo della stima al momento del download PDF o della visualizzazione storico:** viola D-09 (immutabilità) — il PDF e la vista dettaglio devono leggere **solo** `risultato_json`, mai richiamare `EstimationService.compute()`.
- **Un solo cookie per sessione OAuth e sessione applicativa:** Authlib scrive nel cookie di `SessionMiddleware`; se si riusa lo stesso nome/secret per il cookie `session_id` applicativo si rischia un cookie-clobbering silenzioso tra i due meccanismi.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Hashing password | Un proprio schema hash+salt | `argon2-cffi` (`PasswordHasher().hash()`/`.verify()`) | Argon2id è lo standard OWASP corrente; resistenza GPU/ASIC tarata, gestisce automaticamente salt e parametri di costo |
| Scambio OAuth Google (state, PKCE, verifica id_token/JWKS) | Chiamate HTTP manuali a Google | `Authlib` (`OAuth` + `authorize_redirect`/`authorize_access_token`) | La verifica della firma id_token e la gestione dello `state` anti-CSRF sono superficie di sicurezza delicata già risolta e testata dalla libreria |
| Token di reset password con scadenza e anti-tamper | Stringa random + colonna `expires_at` fatta a mano (comunque valida, ma va fatta bene) | `itsdangerous.URLSafeTimedSerializer` | Firma il payload (user_id) e la scadenza in un colpo solo; nessun round-trip DB necessario per validare la firma prima di controllare l'uso singolo |
| Generazione PDF con layout/branding | Costruzione manuale byte-a-byte con una libreria low-level (es. reportlab canvas) | `WeasyPrint` da template HTML/CSS | Riusa gli stessi token Tailwind (colori, spaziature) del frontend via CSS, invece di ridichiarare coordinate assolute |
| Client-side routing | Uno switch manuale su `window.location.pathname` | `react-router` | Gestisce history API, redirect con stato (intent `save`/`download`), route protette, in modo testato e idiomatico React |

**Key insight:** in questa fase la superficie di sicurezza (password, OAuth, sessione, reset token) è ampia rispetto al resto del progetto — ogni pezzo "fatto in casa" qui è un pezzo di crittografia/auth applicata scritto da zero, la categoria di codice con il tasso di bug più alto e le conseguenze più gravi se sbagliata.

## Common Pitfalls

### Pitfall 1: Confusione tra cookie di sessione OAuth (Authlib/Starlette) e cookie di sessione applicativo
**What goes wrong:** si usa lo stesso nome cookie o lo stesso secret per `SessionMiddleware` (usato da Authlib per `state`/PKCE) e per il cookie `session_id` applicativo (Pattern 1), causando login Google che "funziona a intermittenza" o sovrascrive la sessione utente.
**Why it happens:** entrambi si chiamano genericamente "session" nella documentazione Starlette/Authlib.
**How to avoid:** due meccanismi separati e nominati esplicitamente — `SessionMiddleware` con secret dedicato (`OAUTH_SESSION_SECRET`, usato SOLO durante il flusso OAuth, cookie nome default `session`) e il cookie applicativo `session_id` (Pattern 1, gestito a mano, mai da Starlette).
**Warning signs:** login Google che funziona la prima volta ma non al secondo tentativo nella stessa sessione browser; utente sloggato dopo un login Google riuscito.

### Pitfall 2: `passlib` è deprecato e rotto con bcrypt recente
**What goes wrong:** seguendo la documentazione storica di FastAPI (che ancora oggi in molte guide mostra `passlib[bcrypt]`), si ottiene `AttributeError: module 'bcrypt' has no attribute '__about__'` con bcrypt ≥ 4.1, perché `passlib` non è più manutenuto dal 2020.
**Why it happens:** `passlib` introspeziona l'API interna di `bcrypt` per leggerne la versione, e quell'API è cambiata.
**How to avoid:** non usare `passlib`. Usare `argon2-cffi` direttamente (`from argon2 import PasswordHasher`), che non ha questa dipendenza fragile.
**Warning signs:** warning/errore su `__about__` nei log all'avvio o al primo hash.
[CITED: github.com/pyca/bcrypt/issues/684, github.com/fastapi/fastapi/discussions/11773]

### Pitfall 3: WeasyPrint su Windows (ambiente di sviluppo di questo progetto) richiede GTK
**What goes wrong:** `pip install weasyprint` (o `uv add weasyprint`) installa il pacchetto Python, ma al primo utilizzo fallisce con errori di libreria nativa mancante (Pango/Cairo/GDK-PixBuf), perché su Windows queste non sono incluse nel pacchetto PyPI — vanno installate a parte (GTK3 runtime).
**Why it happens:** WeasyPrint dipende da librerie di rendering testo/immagine C (parte dello stack GTK) che su Linux/macOS sono spesso già presenti o installabili via package manager di sistema, mentre su Windows richiedono un installer dedicato.
**How to avoid:** (a) installare il [GTK3 runtime per Windows](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases) e aggiungerne il `bin/` al PATH per lo sviluppo locale, oppure (b) sviluppare/testare la generazione PDF dentro Docker/WSL2 (Debian, dove `apt install libpango-1.0-0 libpangoft2-1.0-0` basta), oppure (c) tenere `reportlab` come fallback esplicito se il team non riesce a far girare WeasyPrint in locale. In produzione su Railway (ambiente Debian via Nixpacks) l'installazione delle librerie native è gestibile con un `nixpacks.toml`/`aptPkgs` dedicato — non è un problema di produzione, solo di sviluppo locale Windows.
**Warning signs:** `OSError: cannot load library 'gobject-2.0-0'` o simili al primo tentativo di generare un PDF in locale.
[CITED: github.com/Kozea/WeasyPrint/issues/1464, doc.courtbouillon.org/weasyprint/stable/first_steps.html]

### Pitfall 4: Cookie httpOnly cross-origin durante lo sviluppo (frontend Vite :5173, backend FastAPI su porta diversa)
**What goes wrong:** il cookie di sessione non viene inviato dal browser sulle richieste `fetch` verso il backend, l'utente sembra "sempre sloggato" nonostante login riuscito.
**Why it happens:** in dev, frontend e backend girano su origin diverse (porte diverse = origin diverse per i cookie); senza `credentials: "include"` lato fetch E `allow_credentials=True` + `CORS_ORIGINS` esplicito (non `*`) lato FastAPI `CORSMiddleware`, il cookie non attraversa la richiesta cross-origin.
**Why it happens (continua):** `api/client.ts`/`api/stima.ts` esistenti oggi NON impostano `credentials: "include"` (verificato: nessuna occorrenza nel codice attuale) — vanno aggiornati per tutte le chiamate autenticate.
**How to avoid:** ogni `fetch` verso endpoint autenticati deve avere `credentials: "include"`; il backend deve avere `CORSMiddleware(allow_origins=settings.cors_origins_list, allow_credentials=True, ...)` (già presente `cors_origins_list` in `config.py`, va solo collegato con `allow_credentials=True` in `main.py` — verificare che oggi sia già attivo o vada aggiunto); in produzione, se frontend e backend sono sullo stesso dominio (o sotto-dominio con `SameSite=Lax`), il problema si attenua ma va comunque verificato con `Secure=True` su HTTPS.
**Warning signs:** login risponde 200 ma la richiesta successiva a `GET /me` risponde 401; il cookie non compare nel tab Network → Cookies della richiesta successiva.

### Pitfall 5: Ordine di creazione — salvare la stima "al signup" richiede il payload dal client, non un ricalcolo
**What goes wrong:** se l'endpoint di registrazione (o un endpoint successivo di salvataggio) ricalcola la stima invece di accettare lo snapshot già calcolato dal client, si rischia una incoerenza (listino aggiornato nel frattempo, race condition) e si viola D-09 (lo snapshot deve essere il MOMENTO esatto già mostrato all'utente).
**Why it happens:** sembra "più sicuro" ricalcolare server-side per garantire coerenza, ma qui il rischio è opposto: la stima mostrata prima della registrazione (già calcolata dall'endpoint `POST /stima` esistente, anti-leak-safe) è quella che l'utente ha visto e vuole salvare.
**How to avoid:** l'endpoint di salvataggio accetta il payload `StimaResponse`-shaped già ottenuto dal client (che a sua volta lo ha ricevuto, intatto, dal backend un momento prima) e lo scrive as-is in `risultato_json` — nessuna chiamata a `EstimationService.compute()` in questo percorso. Il client non deve poter INVENTARE un totale: si può mitigare validando che i valori numerici nel payload rispettino i vincoli di schema (Decimal, campi chiusi) ma la fonte di verità resta "quello che l'utente ha appena visto", che a sua volta proviene da un endpoint server-side. (Un irrigidimento ulteriore, fuori scope v1: rifirmare la risposta di `/stima` con un token effimero da ripresentare al salvataggio, per impedire manomissioni — valutabile come hardening futuro, non richiesto da CONTEXT.md.)
**Warning signs:** test che salva una stima con un totale diverso da quello che l'endpoint `/stima` avrebbe prodotto per lo stesso input passa senza errori.

## Code Examples

### Hashing e verifica password (argon2-cffi)
```python
# Source: ASSUMED (API pubblica argon2-cffi, pattern standard)
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

ph = PasswordHasher()  # parametri di default OWASP-adeguati

def hash_password(plain: str) -> str:
    return ph.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return ph.verify(hashed, plain)
    except VerifyMismatchError:
        return False
```

### Token di reset password (itsdangerous)
```python
# Source: ASSUMED (API pubblica itsdangerous, pattern standard "URLSafeTimedSerializer")
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

serializer = URLSafeTimedSerializer(settings.SECRET_KEY, salt="password-reset")

def make_reset_token(user_id: int) -> str:
    return serializer.dumps({"user_id": user_id})

def read_reset_token(token: str, max_age_seconds: int = 3600) -> int | None:
    try:
        data = serializer.loads(token, max_age=max_age_seconds)
        return data["user_id"]
    except (SignatureExpired, BadSignature):
        return None
```

### Generazione PDF (WeasyPrint da template Jinja2)
```python
# Source: ASSUMED (API pubblica WeasyPrint, pattern standard HTML→PDF)
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

env = Environment(loader=FileSystemLoader("app/templates"))

def render_pdf(stima: StimaSalvata, user: User) -> bytes:
    template = env.get_template("pdf_stima.html")
    html_content = template.render(
        stima=stima.risultato_json,   # SOLO dallo snapshot congelato
        nome=user.nome,
        data=stima.created_at,
    )
    return HTML(string=html_content).write_pdf()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `passlib[bcrypt]` per hashing password in FastAPI | `argon2-cffi` diretto, o `bcrypt` diretto senza wrapper | passlib non manutenuto dal 2020, rottura conclamata con bcrypt≥4.1 (2023-2024) | Molte guide FastAPI online (incluse quelle ufficiali storiche) mostrano ancora il pattern rotto — va evitato consapevolmente |

**Deprecated/outdated:**
- `passlib`: nessun rilascio dal 2020, rotto con bcrypt recenti — non usare per codice nuovo.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `argon2-cffi` è la scelta di hashing password raccomandata rispetto a `bcrypt` diretto o `passlib` | Standard Stack, Pitfall 2 | Basso — sono comunque entrambi accettabili per D-01 ("bcrypt/argon2"); se il team preferisce `bcrypt` diretto (senza passlib) è comunque conforme alla decisione locked |
| A2 | Sessione DB-backed (tabella `user_session`) preferita a JWT stateless | Pattern 1, Alternatives Considered | Medio — se il planner sceglie JWT comunque, va aggiunta una qualche forma di revoca (blocklist) per onorare "logout server-side pulito" (D-02); altrimenti il logout è solo client-side |
| A3 | Snapshot storage ibrido (colonne scalari + JSONB) è lo schema preferito | Pattern 3 | Basso — CONTEXT.md lascia esplicitamente la struttura a discrezione, purché immutabile/storico/anti-leak; una normalizzazione completa in tabelle figlie resterebbe comunque conforme, solo più complessa |
| A4 | WeasyPrint preferito a reportlab/Playwright per il PDF | Standard Stack, Alternatives Considered, Pitfall 3 | Medio — se il team non riesce a far girare WeasyPrint in locale su Windows in tempi ragionevoli, va fatto un fallback esplicito a reportlab (perdendo fedeltà di branding CSS) o si sviluppa la feature PDF dentro un container Docker locale |
| A5 | Email transazionale via SMTP generico astratto (nessun provider specifico) | Standard Stack (Supporting) | Basso — CONTEXT.md lascia il provider a discrezione; qualunque provider SMTP standard (Gmail SMTP con app-password, Resend SMTP relay, Postmark, ecc.) si collega senza modifiche al codice, solo variabili d'ambiente diverse |
| A6 | Tutti i pacchetti in Package Legitimacy Audit sono legittimi nonostante slopcheck non abbia potuto verificarli in questa sessione | Package Legitimacy Audit | Basso — sono tutti pacchetti con >8 anni di storia e adozione di massa nel proprio ecosistema (argon2-cffi, authlib, itsdangerous, weasyprint, jinja2, react-router); rischio di slopsquat molto basso ma non confermato meccanicamente — planner deve comunque inserire `checkpoint:human-verify` |

**Se questa tabella fosse vuota:** non è il caso — 6 claim marcate `[ASSUMED]`, nessuna riguarda requisiti di dominio non negoziabili (CLAUDE.md), solo scelte tecniche di libreria entro lo spazio di discrezione di CONTEXT.md.

## Open Questions (RESOLVED)

<!-- Q1 (CORS allow_credentials): verified già true in backend/app/main.py — nessuna azione. Q2 (schema_version): implementato in 02-07 dentro risultato_json. Q3 (credenziali Google Cloud): gestito da 02-05 Task 1, checkpoint:human-verify bloccante. -->


1. **`allow_credentials=True` è già attivo in `main.py`?**
   - What we know: `config.py` espone già `cors_origins_list`, ma non abbiamo letto `main.py` per confermare se `CORSMiddleware` è già configurato con `allow_credentials=True`.
   - What's unclear: se manca, i cookie httpOnly non attraverseranno le richieste cross-origin in dev (Pitfall 4).
   - Recommendation: il planner deve verificare/aggiungere questa configurazione come primo task della fase, prima di qualunque endpoint auth.

2. **Formato esatto di `risultato_json`: identico a `StimaResponse` o un supersets con metadati aggiuntivi?**
   - What we know: deve contenere tutto ciò che serve a ricostruire dettaglio+PDF senza ricalcolo (4 categorie a range, totale, IVA, disclaimer).
   - What's unclear: se conviene aggiungere un campo `versione_schema` per gestire evoluzioni future del formato snapshot (utile quando Fase 3 aggiungerà le sottocategorie Pro allo stesso record).
   - Recommendation: aggiungere fin da subito un campo `schema_version: 1` nel JSON per non dover fare data-migration silenziose in futuro — costo quasi nullo ora.

3. **`GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`: già esistono credenziali Google Cloud per questo progetto?**
   - What we know: nessuna menzione in CONTEXT.md o nel codice di un progetto Google Cloud Console esistente.
   - What's unclear: la registrazione dell'app OAuth (redirect URI autorizzati, consent screen) è un passo manuale fuori dal codice che deve avvenire prima che il login Google funzioni anche in ambiente di sviluppo.
   - Recommendation: il planner dovrebbe inserire un task `checkpoint:human-verify` esplicito per la creazione delle credenziali OAuth Google (Console Cloud) prima o durante l'implementazione di AUTH-02.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.13 | Backend | ✓ | 3.13 (da `.python-version`/pyproject) | — |
| Node.js | Frontend | ✓ | v24.16.0 (da PATH) | — |
| PostgreSQL | Deploy prod (dev usa SQLite oggi, `DATABASE_URL` default `sqlite:///./dev.db`) | non verificato in locale (dev su SQLite) | — | SQLite già usato come DB di sviluppo in Fase 1; JSONB non è nativo su SQLite — va verificato che SQLAlchemy mappi comunque un tipo JSON generico per compatibilità dev/prod (vedi Pitfall implicito: `JSONB` di Postgres non esiste su SQLite, usare `sqlalchemy.JSON` generico o forzare Postgres anche in dev) |
| GTK3 runtime (Pango/Cairo/GDK-PixBuf) | WeasyPrint (dev locale Windows) | ✗ (non verificato installato) | — | Vedi Pitfall #3: installer GTK3 Windows, oppure sviluppo PDF in Docker/WSL2 |
| slopcheck | Package Legitimacy Audit | ✓ (installato in sessione) | 0.6.1 | Configurato solo per npm di default; per Python il verdetto non è stato ottenibile in questa sessione (proxy aziendale) |

**Missing dependencies with no fallback:**
- Credenziali Google OAuth (Client ID/Secret) — bloccante per AUTH-02, va creato un progetto Google Cloud Console (nessun fallback tecnico, è un prerequisito organizzativo).

**Missing dependencies with fallback:**
- GTK3 runtime per WeasyPrint in dev locale Windows — fallback: Docker/WSL2 per la sola generazione PDF, o reportlab come piano B.
- Verifica tipo colonna JSON compatibile SQLite/Postgres — fallback: usare `sqlalchemy.types.JSON` generico invece di `postgresql.JSONB` esplicito, così il dev locale su SQLite continua a funzionare senza forzare Postgres locale (già il pattern usato oggi con `connect_args` condizionale in `db.py`).

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | Sì | Argon2id per password (V2.4), lockout/rate-limit su login (riusa `app/limiter.py` esistente, già usato su `/stima` — estendere a `/auth/login`), nessuna enumerazione utenti nel messaggio di errore reset password (UI-SPEC già lo prevede: "mostra sempre la conferma, indipendentemente dall'esistenza dell'email") |
| V3 Session Management | Sì | Cookie httpOnly + Secure (prod) + SameSite=Lax, id di sessione ad alta entropia (`secrets.token_urlsafe(32)`), scadenza server-side, invalidazione esplicita al logout (Pattern 1) |
| V4 Access Control | Sì | Dependency `require_admin` lato server per ogni route riservata; nessuna verifica di ruolo lasciata al frontend (il ruolo admin non ha ancora UI in questa fase, ma le route vanno comunque protette server-side per AUTH-04) |
| V5 Input Validation | Sì | Schemi Pydantic a campi chiusi per tutti gli input auth (email format, password min-length già in UI-SPEC: 8 caratteri), replicando il pattern `StimaRequest` esistente |
| V6 Cryptography | Sì | Mai hand-roll: Argon2id (libreria), token di reset firmati con `itsdangerous` (HMAC sotto il cofano) — nessun algoritmo crittografico scritto a mano in questa fase |

### Known Threat Patterns for questo stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| Credential stuffing / brute-force su login | Tampering / Elevation of Privilege | Rate limit su `/auth/login` (riuso `slowapi`/`app/limiter.py` già presente in Fase 1, es. `5/minute` per IP) |
| Session fixation | Spoofing | Rigenerare sempre un nuovo `session_id` al login (mai riusare un id di sessione pre-login) |
| CSRF sulle azioni che cambiano stato (logout, salvataggio stima) | Tampering | `SameSite=Lax` sul cookie applicativo copre la maggior parte dei casi per richieste GET-navigazione; per POST cross-site, `SameSite=Lax` blocca comunque l'invio del cookie su richieste cross-site non "top-level navigation" — sufficiente per API JSON chiamate via `fetch` da un altro dominio (il browser non allega il cookie) |
| User enumeration via messaggi di errore diversi (login/reset password) | Information Disclosure | Messaggio di errore login generico ("Email o password non corretti", già in UI-SPEC copy) e conferma reset-password sempre identica indipendentemente dall'esistenza dell'account (già in UI-SPEC §D) |
| OAuth state/CSRF su login Google | Spoofing | Gestito internamente da Authlib (`state` parameter verificato in `authorize_access_token`) — non reinventare |
| Leak di `password_hash` o campi interni verso il client | Information Disclosure | Stesso pattern anti-leak di Fase 1: schema Pydantic a campi chiusi per `UserOut`, mai `model_validate` diretto su `User` |

## Sources

### Primary (HIGH confidence)
- `pip index versions <pkg>` (registro PyPI, eseguito in sessione) — argon2-cffi 25.1.0, authlib 1.7.2, itsdangerous 2.2.0, weasyprint 69.0, pyjwt 2.13.0, passlib 1.7.4, bcrypt 5.0.0
- `npm view react-router version` (registro npm, eseguito in sessione) — 8.3.0
- Lettura diretta del codice esistente: `backend/app/routers/stima.py`, `backend/app/schemas/stima.py`, `backend/app/services/estimation.py`, `backend/app/models/*.py`, `backend/app/limiter.py`, `backend/app/db.py`, `backend/app/config.py`, `backend/alembic/versions/0001_initial_schema.py`, `frontend/src/api/*.ts`, `frontend/src/components/SoftWallCta.tsx`, `frontend/src/pages/EstimatePage.tsx`, `frontend/package.json`

### Secondary (MEDIUM confidence)
- docs.authlib.org — FastAPI OAuth Client (pattern `SessionMiddleware` + `authorize_redirect`/`authorize_access_token`) [CITED]
- doc.courtbouillon.org/weasyprint — First Steps / installazione (dipendenze GTK su Windows) [CITED]

### Tertiary (LOW confidence)
- github.com/pyca/bcrypt/issues/684, github.com/fastapi/fastapi/discussions/11773 — rottura passlib/bcrypt, cross-verificata su più issue indipendenti quindi elevata a MEDIUM nel testo sopra
- github.com/Kozea/WeasyPrint/issues/1464 — problemi installazione Windows storici, pattern ancora valido ma non verificato con una fonte 2026

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM — versioni verificate su registro ufficiale, ma provenienza pacchetti resta `[ASSUMED]` per assenza di slopcheck funzionante su PyPI in questa sessione
- Architecture: MEDIUM-HIGH — pattern (sessione DB-backed, snapshot ibrido, Authlib+SessionMiddleware) sono standard di settore ben consolidati, ma non ci sono doc ufficiali "canoniche" per la combinazione specifica (composizione di più librerie)
- Pitfalls: HIGH per Pitfall 2 (passlib, cross-verificato su 2 fonti indipendenti) e Pitfall 3 (WeasyPrint Windows, multiple issue GitHub concordanti); MEDIUM per Pitfall 1/4/5 (ragionamento da conoscenza del dominio + lettura diretta del codice esistente, non da una fonte esterna singola)

**Research date:** 2026-08-25
**Valid until:** 30 giorni (stack stabile, nessuna libreria in fase di rapida evoluzione in questo scope)
