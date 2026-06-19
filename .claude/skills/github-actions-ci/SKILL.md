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
The **2025 tj-actions/changed-files compromise** (a popular action's tags were repointed to credential-
stealing code) is the cautionary tale — assume any action you don't pin can change under you.
- **Least-privilege token:** set `permissions:` explicitly; default to `contents: read` and grant only
  what's needed. Avoid the broad default token.
- **OIDC over long-lived secrets:** `permissions: { id-token: write }` lets a job mint a short-lived
  token from an OIDC-aware broker (a cloud IdP, Vault) at run time instead of storing static creds
  (`id-token: write` only grants *requesting* the token). On our PCF stack this rarely means a cloud
  IdP — deploy creds usually come from a self-hosted runner's internal store (CredHub auth is via UAA,
  not GitHub OIDC — see the PCF deploy notes below).
- **Pin third-party actions by full commit SHA** (tags are mutable), with the version in a trailing
  comment so updates stay legible: `- uses: actions/checkout@<40-char-sha> # v4.2.2`.
- **No script injection:** never interpolate `${{ github.event.* }}` (PR title/body, branch name, etc.)
  directly into a `run:` block — an attacker controls those strings and they execute in your shell.
  Pass them through a quoted `env:` var instead and reference `"$VAR"`.
- **Treat `pull_request_target` as dangerous:** it runs *your* workflow with repo secrets but can be
  triggered by untrusted fork PRs ("pwn request"). Don't check out + build fork code under it; prefer
  plain `pull_request` (no secrets) for untrusted contributions.
- Secrets via `secrets:` / environment secrets — never echo them; mask anything sensitive. Enable
  **secret scanning + push protection** on the repo.
- **Lint workflows in CI** with `actionlint` (syntax/expression bugs) and `zizmor` (security smells like
  the two above) so these regress loudly.

## Supply-chain provenance (releasable artifacts)
For artifacts you ship, attest where they came from: `actions/attest-build-provenance` plus an SBOM via
`actions/attest-sbom`, and verify downstream with `gh attestation verify`. This lets a consumer prove the
artifact was built by your pipeline from your source, not swapped in.

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
can use them. Prefer **`--ephemeral`** runners (one job per runner, fresh each time) so a poisoned job
can't persist and tamper with the next — and **never** attach self-hosted runners to public repos.

## Deploy to PCF from Actions (paste-ready)
Use a self-hosted runner with a pinned cf CLI v8 already installed (or install from an internal,
checksum-verified package). Authenticate from **environment** secrets, keep shell tracing off, and
understand the residual risk: `cf auth` takes the password as an argument, so run it only on a locked-down
or ephemeral runner. The deploy job is prod-facing → it belongs to `release-engineer` and gates on the
`production` environment (`release-gate`).
```yaml
deploy-prod:
  runs-on: [self-hosted, pcf]          # runner group with foundation network access
  environment: production               # required reviewers approve before this runs
  concurrency: { group: deploy-prod, cancel-in-progress: false }   # never cancel a deploy
  steps:
    - uses: actions/checkout@<pin-to-sha>
    - uses: actions/download-artifact@<pin-to-sha>   # promote the SAME artifact built earlier
      with: { name: app-build }
    - name: Verify cf CLI v8
      run: |
        cf version
    - name: Deploy
      env:                              # from environment secrets — not echoed, not in ps
        CF_API: ${{ secrets.CF_API }}
        CF_USERNAME: ${{ secrets.CF_USERNAME }}
        CF_PASSWORD: ${{ secrets.CF_PASSWORD }}   # residual argv exposure during cf auth; use locked-down runners
        CF_ORG: ${{ vars.CF_ORG }}
        CF_SPACE: ${{ vars.CF_SPACE }}
      run: |
        cf api "$CF_API"
        cf auth "$CF_USERNAME" "$CF_PASSWORD"
        cf target -o "$CF_ORG" -s "$CF_SPACE"
        cf push -f manifest.yml --strategy rolling   # or blue-green via route remap — see pcf-deploy
```
Prefer a CI **service account** with the minimum org/space roles and short-lived or frequently rotated
credentials. For cloud targets, OIDC to your cloud IdP avoids long-lived tokens (note:
GitHub-OIDC→CredHub is **not** a turnkey integration — CredHub authenticates via UAA, not GitHub OIDC
JWTs). Always clear `release-gate` + `production-change-gate` first.

## Tips
- Validate locally where possible (`act`, or `gh workflow run` + `gh run watch`).
- Reproduce a failing run from logs before editing blindly; most failures are env/permission/secret,
  not YAML syntax.
- The actual deploy step is prod-facing → it belongs to `release-engineer` and clears `release-gate` +
  `production-change-gate`.
