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
    Scope   - no agent/skill *promotes* off-charter tooling (Kubernetes/IaC/Prometheus); our runtime is
              on-prem + PCF and observability is Wavefront/Splunk/Grafana. Charter disclaimers and
              portability/equivalence notes are allowlisted in the script.

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

    # referenced bundle files exist (references/ assets/ scripts/).
    # Require the final path segment to be a real filename: at least one name char, NOT ending in a
    # bare '.' or '/'. Without this, prose like "assets/." extracted "assets/." and Test-Path matched
    # the directory, masking a genuinely missing file. We then strip any trailing punctuation that
    # leaked in from surrounding prose ('.', ',', ')', etc.) before the existence check.
    $body = Get-Content -LiteralPath $sk -Encoding UTF8 -Raw
    foreach ($m in [regex]::Matches($body, '(?<![\w./])(references|assets|scripts)/[A-Za-z0-9._/-]*[A-Za-z0-9_-]')) {
        $rel = $m.Value -replace '[.,;:)\]]+$', ''      # drop trailing prose punctuation
        if ([string]::IsNullOrWhiteSpace($rel)) { continue }
        # Skip a bare directory reference (no filename component, e.g. "assets/") -- only check files.
        $leaf = Split-Path $rel -Leaf
        if ($leaf -eq 'references' -or $leaf -eq 'assets' -or $leaf -eq 'scripts') { continue }
        # Resolve against the skill's own bundle first, then fall back to the repo root: a SKILL.md may
        # legitimately reference a SHARED repo-root script (e.g. scripts/production-change-guard.py),
        # not only a file bundled under the skill. A genuinely missing file fails BOTH checks.
        if (-not (Test-Path (Join-Path $d.FullName $rel)) -and -not (Test-Path (Join-Path $root $rel))) {
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
    $tools = Get-Field $fm 'tools'
    if ($tools -and $tools -match '\bBash\b' -and $tools -notmatch '\b(Write|Edit)\b') {
        $body = Get-Content -LiteralPath $a.FullName -Encoding UTF8 -Raw
        if ($body -notmatch 'readonly-guard\.py') {
            $issues.Add("agent '$($a.Name)': read-only Bash agent is missing readonly-guard.py hook")
        }
    }
}

# ---- Model policy ----
# The model: frontmatter must match the documented policy (CLAUDE.md -> "Model policy"): opus for
# open-ended reasoning under ambiguity, sonnet for structured/procedural work. Drift here silently
# changes cost/behavior, so assert it structurally in CI.
$modelPolicy = @{
    'sde-engineer'         = 'opus'
    'prompt-engineer'      = 'opus'
    'code-reviewer'        = 'opus'
    'security-reviewer'    = 'opus'
    'sre-engineer'         = 'opus'
    'database-reliability' = 'opus'
    'release-engineer'     = 'sonnet'
    'researcher'           = 'sonnet'
    'runbook-author'       = 'sonnet'
    'sre-monitor'          = 'sonnet'
    'test-engineer'        = 'sonnet'
}
foreach ($a in $agentFiles) {
    if (-not $modelPolicy.ContainsKey($a.BaseName)) {
        $issues.Add("model-policy: agent '$($a.BaseName)' is not listed in the documented model policy (validate-fleet.ps1 `$modelPolicy) -- add it with its intended model.")
        continue
    }
    $fm = Get-Frontmatter $a.FullName
    $model = if ($null -ne $fm) { Get-Field $fm 'model' } else { $null }
    $expected = $modelPolicy[$a.BaseName]
    if ($model -ne $expected) {
        $issues.Add("model-policy: agent '$($a.BaseName)' has model '$model' but policy requires '$expected' (see CLAUDE.md model policy).")
    }
}

# ---- Scope guard ----
# Charter (AGENTS.md): application operations on on-prem + PCF. NO Kubernetes, IaC, or cloud-managed
# infra; observability is Wavefront/Splunk/Grafana, not Prometheus. Fail any agent/skill that
# *promotes* off-charter tooling, so the charter is enforced in CI rather than living only in prose.
# Legitimate mentions (charter disclaimers; portability/equivalence notes) are allowlisted by exact
# fragment below -- add a line here WITH a reason if a new legitimate use appears.
$scopeTokens = 'kubernetes','kubectl','k8s','terraform','prometheus','promql',
               'eks','gke','aks','helm','argocd','datadog','pagerduty','cloudformation','openshift'
$scopeRe     = '(?i)\b(' + ($scopeTokens -join '|') + ')\b'
$scopeAllow  = @(
    'do NOT propose Kubernetes',  # release-engineer.md  -- charter disclaimer
    'cloud or Kubernetes',        # sde-engineer.md       -- charter disclaimer (line-wrapped)
    'or Terraform/grafana',       # grafana-dashboards    -- dashboards-as-code provisioning aside
    'datasource-managed',         # grafana-dashboards    -- Grafana unified-alerting rule-mode note
    'Prometheus style',           # instrument-service    -- OTel metric-naming portability note
    'suffixes are added by the',  # instrument-service    -- OTel names vs Prometheus-exporter suffixes
    'build verbs (',              # agent-security        -- readonly-guard blocked-verb example (terraform)
    'PromQL equivalence',         # wavefront-queries     -- section heading
    'accepts PromQL'              # wavefront-queries     -- WQL/PromQL equivalence note
)
$scopeTargets = @($agentFiles.FullName)
$scopeTargets += Get-ChildItem (Join-Path $root '.claude/skills') -Directory |
    ForEach-Object { Join-Path $_.FullName 'SKILL.md' } | Where-Object { Test-Path $_ }
foreach ($path in $scopeTargets) {
    $rel = $path.Substring($root.Length).TrimStart('\/')
    $n = 0
    foreach ($ln in (Get-Content -LiteralPath $path -Encoding UTF8)) {
        $n++
        $m = [regex]::Match($ln, $scopeRe)
        if (-not $m.Success) { continue }
        $skip = $false
        foreach ($p in $scopeAllow) { if ($ln -like "*$p*") { $skip = $true; break } }
        if ($skip) { continue }
        $issues.Add("scope '$rel' line ${n}: off-charter tooling '$($m.Groups[1].Value)' - repo is PCF / no-K8s (Wavefront/Splunk/Grafana). Rewrite for our stack, or allowlist the line in validate-fleet.ps1 if it is a deliberate disclaimer/portability note.")
    }
}

Write-Host "Validated $skillCount skills and $($agentFiles.Count) agents (+ scope guard)."
if ($issues.Count -eq 0) {
    Write-Host "VALIDATION: PASS" -ForegroundColor Green
    exit 0
}
Write-Host "VALIDATION: FAIL - $($issues.Count) issue(s):" -ForegroundColor Red
$issues | ForEach-Object { Write-Host "  - $_" }
exit 1
