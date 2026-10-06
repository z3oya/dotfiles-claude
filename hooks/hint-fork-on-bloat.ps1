#Requires -Version 7
# PostToolUse hook (PowerShell tool): hint about fork-first when this session's
# cumulative PowerShell tool output crosses ~50 KB. Port of
# hint-fork-on-bloat.sh. One-shot per session, re-arms after compact.
#
# The counter lives under claude-ps-state (independent from the bash-side
# counter — each shell tool's bytes tally in its own counter; both share the
# same 50 KB threshold and compact re-arm semantics).
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'lib\ps\HookLib.psm1') -Force -DisableNameChecking

$thresholdKb = 50

Read-HookInput
$sid = [string]$HookInput.session_id
if (-not $sid) { exit 0 }

# Skip subagents — agent-* prefix on session_id. Short-lived by design.
if ($sid -like 'agent-*') { exit 0 }

$cacheDir = Join-Path (Get-HookStateRoot) 'hint-fork-bloat'
$counter = Join-Path $cacheDir "$sid.counter"
$fired = Join-Path $cacheDir "$sid.fired"
New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null
Reset-OnCompact $sid $cacheDir @($fired, $counter)

# Already fired this (post-compact) session — cheapest exit.
if (Test-Path -LiteralPath $fired) { exit 0 }

# Estimate tool_response byte size (JSON text, like jq's tostring|length;
# escape inflation ~10-15% on both sides — threshold is approximate anyway).
$resp = $HookInput.tool_response | ConvertTo-Json -Depth 100 -Compress
$bytes = 0
if ($resp) { $bytes = [System.Text.Encoding]::UTF8.GetByteCount($resp) }
if ($bytes -le 0) { exit 0 }

# Read counter (default 0 on missing/corrupt).
$current = 0
if (Test-Path -LiteralPath $counter) {
    [void][int]::TryParse((Get-Content -LiteralPath $counter -Raw).Trim(), [ref]$current)
}
$new = $current + $bytes
Set-Content -LiteralPath $counter -Value $new -NoNewline

if ($new -lt ($thresholdKb * 1024)) { exit 0 }

# Crossed the line — fire one-shot.
New-Item -ItemType File -Force -Path $fired | Out-Null
$kb = [int][math]::Floor(($new + 512) / 1024)

Emit-PostToolContext "This session has spent ~${kb} KB on PowerShell tool output (the bash-side counter tallies Bash/Read/Grep/Glob separately). If you're surveying — count / breakdown / sweep / locate over a corpus, or smoke-testing with verbose output — consider forking the next batch via Agent (omit subagent_type to fork yourself). Intermediate fork output stays out of main context, so subsequent main turns re-read less. See CLAUDE.md 'Fork-first on Surveys'.
(One-shot hint — will not fire again this session.)"
exit 0
