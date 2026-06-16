---
name: powershell-craft
description: >-
  Idiomatic, robust PowerShell conventions for this team — approved verbs, advanced functions, strict
  error handling, object-pipeline output, and cross-version care (5.1 vs 7+). Use whenever writing,
  reviewing, or refactoring PowerShell for Windows/ops automation. Covers CmdletBinding, $null
  comparison, splatting, PSScriptAnalyzer, Pester, and avoiding Write-Host.
metadata:
  domain: language
  language: powershell
---

# PowerShell craft

Write cmdlet-style PowerShell that composes in a pipeline and fails safely. Mind that **Windows
PowerShell 5.1** and **PowerShell 7+** differ — state which you target.

## Function shape
```powershell
function Get-Thing {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Name,
        [int]$Count = 1
    )
    # comment-based help above; approved verb (Get/Set/New/Remove/...) + singular noun
}
```
- **Approved verbs** (`Get-Verb`); `[CmdletBinding()]` + typed, validated params
  (`[ValidateSet()]`, `[ValidateNotNullOrEmpty()]`).
- Support `-WhatIf`/`-Confirm` via `SupportsShouldProcess` for state-changing functions.

## Error handling
- Set `$ErrorActionPreference = 'Stop'` (or `-ErrorAction Stop` per call) so failures are catchable;
  wrap risky work in `try/catch`. Don't rely on `$?`.
- Throw `terminating` errors for real failures; use `Write-Error` for non-terminating with context.

## Output & pipeline
- **Emit objects, not formatted text** (`[pscustomobject]@{...}`); let the caller format. Reserve
  `Format-*` for the end of a display pipeline.
- **Never `Write-Host` for data** — it bypasses the pipeline. Use `Write-Output`/return, and
  `Write-Verbose`/`Write-Information` for diagnostics.

## Correctness traps
- **`$null` on the left:** `if ($null -eq $x)`, not `if ($x -eq $null)` (array-comparison gotcha).
- Use **splatting** for many params: `$p = @{ Name='x'; Count=2 }; Get-Thing @p`.
- `5.1 vs 7`: `??`/`?:`/ternary, `ForEach-Object -Parallel`, and some cmdlets are 7-only. Avoid
  `2>&1` capture quirks on native exes in 5.1.

## Quality gate & tests
- **Pass `PSScriptAnalyzer`**. Test with **`Pester`**: `Describe/Context/It`, `Mock`, `Should`;
  test param validation and error paths. See `tdd-workflow`.
- Keep secrets out of logs/transcripts; use `SecureString`/credential objects, never plaintext.
