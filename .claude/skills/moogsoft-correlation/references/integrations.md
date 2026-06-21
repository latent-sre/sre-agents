# Our Moogsoft feeds, dedup keys & routing — fill in

Concrete values for the `moogsoft-correlation` skill. The agent loads this on demand.

> Names, integration IDs, and links only — **no credentials or API keys**.

## Event sources / integrations (feeds in)
| Source | Integration | Event fields we map | Notes |
|---|---|---|---|
| `<Splunk>` | `<integration name>` | `source/service/check → <fields>` | log alerts |
| `<Wavefront>` | `<integration name>` | `<fields>` | metric alerts |
| `<ThousandEyes>` | `<integration name>` | `<fields>` | synthetic |

## Dedup keys (so repeats collapse to one alert)
| Source | Dedup key formula | Watch-out |
|---|---|---|
| `<source>` | `<source>:<service>:<check>` | too broad merges unrelated; too narrow leaks dupes |

## Sigaliser tuning (Cookbook recipes / Tempus)
| Recipe | Clusters by (fields) | Validated against incident |
|---|---|---|
| `<recipe name>` | `<service, app, dependency>` | `<past incident link>` |

## Enrichment & routing
- Tags added to events: `<service>`, `<owner/team>`, `<runbook url>`.
- Situation → notify/page routing: `<policy / escalation by service>` (names/links only).

## Maintenance windows
- How deploys/patching suppress noise: `<window mechanism / schedule source>`.

## Health metrics we track
- alerts/Situation ratio: `<target>` · % auto-clustered: `<target>` · page volume: `<target>`.
