#!/usr/bin/env bash
#
# Generate VS Code / GitHub Copilot native artifacts from the canonical .claude/ definitions.
#
# Both Claude Code and VS Code/Copilot read `.claude/agents` and `.claude/skills` directly, so the fleet
# already works in Copilot with no build step. Run this only when you want Copilot-NATIVE files:
#   * .github/agents/<name>.agent.md  — from .claude/agents/<name>.md, with `tools:` translated to
#     Copilot's vocabulary and the Claude-only `model:`, `color:`, `skills:`, `hooks:` keys dropped
#     (Copilot picks its model and still auto-loads skills by description). Body copied verbatim.
#   * .github/skills/                 — a mirror of .claude/skills/ (identical SKILL.md open standard).
#
# The tool translation is conservative. Claude-only hooks are not portable to Copilot, so generated
# read-only agents do not receive runCommands; writer agents keep terminal access. Idempotent.
# From repo root: bash scripts/sync-copilot.sh
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/.." && pwd)"
claude_agents="$root/.claude/agents"
claude_skills="$root/.claude/skills"
gh_agents="$root/.github/agents"
gh_skills="$root/.github/skills"

# Map Claude tool names -> Copilot tool/toolset names, preserving read-only vs. write intent.
translate_tools() {
    local line="$1"
    local out="'search'"                                             # read/search codebase (toolset)
    local can_write=0
    # Whole-word matches (POSIX classes, portable to macOS bash 3.2) so 'TodoWrite' is NOT read as write
    # access — parity with the .ps1 '\bWrite\b'. Without this, every read-only agent (all carry TodoWrite)
    # would wrongly receive 'edit'/'runCommands' in the Copilot output.
    if [[ "$line" =~ (^|[^[:alnum:]])(Write|Edit)([^[:alnum:]]|$) ]]; then out+=", 'edit'"; can_write=1; fi  # file writes
    # Claude-only hooks are stripped from Copilot output, so read-only agents do not get terminal access.
    if [[ $can_write -eq 1 && "$line" =~ (^|[^[:alnum:]])Bash([^[:alnum:]]|$) ]]; then out+=", 'runCommands'"; fi  # terminal
    if [[ "$line" =~ (^|[^[:alnum:]])(WebFetch|WebSearch)([^[:alnum:]]|$) ]]; then out+=", 'web/fetch'"; fi  # web
    printf 'tools: [%s]\n' "$out"
}

# Clean first (like skills, below) so agents deleted upstream don't linger as stale
# .github/agents/*.agent.md wrappers — Copilot reads those, so a removed agent would still show.
rm -rf "$gh_agents"
mkdir -p "$gh_agents"
agent_count=0

shopt -s nullglob
for f in "$claude_agents"/*.md; do
    name="$(basename "$f" .md)"
    dest="$gh_agents/$name.agent.md"
    : > "$dest"
    fm_seen=0; skip_block=0
    while IFS= read -r line || [[ -n "$line" ]]; do
        line="${line%$'\r'}"                                     # tolerate CRLF sources (Windows checkouts)
        if [[ "$line" == '---' && $fm_seen -lt 2 ]]; then
            fm_seen=$((fm_seen + 1)); skip_block=0; printf '%s\n' "$line" >> "$dest"; continue
        fi
        if [[ $fm_seen -eq 1 ]]; then                                # inside frontmatter
            if [[ $skip_block -eq 1 ]]; then                         # inside a dropped block (hooks:/skills:)
                if [[ "$line" =~ ^[[:space:]]+[^[:space:]] || -z "${line// }" ]]; then continue; else skip_block=0; fi
            fi
            if [[ "$line" =~ ^[[:space:]]*tools[[:space:]]*: ]]; then translate_tools "$line" >> "$dest"; continue; fi
            if [[ "$line" =~ ^[[:space:]]*model[[:space:]]*: ]]; then continue; fi   # drop model alias
            if [[ "$line" =~ ^[[:space:]]*color[[:space:]]*: ]]; then continue; fi   # drop Claude-only color
            if [[ "$line" =~ ^[[:space:]]*hooks[[:space:]]*: ]]; then skip_block=1; continue; fi   # Claude-only
            if [[ "$line" =~ ^[[:space:]]*skills[[:space:]]*: ]]; then skip_block=1; continue; fi  # Claude-only preload
        fi
        printf '%s\n' "$line" >> "$dest"
    done < "$f"
    agent_count=$((agent_count + 1))
done

# Mirror skills (clean first to drop anything deleted upstream).
rm -rf "$gh_skills"
mkdir -p "$gh_skills"
cp -R "$claude_skills/." "$gh_skills/"
skill_count="$(find "$gh_skills" -name SKILL.md -type f | wc -l | tr -d ' ')"

echo "Generated $agent_count Copilot agents -> .github/agents/"
echo "Mirrored  $skill_count skills         -> .github/skills/"
echo "Done. (Both tools also read .claude/ directly, so this is optional polish.)"
