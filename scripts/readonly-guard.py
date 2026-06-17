#!/usr/bin/env python3
"""PreToolUse guard — enforce read-only agents at the command level.

Wired into the read-only agents that still need Bash for observation
(sre-engineer, code-reviewer, security-reviewer, incident-commander) via their
`hooks: PreToolUse` frontmatter. Claude Code pipes the pending tool call as JSON on
stdin; this denies Bash commands that CHANGE STATE (prod or repo) so "read-only" is
enforced, not merely promised. Read-only triage commands (cf logs/app/events, git
log/diff/status, grep, curl GET, redirect to /dev/null, etc.) pass through untouched.

Scope: this is a guardrail for a COOPERATIVE agent, not a sandbox. It blocks the common
state-changing commands — cf writes, git writes, file/process/service mutations, package
installs, HTTP writes, output redirection to a file, tee, cp, and in-place sed/perl. It
cannot stop a determined bypass through an arbitrary interpreter (python -c, bash -c,
eval, xargs sh, …); pair it with OS-level least-privilege credentials for defense in depth.
Covered by scripts/test_readonly_guard.py (pure-stdlib, runs offline).

Decision is returned as a permissionDecision JSON on stdout with exit 0 (the documented
non-error path). See https://code.claude.com/docs/en/hooks

Cross-platform: pure Python stdlib, no jq. On systems where the interpreter is `python3`,
adjust the hook command accordingly (this repo's agent frontmatter uses `python`).
"""
import json
import re
import sys

# State-changing command patterns — denied for read-only agents. Case-insensitive.
_DENY_PATTERNS = [
    # PCF / cf CLI writes: deploys, scaling, lifecycle, routes, services, env, ssh, tasks
    r"\bcf\s+(push|delete|delete-[a-z-]+|scale|restart|restage|restart-app-instance|stop|start|"
    r"stage|map-route|unmap-route|create-route|delete-route|set-env|unset-env|rename|bind-service|"
    r"unbind-service|create-service|update-service|enable-ssh|disable-ssh|run-task|terminate-task|"
    r"rollback|create-app|delete-app|copy-source|set-health-check|bind-route-service|"
    r"unbind-route-service)\b",
    r"\bcf\s+curl\b.*-X\s*(POST|PUT|DELETE|PATCH)",
    # git writes: history, remote, index, or worktree mutations
    r"\bgit\s+(add|mv|rm|push|commit|reset|rebase|merge|cherry-pick|revert|clean|am|apply|"
    r"restore|checkout|switch|pull|stash|gc|prune|init|branch\s+-[dDmM]|tag\s+-d|"
    r"remote\s+(add|rm|remove|set-url))\b",
    # filesystem / process / service mutations
    r"\b(rm|rmdir|mv|cp|rsync|dd|truncate|shred|chmod|chown|chgrp|ln|mkfs)\b",
    # in-place file editors
    r"\bsed\s+(-[^\s]*i|--in-place)",
    r"\bperl\s+-[^\s]*i",
    # shell output redirection to a file (allow >/dev/null and fd-dup like 2>&1), and tee
    r">>?\s*(?!&|/dev/null)[~./$A-Za-z0-9_-]",
    r"\btee\b",
    r"\b(kill|pkill|killall)\b",
    r"\b(systemctl|service)\s+(start|stop|restart|reload|enable|disable)\b",
    r"\b(shutdown|reboot|halt|poweroff)\b",
    # package / dependency installs (state change, out of scope for read-only triage)
    r"\b(apt|apt-get|yum|dnf|zypper|pip|pip3|npm|pnpm|yarn|gem|brew|choco)\s+"
    r"(install|remove|uninstall|update|upgrade|add)\b",
    # HTTP writes
    r"\bcurl\b.*(-X\s*(POST|PUT|DELETE|PATCH)|--request\s+(POST|PUT|DELETE|PATCH))",
    r"\bcurl\b.*(--data|--data-raw|--data-binary|--form|\s-d\s|\s-F\s)",
    r"\bwget\b.*--(post|method=)",
]
_DENY_RE = re.compile("|".join(_DENY_PATTERNS), re.IGNORECASE)

_REASON = (
    "Blocked: this is a read-only agent. The command appears to change state "
    "(deploy/scale/restart, git write, file/process/service mutation, package install, or an "
    "HTTP write). Recommend the action instead and hand off to release-engineer to execute with "
    "human sign-off (see the production-change-gate skill)."
)


def main() -> None:
    try:
        # Read raw bytes and decode with utf-8-sig so a leading BOM (which some Windows shells
        # and pipes prepend) is stripped reliably, regardless of the locale encoding.
        raw = sys.stdin.buffer.read().decode("utf-8-sig", errors="replace")
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        sys.exit(0)  # unparseable input -> don't interfere with the normal permission flow

    if data.get("tool_name") != "Bash":
        sys.exit(0)

    command = (data.get("tool_input") or {}).get("command", "") or ""
    if _DENY_RE.search(command):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": _REASON,
            }
        }))
    sys.exit(0)


if __name__ == "__main__":
    main()
