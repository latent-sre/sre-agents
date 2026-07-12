# Our PCF / TAS foundations — fill in

Concrete values for the `pcf-ops` and `pcf-deploy` skills. The agent loads this on demand.

> **Keep secrets OUT of this file** — no passwords, tokens, or service keys. URLs, org/space names,
> and app inventory only. (This file is in version control.)

## Foundations
| Environment | `cf api` endpoint | Notes (UAA, who has access) |
|---|---|---|
| prod | `https://api.sys.<PROD>.example.com` | `<...>` |
| nonprod / staging | `https://api.sys.<NONPROD>.example.com` | `<...>` |
| dev | `https://api.sys.<DEV>.example.com` | `<...>` |

## Orgs & spaces (per foundation)
| Foundation | Org | Spaces |
|---|---|---|
| prod | `<org>` | `<space-a>`, `<space-b>` |

## Key app inventory
| App | Org / Space | Route(s) | Owner | Runbook |
|---|---|---|---|---|
| `<app>` | `<org>/<space>` | `<app>.apps.example.com` | `<team>` | `runbooks/<file>.md` |

## Handy read-only one-liners (fill in real names)

The four reads below ARE the triage sequence. Run them directly — read-only agents cannot execute
`scripts/triage.{sh,ps1}` (the guard denies local script execution; the scripts are for humans, and
they just run these same four commands).

```bash
cf target                                   # confirm foundation/org/space FIRST
cf app <app>                                # instance health, memory/cpu/disk, routes
cf events <app> | head -n 25                # what changed — crashes, restarts, scaling, updates
cf logs <app> --recent | tail -n 120        # last log buffer — stack traces / OOM / 5xx
cf apps                                     # everything in the current space
```
