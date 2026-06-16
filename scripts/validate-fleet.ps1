#requires -Version 5.1
<#
.SYNOPSIS
  Validate the agent + skill fleet against the Agent Skills open standard and Claude Code's
  subagent rules. Exits non-zero on any failure (CI-friendly).

.DESCRIPTION
  Checks, per the spec at https://agentskills.io/specification :
    Skills  - SKILL.md present; YAML frontmatter present; `name` 1-64 chars, lowercase a-z/0-9/hyphen,
              no leading/trailing/consecutive hyphen, matches the parent directory; `description`
              present, non-empty, <= 1024 chars; referenced files (references/ assets/ scripts/) exist.
    Agents  - frontmatter present; `name` valid charset and matches the filename; `description` present.

  This covers the documented hard rules. For the upstream reference validator, see
  https://github.com/agentskills/agentskills (skills-ref).

.NOTES
  From repo root:  pwsh scripts/validate-fleet.ps1
#>
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'

$root   = Split-Path -Parent $PSScriptRoot
$issues = [System.Collections.Generic.List[string]]::new()
$nameRe = '^[a-z0-9]+(-[a-z0-9]+)*$'   # lowercase alnum + single hyphens; no lead/trail/double hyphen

function Get-Frontmatter([string]$path) {
    $lines = Get-Content -LiteralPath $path -Encoding UTF8
    $dash = @()
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i].Trim() -eq '---') { $dash += $i; if ($dash.Count -eq 2) { break } }
    }
    if ($dash.Count -lt 2) { return $null }
    if ($dash[1] -le $dash[0] + 1) { return @() }
    return $lines[($dash[0] + 1)..($dash[1] - 1)]
}

function Get-Field([string[]]$fm, [string]$key) {
    $line = $fm | Where-Object { $_ -match "^\s*$key\s*:" } | Select-Object -First 1
    if (-not $line) { return $null }
    return ($line -replace "^\s*$key\s*:\s*", '').Trim()
}

# ---- Skills ----
$skillCount = 0
foreach ($d in (Get-ChildItem (Join-Path $root '.claude/skills') -Directory)) {
    $sk = Join-Path $d.FullName 'SKILL.md'
    if (-not (Test-Path $sk)) { $issues.Add("skill '$($d.Name)': missing SKILL.md"); continue }
    $skillCount++
    $fm = Get-Frontmatter $sk
    if ($null -eq $fm) { $issues.Add("skill '$($d.Name)': no YAML frontmatter"); continue }

    $name = Get-Field $fm 'name'
    if (-not $name) { $issues.Add("skill '$($d.Name)': missing name") }
    else {
        if ($name -ne $d.Name)        { $issues.Add("skill '$($d.Name)': name '$name' != directory") }
        if ($name.Length -gt 64)      { $issues.Add("skill '$($d.Name)': name > 64 chars") }
        if ($name -notmatch $nameRe)  { $issues.Add("skill '$($d.Name)': name '$name' fails charset rule") }
    }

    if (-not (Get-Field $fm 'description')) {
        # description may be a folded block; treat presence of the key as satisfied, then length-check the block
        if (-not ($fm | Where-Object { $_ -match '^\s*description\s*:' })) {
            $issues.Add("skill '$($d.Name)': missing description")
        }
    }
    # description length (join folded lines)
    $desc = @(); $inDesc = $false
    foreach ($ln in $fm) {
        if ($ln -match '^description\s*:') { $inDesc = $true; $desc += ($ln -replace '^description\s*:\s*(>-|>|\|)?\s*',''); continue }
        if ($inDesc) { if ($ln -match '^[a-zA-Z_]+\s*:') { break }; $desc += $ln.Trim() }
    }
    $descLen = ([string]::Join(' ', $desc)).Trim().Length
    if ($descLen -eq 0)    { $issues.Add("skill '$($d.Name)': empty description") }
    if ($descLen -gt 1024) { $issues.Add("skill '$($d.Name)': description $descLen > 1024 chars") }

    # referenced bundle files exist (references/ assets/ scripts/)
    $body = Get-Content -LiteralPath $sk -Encoding UTF8 -Raw
    foreach ($m in [regex]::Matches($body, '(?<![\w./])(references|assets|scripts)/[A-Za-z0-9._/-]+')) {
        $rel = $m.Value
        if (-not (Test-Path (Join-Path $d.FullName $rel))) {
            $issues.Add("skill '$($d.Name)': references missing file '$rel'")
        }
    }
}

# ---- Agents ----
$agentFiles = Get-ChildItem (Join-Path $root '.claude/agents') -Filter '*.md' -File
foreach ($a in $agentFiles) {
    $fm = Get-Frontmatter $a.FullName
    if ($null -eq $fm) { $issues.Add("agent '$($a.Name)': no YAML frontmatter"); continue }
    $name = Get-Field $fm 'name'
    if (-not $name) { $issues.Add("agent '$($a.Name)': missing name") }
    else {
        if ($name -ne $a.BaseName)   { $issues.Add("agent '$($a.Name)': name '$name' != filename") }
        if ($name -notmatch $nameRe) { $issues.Add("agent '$($a.Name)': name '$name' fails charset rule") }
    }
    if (-not ($fm | Where-Object { $_ -match '^\s*description\s*:' })) {
        $issues.Add("agent '$($a.Name)': missing description")
    }
}

Write-Host "Validated $skillCount skills and $($agentFiles.Count) agents."
if ($issues.Count -eq 0) {
    Write-Host "VALIDATION: PASS" -ForegroundColor Green
    exit 0
}
Write-Host "VALIDATION: FAIL - $($issues.Count) issue(s):" -ForegroundColor Red
$issues | ForEach-Object { Write-Host "  - $_" }
exit 1
