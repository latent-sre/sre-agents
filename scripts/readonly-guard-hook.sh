#!/bin/sh
# Fail-closed launcher for the read-only allowlist guard (scripts/readonly-guard.py).
# Wired via per-agent frontmatter PreToolUse hooks (matcher: Bash) on sre and sre-steward.
# Protocol: guard exits 42 = allow (empty stdout), 43 = deny (permissionDecision JSON on stdout).
# If NO interpreter answers with the guard's own exit codes, the guard is missing or broken:
# DENY — these hooks only fire for guarded agents, so failing closed cannot hit the user's session.
IN=$(cat)
G="${CLAUDE_PROJECT_DIR:-.}/scripts/readonly-guard.py"
for C in python py python3; do
  command -v "$C" >/dev/null 2>&1 || continue
  OUT=$(printf '%s' "$IN" | "$C" -I -S "$G" 2>/dev/null); RC=$?
  if [ "$RC" -eq 42 ]; then exit 0; fi
  if [ "$RC" -eq 43 ]; then printf '%s' "$OUT"; exit 0; fi
done
printf '%s' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Read-only guard unavailable: no interpreter answered with the guard exit codes (tried python, py, python3). Bash is denied for guarded agents until the guard is restored."}}'
exit 0
