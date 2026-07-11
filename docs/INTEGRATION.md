# Embedding the fleet in another repo (as a subdirectory)

This guide explains how to drop this fleet into an existing repository as a **subdirectory** (a vendored
folder) while keeping the agents and skills working. It is written for the "prep this side" case: the
content here is self-contained and portable; the only thing you must reconcile on the host side is the
handful of **root-magic files** that Claude Code and VS Code/Copilot only read from the **repo root**.

> **Note (2026-07-11):** this fleet no longer ships a CI workflow (`.github/workflows/validate.yml`) or
> Copilot-native `.github/agents/*.agent.md` wrappers — both tools read `.claude/` directly. The CI and
> Copilot-wrapper sections below are kept as **illustrative templates** if you choose to add your own; run
> `python3 scripts/validate_fleet.py` locally to validate.

## TL;DR

- **The scripts are already location-robust.** `scripts/validate_fleet.py` resolves its root from
  `__file__`. It runs correctly from any working directory and at any nesting depth — no edits needed.
- **The discovery files are NOT location-robust** — by design, the tools only look at the repo root:
  - Claude Code reads `./.claude/agents`, `./.claude/skills`, and `./CLAUDE.md` from the **repo root**.
  - VS Code/Copilot reads `./.claude/` from the **repo root** (this fleet does not ship `.github/agents/*.agent.md`
    wrappers — if you want them, provide your own in the host repo).
  - GitHub Actions only runs workflows in `./.github/workflows/` at the **repo root**.
- So: vendor the whole tree under a subdirectory for storage, then **surface** the root-magic files to the
  host root (symlink or copy). Pick one of the two strategies below.

## Recommended layout

```
host-repo/
├─ .claude/                 → surfaced from tools/sre-agents/.claude   (symlink or copy)
├─ CLAUDE.md                → surfaced from tools/sre-agents/CLAUDE.md  (symlink or copy)
├─ AGENTS.md                → surfaced from tools/sre-agents/AGENTS.md  (symlink or copy)
├─ .github/
│  └─ workflows/
│     └─ sre-agents-validate.yml   ← copy of this repo's validate.yml, path-adjusted (see CI section)
└─ tools/
   └─ sre-agents/           ← this entire repo, vendored verbatim
      ├─ .claude/
      ├─ AGENTS.md
      ├─ CLAUDE.md
      ├─ scripts/
      ├─ evals/
      ├─ docs/
      └─ ...
```

Choose any subdirectory path (`tools/sre-agents/`, `sre-agents/`, `.agents/`…). The examples below use
`tools/sre-agents/`.

## Strategy A — Symlink the root-magic files (recommended)

Keeps a single source of truth under `tools/sre-agents/`; the root entries are just pointers.

```bash
cd host-repo
ln -s tools/sre-agents/.claude  .claude
ln -s tools/sre-agents/CLAUDE.md CLAUDE.md
ln -s tools/sre-agents/AGENTS.md AGENTS.md
git add .claude CLAUDE.md AGENTS.md
```

- **Pros:** no duplication; updating the vendored folder updates everything.
- **Cons:** symlinks need `core.symlinks=true` (default on macOS/Linux; on Windows requires Developer Mode
  or admin). Claude Code and Copilot follow symlinked `.claude/` fine on POSIX checkouts. If your host repo
  already has a `.claude/`, `CLAUDE.md`, or `AGENTS.md`, you must merge instead — see "Collisions" below.

## Strategy B — Copy the root-magic files (Windows-safe, no symlinks)

```bash
cd host-repo
cp -r tools/sre-agents/.claude  .claude
cp     tools/sre-agents/CLAUDE.md CLAUDE.md
cp     tools/sre-agents/AGENTS.md AGENTS.md
```

- **Pros:** works everywhere, no symlink support required.
- **Cons:** two copies to keep in sync. Add a CI check (or a `make sync` target) that fails if
  `tools/sre-agents/.claude` and the root `.claude` diverge, or re-copy on each update.

## CI integration

This repo's `.github/workflows/validate.yml` assumes the repo root **is** the fleet. When the fleet is
nested, copy it to the host's `.github/workflows/` and pin every step to the subdirectory. The cleanest way
is a job-level `working-directory` default:

```yaml
name: Validate SRE agent fleet

on:
  pull_request:
    paths: ["tools/sre-agents/**"]   # only run when the fleet changes
  push:
    branches: [main]
    paths: ["tools/sre-agents/**"]

permissions:
  contents: read

jobs:
  validate:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: tools/sre-agents   # ← every `run:` executes here
    steps:
      - uses: actions/checkout@v4
      - run: python3 scripts/validate_fleet.py
      - run: python3 scripts/test_readonly_guard.py
      - run: python3 scripts/test_production_change_guard.py
      - run: python3 scripts/test_guard_cf_parity.py
      - run: |
          python3 -m pip install --quiet -r requirements-dev.txt
          python3 evals/run_evals.py --validate
          python3 evals/discovery_probe.py --validate
      - run: |
          python3 evals/test_graders.py
          python3 evals/test_discovery_probe.py
      - run: python3 .claude/skills/slo-error-budget/scripts/error_budget.py --slo 99.9 --window-days 28 --bad-minutes 10
```

Notes:
- `working-directory` does **not** apply to `uses:` steps, only `run:` steps — that's fine here.
- This fleet does **not** ship a `scripts/sync-copilot.sh` or `.github/agents/*.agent.md` wrappers — both
  Claude Code and Copilot read `.claude/` directly. If the host repo adds its own `.agent.md` wrappers and
  a drift gate, point the drift check at the host-root `.github/agents/` (not the vendored copy). If you
  only use `.claude/`-based discovery you can skip the drift gate entirely.
- The `tools/chaos_game.py` smoke-compile step from the original workflow is repo-demo scaffolding; keep it
  only if you vendor `tools/`.

## Collisions to reconcile

If the host repo already has any of these, you must merge rather than overwrite:

| Host file | What to do |
|---|---|
| `CLAUDE.md` | Append an `@tools/sre-agents/AGENTS.md` import (or paste the "Claude Code specifics" section) instead of replacing the host's guidance. |
| `AGENTS.md` | Merge the rosters/conventions; don't clobber the host's existing AGENTS.md. |
| `.claude/agents/` or `.claude/skills/` | Namespacing is by filename/dirname. Watch for name clashes (e.g. a host `researcher` agent). Rename one side if they collide. |
| `.github/workflows/` | Add the fleet workflow under a distinct filename (e.g. `sre-agents-validate.yml`); don't merge into an unrelated workflow. |

## What does NOT need changing

- All Python/Bash/PowerShell under `scripts/`, `evals/`, and the skills' bundled helpers resolve their own
  paths and run from any working directory.
- The `PreToolUse` hook commands in agent frontmatter use `scripts/readonly-guard.py` /
  `scripts/production-change-guard.py` **relative to the repo root Claude Code runs in**. If you surface
  `.claude/` at the host root via symlink (Strategy A), these resolve against the host root — so also ensure
  `scripts/` is reachable from the host root, or update the hook `command` paths to point at
  `tools/sre-agents/scripts/...`. (Copy strategy: same consideration.) Verify the hook actually fires in
  your environment — it's the one piece that can't be unit-tested offline.

## After integrating

Run the validator from the vendored folder to confirm nothing drifted:

```bash
cd host-repo/tools/sre-agents
python3 scripts/validate_fleet.py
```
