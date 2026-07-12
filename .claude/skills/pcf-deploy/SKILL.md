---
name: pcf-deploy
description: >-
  Deploy applications to PCF / Tanzu Application Service safely with the cf CLI (v8) — manifests,
  blue-green via route mapping, the rolling/canary strategies, env changes + restage, and scaling. Use
  when shipping to PCF or designing the deploy step of a pipeline. State-changing: prod deploys require
  human confirmation. Pairs with release-gate and rollback-mitigation.
compatibility: Requires the cf CLI v8 and authorized access to the target PCF foundation/space
# Claude-specific: a deploy is deliberately human-initiated. The model won't auto-invoke this
# playbook as an action; a human runs `/pcf-deploy` (or a human release owner applies it under human
# direction). Safety-in-depth on top of the release-gate hook. Copilot ignores this key.
disable-model-invocation: true
---

# PCF / TAS deploy (cf CLI v8)

Deploy so that reversing a bad release is **fast and rehearsed** — not because it is "instant", which is
a lie that gets told right up until the rollback that doesn't work. Default to **blue-green** for prod;
use the built-in rolling/canary strategy for lower-risk changes. **Prod deploys are prod-facing → confirm
with a human and clear `release-gate` + `production-change-gate` first.** Show the plan and rollback
before executing.

> ### ⚠️ What a rollback does NOT reverse
> A route swap or `cf rollback` reverses **code + start command + (revision-scoped) env vars**. It does
> **not** reverse:
> - **data and schema** — the migration the new version ran, and the rows it wrote. *A rollback after
>   an expand→contract migration's **contract** phase is not a rollback at all* — the column the old
>   code needs is gone. Sequence values are not returned either. This is the one that causes outages.
> - **service bindings**, **routes**, **scale** (instances / memory / disk quotas), **app features** —
>   none of these are captured in a revision.
> - anything a **consumer** already did with the new version's output (messages published, webhooks
>   fired, files written).
>
> Design the change so it is reversible (`database-reliability`: expand → backfill → dual-write, and do
> **not** contract until the old code is gone for good). "We can roll back" is a claim to **verify**,
> not assume.

**Starter:** copy `assets/manifest.yml` — a health-checked, multi-instance, service-bound manifest with
blue-green notes baked in.

## Manifest (declarative, in version control)
```yaml
# manifest.yml
applications:
- name: checkout
  instances: 3
  memory: 1G
  buildpacks: [java_buildpack_offline]
  routes:
  - route: checkout.apps.example.com
  env:
    SPRING_PROFILES_ACTIVE: prod
```
Bind services in the manifest or via `cf bind-service`. Keep secrets out of the manifest — use bound
services / CredHub.

## Blue-green (classic) — preferred for prod
*Reversible in the **routing** layer, which is the fast part — not in the data layer (see the box above).*

```bash
# 1. push the new version WITHOUT the prod route
cf push checkout-green -f manifest.yml --no-route
# 2. give it a temp route and smoke-test
cf map-route checkout-green apps.example.com --hostname checkout-green
#    ...run smoke tests against checkout-green...
# 3. cut over: add prod route to green, then remove it from blue
cf map-route   checkout-green apps.example.com --hostname checkout
cf unmap-route checkout-blue  apps.example.com --hostname checkout
# 4. keep blue running, healthy, and route-unmapped for fast rollback; delete only after a soak period
```
Rollback = re-map the prod route to `checkout-blue` and unmap green (see `rollback-mitigation`).

## Built-in strategies (simpler, for lower-risk changes)
```bash
cf push checkout -f manifest.yml --strategy rolling   # rolling: replaces instances incrementally
cf push checkout -f manifest.yml --strategy canary    # canary (cf CLI v8.8.0+/CAPI V3.173.0+): small % first, then `cf continue-deployment`
cf cancel-deployment checkout                         # abort an in-flight rolling/canary deploy
```
With app revisions enabled, `cf rollback checkout --version <n>` reverts to a prior droplet + config
(revisions/rollback are GA in cf CLI v8.10.0+; older v8.x marks them experimental).

> **Revisions capture less than people assume.** A revision holds a **droplet, a start command, and
> environment variables** — *not* routes, service bindings, or scale.
> - **Your real rollback window is ~5 droplets, not 100 revisions.** CF retains only the **five most
>   recent staged droplets**; you can roll back only to a revision still backed by one of them. A long
>   revision history is largely decorative. (CAPI keeps up to 100 revisions by default — the droplet
>   limit is the binding one.)
> - `cf rollback` **deploys a new revision** (the counter goes up); it does not rewind history.
> - **Cancelling ≠ rolling back.** `cf cancel-deployment` "does **not** guarantee zero downtime", and
>   **changes to environment variables and service bindings are not reverted**.

## Config changes & scaling
```bash
cf set-env checkout KEY value && cf restart checkout   # runtime-only var: RESTART is enough
cf set-env checkout JBP_CONFIG_X value && cf restage checkout   # buildpack-consumed: RESTAGE required
cf scale checkout -i 5            # horizontal: more instances
cf scale checkout -m 2G -k 2G     # vertical: memory/disk (causes restart)
```
> **"Env changes require a restage" is folklore.** It depends on **who consumes the variable**:
> - **`cf restart`** is enough when only the **app** reads it at runtime (feature flags, endpoints,
>   credentials). Restart reuses the already-compiled droplet — much faster, no rebuild.
> - **`cf restage`** is genuinely required when the **buildpack** consumes it at **staging** time, because
>   staging bakes it into the droplet (`JBP_CONFIG_*`, `BP_*`, `PIP_INDEX_URL`, `NODE_ENV` for pruning…).
>
> The blanket "TIP: use `cf restage`" that `cf set-env` prints is a **conservative default** — the CLI
> can't know whether your buildpack reads the var. Restaging when a restart would do costs you a full
> rebuild on every config flip. *(Note `cf env` shows the new value immediately while the running
> container still has the old one — the value is injected at container start.)*

## Verify every deploy
After cutover, check `cf app checkout` (all instances healthy) and the golden signals in Wavefront/
Grafana (the golden-signals reference in `sre-ladder`) before declaring success. Define abort criteria up front; if they
trip, roll back — that's success, not failure.

## Tip
`cf push` is destructive to the running app's lifecycle — never run it against prod without sign-off,
the manifest diff shown, and the rollback path confirmed.
