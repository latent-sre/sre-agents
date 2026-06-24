# Curation: what to keep, genericize, or drop when reusing this fleet

Prep notes for making the fleet reusable by another team / repo. Use this as the **review checklist** when
you vendor the fleet into a subdirectory and have an LLM pass over it (see
[INTEGRATION.md](INTEGRATION.md) for the mechanics of the subdirectory layout).

## Verdict up front

The fleet is **already clean of org-specific leakage** — there are no secrets, no real hostnames, and no
internal index/foundation names. Every stack reference file under `.claude/skills/*/references/` is a
**fill-in template** using `<placeholders>` (e.g. `<app_index>`, `api.sys.<PROD>.example.com`), and the one
real org name (`latent-sre`, in `LICENSE`) is already genericized. So this is **not** a scrubbing job.

The real decision is **portability vs. opinionation**: this fleet is deliberately built for *one* stack —
**on-prem + PCF (Tanzu), no Kubernetes, Python/Bash/PowerShell, Splunk/Wavefront/Moogsoft/ThousandEyes/
Grafana, GitHub Actions**. A different team keeps the universal scaffolding and swaps the stack layer.

Pick an adoption mode first, because it determines what "review and update" means:

- **Mode A — Same/similar stack (least work).** Keep everything; just fill in the `references/` files with
  your real values. Stop here. Most of this doc's "genericize" work is unnecessary for you.
- **Mode B — Different stack / truly "anyone can use it" (most work).** Keep Tier 1 verbatim, replace the
  Tier 2 stack skills with your equivalents, and genericize the Tier 3 environment framing.

## Tier 1 — Universal scaffolding (KEEP verbatim, any team/stack)

This is the crown jewel and is stack-agnostic. Do not remove these.

- **Fleet structure & enforcement:** the 10-agent roster pattern, read-only agents + `readonly-guard.py`,
  the `production-change-guard.py` gate hook, the `model:` policy + `validate_fleet.py` CI gate, the
  Copilot sync generator, and the `evals/` harness. *(Generic — only the example stack commands inside the
  guards are flavored; see Tier 2.)*
- **Ladders:** `sde-ladder`, `sre-ladder`.
- **Craft & method:** `craft` (Python/Bash/PowerShell/Go/TypeScript/React), `tdd-workflow`,
  `safe-refactor`, `debug-rca`, `self-improve-loop`.
- **Agent-system patterns (Anthropic):** `context-engineering`, `parallelization`, `tool-design`,
  `agent-security`.
- **Build-tooling shapes:** `ops-cli`, `api-design`, `spa-architecture`. *(Mostly stack-neutral; `api-design`
  has one `example.internal` server URL placeholder to leave as-is or swap.)*
- **Gates & routing:** `route-request`, `merge-gate`, `release-gate`, `production-change-gate`.
- **Incident & docs:** `incident-severity`, `blameless-postmortem`, `runbook-template`, `handoff-protocol`,
  `adr-template`.
- **Mostly-universal, light stack mentions (keep; tweak the named tools if you swap stacks):**
  `database-reliability` (Postgres/Oracle/MS SQL — broadly applicable), `instrument-service` (OpenTelemetry —
  vendor-neutral, just notes signals flow to Wavefront/Splunk), `slo-error-budget` (generic SLO math;
  mentions the stack only for where to query), `triage-golden-signals` (generic concept; lists where each
  signal lives on this stack), `github-actions-ci` (GitHub Actions — widely used).

## Tier 2 — Stack-specific skills (KEEP only if your stack matches; else SWAP or DROP)

These encode real value but only for a team on the same tools. For Mode B, replace each with your
equivalent (e.g. a `datadog-queries` skill in place of `wavefront-queries`) or delete it.

| Skill | Tied to | If your stack differs |
|---|---|---|
| `pcf-ops`, `pcf-deploy` | PCF / Tanzu (`cf` CLI) | Swap for your platform (e.g. a `k8s-ops` / `ecs-deploy` skill). These are the most PCF-coupled. |
| `rollback-mitigation` | PCF mitigation verbs (route remap, revision rollback) | Rewrite the mitigation actions for your platform; the *playbook structure* is reusable. |
| `splunk-triage` | Splunk SPL | Swap for your log tool (e.g. `loki-triage`, `elastic-triage`). |
| `wavefront-queries` | Wavefront / WQL | Swap for your metrics tool (`promql-queries`, `datadog-queries`). |
| `moogsoft-correlation` | Moogsoft / APEX AIOps | Swap or drop if you have no AIOps correlation layer. |
| `thousandeyes-network` | Cisco ThousandEyes | Swap or drop if you don't do synthetic/network monitoring. |
| `grafana-dashboards` | Grafana | Often portable as-is (Grafana is common); keep unless you use another dashboard tool. |
| `bamboo-to-actions-migration` | A one-time Bamboo→Actions migration | **Drop** unless you're actively migrating off Bamboo — it's the most disposable. |
| `ops-stack-integration` | Calling cf/Splunk/Wavefront/Moogsoft/TE/Grafana | Keep the *integration discipline* (timeouts, retries, pagination, idempotency); replace the named-tool examples. |

Also Tier-2-flavored (keep the mechanism, swap the example commands): the `cf`-write denylist inside
`production-change-guard.py` and the example commands in `readonly-guard.py`. The guard *logic* is generic;
the specific verbs it blocks are stack examples.

## Tier 3 — Environment framing baked into prose (GENERICIZE for a broad audience)

For Mode B, these assert "we are an on-prem PCF, no-Kubernetes shop" and will read as wrong to other teams:

- `AGENTS.md` — the **Environment** table (PCF/Splunk/Wavefront/Moogsoft/ThousandEyes/Bamboo) and the
  "Do **not** suggest Kubernetes / cloud-managed services" + "Know the boundary (BOSH, Diego, Gorouter…)"
  paragraphs. This is the single biggest concentration of stack opinion.
- `README.md` — the "Built for an application-operations team on on-prem + PCF, no Kubernetes…" blurb.
- `CLAUDE.md` — inherits the framing via the `@AGENTS.md` import; check the Claude-specifics section for
  PCF/`cf` mentions (e.g. the `pcf-deploy` hook example).
- Most **agent bodies** (`sre-engineer`, `sre-monitor`, `release-engineer`, `database-reliability`) name the
  stack tools in their lane descriptions; their *behavioral* guidance is generic.
- `runbooks/` — the three starters (PCF OOM, 5xx-after-deploy, dependency timeout) use Splunk SPL and PCF
  verbs. Keep as same-stack examples, or replace with your platform's equivalents.

The recommended Mode-B move is **not** to delete the stack entirely but to make it a **named, swappable
profile**: keep one "stack profile" section in `AGENTS.md` that a team edits in one place, and have skills
reference "your metrics tool / your log tool" generically. That preserves the fleet's concreteness (vague
agents are worse) while making the swap a single-file edit.

## Already clean — no action needed

- No secrets, tokens, or credentials anywhere (the `references/` files explicitly warn against committing
  them).
- No real hostnames/indexes/foundations — all `<placeholder>` or `example.com` / `example.internal`.
- `LICENSE` — MIT, copyright holder already genericized.
- Scripts are location-robust (resolve their own paths), so nesting in a subdirectory needs no code edits.

## The "vendor into a subdir, then LLM-review" workflow

1. Copy the fleet into the host repo under a subdirectory (e.g. `tools/sre-agents/`) and surface the
   root-magic files per [INTEGRATION.md](INTEGRATION.md).
2. Decide **Mode A or Mode B** (above) — this is the human call the LLM can't make for you.
3. Run an LLM review pass with a prompt like:

   > You are adapting a vendored AI-agent fleet (under `tools/sre-agents/`) for **our** team. Our stack is:
   > **[fill in: platform, CI, logs, metrics, dashboards, AIOps, synthetics, languages]**.
   > Using `docs/CURATION.md` as the map:
   > (a) Keep all **Tier 1** skills/agents unchanged.
   > (b) For each **Tier 2** skill, either keep it (our stack matches), rewrite it for our equivalent tool,
   >     or delete it — and update `AGENTS.md`'s skill list, `README.md`, and any agent that references it.
   > (c) Genericize the **Tier 3** framing to describe our environment; replace the PCF/no-K8s assertions.
   > (d) Fill in every `.claude/skills/*/references/*.md` with our real (non-secret) values.
   > After changes, run `python3 scripts/validate_fleet.py` and `bash scripts/sync-copilot.sh`, and fix any
   > drift. Report what you kept, swapped, and dropped, with file:line evidence.

4. Validate: `python3 scripts/validate_fleet.py` (CI gate) + re-run the Copilot sync.

## Quick "what would I delete first" answer

If the goal is the **leanest universal core**, drop in this order: `bamboo-to-actions-migration` (most
disposable) → `thousandeyes-network`, `moogsoft-correlation` (niche tools) → `wavefront-queries`,
`splunk-triage`, `pcf-ops`, `pcf-deploy`, `rollback-mitigation` (swap for your stack). Keep everything in
Tier 1. That leaves a portable agent-fleet skeleton any team can build on.
