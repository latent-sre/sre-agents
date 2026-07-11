# Read-only PCF / TAS triage for one app. Runs only safe cf read commands and prints a
# structured summary. Part of the pcf-ops skill.
#
# Usage:   pwsh .claude/skills/pcf-ops/scripts/triage.ps1 -App <app-name>
# Needs:   cf CLI v8, and you are already cf login'd and targeted at the right org/space.

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$App
)

$ErrorActionPreference = 'Continue'

if ([string]::IsNullOrWhiteSpace($App)) {
    [Console]::Error.WriteLine("usage: triage.ps1 -App <app-name>")
    exit 2
}

function Write-Section {
    param([Parameter(Mandatory = $true)][string]$Title)
    Write-Host ""
    Write-Host "==== $Title ===="
}

Write-Section "cf target (CONFIRM this is the intended foundation/org/space)"
cf target

Write-Section "cf app $App  (instance health, memory/cpu/disk, routes)"
cf app $App

Write-Section "cf events $App  (what changed? crashes, restarts, scaling, updates - newest first)"
cf events $App | Select-Object -First 25

Write-Section "cf logs $App --recent  (last log buffer; look for stack traces / OOM / 5xx)"
cf logs $App --recent | Select-Object -Last 120

Write-Section "done (read-only)"
@"
Next steps:
  - Correlate the first event/error timestamp with your last deploy (release pipeline / git log).
  - Logs older than the buffer -> splunk-triage (SPL). Metrics over time -> wavefront-queries (ts()).
  - To MITIGATE (restart/scale/rollback/route remap) hand off to a human release owner; clear the
    production-change-gate for prod. Do not mutate from here.
"@
