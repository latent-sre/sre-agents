#!/usr/bin/env python3
"""Gate B, mechanized: the audit's six Tier-2 bugs must never be ported into the new fleet.

Two halves, both required:
  1. FORBIDDEN: each known-bad string must appear NOWHERE under the new fleet trees
     (skills/, canonical/, generated/). Detection strings chosen from docs/AUDIT-2026-07-12.md
     against the live buggy files -- distinctive enough not to false-positive on fixed content
     (e.g. `cf auth` bare is the FIX; only the argv form is forbidden).
  2. SELF-ARM: each pattern must still match its known-bad legacy copy
     (legacy/claude-fleet/...). A detector that no longer detects is silently dead --
     the audit's through-line is "a check that reports success without executing the
     thing it names"; this half executes the thing.

Pure stdlib. Wired into scripts/gate_a.py. Exit 0 = clean, 1 = regression or dead detector.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEW_FLEET_DIRS = ("skills", "canonical", "generated")
LEGACY = os.path.join("legacy", "claude-fleet")

# (bug id, forbidden string, legacy file that self-arms it)
FORBIDDEN = [
    # 2.1 pcf-deploy: blue-green playbook never rotates names. `checkout-blue` is the ONLY
    # discriminator: the fixed playbook still (correctly) pushes green with --no-route -- what
    # changed is the rotation, so the never-created blue name is the bug's whole signature.
    ("2.1-blue-green", "checkout-blue",
     "skills/pcf-deploy/SKILL.md"),
    # 2.2 wavefront: fabricated WQL `by` clause. Detection is the FULL WQL line (the ts() call
    # makes it unambiguous) -- a bare ')) by (app)' would false-positive on valid PromQL postfix
    # aggregation in obs-metrics' promql.md. The comma form sum(ts(m), app) is the fix.
    ("2.2-wql-by", "sum(ts(app.http.requests.count)) by (app)",
     "skills/wavefront-queries/SKILL.md"),
    ("2.2-wql-caveat", "requires **parentheses** around the grouping keys",
     "skills/wavefront-queries/SKILL.md"),
    # 2.3 splunk: filter-before-bucket. `| where status>=500` alone is legitimate (base-search
    # scoping); the bug is the adjacency with `bin`, plus the sparse `stats count by _time`.
    ("2.3-spl-filter-first", "| where status>=500\n| bin _time span=5m",
     "skills/splunk-triage/SKILL.md"),
    ("2.3-spl-sparse-stats", "| stats count by _time",
     "skills/splunk-triage/SKILL.md"),
    # 2.4 error_budget.py: false all-clear + cosmetic window labels. NOTE: min(burn_long, burn_short)
    # is NOT a detection string -- the correct fix legitimately keeps it (both-windows = min >= threshold);
    # the bug's signatures are the else-branch's all-clear text and the free-label window args.
    ("2.4-budget-allclear", 'within budget (burn < 1x)',
     "skills/slo-error-budget/scripts/error_budget.py"),
    ("2.4-budget-cosmetic", "label for the long window",
     "skills/slo-error-budget/scripts/error_budget.py"),
    # 2.5 cf auth argv leak. Bare `cf auth` (env-fed) is the fix; the argument form is the bug,
    # as is the prose that teaches accepting the "residual" risk.
    ("2.5-cf-auth-argv", 'cf auth "$CF_USERNAME" "$CF_PASSWORD"',
     "skills/github-actions-ci/SKILL.md"),
    ("2.5-cf-auth-prose", "residual argv exposure during cf auth",
     "skills/github-actions-ci/SKILL.md"),
    ("2.5-cf-auth-risk-acceptance", "takes the password as an argument, so run it only on a locked-down",
     "skills/github-actions-ci/SKILL.md"),
    # 2.6 grafana: a data source that does not exist, recommended caveat-free.
    ("2.6-te-datasource", "external/synthetic from **ThousandEyes**",
     "skills/grafana-dashboards/SKILL.md"),
    ("2.6-te-uid-row", "| `<ThousandEyes>` | — | `<uid>` |",
     "skills/grafana-dashboards/references/dashboards.md"),
    # --- The two ECHO sites (found by the PR #61 harvest): the same audit bugs restated OUTSIDE
    # the sections the port tasks fix. Without these needles, 2.1 and 2.2 re-ship inside the very
    # skills that "fixed" them -- a bundled asset and a tips section, both invisible to the
    # section-scoped fixes. Confirm each self-arms on first run; if a needle does not match its
    # legacy file, the text drifted -- re-anchor it, do not delete it.
    ("2.1-echo-manifest-asset", "unmap the old app's route and delete it",
     "skills/pcf-deploy/assets/manifest.yml"),
    ("2.2-echo-wql-tips", "`by instance`/`by host`",
     "skills/wavefront-queries/SKILL.md"),
]

# 2.6, positive half: IF the new fleet ships obs-dashboards (Phase 3), it must carry the
# Enterprise-licensing caveat the old skill omitted. Conditional so Phases 1-2 stay green
# without being vacuous forever: once the file exists, the assertion bites.
CONDITIONAL_REQUIRED = [
    ("2.6-licence-caveat", os.path.join("skills", "obs-dashboards", "SKILL.md"), "nterprise"),
]

TEXT_EXTS = {".md", ".py", ".yml", ".yaml", ".json", ".sh", ".ps1", ".txt"}


def _read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read().replace("\r\n", "\n")


def _iter_files(base):
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for name in files:
            if os.path.splitext(name)[1] in TEXT_EXTS:
                yield os.path.join(root, name)


def main():
    os.chdir(ROOT)
    failures = []

    # Half 2 first: dead detectors invalidate half 1's green.
    for bug, needle, legacy_rel in FORBIDDEN:
        legacy_path = os.path.join(LEGACY, legacy_rel)
        if not os.path.exists(legacy_path):
            failures.append("SELF-ARM %s: legacy file missing: %s" % (bug, legacy_path))
        elif needle not in _read(legacy_path):
            failures.append("SELF-ARM %s: pattern no longer matches %s -- dead detector"
                            % (bug, legacy_path))

    for base in NEW_FLEET_DIRS:
        if not os.path.isdir(base):
            continue
        for path in _iter_files(base):
            content = _read(path)
            for bug, needle, _ in FORBIDDEN:
                if needle in content:
                    failures.append("REGRESSION %s: forbidden string ported into %s"
                                    % (bug, path))

    for bug, path, required in CONDITIONAL_REQUIRED:
        if os.path.exists(path) and required not in _read(path):
            failures.append("MISSING FIX %s: %s exists but never mentions %r"
                            % (bug, path, required))

    if failures:
        print("test_no_regressions: FAIL")
        for failure in failures:
            print("  " + failure)
        return 1
    print("test_no_regressions: PASS (%d forbidden patterns armed, %d conditional checks)"
          % (len(FORBIDDEN), len(CONDITIONAL_REQUIRED)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
