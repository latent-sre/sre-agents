# Branch Review — What We Can Learn From the Other Branches

**Date:** 2026-06-17 · **Reviewer branch:** `claude/review-skills-agents-branches-ip9agh`
**Method:** 3 independent deep scans (3 passes each: *architecture → content → gaps*) of every other branch, compared against HEAD.

---

## 0. The one-paragraph answer

All three branches are **alternative redesigns of the same fleet, not incremental improvements** — each one *deletes* our biggest differentiators (the PCF/Splunk/Wavefront/Moogsoft/ThousandEyes stack lane, `AGENTS.md`, the `readonly-guard.py` enforcement hook, `validate-fleet.ps1`, `sync-copilot`, `runbooks/`, the gate skills, `route-request`/`coordinator`, and the ladder skills). **Adopt none of them wholesale** — that would be a regression in stack fidelity and enforced ops maturity. **But each branch carries genuinely valuable ideas we lack**, and the highest-value ones cluster into three themes: *(1) missing language standards (Go/TS/React), (2) missing domains (database reliability, debugging/RCA, telemetry emission), and (3) missing documentation/discoverability (architecture rationale, handoff map, agent catalog).*

---

## 1. The branches at a glance

| Branch | One-line identity | Net change vs HEAD | Verdict |
|---|---|---|---|
| `elite-agent-architecture-n0q56b` | Generic, cloud/K8s + OpenTelemetry fleet; **domain-specialist agents** | +670 / **−3,486** | Mine for *domains*; reject the stack |
| `great-shannon-98cxyn` | Vendor-neutral, **research-backed** rewrite; **language standards + ADR + docs** | +1,935 / −3,446 | Mine for *standards + rationale docs* |
| `vscode-sre-sde-agents-eu1uvu` | **VS Code/Copilot-first**; named-seniority agents; **handoff + catalog docs** | +1,810 / −3,510 | Mine for *docs + content nuggets* |

> ⚠️ **Common regression in all three:** they drop `readonly-guard.py` (enforced read-only → becomes promise-only), gates, runbooks, the validator, the Copilot generator, and our PCF stack specificity. Several actively push **Kubernetes / Prometheus / Datadog / Terraform**, which violates our "on-prem + PCF, **No Kubernetes**, stay in the app/ops lane" charter.

---

## 2. Scorecard — us vs them

| Dimension | HEAD (ours) | elite | great-shannon | vscode | Who wins |
|---|:--:|:--:|:--:|:--:|---|
| Stack fidelity (PCF/Splunk/Wavefront…) | 🟢 | 🔴 | 🔴 | 🟡 | **Us** |
| Enforced read-only (hook) | 🟢 | 🔴 | 🔴 | 🔴 | **Us** |
| Gates (merge/release/prod-change) | 🟢 | 🔴 | 🔴 | 🔴 | **Us** |
| Routing selector (coordinator/route-request) | 🟢 | 🔴 | 🟡 | 🟡 | **Us** |
| Runbooks + helper scripts + references | 🟢 | 🔴 | 🔴 | 🔴 | **Us** |
| Validator + Copilot generator | 🟢 | 🔴 | 🔴 | 🔴 | **Us** |
| Seniority model | 🟢 ladder skills | 🟡 baked-in | 🟡 named agents | 🟡 named agents | **Us** (flexible) |
| Language coverage (Go/TS/React) | 🔴 *(claimed, not backed)* | 🔴 | 🟢 | 🔴 | **shannon** |
| Domain depth (DB / debug / instrument) | 🔴 | 🟢 | 🟡 | 🟡 | **elite** |
| Design-decision capture (ADR) | 🔴 | 🔴 | 🟢 | 🔴 | **shannon** |
| Architecture/rationale docs | 🔴 | 🟡 | 🟢 | 🟢 | **shannon/vscode** |
| Handoff map + agent catalog | 🟡 *(spread out)* | 🔴 | 🟡 | 🟢 | **vscode** |
| Per-agent `model:` tuning | 🟡 | 🟢 | 🟡 | 🟡 | **elite** |

🟢 strong · 🟡 partial · 🔴 absent/weak

---

## 3. Pros & cons of each branch

### 🟣 `elite-agent-architecture` — domain specialists
**Pros (theirs > ours)**
- **Domain agents we don't have:** `database-reliability`, `debugger`, `instrument-service` (skill). Dense, first-principles prose.
  - `debugger`: *"Reproduce → What changed? → rank hypotheses by likelihood & cheapness-to-test → test one at a time (`git bisect`) → causal chain: trigger → mechanism → failure → minimal fix + regression test."*
  - `database-reliability`: expand→contract + backfill + dual-write, `EXPLAIN`/N+1, connection-pool/replication-lag saturation, **tested restores + RPO/RTO**.
  - `instrument-service` **cardinality rule:** *"Bounded dimensions → metric labels. Unbounded identity (user/request/trace IDs, URLs, emails) → traces/logs, never metric labels."*
- `sde`: Conventional Commits → semver, **Two-Hats** rule, ~100-line change target, checkbox Definition of Done.
- Explicit per-agent `model:` (opus/sonnet/inherit).

**Cons (ours > theirs)**
- Ships **Kubernetes** quick-refs (`kubectl rollout undo`) — wrong runtime.
- `infrastructure-iac` agent (Terraform/K8s) is outside our lane.
- No stack grounding, no references, no helper scripts, weak handoff contracts, no gates/enforcement.

### 🔵 `great-shannon` — research-backed standards
**Pros (theirs > ours)**
- **6 language standards** incl. **Go / TypeScript / React** — which our `test-engineer` *already advertises* but nothing backs. Modern & specific:
  - go: *"wrap with `fmt.Errorf("…: %w", err)` only when you intend to expose it (Hyrum's Law)"; "always `defer cancel()`."*
  - ts: *"`strict: true` + `verbatimModuleSyntax` + `noUncheckedIndexedAccess`"; "`satisfies` to validate without widening."*
  - react: *"React Compiler v1.0 removes most manual `useMemo`/`useCallback`"; "user-interaction logic belongs in the event handler, not an Effect."*
- **`docs/ARCHITECTURE.md`** — *why* the fleet is shaped this way, with a model/tool matrix + **mermaid handoff diagram**.
- **`docs/RESEARCH.md`** — every design claim linked to a primary source with a currency date (practices our own "cite sources" rule, which we preach but don't document).
- **`adr-template`** (Nygard ADR + lightweight RFC): *"ADRs are immutable once accepted"; "name 3–5 specific reviewers."*
- **`code-review-checklist`** (Google eng-practices + Conventional Comments + SmartBear *"review 200–400 LOC; detection drops past ~400"*).
- `bash-standards` caveat we omit: *"`set -e` is suppressed in `if`/`while`/`$()`; use `shopt -s inherit_errexit`."*

**Cons (ours > theirs)**
- `sre-investigator`/`release-engineer` center **K8s/Prometheus/Datadog/Argo/AWS/Terraform** — hard charter violation.
- 4 of 6 agents reference **no skills**; some skill names don't match folders.
- Hard-pins seniority to "principal" — loses responder & elite/distinguished tiers.
- Self-flags that several RESEARCH.md figures are unverified — re-verify before copying.

### 🟢 `vscode-sre-sde-agents` — discoverability & Copilot-first
**Pros (theirs > ours)**
- **`docs/HANDOFFS.md`** — explicit collaboration map with ASCII flow diagrams + per-edge rules: *"sre-investigator → platform team when root cause is BOSH/Diego/Gorouter/foundation/certs"; "incident-commander → postmortem-writer: always after Sev1/Sev2."*
- **`docs/AGENT-CATALOG.md`** — narrative roster + a ranked **"future agents" roadmap** tied to our stack.
- Sharp content nuggets:
  - **researcher CISA-KEV-first:** *"check CISA KEV status first — NVD now fully enriches mainly KEV/critical, so KEV is the urgency signal, not the raw NVD score."*
  - **PCF mnemonics:** **exit 137 = OOM**; **Gorouter 502 vs 503** (502 = backend TCP/keep-alive/`max_attempts`; 503 = clock skew / `x509: certificate not yet valid`).
  - **code-review specificity:** exact **Bandit IDs** (B602/604/605, B105-107, B307, B506, B608) and **ShellCheck codes** (SC2086/2164/2155/**2115** → `"${dir:?}"` before `rm -rf`); **tj-actions** supply-chain + `pull_request_target` "pwn requests."
- Crisper app-vs-platform boundary wording in CLAUDE.md.

**Cons (ours > theirs)**
- No `scripts/` at all → read-only is prose-only; no validator; no Copilot generator.
- No gate skills, no runbooks (has the template, zero instances), no coordinator/route-request.
- Our `splunk-triage`/`wavefront-queries` keep the more operable touches (before/after-deploy comparison, "missing correlation id is a finding," `references/` fill-in files, hand-off to `sre-monitor`).

---

## 4. Gap matrix — what they expose in us

| Gap in OUR fleet | Seen on | Severity |
|---|---|:--:|
| No **Go / TypeScript / React** standards (yet `test-engineer` claims them) | shannon | 🔴 High |
| No **database-reliability** domain (migrations, EXPLAIN, replication, restores/RPO-RTO) | elite | 🔴 High |
| No **debug/RCA** primitive for failing tests / flaky builds (our RCA is incident-only) | elite | 🔴 High |
| No **architecture-rationale** doc (*why*, not just *what*) | shannon, vscode | 🔴 High |
| No **handoff map** + **agent catalog** as discoverable docs | vscode | 🟠 Med-High |
| No **ADR/RFC template** to capture design decisions | shannon | 🟠 Med |
| No **instrument-service** skill (how to *emit* telemetry; cardinality) | elite | 🟠 Med |
| researcher lacks **CISA-KEV-first** CVE rule | vscode | 🟠 Med |
| `security-reviewer` lacks explicit **OWASP Top 10:2025** mapping | elite | 🟠 Med |
| `code-reviewer`/`merge-gate` lacks **Bandit/ShellCheck IDs** + tj-actions note | vscode | 🟠 Med |
| `sde-engineer` lacks **Conventional Commits / Two-Hats / DoD** | elite | 🟠 Med |
| `bash-craft` missing **`inherit_errexit`** caveat | shannon | 🟡 Low-Med |
| No **PCF crash mnemonics** (exit 137, 502 vs 503) in triage skills | vscode | 🟡 Low-Med |
| No committed **`.github/copilot-instructions.md`** baseline | shannon | 🟡 Low |
| `wavefront-queries` missing **PromQL-bridge** + data-gap alert note | vscode | 🟡 Low |

---

## 5. Prioritized action plan — what to change & the benefit

### 🔴 HIGH — do first

| # | Change to OUR fleet | Source | Benefit |
|:--:|---|---|---|
| 1 | **NEW skills `go-standards`, `typescript-standards`, `react-standards`** (keep generic, not stack-coupled); wire into `test-engineer`/`sde-engineer` | shannon | Backs languages our agents already advertise but can't support; closes the biggest content gap |
| 2 | **NEW skill `database-reliability`** (adapt to Oracle/Postgres/MSSQL): online/reversible migrations, expand→contract+backfill+dual-write, `EXPLAIN`/N+1/index-for-pattern, pool/lock/replication-lag triage, **tested restores + RPO/RTO**; referenced by `sde-engineer` + `sre-engineer` | elite | Fills an entire missing domain; pairs with `pcf-ops` for DB-driven incidents |
| 3 | **NEW skill `debug-rca`** (reproduce → "what changed" → ranked parallel hypotheses → `git bisect` → causal chain → minimal fix + regression test); loaded by `sde-engineer` + `test-engineer` | elite | Gives non-incident RCA (failing tests, flaky builds) a home our fleet lacks |
| 4 | **NEW `docs/ARCHITECTURE.md`** — *our* rationale: PCF lane, why ladder-skills-not-agents, why gates+`readonly-guard`, coordinator-as-plan-output. Borrow their structure + mermaid map, not their generic content | shannon, vscode | Onboarding + a defensible "why"; we currently document only "what" |
| 5 | **NEW `docs/HANDOFFS.md`** — visual handoff map adapted to our roster (ladder skills, coordinator, gates); encode edges + the multi-agent constraint note | vscode | One discoverable picture of the fleet; complements `route-request` |
| 6 | **NEW `docs/AGENT-CATALOG.md`** — one paragraph per agent (lane, skills, escalation) + a "future agents" roadmap; cross-link from `AGENTS.md`/`README.md` | vscode | Makes the 11-agent fleet legible without reading 11 files |
| 7 | **NEW skill `adr-template`** (Nygard ADR + lightweight RFC); wire into `sde-ladder-principal`/`distinguished` | shannon | Captures design-decision *why*; our ladder skills produce designs but have no record format |

### 🟠 MEDIUM — high value, lower urgency

| # | Change to OUR fleet | Source | Benefit |
|:--:|---|---|---|
| 8 | **NEW skill `instrument-service`** (Wavefront/OTel-flavored): RED/USE emission, **cardinality rule**, `service.name`/version tagging, metric↔trace↔log correlation; feeds `slo-error-budget` | elite | Our obs lane only *reads* signals; this teaches teams to *emit* them well |
| 9 | **`researcher.md`** — add **CISA-KEV-first** CVE-triage rule | vscode | Materially better vuln prioritization for `security-reviewer`/`release-engineer` |
| 10 | **`security-reviewer.md`** — add explicit **OWASP Top 10:2025** (A01–A10 by ID) + a "should release be gated?" verdict line | elite | Modern taxonomy + clearer release-gating signal |
| 11 | **`code-reviewer.md` / `merge-gate`** — add specific **Bandit IDs / ShellCheck codes** (esp. SC2115) + **tj-actions SHA-pin / `pull_request_target`** notes | vscode | Higher-signal, grep-able review findings |
| 12 | **`sde-engineer.md`** (or `python-craft`/`safe-refactor`) — add **Conventional Commits → semver**, **Two-Hats**, ~100-line target, checkbox **DoD** | elite | Concrete commit/PR discipline; better diffs & reviews |
| 13 | **`triage-golden-signals` / `pcf-ops`** — add **exit 137 = OOM** + **Gorouter 502 vs 503** decision tree | vscode | Faster, more confident first response on the exact failures our PCF apps hit |
| 14 | **`CLAUDE.md` / `AGENTS.md`** — adopt crisper platform boundary (name BOSH/Ops Manager/Diego/Gorouter/foundation as platform-owned; "escalate with evidence") | vscode | Reduces mis-scoped investigations |
| 15 | **`bash-craft`** — add `set -e` suppression caveat (`inherit_errexit`) + `shfmt` note | shannon | Closes a genuine correctness gap |
| 16 | **NEW `docs/RESEARCH.md` (adapted)** — sourced findings for *our* stack claims (golden signals, SLO burn-rate windows, postmortem sections, PCF/`cf` practices); drop their K8s/cloud sections; **re-verify load-bearing numbers** | shannon | Practices our own "evidence over assertion" rule; makes recommendations auditable |

### 🟡 LOW — polish

| # | Change to OUR fleet | Source | Benefit |
|:--:|---|---|---|
| 17 | Add explicit per-agent **`model:`** (opus/sonnet/inherit split) across all agents | elite | Cost/quality tuning |
| 18 | Commit a thin hand-maintained **`.github/copilot-instructions.md`** baseline (keep `sync-copilot` for richer outputs) | shannon | Copilot users get conventions with zero generator step |
| 19 | **`wavefront-queries`** — add PromQL-bridge note + data-gap alert (`mcount(5m, ts(...)) <= N`) | vscode | Helps PromQL-fluent engineers; covers data-gap alerting we omit |
| 20 | Decide: **`code-review-checklist`** as a new skill *or* fold review-technique (priority order, Conventional Comments, 200–400 LOC sizing) into `code-reviewer`/`merge-gate` | shannon, vscode | Reviewers get a "how to review" reference distinct from the pass/fail gate |
| — | **Wire-up:** register all new skills in `route-request`, `AGENTS.md`, `README.md`; run `validate-fleet.ps1` | — | Keeps the selector + source-of-truth + validator authoritative |

---

## 6. Explicitly DO NOT adopt

- ❌ Deleting our **stack lane** (PCF/Splunk/Wavefront/Grafana/Moogsoft/ThousandEyes/`cf` CLI).
- ❌ Removing `readonly-guard.py`, the **gate skills**, **runbooks**, `validate-fleet.ps1`, `sync-copilot`, `route-request`/`coordinator`, the **ladder skills**.
- ❌ Renaming to **named-seniority agents** (we keep one `sde-engineer`/`sre-engineer` + ladder skills — more flexible & portable).
- ❌ Any **Kubernetes / Prometheus / Datadog / Terraform / AWS / `infrastructure-iac`** content — outside our charter; hand to the platform team.

---

## 7. Suggested sequencing

```
Wave 1 (High, content gaps)      Wave 2 (Medium, sharpening)        Wave 3 (Low, polish)
┌───────────────────────────┐    ┌───────────────────────────┐     ┌──────────────────────────┐
│ go/ts/react-standards (1)  │    │ instrument-service (8)     │     │ per-agent model (17)     │
│ database-reliability (2)   │ →  │ researcher KEV (9)         │  →  │ copilot-instructions(18) │
│ debug-rca (3)              │    │ security OWASP-2025 (10)   │     │ wavefront PromQL (19)    │
│ ADR template (7)           │    │ code-reviewer IDs (11)     │     │ review-checklist (20)    │
│ docs: ARCH/HANDOFFS/CATALOG│    │ sde commits/DoD (12)       │     └──────────────────────────┘
│      (4,5,6)               │    │ PCF mnemonics (13)         │
└───────────────────────────┘    │ platform boundary (14)     │
        then: wire into          │ bash inherit_errexit (15)  │
        route-request +          │ RESEARCH.md (16)           │
        validate-fleet           └───────────────────────────┘
```

> **Bottom line:** Keep our architecture and enforced safety — it is the most operationally mature of the four. Import *capabilities* (languages, DB, debug, instrument), *discoverability* (3 docs), and a handful of *sharp content nuggets* (KEV, PCF mnemonics, Bandit/ShellCheck IDs, Conventional Commits, OWASP-2025). That gives us the best of all three branches without sacrificing what makes ours safe and repeatable.
