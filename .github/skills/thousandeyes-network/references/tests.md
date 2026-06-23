# Our ThousandEyes tests, agents & critical paths — fill in

Concrete values for the `thousandeyes-network` skill. The agent loads this on demand.

> Test names, agent labels, and links only — **no credentials or API tokens**.

## Enterprise agents (our on-prem vantage points)
| Agent label | Location / data center | Network it tests |
|---|---|---|
| `<agent>` | `<site>` | `<inside path to …>` |

## Test inventory
| Test | Type | Target | Agents | Alert rule | Runbook |
|---|---|---|---|---|---|
| `<checkout journey>` | web: transaction | `<url>` | `<cloud+ent>` | `<rule>` | `<runbook url>` |
| `<dep reachability>` | network: agent-to-server | `<host:port>` | `<ent>` | `<rule>` | `<runbook url>` |
| `<dns>` | dns server | `<record>` | `<…>` | `<rule>` | — |

## Critical user journeys & key dependencies (what must be covered)
| Journey / dependency | Covered by test | Owner |
|---|---|---|
| `<journey>` | `<test name>` | `<team>` |

## BGP / routing monitors
| Prefix / target | Monitor | Escalate to |
|---|---|---|
| `<prefix>` | `<BGP monitor>` | `<network/provider contact>` |

## Automation
- REST API base / account group: `<label>` (confirm the current API version against the docs; no token here).
- Test/alert-as-code location: `<repo path>` — changes via `release-engineer`/`sde-engineer`.
