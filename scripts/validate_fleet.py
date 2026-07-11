#!/usr/bin/env python3
"""Validate the agent + skill fleet against the Agent Skills open standard and Claude Code's
subagent rules. Exits non-zero on any failure (CI-friendly).

Pure stdlib (no pip deps). YAML frontmatter is parsed by hand, line-oriented rather than via a real
YAML parser, on purpose — the fleet's frontmatter is deliberately simple and this keeps the CI gate
dependency-free. Runs the same on every platform (`python`/`python3`); this is the only validator.

Checks, per the spec at https://agentskills.io/specification :
  Skills  - SKILL.md present; YAML frontmatter present; `name` matches the parent directory, <= 64
            chars, lowercase a-z/0-9/hyphen with no leading/trailing/consecutive hyphen; `description`
            present, non-empty, <= 1024 chars; referenced files (references/ assets/ scripts/) exist.
  Agents  - frontmatter present; `name` valid charset and matches the filename; `description` present;
            read-only Bash agents declare the readonly-guard.py hook; model: matches the model policy.
  Scope   - no agent/skill *promotes* off-charter tooling (Kubernetes/IaC/Prometheus); our runtime is
            on-prem + PCF and observability is Wavefront/Splunk/Grafana. Charter disclaimers and
            portability/equivalence notes are allowlisted below.

From repo root:  python3 scripts/validate_fleet.py
"""

import os
import re
import sys

# lowercase alnum + single hyphens; no lead/trail/double hyphen
NAME_RE = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_lines(path):
    """Read a UTF-8 file as a list of lines without trailing newlines (mirrors Get-Content)."""
    with open(path, 'r', encoding='utf-8') as fh:
        text = fh.read()
    # splitlines() handles \n, \r\n, and \r consistently with Get-Content's line splitting.
    return text.splitlines()


def read_raw(path):
    with open(path, 'r', encoding='utf-8') as fh:
        return fh.read()


def get_frontmatter(path):
    """Return the frontmatter lines (between the first two '---' fences).

    Returns None if there are fewer than two fences (no frontmatter), or [] if the fences are
    empty/adjacent. Mirrors Get-Frontmatter in the .ps1.
    """
    lines = read_lines(path)
    dash = []
    for i, ln in enumerate(lines):
        if ln.strip() == '---':
            dash.append(i)
            if len(dash) == 2:
                break
    if len(dash) < 2:
        return None
    if dash[1] <= dash[0] + 1:
        return []
    return lines[dash[0] + 1:dash[1]]


def get_field(fm, key):
    """Return the value of a top-level-ish frontmatter field, or None.

    Mirrors Get-Field: first line matching `^\\s*<key>\\s*:` with the `<key>:` prefix stripped and
    trimmed. The PowerShell `-replace` is non-anchored, but because we already matched the prefix at
    the line start the result is equivalent to stripping the leading `key:`.
    """
    key_match = re.compile(r'^\s*' + re.escape(key) + r'\s*:')
    strip_re = re.compile(r'^\s*' + re.escape(key) + r'\s*:\s*')
    for ln in fm:
        if key_match.search(ln):
            return strip_re.sub('', ln, count=1).strip()
    return None


def has_field_line(fm, key):
    """True if any frontmatter line matches `^\\s*<key>\\s*:` (presence of the key)."""
    key_match = re.compile(r'^\s*' + re.escape(key) + r'\s*:')
    return any(key_match.search(ln) for ln in fm)


def description_length(fm):
    """Compute the folded-description length the same way the .ps1 does.

    Start collecting at a line matching `^description\\s*:` (anchored at column 0, no leading space),
    stripping any folded-block marker (>-, >, |). Continue appending trimmed lines until a line that
    looks like a new top-level key (`^[a-zA-Z_]+\\s*:`). Join with single spaces and trim.
    """
    desc = []
    in_desc = False
    start_re = re.compile(r'^description\s*:')
    strip_re = re.compile(r'^description\s*:\s*(>-|>|\|)?\s*')
    key_re = re.compile(r'^[a-zA-Z_]+\s*:')
    for ln in fm:
        if start_re.search(ln):
            in_desc = True
            desc.append(strip_re.sub('', ln, count=1))
            continue
        if in_desc:
            if key_re.search(ln):
                break
            desc.append(ln.strip())
    return len(' '.join(desc).strip())


# Referenced-bundle-file extraction. Mirrors the .ps1 regex:
#   (?<![\w./])(references|assets|scripts)/[A-Za-z0-9._/-]*[A-Za-z0-9_-]
REF_RE = re.compile(r'(?<![\w./])(references|assets|scripts)/[A-Za-z0-9._/-]*[A-Za-z0-9_-]')
TRAIL_PUNCT_RE = re.compile(r'[.,;:)\]]+$')


def main():
    issues = []

    # ---- Skills ----
    skills_dir = os.path.join(ROOT, '.claude', 'skills')
    skill_count = 0
    skill_dirs = sorted(
        d for d in os.listdir(skills_dir)
        if os.path.isdir(os.path.join(skills_dir, d))
    )
    for name_dir in skill_dirs:
        dfull = os.path.join(skills_dir, name_dir)
        sk = os.path.join(dfull, 'SKILL.md')
        if not os.path.exists(sk):
            issues.append("skill '%s': missing SKILL.md" % name_dir)
            continue
        skill_count += 1
        fm = get_frontmatter(sk)
        if fm is None:
            issues.append("skill '%s': no YAML frontmatter" % name_dir)
            continue

        name = get_field(fm, 'name')
        if not name:
            issues.append("skill '%s': missing name" % name_dir)
        else:
            if name != name_dir:
                issues.append("skill '%s': name '%s' != directory" % (name_dir, name))
            if len(name) > 64:
                issues.append("skill '%s': name > 64 chars" % name_dir)
            if not NAME_RE.search(name):
                issues.append("skill '%s': name '%s' fails charset rule" % (name_dir, name))

        if not get_field(fm, 'description'):
            # description may be a folded block; treat presence of the key as satisfied.
            if not has_field_line(fm, 'description'):
                issues.append("skill '%s': missing description" % name_dir)

        desc_len = description_length(fm)
        if desc_len == 0:
            issues.append("skill '%s': empty description" % name_dir)
        if desc_len > 1024:
            issues.append("skill '%s': description %d > 1024 chars" % (name_dir, desc_len))

        # referenced bundle files exist (references/ assets/ scripts/).
        body = read_raw(sk)
        for m in REF_RE.finditer(body):
            rel = TRAIL_PUNCT_RE.sub('', m.group(0))  # drop trailing prose punctuation
            if not rel.strip():
                continue
            # Skip a bare directory reference (no filename component, e.g. "assets/").
            leaf = rel.rstrip('/').split('/')[-1] if rel.rstrip('/') else rel
            if leaf in ('references', 'assets', 'scripts'):
                continue
            # Resolve against the skill's own bundle first, then fall back to the repo root: a SKILL.md
            # may legitimately reference a SHARED repo-root script (e.g. scripts/readonly-guard.py).
            if not os.path.exists(os.path.join(dfull, rel)) and not os.path.exists(os.path.join(ROOT, rel)):
                issues.append("skill '%s': references missing file '%s'" % (name_dir, rel))

    # ---- Agents ----
    agents_dir = os.path.join(ROOT, '.claude', 'agents')
    agent_files = sorted(
        f for f in os.listdir(agents_dir)
        if f.endswith('.md') and os.path.isfile(os.path.join(agents_dir, f))
    )
    for a in agent_files:
        afull = os.path.join(agents_dir, a)
        base = a[:-3]  # strip .md (BaseName)
        fm = get_frontmatter(afull)
        if fm is None:
            issues.append("agent '%s': no YAML frontmatter" % a)
            continue
        name = get_field(fm, 'name')
        if not name:
            issues.append("agent '%s': missing name" % a)
        else:
            if name != base:
                issues.append("agent '%s': name '%s' != filename" % (a, name))
            if not NAME_RE.search(name):
                issues.append("agent '%s': name '%s' fails charset rule" % (a, name))
        if not has_field_line(fm, 'description'):
            issues.append("agent '%s': missing description" % a)
        tools = get_field(fm, 'tools')
        if tools and re.search(r'\bBash\b', tools) and not re.search(r'\b(Write|Edit)\b', tools):
            body = read_raw(afull)
            if not re.search(r'readonly-guard\.py', body):
                issues.append("agent '%s': read-only Bash agent is missing readonly-guard.py hook" % a)

    # ---- Model policy ----
    model_policy = {
        'sde-engineer':         'opus',
        'prompt-engineer':      'opus',
        'code-reviewer':        'opus',
        'security-reviewer':    'opus',
        'sre-engineer':         'opus',
        'researcher':           'sonnet',
        'runbook-author':       'sonnet',
        'sre-monitor':          'sonnet',
        'test-engineer':        'sonnet',
    }
    for a in agent_files:
        base = a[:-3]
        if base not in model_policy:
            issues.append(
                "model-policy: agent '%s' is not listed in the documented model policy "
                "(model_policy in this script) -- add it with its intended model." % base
            )
            continue
        fm = get_frontmatter(os.path.join(agents_dir, a))
        model = get_field(fm, 'model') if fm is not None else None
        expected = model_policy[base]
        if model != expected:
            issues.append(
                "model-policy: agent '%s' has model '%s' but policy requires '%s' "
                "(see CLAUDE.md model policy)." % (base, model, expected)
            )

    # ---- Roster coverage (docs that enumerate the roster must name every agent) ----
    # A past agent addition silently missed README.md and the roster docs;
    # this check makes that class of drift a CI failure instead. Two rules:
    #   1. Every agent name appears in each roster-enumerating doc below.
    #   2. Any literal "N agents" / "N skills" count in a CURRENT-STATE doc matches the tree
    #      (blockquote lines are skipped — dated review records live in '>' banners).
    roster_docs = [
        'AGENTS.md',
        'README.md',
        os.path.join('.claude', 'skills', 'route-request', 'SKILL.md'),
    ]
    agent_names = [a[:-3] for a in agent_files]
    for doc in roster_docs:
        p = os.path.join(ROOT, doc)
        rel = doc.replace('\\', '/')
        if not os.path.exists(p):
            issues.append("roster-coverage: expected doc '%s' is missing" % rel)
            continue
        text = read_raw(p)
        for base in agent_names:
            if base not in text:
                issues.append(
                    "roster-coverage: '%s' never mentions agent '%s' -- update it (or drop the "
                    "doc from roster_docs in this script if it no longer enumerates the roster)."
                    % (rel, base)
                )
    count_docs = ['README.md', 'AGENTS.md', 'CLAUDE.md']
    count_re = re.compile(r'\b(\d+)\s+(agents|skills)\b')
    actual = {'agents': len(agent_files), 'skills': skill_count}
    for doc in count_docs:
        p = os.path.join(ROOT, doc)
        if not os.path.exists(p):
            continue
        rel = doc.replace('\\', '/')
        n = 0
        for ln in read_lines(p):
            n += 1
            if ln.lstrip().startswith('>'):
                continue  # dated review-record banners keep their historical counts
            for m in count_re.finditer(ln):
                if int(m.group(1)) != actual[m.group(2)]:
                    issues.append(
                        "roster-coverage: '%s' line %d says '%s' but the tree has %d %s -- "
                        "fix the count or drop it (count-free phrasing preferred)."
                        % (rel, n, m.group(0), actual[m.group(2)], m.group(2))
                    )

    # ---- Scope guard ----
    scope_tokens = [
        'kubernetes', 'kubectl', 'k8s', 'terraform', 'prometheus', 'promql',
        'eks', 'gke', 'aks', 'helm', 'argocd', 'datadog', 'pagerduty',
        'cloudformation', 'openshift',
    ]
    scope_re = re.compile(r'\b(' + '|'.join(scope_tokens) + r')\b', re.IGNORECASE)
    scope_allow = [
        'do NOT propose Kubernetes',   # legacy charter disclaimer
        'cloud or Kubernetes',         # sde-engineer.md       -- charter disclaimer (line-wrapped)
        'or Terraform/grafana',        # grafana-dashboards    -- dashboards-as-code provisioning aside
        'datasource-managed',          # grafana-dashboards    -- Grafana unified-alerting rule-mode note
        'Prometheus style',            # instrument-service    -- OTel metric-naming portability note
        'suffixes are added by the',   # instrument-service    -- OTel names vs Prometheus-exporter suffixes
        'build verbs (',               # agent-security        -- readonly-guard blocked-verb example (terraform)
        'PromQL equivalence',          # wavefront-queries     -- section heading
        'accepts PromQL',              # wavefront-queries     -- WQL/PromQL equivalence note
    ]
    # case-insensitive substring match, mirroring PowerShell's -like "*frag*"
    scope_allow_lc = [p.lower() for p in scope_allow]

    scope_targets = [os.path.join(agents_dir, a) for a in agent_files]
    for name_dir in skill_dirs:
        sk = os.path.join(skills_dir, name_dir, 'SKILL.md')
        if os.path.exists(sk):
            scope_targets.append(sk)

    for path in scope_targets:
        rel = os.path.relpath(path, ROOT).replace('\\', '/')
        n = 0
        for ln in read_lines(path):
            n += 1
            m = scope_re.search(ln)
            if not m:
                continue
            ln_lc = ln.lower()
            if any(frag in ln_lc for frag in scope_allow_lc):
                continue
            issues.append(
                "scope '%s' line %d: off-charter tooling '%s' - repo is PCF / no-K8s "
                "(Wavefront/Splunk/Grafana). Rewrite for our stack, or allowlist the line in "
                "scope_allow in this script if it is a deliberate disclaimer/portability note."
                % (rel, n, m.group(1))
            )

    print("Validated %d skills and %d agents (+ scope guard)." % (skill_count, len(agent_files)))
    if not issues:
        print("VALIDATION: PASS")
        return 0
    print("VALIDATION: FAIL - %d issue(s):" % len(issues))
    for it in issues:
        print("  - %s" % it)
    return 1


if __name__ == '__main__':
    sys.exit(main())
