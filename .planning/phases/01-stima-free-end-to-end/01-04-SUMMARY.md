---
phase: 01-stima-free-end-to-end
plan: 04
subsystem: ui
tags: [react, vite, typescript, shadcn, radix, tailwindcss-v4, react-query, tanstack-query]

# Dependency graph
requires:
  - phase: 01-stima-free-end-to-end plan 03
    provides: "Public POST /api/v1/stima endpoint (anti-leak response contract: 4 category ranges + fixed extras + reconciling total + fallback/disclaimer)"
provides:
  - "Anonymous Free estimate flow: città/mq/tipo input form -> POST /api/v1/stima -> result screen"
  - "CityAutocomplete: free-text città input with a bundled ISTAT comuni (7904 entries) suggestion popover, mouse + keyboard selectable"
  - "Result screen: input summary, conditional fallback disclaimer, 4 neutral category range cards, fixed single-value extras line, accent total emphasis panel, soft-wall CTA cluster"
  - "frontend/src/api/stima.ts: typed StimaRequest/StimaResponse + postStima, normalizing Pydantic's Decimal-as-string wire format to plain numbers"
  - "shadcn/ui component set (radix base) themed with hand-authored Slate + blue-600 CSS variable tokens matching the UI-SPEC color table"
affects: [phase-2-auth-and-save, phase-3-pro-subcategories, phase-4-admin-panel]

# Tech tracking
tech-stack:
  added: [tailwindcss@4 (@tailwindcss/vite), shadcn@4.19.0 (radix base), radix-ui, cmdk, lucide-react, class-variance-authority, clsx, tailwind-merge, tw-animate-css, "@fontsource-variable/inter"]
  patterns:
    - "API boundary normalization: postStima() converts every Decimal-as-JSON-string field (Pydantic v2's default wire format) into a plain number once, in api/stima.ts, so the rest of the app only ever deals with numbers"
    - "cmdk Command + Radix Popover combobox pattern: never close the suggestion list on input onBlur (races with cmdk's click-based onSelect); close via explicit onSelect, Escape, or Radix's own outside-pointerdown dismissal on PopoverContent"
    - "Currency formatting centralized in lib/currency.ts (Intl.NumberFormat it-IT, 0 decimals) — formatEur/formatEurRange used everywhere a monetary value renders"
    - "Extras render as single fixed amounts (never a range); only the 4 category cards and the grand total show a min-max range, per the API's fixed-extras contract"

key-files:
  created:
    - frontend/components.json
    - frontend/src/index.css
    - frontend/src/data/comuni.json
    - frontend/src/lib/utils.ts
    - frontend/src/lib/currency.ts
    - frontend/src/api/stima.ts
    - frontend/src/components/CityAutocomplete.tsx
    - frontend/src/components/EstimateForm.tsx
    - frontend/src/components/CategoryCard.tsx
    - frontend/src/components/TotalCard.tsx
    - frontend/src/components/FallbackDisclaimer.tsx
    - frontend/src/components/SoftWallCta.tsx
    - frontend/src/pages/EstimatePage.tsx
    - frontend/src/components/ui/*.tsx (shadcn primitives - input, label, button, card, command, popover, radio-group, skeleton, alert, separator, badge, dialog, input-group, textarea)
  modified:
    - frontend/src/App.tsx
    - frontend/tsconfig.json
    - frontend/tsconfig.app.json
    - frontend/vite.config.ts
    - frontend/index.html
    - frontend/package.json

key-decisions:
  - "shadcn CLI has moved to a new generation (v4.19.0) since UI-SPEC/RESEARCH were written: no literal 'New York'/Slate preset exists anymore (presets are now nova/vega/maia/lyra/mira/luma/sera/rhea, with a separate --base radix/base/aria selector). Used --base radix (matches UI-SPEC's 'Component library: radix' requirement) with a minimal preset, then hand-authored the exact Slate + blue-600 CSS variable tokens from the UI-SPEC color table directly in index.css, overriding the CLI's own generated theme."
  - "FastAPI/Pydantic v2 serializes Decimal response fields as JSON strings (e.g. \"20400\", \"0.100\"), not numbers, to avoid float precision loss on the wire - not explicit in the 01-03 API contract doc. Normalized once at the API boundary in api/stima.ts (normalizeResponse) rather than scattering Number() calls through every consuming component."
  - "City autocomplete: removed onBlur-driven popover close (classic combobox bug - blur fires before cmdk's click-based onSelect, unmounting the option before its click handler runs). Closing is instead driven by onSelect, Escape, and Radix Popover's own outside-pointerdown dismissal, which correctly distinguishes an in-content click from an outside one."
  - "Autocomplete active-row highlight strengthened from bg-muted (slate-100, too subtle) to bg-primary/text-primary-foreground (solid blue-600 + white) per UI-SPEC's reserved accent usage #4 ('autocomplete active/highlighted row'); cmdk drives this from one shared state for both mouse hover and keyboard navigation, so no logic duplication was needed."

requirements-completed: [EST-01, EST-02, EST-06]

# Metrics
duration: ~58min
completed: 2026-08-24
---

# Phase 1 Plan 04: Free Estimate Frontend Summary

**Anonymous città/mq/tipo -> POST /api/v1/stima -> 4-category range + reconciling IVA-inclusive total result screen, built with shadcn (radix) on Tailwind v4, react-query, and a bundled 7904-comune ISTAT autocomplete.**

## Performance

- **Duration:** ~58 min (14:00-14:59 CET)
- **Started:** 2026-08-24T14:00:52+02:00
- **Completed:** 2026-08-24T14:58:48+02:00
- **Tasks:** 2 planned auto tasks + 1 human-verify checkpoint (2 rounds of post-checkpoint fixes requested and applied)
- **Files modified:** ~35 (shadcn scaffold + app code)

## Accomplishments
- Initialized shadcn (radix base) on Tailwind v4/Vite with the UI-SPEC's exact Slate + blue-600 design tokens (dominant slate-50, cards white/slate-200, blue-600 accent reserved for primary CTA/total panel/selected tipo/autocomplete highlight, amber for the fallback disclaimer), Inter font via `@fontsource-variable/inter`.
- Bundled the ISTAT comuni dataset (7904 comuni, `{nome, provincia}`) into `frontend/src/data/comuni.json` for a 100% client-side, zero-network autocomplete.
- `CityAutocomplete.tsx`: free-text città input (D-06 - any text is submittable) with a cmdk-in-Radix-Popover suggestion list, mouse- and keyboard-selectable (fixed post-checkpoint - see Deviations).
- `EstimateForm.tsx`: città + mq (m² adornment, numeric-only, min 1) + tipo (3 radio cards with D-02 descriptions, accent selected state, 44px min touch target), Italian inline validation, primary CTA disabled until all three valid.
- `api/stima.ts`: typed `StimaRequest`/`StimaResponse` contract mirroring 01-03's schema, `postStima()` calling `POST /api/v1/stima`, with wire-format normalization (Decimal-as-string -> number).
- `EstimatePage.tsx`: form -> `useMutation(postStima)` -> input summary (editable via "Modifica") + conditional amber fallback disclaimer + 2x2 (1-col mobile) neutral category cards showing IVA-inclusive ranges + fixed-extras line (single amounts, never a range) + accent `TotalCard` (reconciling grand total) + `SoftWallCta` (4 CTAs, "Disponibile a breve" feedback, no navigation); `skeleton` placeholders while loading, destructive `alert` + "Riprova" on error.
- Live-verified against the real backend: 85mq/totale/Reggio Emilia reconciles exactly - 4 category ranges (22.440+10.785+7.466+4.488) + fixed extras (2.806) = **47.985-70.575 EUR**, matching 01-03's pinned oracle; Modena returns `fallback=true` with the Reggio Emilia disclaimer.
- `grep` across `frontend/src` confirms no `0.65/0.6/0.55/0.5` coefficient literals or impresa references anywhere in the frontend source.

## Task Commits

1. **Task 1: shadcn init + design tokens + input form** - `faa8cae` (feat)
2. **Task 2: Result screen wired to POST /api/v1/stima** - `469b056` (feat)
3. **Post-checkpoint fix: city autocomplete options not selectable** - `0d7aaa9` (fix)
4. **Post-checkpoint fix: stronger active-suggestion highlight** - `7826d7f` (style)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `frontend/components.json` - shadcn config (style: radix-vega base, baseColor: slate)
- `frontend/src/index.css` - hand-authored Slate + blue-600 CSS variable tokens (UI-SPEC color table), Tailwind v4 `@theme inline`
- `frontend/src/data/comuni.json` - bundled ISTAT comuni dataset (7904 entries, `{nome, provincia}`)
- `frontend/src/lib/utils.ts` - `cn()` class-merge helper (shadcn convention)
- `frontend/src/lib/currency.ts` - `formatEur`/`formatEurRange` (`Intl.NumberFormat('it-IT', ...)`)
- `frontend/src/api/stima.ts` - typed `StimaRequest`/`StimaResponse`, `postStima`, wire-format normalization
- `frontend/src/components/CityAutocomplete.tsx` - free-text città input + suggestion popover (mouse/keyboard selectable, strengthened highlight)
- `frontend/src/components/EstimateForm.tsx` - città + mq + tipo inputs, validation, gated primary CTA
- `frontend/src/components/CategoryCard.tsx` - neutral category range card
- `frontend/src/components/TotalCard.tsx` - accent emphasis panel, reconciling total range
- `frontend/src/components/FallbackDisclaimer.tsx` - amber alert, conditional on `fallback=true`
- `frontend/src/components/SoftWallCta.tsx` - 4-CTA cluster, soft-wall feedback
- `frontend/src/pages/EstimatePage.tsx` - form -> mutation -> result screen assembly, loading/error states
- `frontend/src/components/ui/*.tsx` - shadcn primitives (input, label, button, card, command, popover, radio-group, skeleton, alert, separator, badge, dialog, input-group, textarea)
- `frontend/src/App.tsx` - mounts `EstimatePage` (replaces the Plan 01 health-check placeholder)
- `frontend/tsconfig.json`, `frontend/tsconfig.app.json` - `@/*` path alias
- `frontend/vite.config.ts` - `@tailwindcss/vite` plugin, `@` alias resolution
- `frontend/index.html` - `lang="it"`

## Decisions Made
See `key-decisions` in frontmatter: shadcn CLI generation drift (hand-authored tokens over CLI-generated theme), Decimal-as-string wire format normalization, autocomplete onBlur-race fix, and the strengthened active-suggestion highlight.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] shadcn CLI's classic "New York"/Slate preset no longer exists**
- **Found during:** Task 1 (`npx shadcn init`)
- **Issue:** The installed shadcn CLI (v4.19.0) is a different generation than RESEARCH/UI-SPEC assumed - no `new-york` preset, and the default `init -d` picked a "base-nova" preset on `@base-ui/react` (not Radix) with a neutral/grayscale theme, not Slate/blue-600.
- **Fix:** Re-initialized with `--base radix` (matches UI-SPEC's "Component library: radix" requirement) and the `vega` preset for component structure; reinstalled `button` with `--overwrite` to confirm it uses `radix-ui`/`@radix-ui/react-slot`, not `@base-ui/react`; uninstalled the leftover `@base-ui/react` and `@fontsource-variable/geist` packages; hand-authored the exact Slate + blue-600 CSS variable tokens (background/foreground/primary/accent/border/amber-\*) from the UI-SPEC color table directly in `index.css`, overriding the CLI's generated theme; set `components.json` `baseColor` to `slate`.
- **Files modified:** `frontend/components.json`, `frontend/src/index.css`, `frontend/package.json`
- **Verification:** `npm run build` passes; `grep -n "radix-ui" src/components/ui/button.tsx` confirms Radix usage; visual tokens match the UI-SPEC color table 1:1 (verified by inspecting rendered oklch values against the spec's hex table).
- **Committed in:** `faa8cae` (Task 1 commit)

**2. [Rule 1 - Bug] Backend serializes Decimal fields as JSON strings, not numbers**
- **Found during:** Task 2, live verification against the real `POST /api/v1/stima` endpoint
- **Issue:** FastAPI/Pydantic v2 serializes `Decimal` response fields as JSON strings (e.g. `"20400"`, `"0.100"`, `"800.00"`) by default, not JSON numbers - not explicit in the 01-03 API contract doc, discovered by curling the live endpoint. My initial TS types declared these fields as `number`, which would have broken `Intl.NumberFormat` rendering.
- **Fix:** Added `normalizeResponse()` in `api/stima.ts` to convert every monetary/percentage field from string to number once, at the API boundary, so the rest of the app (`CategoryCard`, `TotalCard`, extras line) only ever handles plain numbers.
- **Files modified:** `frontend/src/api/stima.ts`
- **Verification:** Live call to `POST /api/v1/stima` confirmed the reconciled total (47.985-70.575) renders correctly after normalization; `npm run build` passes.
- **Committed in:** `469b056` (Task 2 commit)

**3. [Rule 1 - Bug, post-checkpoint] City autocomplete suggestions were visible but not selectable**
- **Found during:** Human verification checkpoint (user report: "mi suggerisce il nome ma non posso selezionare dall'elenco")
- **Issue:** `CommandInput`'s `onBlur={() => setOpen(false)}` closed the Radix Popover synchronously on input blur, which fires on `mousedown` - before cmdk's `CommandItem` fires its `onSelect` (which cmdk triggers on the `click` event, confirmed by reading `node_modules/cmdk` source). The popover content (and the clicked item) was unmounted before the `click` event ever reached it, silently dropping every selection attempt (mouse and keyboard/Enter alike).
- **Fix:** Removed the `onBlur`-driven close entirely. Closing is now handled by three well-scoped triggers: explicit `onSelect` (successful selection), `Escape` keydown, and Radix Popover's own outside-pointerdown dismissal on `PopoverContent` (which correctly treats a click *inside* content as not-outside, so it no longer races with selection).
- **Files modified:** `frontend/src/components/CityAutocomplete.tsx`
- **Verification:** `npm run build` passes; confirmed via HMR that the dev server served the updated module; user re-tested in-browser and confirmed selection now works for both mouse and keyboard, and the selected città reaches `POST /api/v1/stima` correctly (Reggio nell'Emilia · 85 · Totale -> 47.985-70.575 EUR).
- **Committed in:** `0d7aaa9`

**4. [Rule 1 - Bug/polish, post-checkpoint] Active suggestion highlight too subtle**
- **Found during:** Human verification checkpoint, immediately after issue #3's fix was approved (user request: "deve anche diventare più scuro quello che sto selezionando")
- **Issue:** `CommandItem`'s active-row style used `bg-muted` (slate-100), too subtle to visually confirm which suggestion was about to be selected, and didn't match the UI-SPEC's reserved accent usage #4 ("autocomplete active/highlighted row").
- **Fix:** Changed the `data-selected` style in `ui/command.tsx` to `bg-primary`/`text-primary-foreground` (solid blue-600 + white). cmdk drives `data-selected` from one shared internal state updated by both mouse `onPointerMove` and keyboard Arrow navigation, so both input modes now share the identical, stronger highlight with no logic duplication.
- **Files modified:** `frontend/src/components/ui/command.tsx`
- **Verification:** `npm run build` passes; confirmed via HMR the dev server served the updated style.
- **Committed in:** `7826d7f`

---

**Total deviations:** 4 auto-fixed (1 blocking/tooling, 3 bug/polish - 2 of which were raised directly by the user at the human-verify checkpoint)
**Impact on plan:** All fixes were necessary to deliver the plan's own acceptance criteria (working, spec-matching UI) or were direct, in-scope corrections requested by the user during the mandated human-verify checkpoint. No scope creep beyond what verification surfaced.

## Issues Encountered
None beyond the four auto-fixed deviations above.

## User Setup Required
None - `frontend/.env` (`VITE_API_BASE=http://localhost:8000/api/v1`) is a local dev convenience file, matching the already-documented `.env.example` from Plan 01. No external service configuration required.

## Human Verification

**Checkpoint:** Full anonymous Free estimate flow (input form -> result screen), per plan's Task 3 (`checkpoint:human-verify`).
**Outcome:** Approved, after two rounds of post-checkpoint fixes (city autocomplete selectability, active-suggestion highlight contrast) requested by the user and applied as atomic commits (`0d7aaa9`, `7826d7f`).
**Verified in-browser by the user:** città autocomplete selection (mouse + keyboard), Reggio Emilia flow reaching the correct reconciled total (47.985-70.575 EUR), Modena fallback disclaimer, and the corrected suggestion highlight.
**Verified by the executor (no browser-automation tool available in this environment):** production build passes at every step; live HTTP calls to the real backend confirmed the reconciliation math, the fallback/disclaimer behavior, and the Decimal-as-string wire format; `grep` confirmed no impresa/coefficient leakage in `frontend/src`; HMR-served module content confirmed each fix reached the running dev server before commit.

## Next Phase Readiness
- The full anonymous Free estimate flow (EST-01, EST-02, EST-06) is live, human-verified, and human-approved end-to-end: città/mq/tipo -> `POST /api/v1/stima` -> 4 category ranges + fixed extras + reconciling IVA-inclusive total + conditional fallback disclaimer + soft-wall CTAs.
- The 4 soft-wall CTAs ("Passa a Pro", "Contatta un professionista", "Scarica PDF", "Salva / crea account") are wired to a no-op "Disponibile a breve" feedback, ready to be made real in Phase 2 (auth/save), Phase 3 (Pro subcategories), and Phase 4 (lead/PDF).
- `api/stima.ts`'s wire-format normalization pattern (Decimal-as-string -> number) should be reused by any future endpoint consuming `Decimal` fields from this backend.
- The `CityAutocomplete`/cmdk-Popover combobox pattern (no onBlur-close; onSelect/Escape/outside-pointerdown only) is now the reference implementation for any future autocomplete in this app.
- No blockers for Phase 2.

---
*Phase: 01-stima-free-end-to-end*
*Completed: 2026-08-24*

## Self-Check: PASSED

All 14 created/key files verified present on disk (`components.json`, `index.css`, `comuni.json`, `lib/utils.ts`, `lib/currency.ts`, `api/stima.ts`, `CityAutocomplete.tsx`, `EstimateForm.tsx`, `CategoryCard.tsx`, `TotalCard.tsx`, `FallbackDisclaimer.tsx`, `SoftWallCta.tsx`, `EstimatePage.tsx`, this SUMMARY.md); all 5 commits (`faa8cae`, `469b056`, `0d7aaa9`, `7826d7f`, `881e115`) verified present in `git log`.
