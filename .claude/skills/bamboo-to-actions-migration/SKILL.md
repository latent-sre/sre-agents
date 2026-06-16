---
name: bamboo-to-actions-migration
description: >-
  Migrate a CI/CD pipeline from Atlassian Bamboo to GitHub Actions — concept mapping, a step-by-step
  migration approach, and the common gotchas. Use when porting a Bamboo plan or deployment project to
  Actions, or planning the team's move off Bamboo. Pairs with github-actions-ci.
metadata:
  domain: cicd
  tool: github-actions
---

# Bamboo → GitHub Actions migration

We're moving off Bamboo. Migrate **one plan at a time**, run both in parallel until the Actions pipeline
is trusted, then retire the Bamboo plan.

## Concept mapping
| Bamboo | GitHub Actions |
|---|---|
| Plan | Workflow (`.github/workflows/<name>.yml`) |
| Stage (sequential gate) | Job(s) with `needs:` dependencies |
| Job (parallel within stage) | Job (jobs run in parallel by default) |
| Task | Step (`run:` or `uses:`) |
| Plan trigger (poll/push/scheduled) | `on:` (`push`, `pull_request`, `schedule`, `workflow_dispatch`) |
| Plan variables / global variables | `env:`, `vars` (repo/org variables), `secrets` |
| Agent / agent capability | Runner (GitHub-hosted or **self-hosted** + labels/runner groups) |
| Artifacts (shared between stages) | `actions/upload-artifact` / `download-artifact` |
| Deployment project | (Reusable) deploy workflow targeting an **environment** |
| Deployment environment + approvals | **Environment** + deployment protection rules (required reviewers) |
| Linked repositories | `actions/checkout` (+ multiple repos if needed) |
| Bamboo Specs (YAML/Java) | Workflow YAML (+ reusable workflows / composite actions) |

## Approach
1. **Inventory** the Bamboo plan: triggers, stages/jobs/tasks, variables (which are secret), artifacts,
   agent requirements (does it need on-prem/PCF network access → self-hosted runner), and deployment
   environments + approvers.
2. **Recreate build** first as a workflow: checkout → setup language → install → test → upload artifact.
   Get CI green before touching deploys. See `github-actions-ci`.
3. **Port variables:** non-secret → repo/org **variables**; secret → **secrets** (environment-scoped for
   deploy). Never paste secret values into YAML.
4. **Port deploy** as a separate job/reusable workflow targeting an **environment** with required
   reviewers — that's the Bamboo "deployment approval" equivalent and your `release-gate`.
5. **Map agents → runners.** Anything that runs `cf` against PCF needs a **self-hosted runner** with
   foundation access.
6. **Run in parallel.** Trigger both pipelines on the same commits; diff outputs/artifacts until Actions
   matches Bamboo. Then flip the source of truth and disable the Bamboo trigger.

## Common gotchas
- **Default-on triggers:** Bamboo polling ≠ Actions `on:` — be explicit, or you'll over/under-trigger.
- **Working directory & checkout:** Actions starts clean each run; nothing persists between jobs unless
  you pass it as an artifact or cache. Don't assume Bamboo's shared workspace.
- **Secret scope:** an org secret is broad; prefer environment secrets for prod creds.
- **Approvals:** Bamboo manual stages → environment required reviewers (not an `if:` you can bypass).
- **Parallelism:** stages were sequential by default; Actions jobs are parallel by default — add
  `needs:` to preserve ordering.
- Prod-deploy execution stays with `release-engineer` (+ `production-change-gate`).
