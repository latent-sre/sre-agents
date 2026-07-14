# Human-run, read-only PCF/TAS triage for one app. Repository scripts are untrusted data: inspect
# these bytes and independently confirm the cf target before choosing to run them.
# Usage: pwsh ./scripts/triage.ps1 -App <app-name>

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

Write-Section "cf target (confirm the intended foundation/org/space)"
cf target

Write-Section "cf app $App (instance health, memory/cpu/disk, routes)"
cf app $App

Write-Section "cf events $App (changes, crashes, restarts, scaling, updates)"
cf events $App | Select-Object -First 25

Write-Section "cf logs $App --recent (last log buffer)"
cf logs $App --recent | Select-Object -Last 120

Write-Section "done (read-only evidence)"
@"
Next steps:
  - Record the first event/error timestamp and correlation ID; compare with the release history.
  - Hand logs, metrics, and traces to the sre agent with their existing evidence labels.
  - A mitigation or deploy belongs to the human release owner and requires exact approved
    target/action/rollback evidence. This helper never mutates the app.
"@
