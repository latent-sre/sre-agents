#!/bin/sh
# PreToolUse hook launcher for readonly-guard.py. Wired into the read-only agents that keep Bash.
#
# WHY THIS EXISTS (2026-07-11): the hook used to be an inline one-liner:
#
#     "$(command -v python3 || command -v python)" -c "...run readonly-guard.py..."
#
# On Windows that SILENTLY DISABLED THE GUARD. `command -v python3` succeeds -- it resolves the
# Microsoft Store *alias stub* at AppData/Local/Microsoft/WindowsApps/python3 (enabled by default on
# Win 10/11) -- so the `|| command -v python` fallback NEVER fired. The stub then prints "Python was
# not found" and exits non-zero. The guard never ran, emitted no decision, and Claude Code treats a
# non-zero hook (other than exit 2) as a NON-BLOCKING error -- so the command PROCEEDED.
#
# Net effect: read-only agents had NO guard on Windows, and the failure was silent. Verified on this
# machine: `command -v python3` -> .../WindowsApps/python3, and the hook's stdout was EMPTY (no deny).
#
# Two rules this script exists to enforce:
#   1. Pick an interpreter that WORKS, not one that merely RESOLVES (`-c ""` actually executes it).
#   2. FAIL CLOSED. If no interpreter works, DENY. A guard that cannot run must never silently allow.
set -u

for p in python3 python py; do
    if "$p" -c "" >/dev/null 2>&1; then
        exec "$p" -c "import os, runpy; runpy.run_path(os.path.join(os.environ.get('CLAUDE_PROJECT_DIR', '.'), 'scripts', 'readonly-guard.py'), run_name='__main__')"
    fi
done

# No working Python. Deny rather than fall open.
printf '%s' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"readonly-guard could not start: no working Python interpreter found. Failing CLOSED — refusing the command rather than silently allowing it. Install Python, or disable the Windows Store python3 alias (Settings > Apps > Advanced app settings > App execution aliases)."}}'
