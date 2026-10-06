#Requires -Version 7
# PreToolUse hook (PowerShell tool): block oversized inline scripts — heredoc
# (via Git Bash) and PS here-strings, plus multi-line -c payloads — above
# 80 lines; use the Write tool + a temp file instead. Port of no-heredoc.sh,
# extended with the PowerShell here-string idiom.
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'lib\ps\HookLib.psm1') -Force -DisableNameChecking

$maxLines = 80

Read-HookCommand
Exit-IfBypass 'BYPASS_HEREDOC_RESTRICTION'
Exit-IfBypass 'BYPASS_INLINE_SCRIPT_RESTRICTION'

# --- Detection -------------------------------------------------------------
# Heredoc (<<, not <<<) — bash idiom reachable from PS via bash -c.
$hasHeredoc = $HookCommand -match '<<[^<]'

# PS here-string opener: @' / @" at end of line (closed by '@ / "@).
$hasHereString = $HookCommand -match "(?m)@['""]\s*$"

# Multi-line -c payload (python -c "...", pwsh -Command "...", bash -c '...').
$hasInlineC = $false
$inlineCLines = 0
if ($HookCommand -match '(?s)-c\s+[''"]') {
    # Count lines from the line containing -c to the end of the command
    # (approximation of the bash awk quote-matcher: good enough for the
    # 80-line threshold, which is the only decision it feeds).
    $lines = $HookCommand -split "`r?`n"
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match '-c\s+[''"]') {
            $inlineCLines = $lines.Count - $i
            break
        }
    }
    if ($inlineCLines -gt $maxLines) { $hasInlineC = $true }
}

if (-not $hasHeredoc -and -not $hasHereString -and -not $hasInlineC) { exit 0 }

# Implicit bypass for git commit (heredoc used for commit message)
if ($HookCommand -match '\bgit\s+commit\b') { exit 0 }

# --- Line counting ---------------------------------------------------------
$scriptLines = 0
$detectionType = ''
$bypassMarker = ''
$cmdLines = $HookCommand -split "`r?`n"

if ($hasHeredoc) {
    $marker = $null
    if ($HookCommand -match "<<[-'`" ]*([A-Za-z_][A-Za-z0-9_]*)") { $marker = $Matches[1] }
    if ($marker) {
        $in = $false
        foreach ($l in $cmdLines) {
            if (-not $in -and $l -match '<<' -and $l -match [regex]::Escape($marker)) { $in = $true; continue }
            if ($in) {
                if ($l.Trim() -eq $marker) { $in = $false } else { $scriptLines++ }
            }
        }
        $detectionType = 'Heredoc'
        $bypassMarker = 'BYPASS_HEREDOC_RESTRICTION'
    } else { exit 0 }
} elseif ($hasHereString) {
    $in = $false
    foreach ($l in $cmdLines) {
        if (-not $in) {
            if ($l -match "@['""]\s*$") { $in = $true }
            continue
        }
        if ($l -match "^\s*['""]@") { $in = $false } else { $scriptLines++ }
    }
    $detectionType = 'Here-string'
    $bypassMarker = 'BYPASS_HEREDOC_RESTRICTION'
} else {
    $scriptLines = $inlineCLines
    $detectionType = 'Inline -c script'
    $bypassMarker = 'BYPASS_INLINE_SCRIPT_RESTRICTION'
}

if ($scriptLines -le $maxLines) { exit 0 }

# --- Interpreter + suggestion ----------------------------------------------
$interpreter = $null; $ext = $null
if ($HookCommand -match '\buv\s+run\b') { $interpreter = 'uv run'; $ext = 'py' }
elseif ($HookCommand -match '\bpython3?\b') { $interpreter = 'python3'; $ext = 'py' }
elseif ($HookCommand -match '\b(bash|sh|pwsh|powershell)\b') { $interpreter = 'pwsh'; $ext = 'ps1' }
else { exit 0 }

# CLAUDE_PROJECT_DIR may be unset outside a project — Join-Path throws on an
# empty path under EAP=Stop (the .sh original has a ${VAR:-} fallback).
$tmpDir = $env:TEMP
if ($env:CLAUDE_PROJECT_DIR -and (Test-Path (Join-Path $env:CLAUDE_PROJECT_DIR 'temp'))) {
    $tmpDir = Join-Path $env:CLAUDE_PROJECT_DIR 'temp'
}
$tmpFile = Join-Path $tmpDir "script_$PID.$ext"
$example = "Write(`"$tmpFile`", <script>)  →  run: $interpreter `"$tmpFile`""

Emit-PreToolDenyBypassable $bypassMarker "$detectionType >$maxLines lines detected for $interpreter. Use Write tool + temp file instead:
  $example"
exit 0
