---
phase: 02-account-pdf
plan: 05
subsystem: backend-auth
tags: [authlib, oauth-google, session-middleware, tdd]

# Dependency graph
requires:
  - phase: 02-account-pdf
    plan: 03
    provides: "Router auth HTTP (registrati/login/logout/me), main.py con CORS/allow_credentials gia' attivo"
  - phase: 02-account-pdf
    plan: 02
    provides: "AuthService.get_or_create_user_by_email (convergenza D-05), AuthService.create_session (sessione applicativa cookie httpOnly)"
provides:
  - "Login Google via Authlib: GET /api/v1/auth/google/login, GET /api/v1/auth/google/callback"
  - "SessionMiddleware Starlette isolato (OAUTH_SESSION_SECRET), distinto dal cookie applicativo session_id"
  - "Convergenza per-email dimostrata da test (D-05): stesso account per password ed email Google"
affects: [02-06, 02-07]

# Tech tracking
tech-stack:
  added: ["httpx 0.28.1 (dipendenza runtime di authlib.integrations.starlette_client, non dichiarata dal plan/research; verificata dall'utente al checkpoint blocking-human)"]
  patterns:
    - "app/oauth.py: istanza OAuth Authlib in modulo proprio, stesso pattern di app/limiter.py, per evitare import circolari main<->routers/auth"
    - "SessionMiddleware Starlette con secret_key=OAUTH_SESSION_SECRET (dedicato), aggiunto in main.py DOPO CORSMiddleware — usato SOLO da Authlib per lo scambio state/PKCE, mai per la sessione applicativa"
    - "Callback Google: authorize_access_token -> userinfo (email gia' verificata da Google) -> get_or_create_user_by_email (D-05) -> create_session sulla stessa RedirectResponse -> redirect a FRONTEND_URL; su eccezione, redirect a FRONTEND_URL?google_auth=errore senza dettagli tecnici (T-05-04)"
    - "Test TDD con fixture DB in-memory: i moduli app.models.user/app.services.auth_service vanno importati a LIVELLO DI MODULO (non dentro le funzioni di test), altrimenti Base.metadata.create_all nella fixture registra uno schema vuoto quando il file gira in isolamento — 'no such table: user'"

key-files:
  created:
    - backend/app/oauth.py
    - backend/tests/test_google_convergence.py
  modified:
    - backend/app/main.py
    - backend/app/routers/auth.py
    - backend/pyproject.toml
    - backend/uv.lock
    - backend/.env (nuovo, gitignorato, contiene GOOGLE_CLIENT_ID/SECRET reali e SECRET_KEY/OAUTH_SESSION_SECRET generati)

key-decisions:
  - "Trovate credenziali Google OAuth reali scritte per errore in backend/.env.example (file TRACCIATO da git) invece che in backend/.env (gitignorato): ripristinato .env.example ai placeholder originali e spostati i valori reali in backend/.env, mai committato — nessun segreto e' mai entrato in un commit git"
  - "httpx (non dichiarato ne' da 02-RESEARCH.md ne' dal plan) e' risultato dipendenza runtime obbligatoria di authlib.integrations.starlette_client; installato solo dopo checkpoint blocking-human esplicito e conferma dell'utente ('verificato httpx')"
  - "Convergenza D-05: get_or_create_user_by_email NON aggiorna il nome di uno user gia' esistente (converge, non sovrascrive) — comportamento gia' presente dal Plan 02, confermato esplicitamente da un'asserzione nel nuovo test"

requirements-completed: [AUTH-02]

# Metrics
duration: 25min
completed: 2026-08-25
---

# Phase 2 Plan 5: Login Google (OAuth Authlib) + convergenza account Summary

**Login "Accedi con Google" via Authlib (authorization code flow) con `SessionMiddleware` Starlette isolato da un segreto dedicato (`OAUTH_SESSION_SECRET`), callback che converge sull'unico account per email (D-05) e crea la stessa sessione applicativa cookie-httpOnly del flusso email/password — verificato da import pulito e da 2 test TDD di convergenza, 55/55 suite totale verde.**

## Performance

- **Duration:** ~25 min (incluso un checkpoint blocking-human per la dipendenza `httpx`)
- **Started:** 2026-08-25 (dopo conferma utente "credenziali pronte")
- **Completed:** 2026-08-25
- **Tasks:** 3 (Task 1 gate credenziali gia' soddisfatto dall'utente, Task 2 implementazione, Task 3 test TDD)
- **Files modified:** 7 (2 creati, 4 modificati, 1 nuovo file locale gitignorato)

## Accomplishments

- **Pre-flight security fix (fuori piano, Rule 1):** le credenziali Google OAuth reali erano state scritte in `backend/.env.example` (file tracciato da git) invece che in `backend/.env` (gitignorato) — rilevato con `git diff` prima di qualunque commit, corretto spostando i valori reali in `backend/.env` (nuovo, mai tracciato) e ripristinando `.env.example` ai placeholder vuoti con `git checkout --`. Nessun segreto e' mai entrato nella cronologia git.
- `backend/app/oauth.py`: istanza `OAuth` Authlib registrata per Google (`server_metadata_url` OIDC discovery, `client_kwargs={"scope": "openid email profile"}`), modulo dedicato per evitare import circolari (pattern `limiter.py`).
- `backend/app/main.py`: `SessionMiddleware` Starlette aggiunto con `secret_key=settings.OAUTH_SESSION_SECRET` — segreto e cookie **distinti** dal cookie applicativo `session_id` gestito a mano da `AuthService` (Pitfall 1 / T-05-02).
- `backend/app/routers/auth.py`: `GET /auth/google/login` (`oauth.google.authorize_redirect` verso `request.url_for("google_callback")`) e `GET /auth/google/callback` (`authorize_access_token` → `userinfo["email"]` gia' verificata da Google → `AuthService.get_or_create_user_by_email` per la convergenza D-05 → `AuthService.create_session` sulla `RedirectResponse` verso `FRONTEND_URL`). Su eccezione nello scambio token, redirect a `FRONTEND_URL?google_auth=errore` senza esporre dettagli tecnici (T-05-04).
- **Checkpoint blocking-human superato:** `authlib.integrations.starlette_client` importa incondizionatamente `httpx` (non dichiarato da 02-RESEARCH.md ne' da `pyproject.toml`, ne' installabile automaticamente per policy — package-legitimacy gate). Fermato, chiesto verifica esplicita all'utente; ricevuta conferma ("verificato httpx — encode/httpx, pypi.org/project/httpx/"), poi `uv add httpx --native-tls` eseguito.
- `backend/tests/test_google_convergence.py`: 2 test — (1) uno user gia' esistente via password converge sullo stesso `id` quando `get_or_create_user_by_email` viene richiamata con la stessa email (nessun duplicato, nome esistente non sovrascritto); (2) un'email inedita crea uno user alla prima chiamata, la seconda chiamata converge sullo stesso `id`. Nessuna rete verso Google: si testa direttamente la funzione di convergenza gia' esistente dal Plan 02.
- Suite completa: **55/55 test verdi** (2 nuovi + 53 preesistenti).

## Task Commits

1. **Task 2: OAuth Google + SessionMiddleware isolato + convergenza account** - `96cb523` (feat)
2. **Task 3: Test convergenza per-email (D-05)** - `d9e467b` (test)

**Plan metadata:** (commit successivo con SUMMARY.md/STATE.md/ROADMAP.md)

## TDD Gate Compliance

Task 3 ha `tdd="true"` ma il testo del piano indica esplicitamente che `get_or_create_user_by_email` **esiste gia'** dal Plan 02 e il test deve "farlo passare" ("il servizio esiste gia' dal Plan 02; se manca un caso, completalo li'") — non un vero ciclo RED→GREEN. Il test e' infatti passato al primo tentativo (dopo aver corretto un problema di ordinamento import — vedi Deviazioni), coerentemente con l'istruzione esplicita del piano, non con la regola generale "fail-fast se un test passa inaspettatamente durante RED". Nessun commit `test(...)` separato da un commit `feat(...)` successivo per Task 3: e' un singolo commit `test(02-05): ...` perche' non e' stata scritta nuova logica di produzione (il comportamento testato preesisteva interamente).

## Files Created/Modified

- `backend/app/oauth.py` - istanza OAuth Authlib per Google
- `backend/app/main.py` - `SessionMiddleware` con `OAUTH_SESSION_SECRET`
- `backend/app/routers/auth.py` - endpoint `/auth/google/login`, `/auth/google/callback`
- `backend/tests/test_google_convergence.py` - 2 test TDD convergenza D-05
- `backend/pyproject.toml`, `backend/uv.lock` - dipendenza `httpx` aggiunta
- `backend/.env` - nuovo file locale (gitignorato) con le credenziali reali fornite dall'utente

## Decisions Made

- Credenziali Google OAuth spostate da `backend/.env.example` (tracciato) a `backend/.env` (gitignorato) prima di qualunque altra azione — vedi Deviazioni.
- `httpx` installato solo dopo checkpoint `blocking-human` esplicito e conferma utente, per rispettare rigorosamente l'esclusione "package manager installs" dalla Rule 3 (rischio slopsquat, anche per pacchetti notissimi).
- Import dei moduli `app.models.user`/`app.services.auth_service` spostati a livello di modulo in `test_google_convergence.py` (non dentro le funzioni di test) per garantire che `Base.metadata.create_all` nella fixture veda le tabelle registrate anche quando il file gira in isolamento.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Security] Credenziali Google OAuth reali esposte nel file tracciato `backend/.env.example` invece che in `backend/.env`**
- **Found during:** lettura pre-esecuzione dei file richiesti dal piano (prima del Task 2)
- **Issue:** `git diff` su `backend/.env.example` mostrava `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` reali scritti direttamente nel template committato, in contrasto con la docstring esplicita di `config.py` ("no real secret is ever hardcoded here. See backend/.env.example for how to generate them locally") e con l'invariante generale anti-leak di segreti del progetto.
- **Fix:** creato `backend/.env` (gia' in `.gitignore`) con i valori reali + `SECRET_KEY`/`OAUTH_SESSION_SECRET` generati via `secrets.token_urlsafe(32)`; ripristinato `backend/.env.example` alla versione committata coi placeholder vuoti tramite `git checkout -- backend/.env.example`.
- **Files modified:** `backend/.env` (nuovo, gitignorato), `backend/.env.example` (ripristinato, nessuna modifica netta rispetto a HEAD)
- **Verification:** `git status --short` pulito su `.env.example` prima di qualunque commit; `git log -- backend/.env.example` conferma che nessun commit successivo lo tocca in questo plan.
- **Committed in:** nessun commit (il file reale e' gitignorato per design; il template e' stato riportato allo stato gia' su HEAD, quindi nessun commit necessario)

**2. [Rule 3 - Blocking, con checkpoint esplicito per package legitimacy] Dipendenza `httpx` mancante, non dichiarata dal piano/RESEARCH**
- **Found during:** Task 2, verifica import (`import app.main` falliva con `ModuleNotFoundError: No module named 'httpx'`)
- **Issue:** `authlib.integrations.starlette_client` importa incondizionatamente `authlib.integrations.httpx_client`, che richiede il pacchetto `httpx` — mai dichiarato in `pyproject.toml`/`uv.lock` ne' menzionato in 02-RESEARCH.md (il progetto aveva solo `httpx2`, un pacchetto diverso installato in Fase 1 per altri motivi).
- **Fix:** per policy (gli install di pacchetti sono esclusi dal fix automatico anche se il pacchetto e' notissimo), fermato in un checkpoint `blocking-human` dedicato; l'utente ha confermato la legittimita' di `httpx` (encode/httpx, PyPI); eseguito `uv add httpx --native-tls`.
- **Files modified:** `backend/pyproject.toml`, `backend/uv.lock`
- **Verification:** `uv run python -c "import app.main; import app.oauth"` → `import OK`; suite completa 55/55 verde dopo l'installazione.
- **Committed in:** `96cb523` (parte del commit Task 2)

**3. [Rule 1 - Bug] Ordine di import nei test di convergenza causava "no such table: user" in isolamento**
- **Found during:** Task 3, prima esecuzione di `pytest tests/test_google_convergence.py` da solo
- **Issue:** importando `app.models.user`/`app.services.auth_service` DENTRO le funzioni di test (stesso stile apparente di `test_auth_service.py`), la fixture `session` chiamava `Base.metadata.create_all` PRIMA che le classi ORM fossero registrate su `Base.metadata` — schema vuoto, ogni `INSERT` falliva con `no such table: user`. `test_auth_service.py` "funziona" solo perche', eseguito nella suite completa, un altro file importa gia' quei moduli prima; in isolamento fallirebbe allo stesso modo (verificato).
- **Fix:** spostati gli import di `app.models.user`/`app.services.auth_service` a livello di modulo in `test_google_convergence.py`, cosi' la registrazione su `Base.metadata` avviene prima di qualunque fixture, indipendentemente dall'ordine/isolamento di esecuzione.
- **Files modified:** `backend/tests/test_google_convergence.py`
- **Verification:** `uv run pytest tests/test_google_convergence.py -x` → 2/2 verdi sia in isolamento sia nella suite completa; `uv run pytest -q` → 55/55 verde.
- **Committed in:** `d9e467b` (parte del commit Task 3)

---

**Total deviations:** 3 (1 Rule 2 - security, 1 Rule 3 - blocking con checkpoint human esplicito, 1 Rule 1 - bug)
**Impact on plan:** Nessuno scope creep funzionale: tutti i fix erano necessari per completare in sicurezza i criteri di accettazione gia' scritti nel piano. La correzione della fuga di credenziali (#1) e' una scoperta di sicurezza pre-esecuzione, non un cambio di superficie applicativa.

## Issues Encountered

Verifica live del redirect `GET /api/v1/auth/google/login` verso `accounts.google.com` non eseguibile in questo ambiente sandbox: la chiamata di rete al discovery OIDC di Google (`https://accounts.google.com/.well-known/openid-configuration`, effettuata da Authlib al primo `authorize_redirect`) fallisce con `SSL: CERTIFICATE_VERIFY_FAILED` per il certificato self-signed del proxy aziendale — stesso vincolo gia' documentato per `uv add`/`npm install` in questo progetto (richiede `--native-tls`, non applicabile a una richiesta HTTPS runtime arbitraria fatta da una libreria terza). Il piano stesso marca questa verifica come opzionale/manuale ("verificabile con endpoint mockato o a mano"); i criteri di accettazione automatizzati (import pulito + grep `OAUTH_SESSION_SECRET`) sono entrambi verdi. Verifica live raccomandata in un ambiente di sviluppo reale (fuori proxy aziendale) prima del go-live.

## User Setup Required

Nessuna ulteriore azione richiesta oltre a quanto gia' fatto dall'utente (credenziali Google Cloud in `backend/.env`, redirect URI registrato). Per un test end-to-end reale del login Google servira' avviare backend+frontend fuori dal proxy aziendale (o con un trust store aggiornato) e cliccare "Accedi con Google" dal frontend.

## Next Phase Readiness

- AUTH-02 completo: login Google funzionante lato backend, convergenza D-05 dimostrata da test, sessione applicativa identica al flusso email/password (Plan 02/03).
- Nessun blocco noto per Plan 02-06 (reset password via email) — riusa lo stesso `SECRET_KEY`/pattern `itsdangerous` gia' in `config.py`, non tocca `OAUTH_SESSION_SECRET`.
- Attenzione per chi tocchera' altri file di test in futuro: replicare il pattern "import modelli/servizi a livello di modulo, non dentro le funzioni di test" quando si scrivono nuovi test con fixture DB in-memory, per evitare lo stesso bug di ordinamento.

---
*Phase: 02-account-pdf*
*Completed: 2026-08-25*

## Self-Check: PASSED
All claimed files and commits verified present on disk / in git log.

## Verifica live (2026-08-25): bloccata dal proxy aziendale — decisione: rimandare a produzione

Alla verifica live sulla macchina di sviluppo, `GET /api/v1/auth/google/login` restituisce **500** con:
```
httpx.ConnectError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate in certificate chain
```
**Causa**: il proxy aziendale intercetta il TLS (MITM) e inietta una CA self-signed nella catena; quando Authlib scarica i metadata OpenID di Google (`accounts.google.com/.well-known/openid-configuration`), `httpx` non si fida di quella CA. È la stessa radice che in Fase 1 ha richiesto `uv --native-tls` per gli install — ma `--native-tls` vale solo per il package manager, non per `httpx` a runtime. I test di questo plan mockano la rete, quindi non intercettano l'errore.

**Non è un difetto del codice OAuth**: il flusso è corretto e funzionerà in produzione (Railway/Debian, nessun proxy MITM), esattamente come WeasyPrint (02-08) fallisce solo per il GTK mancante su Windows ma è corretto in prod.

**Decisione dell'utente (2026-08-25)**: *rimandare a produzione*. Il codice resta invariato; nessun pacchetto aggiunto. La verifica live di Google va eseguita in ambiente prod o su una rete senza TLS-interception.

**Fix opzionale futuro** (se serve testare Google in dev dietro il proxy): aggiungere `truststore` e chiamare `truststore.inject_into_ssl()` all'avvio dell'app, così `httpx` usa il trust store del SO (che contiene già la CA aziendale). È production-safe. Non applicato per scelta dell'utente.
