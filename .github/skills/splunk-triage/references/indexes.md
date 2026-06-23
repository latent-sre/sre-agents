# Our Splunk indexes & saved searches — fill in

Concrete values for the `splunk-triage` skill. The agent loads this on demand.

> Names and links only — no credentials.

## Indexes / sourcetypes by app
| App / service | `index` | `sourcetype` | `host` pattern |
|---|---|---|---|
| `<app>` | `<index>` | `<sourcetype>` | `<host-*>` |

## Correlation fields (so we can trace one request across services)
- Request/correlation id field: `<field_name>` (e.g. `request_id`, `traceId`, `x_request_id`)
- User/session id field: `<field_name>`
- If a service doesn't emit one, that's a finding → ask `sde-engineer` to add it.

## Field extractions we rely on
| Field | How it's extracted | Example |
|---|---|---|
| `status` | `<auto / props.conf / rex>` | HTTP status |
| `latency_ms` | `<rex pattern>` | per-request latency |

## Saved searches & dashboards
| Name | Link | Purpose |
|---|---|---|
| `<saved search>` | `<url>` | `<error-rate alert, etc.>` |
