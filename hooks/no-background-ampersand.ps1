#Requires -Version 7
# PreToolUse hook (PowerShell tool): no shell-level backgrounding.
# Port of no-background-ampersand.sh, extended for PowerShell semantics:
# - trailing `&` (a bash idiom; in PS it is a syntax error, still worth flagging)
# - Start-Job (the PowerShell-native background primitive; Start-Process has
#   too many legitimate foreground uses to blanket-deny)
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'lib\ps\HookLib.psm1') -Force -DisableNameChecking

Read-HookCommand
Exit-IfBypass 'BYPASS_BACKGROUND_CHECK'

# (?m): any line ending in `&` (bash background idiom; in PS a syntax error,
# still flagged) — or the PowerShell-native Start-Job primitive.
if ($HookCommand -match '(?m)[^&]&[ \t]*$' -or $HookCommand -match '(?i)\bstart-job\b') {
    Emit-PreToolDenyBypassable 'BYPASS_BACKGROUND_CHECK' 'Do not background by shell. Use the tool parameter instead:
  PowerShell(command="...", run_in_background=true)'
}

exit 0
