#Requires -Version 7
# PreToolUse hook (PowerShell tool): use Write tool instead of cat-heredoc file
# writes (reachable from PS via bash -c or Git Bash cat.exe). Port of
# no-cat-write.sh.
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'lib\ps\HookLib.psm1') -Force -DisableNameChecking

Read-HookCommand
Exit-IfBypass 'BYPASS_CAT_WRITE'

$ANCHORS = '(' + $CMD_ANCHOR_SUDO + '|' + $CMD_WRAPPER + ')'

# Detect cat with heredoc AND file redirection (>, >>, or | tee).
if ($HookCommand -notmatch ('(?i)' + $ANCHORS + 'cat\b.*<<')) { exit 0 }
if ($HookCommand -notmatch ('(?i)' + $ANCHORS + 'cat\b.*(>\s*\S|>>\s*\S|\|\s*tee\b)')) { exit 0 }

# Implicit bypass for git commit (heredoc used for commit message)
if ($HookCommand -match '\bgit\s+commit\b') { exit 0 }

# Skip when sudo precedes cat — Write cannot substitute elevated writes.
if ($HookCommand -match '\bsudo[ \t]+[^;&|\r\n]*?\bcat\b') { exit 0 }

# Extract target file path (stop at first space, <, |, & or newline —
# unlike bash grep which is line-oriented, PS \s matches \n, so exclude it).
$file = $null
if ($HookCommand -match '>[ \t]*([^<>|&\r\n ]+)') { $file = $Matches[1] -replace "'", '' }

if ($file) {
    Emit-PreToolDenyBypassable 'BYPASS_CAT_WRITE' "Use Write tool instead of cat heredoc for file writes.
  Write(`"$file`", <content>)"
} else {
    Emit-PreToolDenyBypassable 'BYPASS_CAT_WRITE' 'Use Write tool instead of cat heredoc for file writes.'
}
exit 0
