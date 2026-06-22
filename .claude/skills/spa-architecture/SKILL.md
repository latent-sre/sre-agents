---
name: spa-architecture
description: >-
  Architecture for a single-page-app GUI over our ops-tool APIs — the browser client on top of an
  `api-design` backend. Use when standing up or extending a SPA: build/routing, server-state vs UI-state,
  a typed OpenAPI client, modern accessible styling, browser auth (OIDC+PKCE), web security
  (XSS/CORS/CSP/token storage), and building/serving the bundle on PCF. Pairs with `craft` (React).
metadata:
  domain: method
---

# SPA architecture

You're building a **GUI for an ops tool**: a single-page app in the browser talking to a JSON API. Keep
it a **thin, well-structured client over a well-designed API** (`api-design`) — business rules and authz
live on the server; the SPA renders state and collects intent. Match the repo's existing stack first.
Component-level React patterns live in `craft` (React); this skill is the app around them.

## Stack & structure (defaults)
- **Vite + React + TypeScript** (load `craft` (React), `craft` (TypeScript)). Organize by feature, not by
  file-type. Everything shipped to the browser is **public** — no secrets in the bundle or env.
- **Routing:** a client router (React Router / TanStack Router); **lazy-load** routes/code-split so the
  initial bundle stays small.

## Styling & look (modern, accessible by default)
Ops GUIs should look clean and current, not bespoke — **don't hand-roll a design system or pixel
values.** Defaults when the repo sets none:
- **Styling:** utility-first **Tailwind CSS** (or CSS Modules) over runtime CSS-in-JS (`styled-
  components`/Emotion add a runtime cost and fight Server Components). Drive everything from **design
  tokens / CSS variables** (color, spacing, radius, type scale) so theming and **dark mode** are one
  switch — most on-call work happens at night.
- **Components:** build on an **accessible headless primitive library** — **shadcn/ui** (copy-in
  components on **Radix UI**), Radix Themes, or Mantine — so dialogs, menus, and comboboxes get focus
  management and ARIA for free (this *is* your a11y story below). Don't reinvent a modal.
- **Look:** a consistent **spacing + type scale**, generous whitespace, one accent color, real
  empty/loading/**skeleton**/error states, and **lucide** (or similar) icons. Stay restrained — ops
  tools are read under stress; clarity and density beat decoration.
- **Data-dense views:** ops tools are mostly tables — use a real table primitive (**TanStack Table**)
  with sticky headers, sort/filter, status **badges**, and virtualization (see Performance). Desktop-
  first, but don't break on a laptop.

## Data: server-state vs UI-state (the load-bearing decision)
- Treat **server data as a cache, not app state.** Use **TanStack Query** (or RTK Query) for fetching:
  caching, background refetch, loading/error states, and mutations with invalidation. Don't hand-roll
  fetch-in-`useEffect` + global store — it's the top source of stale-data and waterfall bugs.
- Keep genuine **UI state** (modals, selection, form drafts) local with `useState`/context. See
  "you might not need an Effect" in `craft` (React).

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
for the few critical end-to-end paths. Test behavior as the user sees it (`craft` (React), `tdd-workflow`).

## Definition of done
Typed client generated from the live OpenAPI spec · server-state via a query cache (no fetch-in-Effect) ·
styled from tokens via headless accessible components (no bespoke modal), dark mode works · tokens not in
`localStorage` + CSP set · routes code-split, big lists virtualized · keyboard-accessible ·
SPA fallback works on refresh/deep-link on PCF · RTL/MSW green, critical e2e covered.

## Handoffs
- ← `api-design` for the contract this client consumes (build them together).
- → `security-reviewer` (auth/token storage/CSP/CORS), `test-engineer` (e2e depth),
  `release-engineer` to deploy the bundle on PCF, `sre-monitor` to dashboard client errors/RUM.
