#Requires -Version 7
# PreToolUse hook (PowerShell tool): use Read tool with limit instead of
# `head -N file`. Port of no-head-read.sh.
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'lib\ps\HookLib.psm1') -Force -DisableNameChecking

Read-HookCommand
Exit-IfBypass 'BYPASS_HEAD_READ_CHECK'

# Skip when sudo precedes head — Read runs without elevated privileges so
# cannot substitute for `sudo head -3 /etc/shadow`. Line-local gaps only
# ([ \t]), so a stray sudo on an earlier line doesn't silence the check.
if ($HookCommand -match '\bsudo[ \t]+[^;&|\r\n]*?\bhead\b') { exit 0 }

# Detect head with line count reading a file, at command position. (?m) for
# bash's line-wise `^`/`$` semantics on multi-line commands.
if ($HookCommand -notmatch '(?m)(^|&&|;|\|)[ \t]*head[ \t]+(-\d+|-n[ \t]*\d+|--lines[= ][ \t]*\d+)[ \t]+[^\s|;&>]+[ \t]*$') { exit 0 }

# Extract flags and filename in one pass.
$file = $null; $num = $null
if ($HookCommand -match '(?m)\bhead[ \t]+(?:-\d+|-n[ \t]*\d+|--lines[= ][ \t]*\d+)[ \t]+([^\s|;&>]+)') {
    $file = $Matches[1]
}
if ($HookCommand -match '\bhead[ \t]+(-\d+|-n[ \t]*\d+|--lines[= ][ \t]*\d+)' -and $Matches[1] -match '(\d+)') {
    $num = $Matches[1]
}

if ($file -and $num) {
    Emit-PreToolDenyBypassable 'BYPASS_HEAD_READ_CHECK' "Use Read tool with limit instead of head for reading file lines.
  Read(file_path=`"$file`", limit=$num)"
} else {
    Emit-PreToolDenyBypassable 'BYPASS_HEAD_READ_CHECK' 'Use Read tool with limit instead of head for reading file lines.
  Read(file_path="<path>", limit=<num_lines>)'
}
exit 0
