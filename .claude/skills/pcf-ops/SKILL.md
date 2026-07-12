---
name: pcf-ops
description: >-
  Read-only PCF / Tanzu Application Service triage with the cf CLI (v8 / CAPI V3). Use when
  investigating a degraded or crashing app on PCF — checking app state, instances, recent platform
  events, logs, routes, services, and env. Lists the safe read-only commands for an SRE and flags the
  state-changing commands that require human sign-off via a human release owner.
compatibility: Requires the cf CLI v8 and access/auth to the target PCF foundation
---

# PCF / TAS read-only triage (cf CLI v8)

Our apps run on PCF (VMware Tanzu Application Service). cf CLI v8 talks to CAPI V3. **As `sre-engineer`
you observe only** — every command below is read-only. State-changing commands are listed last and
belong to a human release owner with human sign-off.

> **One-shot triage — run these four reads directly:**
> `cf target` → `cf app <app>` → `cf events <app> | head -n 25` → `cf logs <app> --recent | tail -n 120`.
>
> `scripts/triage.sh` / `triage.ps1` bundle exactly those four commands and remain **for humans**.
> Read-only agents are behind a `PreToolUse` guard that denies executing any local script, including
> these — deliberately. The guard used to carry a path-based exemption for them, but pinning a *path*
> does not pin the *content*: a reviewer works inside a checkout of untrusted code, so any PR could
> rewrite `triage.sh` and inherit its execution pass. The exemption bought no capability (the four
> commands are individually allowed) and cost a code-execution vector, so it was removed. Run the
> commands.
>
> Record our foundations, orgs/spaces, and app inventory in
> [references/foundations.md](references/foundations.md).

## App-side vs platform-side (know your lane)
We operate **our apps**; the **platform** (BOSH, Ops Manager, Diego cells, Gorouter, NTP/certs,
foundation capacity) is the platform team's. Fix app-side problems; **recognize and escalate**
platform-side ones — don't try to debug BOSH.
- **One app / route / instance affected ⇒ likely app-side** (yours).
- **Many apps failing at once, or failing/evacuating cells ⇒ platform-side** — escalate with evidence; don't keep digging.

**Escalation packet (a case they can act on, not a hunch):**
- **Symptom + start time** (UTC) and **trend** (growing / steady / recovering).
- **Blast radius** showing it's *not* just us: which/how many apps/routes/orgs/spaces, and the same
  symptom across apps you don't own (`cf events`, the foundation-wide signal that tipped you off).
- **Evidence our app is healthy:** `cf app <app>` (instances up), recent `cf events` (no crashes/OOM),
  `cf logs --recent` (clean), and nothing changed our side (no recent deploy/config flip).
- **What you already ruled out** app-side (deploy, config, dependency, capacity).
- **The platform signal** you saw: evacuating/failing Diego cells, foundation-wide 502s, cert/NTP, or
  `cf ssh`-to-`2222` timeouts (network path). Label anything `[unverified]`.

## Orient
```bash
cf target                      # current api / org / space — confirm you're looking at prod
cf apps                        # all apps in the space: state, instances, memory, routes
cf app <app>                   # one app: instance health, cpu/mem/disk per instance, routes, buildpack
```

## "What changed?" — the highest-value triage command
```bash
cf events <app>                # recent platform events: crashes, restarts, scaling, ssh, updates
```
Crashes/OOM, restage, scale, or an `audit.app.update`/`...droplet.create` lining up with the incident
start time is your prime suspect. Cross-reference with the release pipeline + `git log`.

## Logs
```bash
cf logs <app> --recent         # dump the recent buffer (start here)
cf logs <app>                  # live tail (RTR = router access logs, APP = app stdout/stderr)
```
RTR lines give status code + response time per request; APP lines are app logs. For history beyond the
buffer, go to Splunk (`splunk-triage`).

## Reading failures (exit codes, 502/503, health checks)

**App crashes — exit codes (`cf events` / `cf app`):**
- `Exited with status 137` = **OOM** — the container exceeded its memory quota and was killed. Mitigate
  with `cf scale -m` or tune the app/JVM heap (can also happen during cell evacuation).
- The app must listen on the platform-assigned **`$PORT`** (never a hardcoded port), or health checks
  fail and it crash-loops. A "1 starting / 1 down / 1 failing" pattern right after a push is usually
  memory or a `$PORT` mistake.

**Gorouter 502 vs 503 — app-side or platform-side?**
- **502 Bad Gateway** — Gorouter reached a backend but the response/connection failed: app crashed
  mid-request, exceeded the router timeout, or the **keep-alive race** — if the app's keep-alive idle
  timeout is **< 90s**, it can close a connection just as Gorouter reuses it → 502. Fix: set the app
  server's keep-alive idle timeout **> 90s** (the Gorouter side is a hardcoded 90s, not an operator-tunable
  knob — e.g. set Tomcat's `server.tomcat.keep-alive-timeout`). Usually app-side. Also seen
  **platform-side**: **clock skew** between Gorouter and a Diego cell makes the cell's TLS cert look
  not-yet-valid (`x509: certificate ... is not yet valid`), which CF surfaces as a **502**
  (`ExpiredOrNotYetValidCertFailure`) — an NTP/time-sync problem for the platform team; escalate with
  evidence, don't chase it app-side. *[sourced: CF router error docs; Broadcom KB 297999]*
- **503 Service Unavailable** — Gorouter has **no backend to route to**: all instances down/crashed, or
  the route isn't registered yet (registration lag right after a push). App-down or routing.
- **One route/app 502/503 while others are fine ⇒ app-side; foundation-wide ⇒ platform-side** (escalate).

**Health checks (`cf set-health-check` / manifest):**
- Types: **`port`** (TCP on `$PORT`), **`http`** (GET an endpoint, must return `200` — preferred for
  web), **`process`** (process alive only — for workers / `--no-route`).
- **Liveness** (default type `port`): on failure CF considers the instance crashed → **stops & restarts** it.
- **Readiness** (default type `process`): on failure CF **removes the instance from the route pool** (no
  traffic) but does **not** restart it.
- Slow `/health` timing out? raise the invocation timeout:
  `cf set-health-check <app> http --endpoint /healthz --invocation-timeout 10`.

## Drill in (read-only)
```bash
cf app <app> --guid            # app guid for CAPI queries
cf curl /v3/apps/<guid>/processes        # process/instance detail (read-only CAPI)
cf env <app>                   # env + bound-service creds — CAUTION: contains secrets; don't paste them
cf routes                      # routing: which routes map to which apps (blast radius)
cf services / cf service <name># bound backing services + last operation status
```

Treat `cf ssh` as privileged shell access, not read-only triage — even a harmless-looking remote shell
can mutate an instance. Read-only agents should not use it; get explicit human approval and hand off if
instance-shell inspection is truly needed.

## State-changing — NOT for sre-engineer (hand to a human release owner + human sign-off)
`cf restart` / `cf restage` / `cf scale` / `cf push` / `cf map-route` / `cf unmap-route` /
`cf set-env` / `cf stop` / `cf delete` / `cf cancel-deployment` / `cf continue-deployment` / `cf ssh`.
These are mitigations/deploys or privileged shell access — see `rollback-mitigation` and `pcf-deploy`.
Recommend them; let a human release owner execute.

## Tips
- `CF_TRACE=true cf <cmd>` shows the raw CAPI request/response when a command behaves oddly.
- App instances are ephemeral and numbered (`-i <n>`); a "fix" that only restarts one hides a recurring
  cause — capture logs/events first.
- Can't `cf ssh` (connection to port `2222` times out)? That's the SSH proxy / network path, not your
  app — a network/platform signal, not an app bug.
- Diagnose a bound backing service via **port-forwarding through the app container**:
  `cf ssh APP -L 63306:db.host:3306` then connect a local client to `localhost:63306`. Note `cf ssh` is
  **privileged shell access** (state-changing list above; the `readonly-guard` blocks it for read-only
  agents) — so this is a **human-run, approved** step, not sre-engineer read-only triage: recommend it and
  hand off. Even then the DB enforces its own access controls; don't run state-changing queries without the
  `production-change-gate`.
