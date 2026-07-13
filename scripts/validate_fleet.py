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
            read-only Bash agents declare the readonly-guard.py hook.
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

# Every frontmatter key Claude Code defines. This exists to close a SILENT-DISARM hole, not for
# tidiness. An unrecognised key is not an error -- Claude Code drops it on the floor. So a one-
# character typo does not fail; it DELETES whatever that key configured. On `code-reviewer`,
# `security-reviewer` and `sre-engineer` the key it would delete is `hooks:`, which is the only
# thing that makes a Bash-holding agent read-only. Renaming `hooks:` -> `hook:` used to leave the
# guard gone and the validator printing VALIDATION: PASS.
KNOWN_AGENT_FIELDS = {
    'name', 'description', 'tools', 'disallowedTools', 'model', 'permissionMode', 'maxTurns',
    'skills', 'mcpServers', 'hooks', 'memory', 'background', 'effort', 'isolation', 'color',
    'initialPrompt',
}
# Agent Skills spec fields + Claude Code's skill extensions.
KNOWN_SKILL_FIELDS = {
    'name', 'description', 'license', 'allowed-tools', 'metadata', 'compatibility',
    'disable-model-invocation', 'user-invocable', 'argument-hint',
}
# A top-level key: column zero, no leading whitespace. Anchoring matters -- the hook block nests
# `PreToolUse:`, `matcher:`, `type:` and `command:` underneath `hooks:`, and a check that matched
# them as top-level keys would reject the real fleet.
TOP_LEVEL_KEY_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_-]*)\s*:')
# The guard script as written in a hook command, e.g.
#   command: "sh \"${CLAUDE_PROJECT_DIR:-.}/scripts/readonly-guard-hook.sh\""
GUARD_PATH_RE = re.compile(r'([^\s"\\]*readonly-guard[\w.-]*)')
ENV_PREFIX_RE = re.compile(r'^\$\{[^}]*\}/')

# The repo being validated. Overridable so the validator can be pointed at a throwaway copy of the
# fleet -- which is the only way to TEST it (scripts/test_validate_fleet.py mutates a copy and asserts
# this script rejects it). It had no tests for exactly this reason, and three of its checks were
# quietly passing inputs they exist to reject. Unset in normal use; CI calls it with no environment.
ROOT = os.environ.get('FLEET_ROOT') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Where the fleet's skills/ and agents/ live UNDER that root. This is resolved, not hardcoded, because
# the Copilot migration MOVES them: `git mv .claude/{agents,skills} legacy/claude-fleet/` is the first
# action of Phase 1, and the plugin layout puts them at the plugin root (skills/, agents/) rather than
# under .claude/. A hardcoded '.claude' segment meant this validator raised FileNotFoundError for the
# entire migration -- i.e. the gate was guaranteed dead across the four phases that author the fleet.
# Probe plugin layout first: post-migration the repo root holds the NEW fleet at skills/, and the old
# one is reachable with FLEET_ROOT=legacy/claude-fleet.
_LAYOUTS = (('skills', 'agents'), (os.path.join('.claude', 'skills'), os.path.join('.claude', 'agents')))


def _resolve_layout():
    """Return (skills_dir, agents_dir) for the first layout present under ROOT.

    Falls back to the .claude layout so a genuinely missing fleet fails with the existing
    'directory not found' error rather than silently validating zero units -- a validator that
    passes because it found nothing to check is the exact failure mode this repo keeps hitting.
    """
    for skills, agents in _LAYOUTS:
        if os.path.isdir(os.path.join(ROOT, skills)) and os.path.isdir(os.path.join(ROOT, agents)):
            return os.path.join(ROOT, skills), os.path.join(ROOT, agents)
    claude_skills, claude_agents = _LAYOUTS[1]
    return os.path.join(ROOT, claude_skills), os.path.join(ROOT, claude_agents)


SKILLS_DIR, AGENTS_DIR = _resolve_layout()


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


def get_list_field(fm, key):
    """Return a list-field value as a list of token strings, handling both YAML shapes:
      inline: `tools: Skill, Read, Grep`
      block:  `tools:` followed by `  - Skill` / `  - Read` lines
    Returns [] if the key is absent or empty. Line-oriented on purpose — matches get_field's approach
    and keeps the validator stdlib-only. A previous version only inspected same-line values, so a
    block-list form that omitted `Skill` would silently pass the `Skill` allowlist check."""
    key_match = re.compile(r'^\s*' + re.escape(key) + r'\s*:\s*(.*)$')
    item_re = re.compile(r'^(\s*)-\s*(.+?)\s*$')
    for i, ln in enumerate(fm):
        m = key_match.match(ln)
        if not m:
            continue
        rest = m.group(1).strip()
        if rest:
            # inline: split on commas, drop empties
            return [t.strip() for t in rest.split(',') if t.strip()]
        # block form: consume subsequent `- item` lines at deeper indent than the key
        key_indent = len(ln) - len(ln.lstrip(' '))
        items = []
        for ln2 in fm[i + 1:]:
            if not ln2.strip():
                continue
            im = item_re.match(ln2)
            if not im:
                break
            item_indent = len(im.group(1))
            if item_indent <= key_indent:
                break
            items.append(im.group(2).strip())
        return items
    return []


def top_level_keys(fm):
    """Frontmatter keys at column zero. Nested config (hooks' PreToolUse/matcher/command) is
    indented and deliberately excluded."""
    keys = []
    for ln in fm:
        m = TOP_LEVEL_KEY_RE.match(ln)
        if m:
            keys.append(m.group(1))
    return keys


def block_lines(fm, key):
    """The indented lines belonging to a top-level `key:` block (up to the next column-zero key)."""
    out = []
    inside = False
    for ln in fm:
        if TOP_LEVEL_KEY_RE.match(ln):
            if inside:
                break
            inside = ln.startswith(key + ':')
            continue
        if inside:
            out.append(ln)
    return out


def guard_wiring_issues(fm, root):
    """Verify the read-only guard is actually WIRED, not merely mentioned.

    The old check was `re.search(r'readonly-guard(-hook\\.sh|\\.py)', body)` -- a substring grep over
    the whole file. It proves the string appears somewhere; it proves nothing about the hook. It
    passed a file whose `hooks:` key was misspelled (so Claude Code ignored the block entirely), and
    it would pass a file that merely discusses the guard in prose. This resolves the wiring instead:
    a PreToolUse hook, matching Bash, running a guard script that exists on disk.
    """
    if 'hooks' not in top_level_keys(fm):
        return ["declares no 'hooks:' key, so its Bash is unguarded"]

    hook_block = block_lines(fm, 'hooks')
    if not any(re.match(r'\s*PreToolUse\s*:', ln) for ln in hook_block):
        return ["hooks: has no PreToolUse -- the guard can only fire before a tool call"]

    # Split the block into `- matcher: X` entries and check the one that matches Bash carries the
    # guard command. A guard hung on a non-Bash matcher never runs on Bash.
    entries, current = [], None
    for ln in hook_block:
        m = re.match(r'\s*-\s*matcher\s*:\s*(.+?)\s*$', ln)
        if m:
            current = {'matcher': m.group(1).strip('\'"'), 'lines': []}
            entries.append(current)
        elif current is not None:
            current['lines'].append(ln)

    bash_entries = [e for e in entries if re.search(r'\bBash\b', e['matcher'])]
    if not bash_entries:
        got = ', '.join(repr(e['matcher']) for e in entries) or 'none'
        return ["PreToolUse has no Bash matcher (matchers: %s) -- Bash is unguarded" % got]

    issues = []
    for e in bash_entries:
        cmd = ' '.join(e['lines'])
        m = GUARD_PATH_RE.search(cmd)
        if not m:
            issues.append("PreToolUse Bash matcher runs no readonly-guard command")
            continue
        rel = ENV_PREFIX_RE.sub('', m.group(1)).lstrip('./')
        if not os.path.exists(os.path.join(root, rel)):
            issues.append("guard script '%s' does not exist -- the hook fails open" % rel)
    return issues


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
    skills_dir = SKILLS_DIR
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

        # Unknown/misspelled top-level keys -- same silent-drop hazard as agents. Misspell
        # `disable-model-invocation` and a side-effecting skill becomes model-invocable again.
        for key in top_level_keys(fm):
            if key not in KNOWN_SKILL_FIELDS:
                issues.append(
                    "skill '%s': unknown frontmatter key '%s' -- unrecognised keys are silently "
                    "IGNORED, so this configures nothing" % (name_dir, key)
                )

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

    # What an agent's `skills:` list may name. A skill that disables model invocation cannot be
    # preloaded either -- preloading draws from the same set Claude can invoke.
    skill_names = set(skill_dirs)
    no_preload_skills = set()
    for name_dir in skill_dirs:
        sk_path = os.path.join(skills_dir, name_dir, 'SKILL.md')
        if not os.path.exists(sk_path):
            continue  # already reported above; don't crash re-reading it
        sfm = get_frontmatter(sk_path)
        if sfm and (get_field(sfm, 'disable-model-invocation') or '').strip().lower() == 'true':
            no_preload_skills.add(name_dir)

    # ---- Agents ----
    agents_dir = AGENTS_DIR
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
        tool_list = get_list_field(fm, 'tools')
        has_tools = has_field_line(fm, 'tools')
        tool_set = set(tool_list)
        # Unknown/misspelled top-level keys. Claude Code IGNORES an unrecognised key rather than
        # erroring, so a typo silently deletes whatever it configured -- and on the read-only agents
        # that is `hooks:`, i.e. the guard itself. See KNOWN_AGENT_FIELDS.
        for key in top_level_keys(fm):
            if key not in KNOWN_AGENT_FIELDS:
                issues.append(
                    "agent '%s': unknown frontmatter key '%s' -- Claude Code silently IGNORES "
                    "unrecognised keys, so this configures nothing. Misspelling a real key (e.g. "
                    "'hooks') removes what it configured with no error." % (a, key)
                )

        # `skills:` preloads a skill's content at startup. Its VALUES were never checked, so a typo
        # preloaded nothing and the agent quietly lost the knowledge it was given.
        for sk_name in get_list_field(fm, 'skills'):
            if sk_name not in skill_names:
                issues.append(
                    "agent '%s': skills: entry '%s' does not resolve to .claude/skills/%s/SKILL.md "
                    "-- it preloads nothing" % (a, sk_name, sk_name)
                )
            elif sk_name in no_preload_skills:
                issues.append(
                    "agent '%s': skills: entry '%s' sets disable-model-invocation, and such a skill "
                    "CANNOT be preloaded (\"preloading draws from the same set of skills Claude can "
                    "invoke\" -- code.claude.com/docs/en/sub-agents). It preloads nothing." % (a, sk_name)
                )

        if has_tools and 'Bash' in tool_set and not (tool_set & {'Write', 'Edit'}):
            # Read-only Bash agent: its read-only-ness IS the PreToolUse hook. Verify the wiring
            # resolves, rather than grepping the file for the word 'readonly-guard'.
            for problem in guard_wiring_issues(fm, ROOT):
                issues.append("agent '%s': read-only Bash agent -- %s" % (a, problem))
        # An explicit `tools:` list that omits `Skill` is the DOCUMENTED way to stop a subagent
        # invoking skills at all: "To prevent a subagent from invoking skills entirely, omit `Skill`
        # from the tools list" -- https://code.claude.com/docs/en/sub-agents. Every agent body here
        # says "load the X skill", so omitting it silently guts the fleet's core mechanism (agents are
        # WHO, skills are HOW, loaded on demand). It shipped that way and nothing caught it, because
        # the validator only checked that skills EXIST -- never that an agent could REACH one.
        # `skills:` does NOT substitute: it preloads content, it does not grant invocation.
        # Uses get_list_field so both inline (`tools: A, B`) and YAML block (`tools:\n  - A`) forms
        # are covered -- an earlier same-line-only check could be bypassed by reformatting to a list.
        if has_tools and 'Skill' not in tool_set:
            issues.append(
                "agent '%s': tools: omits 'Skill' -- it cannot invoke ANY skill (the documented way to "
                "disable skills). Its body tells it to load skills. Add Skill to tools:, or drop tools: "
                "entirely to inherit all tools." % a
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
        'an EXPORTER\'s rendering',    # instrument-service    -- OTel-name vs exporter-rendering contrast
        'underscore-style exporter',   # instrument-service    -- OTel metric-naming portability note
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
