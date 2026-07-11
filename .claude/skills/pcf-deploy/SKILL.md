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

Deploy so a bad release is **instantly reversible**. Default to **blue-green** for prod; use the
built-in rolling/canary strategy for lower-risk changes. **Prod deploys are prod-facing → confirm with a
human and clear `release-gate` + `production-change-gate` first.** Show the plan and rollback before
executing.

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

## Blue-green (classic, always-reversible) — preferred for prod
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
With app revisions enabled, `cf rollback checkout --version <n>` reverts to a prior droplet+config
(revisions/rollback are GA in cf CLI v8.10.0+; older v8.x marks them experimental).

## Config changes & scaling
```bash
cf set-env checkout KEY value && cf restage checkout   # env change requires restage to take effect
cf scale checkout -i 5            # horizontal: more instances
cf scale checkout -m 2G -k 2G     # vertical: memory/disk (causes restart)
```

## Verify every deploy
After cutover, check `cf app checkout` (all instances healthy) and the golden signals in Wavefront/
Grafana (the golden-signals reference in `sre-ladder`) before declaring success. Define abort criteria up front; if they
trip, roll back — that's success, not failure.

## Tip
`cf push` is destructive to the running app's lifecycle — never run it against prod without sign-off,
the manifest diff shown, and the rollback path confirmed.
