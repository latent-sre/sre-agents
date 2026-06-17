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
```bash
cf target                                  # confirm foundation/org/space first
.claude/skills/pcf-ops/scripts/triage.sh <app>             # Bash one-shot read-only triage
pwsh .claude/skills/pcf-ops/scripts/triage.ps1 -App <app>  # PowerShell one-shot read-only triage
cf apps                                     # everything in the current space
cf events <app> | head -n 25                # what changed
```
