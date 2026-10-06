#Requires -Version 7
# PreToolUse hook (PowerShell tool): nudge once per session when a PowerShell
# command pipes its trailing stage into `Select-Object -First/-Last`.
# PowerShell port of no-head-tail-pipe.sh — the .sh original detects the bash
# equivalent `| head` / `| tail` (a syntax bash cannot see); this one detects
# the PowerShell idiom. Soft advisory, not a block — see the .sh original for
# the rationale. One hint per session; re-arms after compact via the shared
# generation counter.
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'lib\ps\HookLib.psm1') -Force -DisableNameChecking

Read-HookCommand

if ($HookCommand -notmatch $PS_TAIL_TRUNCATION) { exit 0 }

$sid = [string]$HookInput.session_id
if (-not $sid) { $sid = 'unknown' }
if (Test-SessionOneShotLock $sid 'hint-no-head-tail-pipe') {
    Emit-PreToolWarn @'
Trailing `| Select-Object -First/-Last` truncates by position and discards the rest (irrecoverable if the producer was expensive or non-idempotent: the truncation happens before the harness sees the output). The harness already saves large output to a file and shows a head preview, so plain `cmd` gives you the same visible head AND the rest for rg/Read.

Prefer the producer's native limit (semantic — short-circuits work):
  Get-Content  →  -TotalCount N
  rg           →  -m N
  git log      →  -n N

(One-shot hint — will not fire again this session.)
'@
}
exit 0
