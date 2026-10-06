#Requires -Version 7
# PreToolUse hook (PowerShell tool): no output discarding into the void.
# Port of no-devnull-redirect.sh, extended for PowerShell semantics:
# detects both `> /dev/null` (invoking Git Bash tools) and the PS-native
# `> $null` / `2> $null` / `*> $null` discard forms.
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'lib\ps\HookLib.psm1') -Force -DisableNameChecking

Read-HookCommand
Exit-IfBypass 'BYPASS_DEVNULL_CHECK'

# Common denominator: `>` followed by optional whitespace then /dev/null —
# or the PowerShell-native $null equivalent (any stream redirect).
if ($HookCommand -match '>\s*/dev/null\b' -or $HookCommand -match '(?i)>\s*\$null\b') {
    Emit-PreToolDenyBypassable 'BYPASS_DEVNULL_CHECK' 'Do not redirect to /dev/null — noise is cheaper than blindness.
Remove the `>/dev/null` / `2>/dev/null` / `>$null` so output reaches the agent.'
}

exit 0
