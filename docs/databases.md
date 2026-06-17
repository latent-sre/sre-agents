# Our databases — fill in

Concrete facts the [`database-reliability`](../.claude/agents/database-reliability.md) agent needs.
Names, versions, and links only — **keep credentials out of this file.**

## Engines & versions
| Database | Engine + version | Host / cluster | Owning team |
|---|---|---|---|
| `<app-db>` | `<Oracle 19c / PostgreSQL 15 / SQL Server 2019 / …>` | `<on-prem host>` | `<team>` |

## Durability (per database)
| DB | Backup schedule | Restore tested? (date) | RPO | RTO | Replication / failover |
|---|---|---|---|---|---|
| `<...>` | `<...>` | `<...>` | `<...>` | `<...>` | `<...>` |

## Connection / pool limits
- Max connections: `<...>`  ·  app pool size: `<...>`  ·  observed saturation point: `<...>`

## Migration tooling & conventions
- Tool: `<Flyway / Liquibase / Alembic / sqitch / …>`  ·  migrations live in: `<path>`
- Online-DDL notes for our engine: `<lock behavior; native online DDL / gh-ost / pt-osc; etc.>`
- Who executes prod migrations: **`release-engineer`** under the `production-change-gate`.
