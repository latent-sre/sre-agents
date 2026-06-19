# 🔍 Cross-Branch Review — Skills & Agents

**Date:** 2026-06-18 · **Reviewer branch:** `claude/branch-review-skills-agents-6pbvkd`
**Method:** 3 independent deep scans (inventory → content deep-read → gap analysis), one per branch, each
claim verified against our working tree.

> **📌 Status (updated 2026-06-19):** This is a **historical** review artifact — preserved for the
> rationale, not the live state. Its counts and recommendations describe a pre-adoption snapshot. Since
> then: **Recs 1–6 have all shipped** (CI/CD supply-chain hardening, `debug-rca`, `HANDOFFS.md`,
> `AGENT-CATALOG.md`, the review-standard note, PowerShell depth), the fleet now has **12 agents / 43
> skills** (not the 37 cited below), and the agent-system skills (`self-improve-loop`,
> `context-engineering`, `parallelization`, `tool-design`, `agent-security`) were added afterward. Read
> the recommendation table as "what we decided," already done.

---

## 🧭 TL;DR

> **Our branch is the most complete and the only one with *enforced* safety.** All three other branches
> are parallel attempts at the same fleet; none is a superset of ours. The high-value imports are
> **small and concrete**, not architectural. Adopt ~6 targeted changes; reject every structural redesign.

| | 👥 Agents | 🧩 Skills | 🔒 Read-only **enforced** | 🚪 Gates | 🪜 Ladders | 🛠️ Scripts/CI | 📚 Stack-bound |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **OURS** (`6pbvkd`) | **12** | **37** | ✅ `readonly-guard.py` + tests | ✅ 3 | ✅ 6 | ✅ | ✅ PCF/cf/SPL/WQL |
| `review-skills…ip9agh` | 11 | 36 | ✅ guard | ✅ 3 | ✅ 6 | ⚠️ no guard tests | ✅ |
| `vscode…eu1uvu` | 9 | 11 | ❌ prose only | ❌ | ❌ | ❌ | ✅ |
| `great-shannon…98cxyn` | 11 | 10 | ❌ prose only | ❌ | ❌ | ❌ | ❌ K8s/Terraform/PromQL |

**Verdict per branch:** 🟢 cherry-pick · 🔴 reject structure

- 🟢 **`review-skills…ip9agh`** — a near-twin, slightly behind us. Best ideas: **`debug-rca` skill**, **`HANDOFFS.md`**, **`AGENT-CATALOG.md`**.
- 🟢 **`vscode…eu1uvu`** — smaller, Copilot-oriented. Best idea: **CI/CD supply-chain hardening**; a few prose nuggets.
- 🔴 **`great-shannon…98cxyn`** — generic, pre-stack ancestor. **Violates our PCF/no-K8s charter.** Lift only a couple of phrasings.

---

## 🏗️ The one design decision they all tested (and we got right)

```
 THEIRS (great-shannon, vscode)            OURS
 ───────────────────────────────          ────────────────────────────
 senior-developer   ─┐                     sde-engineer ──loads──▶ sde-ladder-{senior,
 principal-developer ─┘ seniority                                   principal,distinguished}
 sre-investigator   ──  = separate         sre-engineer ──loads──▶ sre-ladder-{responder,
 postmortem-writer  ──  AGENTS             postmortem  ──loads──▶ blameless-postmortem (skill)
```

Two branches model **seniority as separate agents**. Our `AGENTS.md` deliberately rejects this
("*Seniority/experience is carried by skills, not separate agents*"). Our model is **strictly more
capable** — it adds `distinguished`/`elite` tiers their split lacks and avoids agent sprawl. Tellingly,
`vscode`'s own catalog lists `security-reviewer` and a monitor as *"future agents not yet built"* — i.e.
they planned what we already shipped. **No structural change warranted.** ✅

---

## 🎯 Recommended changes (ranked, all verified against our files)

Legend: 🔴 High · 🟡 Med · ⚪ Low · ✅ = confirmed absent/partial in ours today

### 🔴 1 — Harden `github-actions-ci` against CI/CD supply-chain attacks
- **Source:** `vscode…eu1uvu` → `github-actions` skill
- **Target:** `.claude/skills/github-actions-ci/SKILL.md` (+ one line in `security-reviewer.md`)
- **Today (verified):** we *do* recommend SHA-pinning ✅, but the skill is **silent** on everything else below.
- **Add:**
  - 🛑 **Script-injection rule:** never interpolate `${{ github.event.* }}` into `run:` — pass via quoted `env:`.
  - ⚠️ **`pull_request_target` "pwn request"** warning (untrusted code + secrets).
  - 🔏 **Build provenance / SBOM:** `actions/attest-build-provenance` + `gh attestation verify`.
  - 🧹 **Lint workflows:** `actionlint` + `zizmor`; the 2025 `tj-actions` compromise as the "why".
  - 🧨 `--ephemeral` self-hosted runners.
- **Benefit:** Closes the **one substantive security gap** found across all branches. This is dual-purpose
  (CI authors *and* `security-reviewer`/`code-reviewer` get a concrete checklist).

### 🔴 2 — Add a `debug-rca` skill (non-incident root-cause)
- **Source:** `review-skills…ip9agh` → `debug-rca` (clean, stack-neutral, high quality)
- **Target:** **new** `.claude/skills/debug-rca/SKILL.md` + **wire it in**
- **Today (verified):** ✅ absent. Our RCA is **incident-only** (`sre-ladder-*`); failing-test / flaky-build
  debugging has **no home**.
- **Add:** reproduce → "what changed" → rank hypotheses by *likelihood × cheapness-to-test* → `git bisect`
  → causal chain (`trigger → mechanism → failure`) → minimal fix **+ a regression test that fails without it**.
  Then reference it from `sde-engineer.md` and `test-engineer.md` bodies, the `AGENTS.md` skill catalog,
  and the `route-request` table.
- **Benefit:** Fills a real capability gap and pairs naturally with `tdd-workflow` + the SRE ladders.

### ✅ 3 — Add `docs/HANDOFFS.md` (fleet handoff map) — **DONE** (adopted from `review-skills…ip9agh`, 2026-06-18)
- **Source:** both `review-skills…` and `vscode…` ship one
- **Target:** **new** `docs/HANDOFFS.md` · **Today (verified):** ✅ added — adapted to our 12-agent roster (incl. `database-reliability`); §-refs repointed to our `ARCHITECTURE.md`/`CLAUDE.md`; linked from `README`, `AGENTS.md`, `ARCHITECTURE.md`
- **Add:** edge-by-edge flow diagrams for Build→review→ship and Operate→mitigate→learn, **plus the
  app-vs-platform escalation boundary** — *BOSH / Ops Manager / Diego cells / Gorouter / foundation / certs
  → platform team, with evidence (timestamps, scope, `cf` output showing our app is healthy)*. Adapt to our
  roster (we have the extra `database-reliability` agent + `incident-severity`/`instrument-service` skills).
- **Benefit:** Discoverable, one-picture handoff contract; sharpens our lane boundary.

### ✅ 4 — Add `docs/AGENT-CATALOG.md` (one page, all 12 agents) — **DONE** (adopted from `review-skills…ip9agh`, 2026-06-18)
- **Source:** both peer branches · **Target:** **new** `docs/AGENT-CATALOG.md` · **Today (verified):** ✅ added — 12 agents incl. `database-reliability`; `model:` assignments cross-checked against `CLAUDE.md` policy; future-agents roadmap kept; linked from `AGENTS.md`/`README`/`ARCHITECTURE.md`. (Rejected the branch's moogsoft edit: it regresses on-prem "Situations" → cloud "incidents".)
- **Add:** a paragraph per agent — lane · `model:` · writes? · skills it loads · handoff targets — and keep their
  ranked **"future agents" roadmap** (on-call/alert front-end, performance/capacity, knowledge agent). Include
  `database-reliability` (peer branches omit it).
- **Benefit:** Makes the 12-agent fleet legible without opening 12 files.

### 🟡 5 — State the "standard of review" in `code-reviewer` / `merge-gate`
- **Source:** `vscode…` + `great-shannon` `code-review-checklist`
- **Target:** `.claude/agents/code-reviewer.md` or `merge-gate/SKILL.md` · **Today (verified):** ✅ absent (we have Conventional Comments + verdicts, not the philosophy)
- **Add (1–2 lines):** *"Approve once the change definitely improves overall code health — don't block on
  perfection; block only on correctness/security/design regressions. Respond within one working day; 'LGTM
  with comments' is fine."* Plus the empirical sizing note: *defect detection drops past ~400 LOC / ~500 LOC/hr — a reviewer may reject solely for size.*
- **Benefit:** Calibrates reviewer strictness; prevents nit-blocking.

### 🟡 6 — Enrich `powershell-craft` with named specifics
- **Source:** `vscode…` `powershell-scripting` (111 lines vs our 59)
- **Target:** `.claude/skills/powershell-craft/SKILL.md` · **Today (verified):** ✅ absent
- **Add:** **SecretManagement + SecretStore** for automation secrets; named high-value **PSScriptAnalyzer**
  rules (`PSUseShouldProcessForStateChangingFunctions`, `PSAvoidUsingConvertToSecureStringWithPlainText`);
  cross-platform notes (`$IsWindows`/`$IsLinux`, `[IO.Path]::PathSeparator`, exact-case env vars on Linux);
  one line on script signing / Constrained Language Mode.
- **Benefit:** Our thinnest craft skill vs its analog; these are concrete and copy-usable.

### ⚪ 7 — Small content nuggets (low effort, high signal)
| Target in ours | Add | From |
|---|---|---|
| `pcf-ops/SKILL.md` | `cf ssh APP -L 63306:db.host:3306` port-forward as the legit diagnostic use of `cf ssh` | `vscode` |
| `blameless-postmortem/SKILL.md` | **"Where we got lucky"** section + **mitigative vs preventative** action-item column; ship an `assets/` fill-in like our other templates | `great-shannon` |
| `runbook-template/SKILL.md` | **runbook vs playbook vs SOP** taxonomy; Communication-cadence + Post-Incident sections; **Crawl→Walk→Run** automation-maturity note | `vscode` + `great-shannon` |
| `docs/ARCHITECTURE.md` | borrow the **"fresh-context review"** rationale (why reviewers are separate, read-only) + Decision/Why framing | `review-skills…` |
| `AGENTS.md` | vivid platform-boundary wording + cite the multi-agent fan-out heuristic (1 / 2–4 / more) | `vscode` |

---

## 🚫 Explicitly DO NOT adopt

| Tempting | Why reject |
|---|---|
| Seniority-as-separate-agents (`senior-developer`/`principal-developer`, `sre-investigator`) | Our **ladder skills** are more capable (extra `distinguished`/`elite` tiers) and avoid sprawl — by design. |
| `postmortem-writer` as a standalone agent | We fold it into the `blameless-postmortem` skill + `incident-commander`/`runbook-author`. |
| `*-standards` / `*-development` / `*-scripting` skill renames | Cosmetic churn; our `*-craft` / lane-suffix naming is consistent and referenced everywhere. |
| **Anything from `great-shannon`'s stack content** | Kubernetes, Terraform, PromQL, PagerDuty — **directly violates** our PCF/on-prem/no-K8s charter. |
| Dropping `readonly-guard.py`, gates, or guard tests to match a leaner branch | Our "*read-only is enforced, not promised*" guarantee is the fleet's key differentiator. |

---

## 📊 Where our gaps actually are (heatmap)

```
Capability area            ours   ip9agh   vscode   shannon   action
──────────────────────────────────────────────────────────────────────
Agent roster (breadth)      ███     ███      ██       ██       keep ours
Skill breadth               ███     ███      █        █        keep ours
Read-only enforcement       ███     ███      ·        ·        keep ours
CI/CD supply-chain depth    █·      ██       ███      ·        ADOPT  (Rec 1) 🔴
Non-incident RCA (debug)    ··      ███      ·        ·        ADOPT  (Rec 2) 🔴
Handoff/catalog docs        █·      ███      ██       █        ADOPT  (Rec 3,4) 🟡
Review philosophy stated    █·      ██       ███      ███      ADOPT  (Rec 5) 🟡
PowerShell depth            █·      █·       ███      █        ADOPT  (Rec 6) 🟡
Stack-correctness (PCF)     ███     ███      ███      ·        keep ours
```

---

## ✅ Suggested sequencing

1. **Security first** → Rec 1 (CI/CD hardening).
2. **Capability gap** → Rec 2 (`debug-rca` + wiring).
3. **Discoverability** → Rec 3 & 4 (`HANDOFFS.md`, `AGENT-CATALOG.md`).
4. **Polish** → Rec 5, 6, 7 (review philosophy, PowerShell, nuggets).

Each is additive and independently shippable behind `merge-gate`; none touches the agent topology.
