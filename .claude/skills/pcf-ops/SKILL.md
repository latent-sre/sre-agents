---
name: pcf-ops
description: >-
  Read-only PCF / Tanzu Application Service triage with the cf CLI (v8 / CAPI V3). Use when
  investigating a degraded or crashing app on PCF — checking app state, instances, recent platform
  events, logs, routes, services, and env. Lists the safe read-only commands for an SRE and flags the
  state-changing commands that require human sign-off via release-engineer.
metadata:
  domain: ops
  platform: pcf-tas
compatibility: Requires the cf CLI v8 and access/auth to the target PCF foundation
---

# PCF / TAS read-only triage (cf CLI v8)

Our apps run on PCF (VMware Tanzu Application Service). cf CLI v8 talks to CAPI V3. **As `sre-engineer`
you observe only** — every command below is read-only. State-changing commands are listed last and
belong to `release-engineer` with human sign-off.

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
RTR lines give status code + response time per request; APP lines give app logs. For history beyond the
buffer, go to Splunk (`splunk-triage`).

## Drill in (read-only)
```bash
cf app <app> --guid            # app guid for CAPI queries
cf curl /v3/apps/<guid>/processes        # process/instance detail (read-only CAPI)
cf ssh <app> -i 0              # inspect ONE instance read-only: top, ps aux, ls, cat logs — change nothing
cf env <app>                   # env + bound-service creds — CAUTION: contains secrets; don't paste them
cf routes                      # routing: which routes map to which apps (blast radius)
cf services / cf service <name># bound backing services + last operation status
```

## State-changing — NOT for sre-engineer (hand to release-engineer + human sign-off)
`cf restart` / `cf restage` / `cf scale` / `cf push` / `cf map-route` / `cf unmap-route` /
`cf set-env` / `cf stop` / `cf delete`. These are mitigations/deploys — see `rollback-mitigation` and
`pcf-deploy`. Recommend them; let release-engineer execute.

## Tips
- `CF_TRACE=true cf <cmd>` shows the raw CAPI request/response when a command behaves oddly.
- App instances are ephemeral and numbered (`-i <n>`); a "fix" that only restarts an instance hides a
  recurring cause — capture logs/events first.
