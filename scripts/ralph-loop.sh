#!/usr/bin/env bash
#
# ralph-loop.sh — EXAMPLE reference scaffold for a "Ralph" unattended outer loop.
# See .claude/skills/self-improve-loop/SKILL.md (Pattern 3) for when/why.
#
# This is a tool YOU run by hand. It is deliberately NOT invoked by CI or any agent, and it does
# NOT ship anything — it only edits code and commits on a feature branch. A human still clears the
# merge-gate before anything merges or deploys.
#
# What it does, each iteration:
#   1. Stop if the backlog has no open items AND the verifier is green (= done).
#   2. Record HEAD, then spin up a FRESH coding-agent process (AGENT_CMD) to do the NEXT one unit of
#      work against your spec/backlog files. Fresh context per pass is the whole point.
#   3. Hard verify gate: run TEST_CMD. On green, commit the work; on red, roll the WHOLE iteration
#      back to the recorded HEAD (reset --hard + clean) so unverified work is never kept or carried.
#
# Guardrails enforced below (this is an ops repo — never loop prod):
#   * requires a git repo and a PRISTINE working tree to start (no tracked changes, no untracked
#     files) — commit your spec/backlog first. Failed iterations roll back with 'git reset --hard'
#     + 'git clean', which must never be able to destroy pre-existing work.
#   * refuses to run on the default branch (main/master)
#   * best-effort prod denylist: refuses if AGENT_CMD/TEST_CMD contain obvious deploy/prod verbs
#     (cf writes, kubectl, terraform). NOT a sandbox — pair with least-privilege creds.
#   * caps iterations (MAX_ITERS) and exits when the backlog is clear and the verifier is green
#   * commits land on the feature branch only; a human clears merge-gate before anything ships
#
# Usage:
#   AGENT_CMD='claude -p "$(cat ralph/PROMPT.md)"' \
#   TEST_CMD='pytest -q' \
#   MAX_ITERS=20 \
#   BACKLOG=ralph/fix_plan.md \
#   bash scripts/ralph-loop.sh
#
set -euo pipefail

: "${AGENT_CMD:?set AGENT_CMD to your coding-agent invocation, e.g. claude -p \"\$(cat ralph/PROMPT.md)\"}"
: "${TEST_CMD:?set TEST_CMD to a hard verifier that exits non-zero on failure, e.g. pytest -q}"
MAX_ITERS="${MAX_ITERS:-20}"
BACKLOG="${BACKLOG:-ralph/fix_plan.md}"

# --- Guardrail: must be inside a git repo -------------------------------------------------------
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "ralph-loop: not inside a git repository — run this from your repo's working tree." >&2
    exit 1
fi

# --- Guardrail: branch only, never the default branch -------------------------------------------
branch="$(git rev-parse --abbrev-ref HEAD)"
case "$branch" in
    main|master|HEAD|"")
        echo "ralph-loop: refusing to run on '$branch' — switch to a feature branch first." >&2
        exit 1
        ;;
esac

# --- Guardrail: pristine working tree to start --------------------------------------------------
# Each failed iteration rolls back with 'git reset --hard' + 'git clean -fd'. If the tree weren't
# pristine, that rollback could destroy pre-existing tracked edits OR untracked files. So require a
# clean slate — commit (or stash) your spec/backlog and everything else before starting.
if [[ -n "$(git status --porcelain)" ]]; then
    echo "ralph-loop: working tree is not pristine — commit or stash everything first (incl. your" >&2
    echo "            spec/backlog). Failed iterations roll back with 'git reset --hard' + 'git clean'." >&2
    exit 1
fi

# --- Guardrail: best-effort prod/deploy denylist ------------------------------------------------
# The loop runs AGENT_CMD/TEST_CMD unattended every iteration; obvious prod-facing commands must not
# be in them (AGENTS.md: prod-facing cf writes need explicit human sign-off). This is a denylist, not
# a sandbox — run with least-privilege creds for real isolation.
_prod_deny='(^|[^[:alnum:]-])(cf[[:space:]]+(push|delete|delete-[a-z-]+|scale|restart|restage|stop|start|map-route|unmap-route|set-env|unset-env|rollback|run-task|ssh|enable-ssh|bind-service|create-service|update-service)|kubectl|terraform[[:space:]]+(apply|destroy))([^[:alnum:]-]|$)'
if printf '%s\n%s\n' "$AGENT_CMD" "$TEST_CMD" | grep -Eiq "$_prod_deny"; then
    echo "ralph-loop: AGENT_CMD/TEST_CMD contain a prod/deploy verb (cf write, kubectl, terraform)." >&2
    echo "            This loop is for code-building only — prod changes need a human + the gates." >&2
    exit 1
fi

echo "ralph-loop: branch='$branch'  max_iters=$MAX_ITERS  verifier='$TEST_CMD'"
echo "ralph-loop: commits land on this branch only; a human clears merge-gate before merge."

backlog_clear() {
    # No backlog file, or no remaining unchecked "- [ ]" items.
    [[ ! -f "$BACKLOG" ]] || ! grep -qE '^[[:space:]]*-[[:space:]]*\[ \]' "$BACKLOG"
}

for ((i = 1; i <= MAX_ITERS; i++)); do
    echo "── iteration $i/$MAX_ITERS ──────────────────────────────────"

    # Stop condition: nothing left to do AND the verifier is green. Verifier runs in a SUBSHELL so a
    # stray cd/set/exit in TEST_CMD can't mutate this loop's state — we only gate on its exit code.
    if backlog_clear && ( eval "$TEST_CMD" ); then
        echo "ralph-loop: backlog clear and verifier green → done after $((i - 1)) iteration(s)."
        exit 0
    fi

    # Record the pre-iteration commit so a red verifier discards EVERYTHING this iteration did —
    # uncommitted changes, any commits the agent made, and any new files it created.
    iter_start="$(git rev-parse HEAD)"

    # Fresh agent context does ONE bounded unit of work against the spec/backlog. Subshell-isolated:
    # it still edits files in the repo (those persist), but can't change the loop's cwd/options/vars.
    if ! ( eval "$AGENT_CMD" ); then
        echo "ralph-loop: agent command failed — stopping for a human to look." >&2
        exit 1
    fi

    # Hard verify gate (subshell-isolated). Commit only on green; otherwise restore the pristine
    # pre-iteration state so unverified work is never kept or carried into the next iteration.
    if ( eval "$TEST_CMD" ); then
        git add -A
        if git diff --cached --quiet; then
            echo "  (verifier green, nothing to commit)"
        elif git commit -q -m "ralph: iteration $i (verifier green)"; then
            echo "  ✓ verified + committed"
        else
            echo "ralph-loop: commit failed with staged changes present (git user.name/email? a" >&2
            echo "            commit hook? GPG signing?) — stopping rather than silently dropping work." >&2
            exit 1
        fi
    else
        echo "  ✗ verifier failed — rolling the iteration back to ${iter_start:0:9}."
        git reset -q --hard "$iter_start"   # drop tracked changes + any commits the agent made
        git clean -fdq                      # drop new untracked files (tree was pristine at start)
    fi
done

echo "ralph-loop: hit MAX_ITERS=$MAX_ITERS without finishing. Review the branch; a human clears" >&2
echo "            the merge-gate before anything merges or ships." >&2
exit 2
