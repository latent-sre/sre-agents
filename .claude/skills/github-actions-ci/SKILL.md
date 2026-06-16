---
name: github-actions-ci
description: >-
  Authoring and fixing GitHub Actions CI/CD pipelines for this team — reusable workflows, matrix builds,
  environments with deployment protection (approval gates), OIDC, caching, concurrency, least-privilege
  permissions, and self-hosted runners for on-prem/PCF access. Use when setting up or debugging a
  workflow, adding a deploy job, or hardening pipeline security.
metadata:
  domain: cicd
  tool: github-actions
---

# GitHub Actions CI/CD

We deploy via GitHub Actions (migrating off Bamboo — see `bamboo-to-actions-migration`). Build once,
promote the same artifact; gate prod with environments.

## Anatomy
- **Workflow** (`.github/workflows/*.yml`) → triggered by `on:` → contains **jobs** → each job runs
  **steps** on a **runner**.
- **Reusable workflow** (`on: workflow_call`, with `inputs`/`secrets`) — factor shared CI/CD so every
  repo calls one maintained pipeline:
  ```yaml
  jobs:
    build: { uses: my-org/.github/.github/workflows/build.yml@v1, with: {lang: python} }
  ```
- **Composite action** (`action.yml`) — package repeated steps.

## Deploy gates (native — use these as `release-gate` enforcement)
Use **environments** with **deployment protection rules**: required reviewers, wait timer, and
environment-scoped secrets. A job that targets a protected environment **pauses for human approval**:
```yaml
jobs:
  deploy-prod:
    environment: production        # required reviewers must approve before this runs
    concurrency: { group: deploy-prod, cancel-in-progress: false }
    steps: [...]
```

## Security (do this every time)
- **Least-privilege token:** set `permissions:` explicitly; default to `contents: read` and grant only
  what's needed. Avoid the broad default token.
- **OIDC over long-lived secrets:** `permissions: { id-token: write }` to mint short-lived cloud/CredHub
  creds at run time instead of storing static tokens.
- **Pin third-party actions by full commit SHA** (not a moving tag) — supply-chain safety.
- Secrets via `secrets:` / environment secrets — never echo them; mask anything sensitive.

## Make it fast & correct
- **Matrix** for multi-version testing: `strategy: { matrix: { python: ['3.11','3.12'] } }`.
- **Cache** deps with `actions/cache` (or `setup-*` built-in caching).
- **Concurrency** to cancel superseded runs on a branch: `concurrency: { group: ${{ github.ref }},
  cancel-in-progress: true }` (but **not** for prod deploys — never cancel a deploy mid-flight).
- Upload build outputs with `actions/upload-artifact`; download in the deploy job to promote the *same*
  artifact.

## Self-hosted runners (on-prem / PCF)
PCF foundations and on-prem services are usually not reachable from GitHub-hosted runners. Use
**self-hosted runners** (in runner groups, scoped to the repos/environments that need them) for jobs
that run `cf` against a foundation. Keep them patched and least-privileged; restrict which workflows
can use them.

## Tips
- Validate locally where possible (`act`, or `gh workflow run` + `gh run watch`).
- Reproduce a failing run from logs before editing blindly; most failures are env/permission/secret,
  not YAML syntax.
- The actual deploy step is prod-facing → it belongs to `release-engineer` and clears `release-gate` +
  `production-change-gate`.
