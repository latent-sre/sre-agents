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
#   2. Spin up a FRESH coding-agent process (AGENT_CMD) to do the NEXT one unit of work against
#      your spec/backlog files. Fresh context per pass is the whole point — state lives in files.
#   3. Hard verify gate: run TEST_CMD. Commit the change ONLY if it passes; otherwise roll the
#      iteration back. Unverified work is never committed.
#
# Guardrails enforced below (this is an ops repo — never loop prod):
#   * requires a git repo and a clean working tree to start (failed iterations roll back with
#     'git reset --hard', so pre-existing uncommitted work must not be at risk)
#   * refuses to run on the default branch (main/master)
#   * requires a feature branch + a hard verifier (TEST_CMD) and an agent command (AGENT_CMD)
#   * caps iterations (MAX_ITERS) and exits when the backlog is clear and the verifier is green
#   * AGENT_CMD / TEST_CMD MUST NOT contain deploy/prod actions (cf push, route remap, scale,
#     migrations, etc.). Keep it to code-building + tests. The loop ships nothing.
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

# --- Guardrail: clean working tree to start -----------------------------------------------------
# Each failed iteration is rolled back with 'git reset --hard', which would destroy any pre-existing
# uncommitted tracked work. Refuse unless staged + unstaged changes are clean before we begin.
# (Untracked files — e.g. your ralph/PROMPT.md spec — are left alone.)
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "ralph-loop: working tree has uncommitted tracked changes — commit or stash them first" >&2
    echo "            (failed iterations roll back with 'git reset --hard')." >&2
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

    # Fresh agent context does ONE bounded unit of work against the spec/backlog. Subshell-isolated:
    # it still edits files in the repo (those persist), but can't change the loop's cwd/options/vars.
    if ! ( eval "$AGENT_CMD" ); then
        echo "ralph-loop: agent command failed — stopping for a human to look." >&2
        exit 1
    fi

    # Hard verify gate (subshell-isolated). Commit only on green; otherwise discard this iteration.
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
        echo "  ✗ verifier failed — discarding this iteration's tracked changes."
        git reset -q --hard
        # NOTE: untracked files the agent created are left in place for inspection rather than
        # auto-deleted. Run 'git clean -fdn' to preview, 'git clean -fd' to remove, for a clean restart.
    fi
done

echo "ralph-loop: hit MAX_ITERS=$MAX_ITERS without finishing. Review the branch; a human clears" >&2
echo "            the merge-gate before anything merges or ships." >&2
exit 2
