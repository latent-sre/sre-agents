#requires -Version 5.1
<#
.SYNOPSIS
  Generate VS Code / GitHub Copilot native artifacts from the canonical .claude/ definitions.

.DESCRIPTION
  Both Claude Code and VS Code/Copilot read `.claude/agents` and `.claude/skills` directly, so the
  fleet already works in Copilot with no build step. Run this only when you want Copilot-NATIVE files:
    * .github/agents/<name>.agent.md  -- generated from .claude/agents/<name>.md, with the `tools:` field
      translated to Copilot's tool vocabulary and the Claude-only `model:`, `color:`, `skills:`, and
      `hooks:` keys dropped (Copilot picks its own model, has no color/preload/hook concepts; it still
      auto-loads skills by description). The body (system prompt) is copied verbatim.
    * .github/skills/                 -- a mirror of .claude/skills/ (the SKILL.md open standard is
      identical for both tools; this is just the .github-native location).

  The tool translation is conservative. Claude-only hooks are not portable to Copilot, so generated
  read-only agents do not receive runCommands; writer agents keep terminal access.

.NOTES
  Idempotent. Re-run after editing anything under .claude/. From repo root: pwsh scripts/sync-copilot.ps1
#>
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'

$root         = Split-Path -Parent $PSScriptRoot
$claudeAgents = Join-Path $root '.claude/agents'
$claudeSkills = Join-Path $root '.claude/skills'
$ghAgents     = Join-Path $root '.github/agents'
$ghSkills     = Join-Path $root '.github/skills'

function Convert-ToolsLine([string]$line) {
    # Map Claude tool names -> Copilot tool/toolset names, preserving read-only vs. write intent.
    # Claude-only PreToolUse hooks are stripped below, so generated read-only agents do not get
    # Copilot terminal access. Writer agents keep runCommands for tests/builds/deploy work.
    $tools = [System.Collections.Generic.List[string]]::new()
    $tools.Add('search')                                                          # read/search codebase (toolset)
    $canWrite = ($line -match '\bWrite\b' -or $line -match '\bEdit\b')
    if ($canWrite) { $tools.Add('edit') }                                        # file writes
    if ($canWrite -and $line -match '\bBash\b') { $tools.Add('runCommands') }    # terminal
    if ($line -match '\bWebFetch\b' -or $line -match '\bWebSearch\b') { $tools.Add('web/fetch') } # web
    $items = ($tools | Select-Object -Unique | ForEach-Object { "'$_'" }) -join ', '
    return "tools: [$items]"
}

function Write-Utf8NoBom([string]$path, [string[]]$lines) {
    $text = ($lines -join "`n") + "`n"
    [System.IO.File]::WriteAllText($path, $text, (New-Object System.Text.UTF8Encoding $false))
}

function Reset-Directory([string]$path) {
    # Hard-fail (do NOT swallow) if the clean fails: a partial delete can leave stale generated files
    # that then ship to Copilot or trip the CI drift gate with confusing diffs. This matches the .sh
    # path, which hard-fails under `set -e` -- keep the two generators' failure semantics in agreement.
    if (Test-Path -LiteralPath $path) {
        [System.IO.Directory]::Delete($path, $true)   # throws -> $ErrorActionPreference='Stop' aborts the run
    }
    New-Item -ItemType Directory -Force -Path $path | Out-Null
}

# Clean first (like skills, below) so agents deleted upstream don't linger as stale
# .github/agents/*.agent.md wrappers -- Copilot reads those, so a removed agent would still show.
Reset-Directory $ghAgents

$agentCount = 0
Get-ChildItem -Path $claudeAgents -Filter '*.md' -File | ForEach-Object {
    $lines = Get-Content -LiteralPath $_.FullName -Encoding UTF8   # 5.1 default is ANSI; force UTF-8
    # Locate the frontmatter block (first two lines that are exactly '---').
    $dashes = @()
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i].Trim() -eq '---') { $dashes += $i; if ($dashes.Count -eq 2) { break } }
    }
    if ($dashes.Count -lt 2) { Write-Warning "Skipping $($_.Name): no YAML frontmatter found."; return }
    $fmEnd = $dashes[1]

    $out = [System.Collections.Generic.List[string]]::new()
    $skipBlock = $false
    for ($i = 0; $i -le $fmEnd; $i++) {
        $l = $lines[$i]
        if ($skipBlock) {                              # inside a dropped multi-line block (hooks:/skills:)
            if ($l -match '^\s+\S' -or $l.Trim() -eq '') { continue }   # indented/blank -> still in block
            $skipBlock = $false                        # dedented -> block ended, fall through
        }
        if ($l -match '^\s*tools\s*:')  { $out.Add((Convert-ToolsLine $l)); continue }
        if ($l -match '^\s*model\s*:')  { continue }   # drop Claude model alias; Copilot uses selected model
        if ($l -match '^\s*color\s*:')  { continue }   # drop Claude-only display color
        if ($l -match '^\s*hooks\s*:')  { $skipBlock = $true; continue }  # Claude-only; not portable to Copilot
        if ($l -match '^\s*skills\s*:') { $skipBlock = $true; continue }  # Claude-only preload list; Copilot auto-loads
        $out.Add($l)
    }
    for ($i = $fmEnd + 1; $i -lt $lines.Count; $i++) { $out.Add($lines[$i]) }   # body, verbatim

    $name = [System.IO.Path]::GetFileNameWithoutExtension($_.Name)
    Write-Utf8NoBom (Join-Path $ghAgents "$name.agent.md") $out
    $agentCount++
}

# Mirror skills (clean first to drop anything deleted upstream).
Reset-Directory $ghSkills
Copy-Item -Path (Join-Path $claudeSkills '*') -Destination $ghSkills -Recurse -Force
$skillCount = (Get-ChildItem -Path $ghSkills -Recurse -Filter 'SKILL.md' -File).Count

Write-Host "Generated $agentCount Copilot agents -> .github/agents/"
Write-Host "Mirrored  $skillCount skills         -> .github/skills/"
Write-Host "Done. (Both tools also read .claude/ directly, so this is optional polish.)"
