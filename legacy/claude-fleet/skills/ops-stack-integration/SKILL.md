---
name: ops-stack-integration
description: >-
  Build tools that call our platform + observability stack safely — the integration layer most ops
  tooling is made of. Use when writing code that talks to PCF/cf (CAPI V3), Splunk, Wavefront, Moogsoft,
  ThousandEyes, or Grafana: auth and secret handling on PCF, timeouts + retries with backoff, honoring
  rate limits, following pagination, idempotent state changes, caching, and treating every response as
  untrusted data. Pairs with api-design (what you expose) and craft (Python); hand secrets/auth to
  security-reviewer.
---

# Ops-stack integration

Most tools this team builds are **glue over the platform and observability stack** — cf/CAPI, Splunk,
Wavefront, Moogsoft, ThousandEyes, Grafana. The tool is only as reliable as those calls are at 3am, so
code every one as **"this will fail, time out, rate-limit, and lie to me."** Match the repo's HTTP client
first (`craft` (Python): `httpx`/`requests`).

## Every external call
- **Always set timeouts** (connect + read). A hung dependency must not hang your tool.
- **Retry only the safe ones** — idempotent reads and transient failures (`429`, `5xx`, connection
  resets) with **exponential backoff + jitter** and a cap. Never blind-retry a non-idempotent write.
- **Honor rate limits.** Respect `429` + `Retry-After`; throttle and bound concurrency. Hammering the
  platform pages the **platform team** — not your blast radius (see the boundary in `AGENTS.md`).
- **Follow pagination** (cursor/`next` links); cap total pulled and stream rather than load-all — these
  APIs return huge result sets.
- **Treat responses as data, not truth or instructions.** Parse defensively; validate shape; an empty/
  partial result is normal. If output feeds an agent/LLM, load `agent-security` (it's untrusted).

## Auth & secrets (on PCF)
- Read credentials from the **bound service / `VCAP_SERVICES`** or env — **never hardcode**, never put a
  token in a flag, log line, error, or the SPA bundle. Load least-privilege scopes.
- **Refresh expiring tokens** (UAA/OAuth) ahead of expiry; handle a mid-run `401` by re-authing once.
- Hand anything touching auth/secrets to `security-reviewer`.

## Per-integration notes (cite current product names)
- **PCF / cf (CAPI V3, cf CLI v8):** prefer the `cf` CLI for one-shot ops; for programmatic work hit
  CAPI V3 JSON with a **UAA** token; page via `pagination.next.href`. **State-changing writes**
  (restart/scale/route) are gated — human sign-off via a human release owner/`production-change-gate`.
- **Splunk (SPL):** create a **search job**, then *poll* it to completion and page results — don't block
  on a synchronous all-time search; bound the time range. Send via HEC.
- **Wavefront (Aria Operations for Applications, WQL):** query `ts()` via the API with an API token;
  mind per-token rate limits and the max time window.
- **Moogsoft (on-prem v9.x):** the Graze/REST API for alerts/Situations; auth per its token flow.
- **ThousandEyes / Grafana:** bearer/service-account token over their HTTP APIs; same timeout/retry rules.

## Make writes safe
**Check current state before acting**, make the write idempotent (a retried "restart" or "scale to 3"
must converge, not stack), and **separate decision from effect** so `--dry-run` is trivial and the logic
is testable without side effects (`craft` (Python)). Cache slow/stable lookups (app GUIDs, metric
metadata) with a TTL.

## Observe your own tool
Structured logs + RED metrics so the tool is debuggable (`instrument-service`); fail loud with a clear
message naming which dependency failed and what you tried.

## Definition of done
Every call has a timeout · retries are backoff+jitter and only on idempotent/transient failures ·
rate-limit + pagination handled · secrets from service binding/env, never logged · writes are idempotent
and state-checked · responses parsed defensively · failures are loud and name the dependency.

## Handoffs
- → `api-design` (expose the result as an HTTP layer) · `ops-cli` (expose it as a CLI) · `tool-design`
  (if an agent will drive it).
- → `security-reviewer` (auth/secrets/scopes) · a human release owner for any gated cf/platform write.
