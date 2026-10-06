#Requires -Version 7
# PreToolUse hook (PowerShell tool): use Read tool with offset/limit instead of
# `sed -n 'Np' file` / `sed -n 'N,Mp' file`. Port of no-sed-print.sh.
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'lib\ps\HookLib.psm1') -Force -DisableNameChecking

Read-HookCommand
Exit-IfBypass 'BYPASS_SED_PRINT_CHECK'

# Skip when sudo precedes sed — Read cannot substitute elevated reads.
if ($HookCommand -match '\bsudo[ \t]+[^;&|\r\n]*?\bsed\b') { exit 0 }

# Detect sed -n with numeric line printing on a file at command position.
# (?m) for bash's line-wise anchoring on multi-line commands. Catches '12p',
# 12p, '12,13p', '12,13!p' — not 's/foo/bar/p' (substitution) or
# '/pattern/p' (regex addresses).
$range = $null; $file = $null
if ($HookCommand -match '(?m)(^|&&|;|\|)[ \t]*sed[ \t]+-n[ \t]+[''"]?(\d+[,.!]\d*p|\d+p)[''"]?[ \t]+([^\s|;&>]+)[ \t]*$') {
    $range = $Matches[2]; $file = $Matches[3]
} else {
    exit 0
}

# Parse range to offset/limit (1-indexed line → 0-indexed offset).
$offset = $null; $limit = $null
if ($range -match '^(\d+)p$') {
    $offset = [int]$Matches[1] - 1; $limit = 1
} elseif ($range -match '^(\d+),(\d+)p$') {
    $offset = [int]$Matches[1] - 1; $limit = [int]$Matches[2] - [int]$Matches[1] + 1
}

if ($file -and $null -ne $offset) {
    Emit-PreToolDenyBypassable 'BYPASS_SED_PRINT_CHECK' "Use Read tool with offset and limit instead of sed -n for reading specific lines.
  Read(file_path=`"$file`", offset=$offset, limit=$limit)"
} else {
    Emit-PreToolDenyBypassable 'BYPASS_SED_PRINT_CHECK' 'Use Read tool with offset and limit instead of sed -n for reading specific lines.
  Read(file_path="<path>", offset=<start_line-1>, limit=<num_lines>)'
}
exit 0
