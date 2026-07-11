#!/usr/bin/env python3
"""PreToolUse speed-bump for whatever agent runs prod `cf` commands.

The prod executor is the fleet's unavoidable lethal-trifecta holder: it carries prod
credentials, ingests untrusted content (CI logs, PR/issue text, webhook comments), AND can
act externally (deploy/scale/restart prod via `cf`). The REAL control for that combination
is the HARD human gate — the production-change-gate, enforced in GitHub via branch
protection + protected environments with required reviewers — plus treating all log/PR/CI
text as DATA, never instructions.

This hook is the local SPEED-BUMP, not that control. Wired via the `hooks: PreToolUse`
frontmatter of whatever agent runs `cf`, it intercepts the pending Bash tool call (same stdin-JSON
contract as readonly-guard.py: read tool input, exit 0 to allow, exit 2 + stderr to block).
It DETECTS state-changing `cf` commands and BLOCKS them UNLESS an explicit clearance signal
is present — so a prod-mutating `cf` command can't fire from an un-cleared session by
accident or by injected-text nudge. Clearance is set by a human after the gate passes:

    PCF_GATE_CLEARED=1            (env var), OR
    a `.gate-cleared` sentinel file in the current working directory.

It is NOT a security boundary: a cooperative agent that has cleared the gate, or anyone who
controls the env/cwd, can satisfy the signal. The load-bearing control remains GitHub branch
protection + protected environments (human reviewers) and OS-level least-privilege creds.

Read-only `cf` commands (cf app/apps/logs/events/target, `cf curl` GET) always pass — this
guard only speed-bumps WRITES. Non-`cf` and non-Bash calls pass untouched (other state
changes are out of this guard's narrow scope; the gate + creds cover them).

SCOPE — `cf` ONLY: this hook does NOT speed-bump the GitHub-Actions prod path the team is migrating
to (`git push` to a protected branch, `gh workflow run`, `gh release create`, Terraform, etc.). Those
are gated by the load-bearing control — GitHub branch protection + protected environments with required
reviewers (admin-bypass disabled) — NOT by this local hook. Do not read "the guard didn't fire" as
"this prod change is safe": for non-`cf` prod actions the GitHub gate is the only thing in the way.

Cross-platform: pure Python stdlib, no jq. The agent hook invokes this via
`"$(command -v python3 || command -v python)" -c ...` — selecting the interpreter once so this
guard's blocking exit 2 propagates unchanged (the older `python3 ... || python ...` form re-ran on
the exit-2 deny and, on a python3-only host where the `|| python` fallback then failed with 127,
let the blocked prod write proceed). Covered by scripts/test_production_change_guard.py (offline).
See https://code.claude.com/docs/en/hooks
"""
import json
import os
import re
import sys

# State-changing `cf` subcommands — mirrors the cf-write classification in readonly-guard.py.
# Kept deliberately aligned: if you add a cf write there, add it here too.
_CF_WRITE = re.compile(
    r"\bcf\s+(?:v3-)?(push|delete|delete-[a-z-]+|scale|restart|restage|restart-app-instance|stop|start|"
    r"stage|map-route|unmap-route|create-route|delete-route|set-env|unset-env|set-label|unset-label|rename|bind-service|"
    r"unbind-service|create-service|update-service|create-user-provided-service|"
    r"update-user-provided-service|delete-user-provided-service|create-service-key|"
    r"delete-service-key|enable-ssh|disable-ssh|ssh(?!-)|run-task|terminate-task|rollback|"
    r"continue-deployment|cancel-deployment|create-app|delete-app|copy-source|set-droplet|"
    r"set-health-check|bind-route-service|unbind-route-service|share-service|unshare-service|"
    r"create-org|delete-org|create-space|delete-space|set-org-role|unset-org-role|"
    r"set-space-role|unset-space-role|create-buildpack|update-buildpack|delete-buildpack|"
    r"enable-feature-flag|disable-feature-flag|create-quota|update-quota|set-quota|"
    r"create-space-quota|update-space-quota|set-space-quota|bind-security-group|"
    r"unbind-security-group|bind-staging-security-group|unbind-staging-security-group|"
    r"create-security-group|update-security-group|add-network-policy|remove-network-policy|"
    r"enable-org-isolation|create-isolation-segment|install-plugin|uninstall-plugin|"
    r"set-running-environment-variable-group|set-staging-environment-variable-group)\b",
    re.IGNORECASE,
)
# `cf curl` carrying a write method or a body is also a state change.
_CF_CURL_WRITE = re.compile(
    r"\bcf\s+curl\b.*(-X\s*(POST|PUT|DELETE|PATCH)|--request[=\s]+(POST|PUT|DELETE|PATCH)|"
    r"--data(-raw|-binary|-urlencode)?|\s-d[\s'\"@=])",
    re.IGNORECASE,
)

_BLOCK_MESSAGE = (
    "Production-change-gate not cleared — run the production-change-gate, get human sign-off, "
    "then set PCF_GATE_CLEARED=1. This is a speed-bump; the real control is GitHub branch "
    "protection + protected environments."
)


def _cleared() -> bool:
    """True when a human has signalled clearance for this session."""
    if os.environ.get("PCF_GATE_CLEARED") == "1":
        return True
    if os.path.isfile(os.path.join(os.getcwd(), ".gate-cleared")):
        return True
    return False


def _is_cf_write(command: str) -> bool:
    return bool(_CF_WRITE.search(command) or _CF_CURL_WRITE.search(command))


def main() -> None:
    try:
        raw = sys.stdin.buffer.read().decode("utf-8-sig", errors="replace")
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        sys.exit(0)  # unparseable input -> don't interfere with the normal permission flow

    if data.get("tool_name") != "Bash":
        sys.exit(0)

    command = (data.get("tool_input") or {}).get("command", "") or ""
    if _is_cf_write(command) and not _cleared():
        sys.stderr.write(_BLOCK_MESSAGE + "\n")
        sys.exit(2)  # exit 2 -> block the tool call (Claude Code PreToolUse contract)

    sys.exit(0)


if __name__ == "__main__":
    main()
