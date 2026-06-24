---
name: database-reliability
description: >-
  Make schema change safe, keep queries fast, and keep data durable — for the relational DBs our PCF
  apps bind to (Postgres, Oracle, MS SQL). Use for schema/migration changes, slow-query and DB-saturation
  issues, and database-driven incidents. Covers online/reversible migrations, the expand→contract +
  backfill + dual-write pattern, EXPLAIN/index/N+1 tuning, connection-pool/lock/replication-lag triage,
  and tested backups with RPO/RTO. Pairs with pcf-ops, sre-engineer, and slo-error-budget.
---

# Database reliability

Keep data **correct, durable, and fast**, and make schema change safe in production. Our apps run on
PCF and bind to managed relational services (Postgres / Oracle / MS SQL) — you operate at the
*application + data* layer, not the DB platform internals.

> **Safety rule (non-negotiable):** read-only inspection is fine; any **state-changing or prod-facing**
> action (running a migration, `UPDATE`/`DELETE`, killing a query, failover, scaling) needs explicit
> human confirmation and goes through `release-engineer` under `production-change-gate`. Show the plan
> **and** the rollback before acting.

## Migrations must be safe and reversible
- **Backward-compatible, online, no long table locks**, deployable without downtime. Every migration
  has a written **rollback path**.
- **Expand → contract** for any schema change the running code depends on:
  1. **Expand** — add the new column/table/index (nullable/with default that doesn't rewrite the table).
  2. **Backfill** — populate in batches; avoid one giant locking transaction.
  3. **Dual-write / dual-read** — new code writes/reads both old and new during the transition.
  4. **Switch** — flip reads to the new shape once backfill is verified.
  5. **Contract** — drop the old column/table in a *later* deploy, after nothing reads it.
- **Never rename or drop in a single deploy** that the currently-running code still uses.
- **Adding `NOT NULL` to an existing column** scan-locks the whole table while it validates every row.
  In Postgres, add the constraint as `CHECK (col IS NOT NULL) NOT VALID` first (cheap, takes a brief
  lock), backfill, then `VALIDATE CONSTRAINT` (which scans without blocking writes) — and set the column
  `NOT NULL` once validated. Don't `ALTER COLUMN … SET NOT NULL` directly on a hot, large table.
- Assess **lock behavior and duration on production-scale data**, not a tiny dev table. Know which DDL
  is online for your engine (e.g. Postgres `CREATE INDEX CONCURRENTLY`, `ADD COLUMN` without a volatile
  default; avoid blocking `ALTER`s on hot tables). Run migrations through tooling (Flyway/Liquibase/
  Alembic/`migrate`), not ad-hoc SQL.

## Performance is a feature
- Reproduce the slow query; read the plan with **`EXPLAIN` / `EXPLAIN ANALYZE`** (Postgres),
  `EXPLAIN PLAN`/AWR (Oracle), or the actual execution plan (MS SQL).
- **Index for the real query patterns** (composite/covering indexes match `WHERE` + `ORDER BY`); avoid
  full scans on hot paths, **N+1** query patterns (a `sde-engineer`/ORM smell), and **unbounded result
  sets** — paginate.
- Verify the fix with **measured before/after numbers**, not a hunch.

## Saturation & incident triage
When a DB-driven incident hits, check the cheap saturation signals first:
- **Connections** — pool exhaustion (app waits on a free connection); right-size the pool, find leaks.
- **Locks / blocking** — long-running transactions blocking others; find the head blocker.
- **Replication lag** — stale reads / failover risk; alert on it (`slo-error-budget`, `sre-monitor`).
- **Disk / IOPS / temp** — space and I/O saturation; runaway sorts/spills.
- **Recent migrations & deploys** — correlate with "what changed" (`sre-engineer`).

Mitigate to stop pain first (kill a runaway query, add capacity, fail over) **with confirmation**, then
diagnose. Pairs with `rollback-mitigation` for the deploy-side undo.

## Durability
- Backups **exist, are monitored, and — crucially — restores are tested**. An untested backup is a
  hope, not a recovery plan.
- Know your **RPO** (how much data you can lose) and **RTO** (how fast you must be back). Verify
  replication and failover; don't assume them.

## Least privilege & guardrails
- Scoped DB credentials; never the admin role from the app.
- Guard against destructive statements: **no unbounded `UPDATE`/`DELETE`** (require a `WHERE` + a row-
  count sanity check); wrap risky changes in a transaction you can roll back.

## Output format
- **Migrations:** the expand/contract plan, forward **and** rollback scripts, and a lock/risk assessment
  at production scale.
- **Performance:** the query plan before/after with the measured improvement.
- Never present a destructive change without its rollback and the stated safety check.

See also: `safe-refactor` (call-site/contract analysis); `sde-ladder` principal tier for
expand→contract design; `pcf-ops` (app-side triage); `craft` (Python) for parameterized SQL (no f-string injection).
