---
name: spa-architecture
description: >-
  Architecture for building a single-page-app GUI that puts a usable front-end on our ops tools — the
  browser client over an `api-design` backend. Use when standing up or extending a SPA: project/build
  setup, routing, server-state vs UI-state, a typed API client generated from OpenAPI, forms+validation,
  browser auth (OIDC + PKCE), web security (XSS/CORS/CSP/token storage), accessibility, big-table
  performance, testing, and building/serving the static bundle on PCF. Pairs with react-craft.
metadata:
  domain: method
---

# SPA architecture

You're building a **GUI for an ops tool**: a single-page app in the browser talking to a JSON API. Keep
it a **thin, well-structured client over a well-designed API** (`api-design`) — business rules and authz
live on the server; the SPA renders state and collects intent. Match the repo's existing stack first.
Component-level React patterns live in `react-craft`; this skill is the app around them.

## Stack & structure (defaults)
- **Vite + React + TypeScript** (load `react-craft`, `typescript-craft`). Organize by feature, not by
  file-type. Everything shipped to the browser is **public** — no secrets in the bundle or env.
- **Routing:** a client router (React Router / TanStack Router); **lazy-load** routes/code-split so the
  initial bundle stays small.

## Data: server-state vs UI-state (the load-bearing decision)
- Treat **server data as a cache, not app state.** Use **TanStack Query** (or RTK Query) for fetching:
  caching, background refetch, loading/error states, and mutations with invalidation. Don't hand-roll
  fetch-in-`useEffect` + global store — it's the top source of stale-data and waterfall bugs.
- Keep genuine **UI state** (modals, selection, form drafts) local with `useState`/context. See
  "you might not need an Effect" in `react-craft`.

## Typed API client
Generate the client/types **from the OpenAPI spec** (`openapi-typescript`/`orval`) so the front-end and
`api-design` backend cannot silently drift. Regenerate on contract change; let `tsc` catch the breaks.

## Forms & validation
React 19 Actions (`useActionState`) or `react-hook-form` + a **zod** schema. Validate client-side for
UX, but the **server is the source of truth** — surface the API's problem+json field errors back onto
the form.

## Auth & web security
- **Auth:** OIDC **Authorization Code + PKCE** against corp SSO; **never** ship a client secret. Prefer a
  **BFF / httpOnly-cookie** session, or hold tokens **in memory** — **not `localStorage`** (XSS can
  exfiltrate it). Silent refresh; guard protected routes; treat the API's `401/403` as the real boundary.
- **XSS:** rely on framework escaping; avoid `dangerouslySetInnerHTML` on anything untrusted; set a
  **Content-Security-Policy**. **CSRF:** for cookie auth use `SameSite` + a CSRF token. Same-origin or a
  locked **CORS** allowlist (server-side, `api-design`). Hand sensitive flows to `security-reviewer`.

## Accessibility & performance (ops tools, used under stress)
- **A11y:** semantic HTML, real labels, keyboard-navigable, focus management, sufficient contrast; ARIA
  only to fill gaps. Aim WCAG 2.2 AA. *[sourced: WCAG]*
- **Perf:** code-split routes; **virtualize large tables/log lists**; avoid request waterfalls (parallel
  queries / prefetch). Show skeletons, not spinners-of-death.

## Build & serve on PCF
Build hashed static assets (`vite build`). Serve them via the **`staticfile`/`nginx` buildpack** or
co-serve from the API app; add the **SPA fallback** (rewrite unknown paths → `index.html`) so deep links
and refresh work, and cache-bust on the hashed filenames. Ship with `pcf-deploy`. Capture client errors/
RUM via `instrument-service`.

## Testing
**React Testing Library** + **MSW** (mock the API at the network layer) for components/flows; **Playwright**
for the few critical end-to-end paths. Test behavior as the user sees it (`react-craft`, `tdd-workflow`).

## Definition of done
Typed client generated from the live OpenAPI spec · server-state via a query cache (no fetch-in-Effect) ·
tokens not in `localStorage` + CSP set · routes code-split, big lists virtualized · keyboard-accessible ·
SPA fallback works on refresh/deep-link on PCF · RTL/MSW green, critical e2e covered.

## Handoffs
- ← `api-design` for the contract this client consumes (build them together).
- → `security-reviewer` (auth/token storage/CSP/CORS), `test-engineer` (e2e depth),
  `release-engineer` to deploy the bundle on PCF, `sre-monitor` to dashboard client errors/RUM.
