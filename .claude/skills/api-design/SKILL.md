---
name: api-design
description: >-
  Design and build the HTTP API layer that fronts our ops tools — the backend our SPA GUIs and other
  services call. Use when adding or changing a REST/JSON endpoint, designing a service contract, or
  wrapping an ops capability (cf/Splunk/Wavefront/an internal script) behind an API. Covers contract-first
  OpenAPI, resource modeling, HTTP semantics + status codes, RFC 9457 problem+json errors, versioning
  (expand→contract), cursor pagination, idempotency keys, authN/Z, rate limiting, and PCF health checks.
metadata:
  domain: method
---

# API design

Build the API as a **contract first**, then implement it. The contract is what every consumer (our SPAs,
other teams, future you) reasons over — design it like a product, not an afterthought of the handler.
Match the repo's existing framework and conventions before applying the defaults below. Our APIs ship as
**PCF apps**; stay in the app lane (no API-gateway/cloud-managed infra — routing is `cf` routes).

## Contract-first
- Author/maintain an **OpenAPI 3.1** spec and treat it as the source of truth; generate server stubs and
  client types from it so server and consumers can't drift (the SPA consumes it via `spa-architecture`).
- Review the contract *before* writing the handler. A breaking change to a shipped contract is a
  principal-altitude change — load `sde-ladder-principal` and **expand→migrate→contract**.

## Resource modeling & HTTP semantics
- Model **nouns as resources**, plural collections (`/incidents`, `/incidents/{id}/events`). Reserve
  verb-y paths for genuine actions that aren't CRUD (`POST /deploys/{id}:cancel`).
- Use methods for their **semantics**: `GET` (safe, cacheable), `POST` (create/non-idempotent),
  `PUT`/`DELETE` (**idempotent**), `PATCH` (partial). Don't `GET` with side effects.
- **Status codes that mean something:** `200/201/202/204`; `400` (malformed) vs `422` (valid shape,
  bad value) vs `409` (conflict); `401` (who are you) vs `403` (not allowed); `404`; `429` (rate
  limited, with `Retry-After`); `503` (dependency down). Never `200` with an error in the body.
- **Long-running ops** (a deploy, a backfill): return `202` + a status resource the client polls; don't
  block the request thread on PCF.

## Errors — RFC 9457 problem+json
Return one consistent machine-readable shape, `application/problem+json`: `type` (stable URI), `title`,
`status`, `detail`, `instance`, plus your own fields (e.g. `errors[]` for field validation). Stable
`type`/codes are part of the contract — consumers branch on them. *[sourced: RFC 9457]*

## Collections
- **Cursor pagination** by default (opaque `cursor` + `limit`, return `next_cursor`); offset paging
  drifts and scans on large/changing sets. Cap `limit`.
- **Filter/sort by an allowlist** of fields only — never interpolate client input into a query (load
  `database-reliability`; parameterize).
- Make list responses envelope-consistent (`{ "data": [...], "next_cursor": ... }`).

## Safety & auth (server is the source of truth)
- **AuthN:** validate a bearer token (OIDC/OAuth2 via corp SSO/UAA) on **every** request; never trust a
  client-supplied identity/role. **AuthZ** per resource — check the caller may act on *this* object, not
  just that they're logged in (broken object-level authz is the classic API bug).
- **Validate every input** (pydantic/schema) — body, query, path, headers; reject unknown fields; bound
  sizes. **CORS** = explicit origin allowlist, never `*` with credentials. Set security headers.
- **Idempotency keys** for non-idempotent `POST` so a retried "restart"/"create" doesn't double-fire.
- **Rate-limit** and set request/time limits. **Never log secrets, tokens, or full bodies** (`python-craft`).
- Hand anything touching auth/crypto/untrusted input to `security-reviewer`.

## Framework & observability
- Python is primary → **FastAPI** (pydantic validation + async + OpenAPI for free); Flask is fine for
  something small; Go → `net/http`/chi. Use the language craft skill for the implementation.
- Emit **RED metrics + structured logs + trace propagation** (`instrument-service`) and expose a
  **health/readiness endpoint** so PCF and `pcf-deploy` can health-check the app.

## Definition of done
OpenAPI 3.1 spec committed and valid · errors are problem+json with stable types · auth **and**
per-object authz enforced server-side · inputs validated, CORS locked, limits + timeouts set ·
pagination capped · health endpoint present · tests cover the contract and the error paths.

## Handoffs
- → `spa-architecture` to build/refresh the GUI client against this contract.
- → `security-reviewer` (auth/input/CORS), `database-reliability` (queries/indexes behind it),
  `test-engineer` (contract + error-path coverage), `tool-design` if an agent will drive the API,
  `release-engineer` to ship it on PCF.
