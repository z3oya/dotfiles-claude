#Requires -Version 7
# Shared helpers for PowerShell PreToolUse / PostToolUse hooks.
# PowerShell equivalent of lib/{read_input,emit,bypass,session_lock,anchors}.sh —
# keeps the .sh originals serving the Bash tool while these serve the PowerShell
# tool (see settings.json matcher split).
#
# Porting semantics (mirrors lib/README.md):
# - bash grep matches line-by-line, so every ^ / $ in a ported pattern needs
#   the (?m) flag. The anchor variables bake (?m) in; standalone patterns
#   (tail-truncation) are exported pre-flagged. Inline options apply to the
#   whole pattern they're embedded in, so callers concatenating
#   (?i)+ANCHOR+TRAIL inherit multi-line semantics automatically.
# - line-local whitespace is [ \t], never \s: in .NET \s matches \n and would
#   let a pattern straddle lines where bash's line-wise grep cannot.
# - bypass markers live in the PowerShell tool's command string, so the
#   bypass footer says "PowerShell command" (parameterized, not hardcoded).

# ---------- stdin ----------

# Read-StdinUtf8 — read all of stdin as UTF-8. Do not use
# [Console]::In: its input encoding follows the console code page, which on
# a CJK locale decodes the harness's UTF-8 payload as GBK and corrupts
# non-ASCII command text (and can swallow adjacent ASCII bytes).
function Read-StdinUtf8 {
    $reader = New-Object System.IO.StreamReader([Console]::OpenStandardInput(), [System.Text.Encoding]::UTF8)
    try {
        $reader.ReadToEnd()
    } finally {
        $reader.Dispose()
    }
}

# Read-HookInput — stdin JSON parser without command extraction, for hooks
# that react to other fields (tool_response, session_id). Sets $global:HookInput
# only; exits 0 on empty/unparseable stdin.
function Read-HookInput {
    $raw = Read-StdinUtf8
    if ([string]::IsNullOrWhiteSpace($raw)) { exit 0 }
    try {
        $global:HookInput = $raw | ConvertFrom-Json
    } catch {
        exit 0
    }
}

# Read-HookCommand — stdin JSON parser (mirror of read_bash_command).
# Sets $global:HookInput and $global:HookCommand (global, not $script: — a
# module's $script: scope is the module itself, invisible to the calling hook
# script); exits 0 (allowing the tool call) if stdin is empty, unparseable, or
# the command field is empty.
function Read-HookCommand {
    $raw = Read-StdinUtf8
    if ([string]::IsNullOrWhiteSpace($raw)) { exit 0 }
    try {
        $global:HookInput = $raw | ConvertFrom-Json
    } catch {
        exit 0
    }
    $global:HookCommand = [string]$global:HookInput.tool_input.command
    if ([string]::IsNullOrEmpty($global:HookCommand)) { exit 0 }
}

# ---------- bypass ----------

# Test-BypassMarker <marker> — non-exiting variant (mirror of has_bypass_marker).
function Test-BypassMarker {
    param([Parameter(Mandatory)][string]$Marker)
    return $global:HookCommand.Contains($Marker)
}

# Exit-IfBypass <marker> — exits 0 if marker present (mirror of bypass_check).
function Exit-IfBypass {
    param([Parameter(Mandatory)][string]$Marker)
    if (Test-BypassMarker $Marker) { exit 0 }
}

# ---------- emit ----------

# Emit-PreToolDeny <reason> — denies the tool call on PreToolUse.
function Emit-PreToolDeny {
    param([Parameter(Mandatory)][string]$Reason)
    @{ hookSpecificOutput = @{
            hookEventName          = 'PreToolUse'
            permissionDecision     = 'deny'
            permissionDecisionReason = $Reason
        } } | ConvertTo-Json -Depth 5 -Compress
}

# Emit-PreToolDenyBypassable <marker> <reason> [toolName] — deny + the standard
# bypass footer. lib/README.md mandates the two-branch wording ("legitimate or
# false-positive") so the agent knows bypass also covers regex misfires. The
# tool name is parameterized: these hooks read the PowerShell tool's command,
# so the default is 'PowerShell' (the .sh lib's footer says "Bash").
function Emit-PreToolDenyBypassable {
    param([Parameter(Mandatory)][string]$Marker, [Parameter(Mandatory)][string]$Reason,
          [string]$ToolName = 'PowerShell')
    Emit-PreToolDeny "$Reason`nIf legitimate or false-positive, append ``# $Marker`` to the $ToolName command."
}

# Emit-PreToolWarn <hint> — non-blocking advisory: injects additionalContext
# without a permissionDecision, so normal permission handling still applies.
function Emit-PreToolWarn {
    param([Parameter(Mandatory)][string]$Hint)
    @{ hookSpecificOutput = @{
            hookEventName     = 'PreToolUse'
            additionalContext = $Hint
        } } | ConvertTo-Json -Depth 5 -Compress
}

# Emit-PostToolContext <message> — injects additionalContext on PostToolUse.
function Emit-PostToolContext {
    param([Parameter(Mandatory)][string]$Message)
    @{ hookSpecificOutput = @{
            hookEventName     = 'PostToolUse'
            additionalContext = $Message
        } } | ConvertTo-Json -Depth 5 -Compress
}

# ---------- session state ----------

# Get-HookStateRoot — the single root for all PowerShell-side hook state
# (one-shot locks, counters, compact gen mirror). Always resolve state paths
# through this; scattering $env:TEMP vs $env:LOCALAPPDATA across hooks splits
# the tree when TEMP is redirected.
function Get-HookStateRoot {
    Join-Path $env:LOCALAPPDATA 'Temp\claude-ps-state'
}

# Reset-OnCompact <sessionId> <cacheDir> <files[]> — mirror of reset_on_compact.
# If the shared per-session generation counter (written by compact-bump.sh to
# a Windows-path copy; see compact-bump.sh) has grown since our last fire,
# clears the listed files so one-shot hints re-arm post-compact.
function Reset-OnCompact {
    param(
        [Parameter(Mandatory)][string]$SessionId,
        [Parameter(Mandatory)][string]$CacheDir,
        [Parameter(Mandatory)][string[]]$Files
    )
    $genSeen = Join-Path $CacheDir "$SessionId.gen-seen"
    $compactGen = Join-Path (Get-HookStateRoot) "compact-events\$SessionId.gen"
    $currentGen = 0; $prevGen = 0
    if (Test-Path -LiteralPath $compactGen) {
        [void][int]::TryParse((Get-Content -LiteralPath $compactGen -Raw).Trim(), [ref]$currentGen)
    }
    if (Test-Path -LiteralPath $genSeen) {
        [void][int]::TryParse((Get-Content -LiteralPath $genSeen -Raw).Trim(), [ref]$prevGen)
    }
    if ($currentGen -gt $prevGen) {
        $Files | ForEach-Object { Remove-Item -LiteralPath $_ -Force -ErrorAction SilentlyContinue }
        New-Item -ItemType Directory -Force -Path $CacheDir | Out-Null
        Set-Content -LiteralPath $genSeen -Value $currentGen -NoNewline
    }
}

# Test-SessionOneShotLock <sessionId> <hintName> [alsoReset] — shared one-shot
# hint lock: creates the lock dir, re-arms on compact (also clearing extra
# files, e.g. bash-side markers), and returns $true exactly when this call is
# the first fire of the (post-compact) session — the lock is created as a side
# effect, so $true means "emit the hint now". agent-* filtering stays in the
# caller (not every hint hook skips subagents).
function Test-SessionOneShotLock {
    param(
        [Parameter(Mandatory)][string]$SessionId,
        [Parameter(Mandatory)][string]$HintName,
        [string[]]$AlsoReset = @()
    )
    $cacheDir = Join-Path (Get-HookStateRoot) $HintName
    $lock = Join-Path $cacheDir $SessionId
    New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null
    Reset-OnCompact $SessionId $cacheDir (@($lock) + $AlsoReset)
    if (Test-Path -LiteralPath $lock) { return $false }
    New-Item -ItemType File -Force -Path $lock | Out-Null
    return $true
}

# ---------- shared detection ----------

# Test-PythonUnbuffered <command> <cwd> — mirror of lib/check-python-unbuffered.sh.
# Returns $true when python is invoked (directly or via a just recipe) without
# PYTHONUNBUFFERED / -u — i.e. the background task needs the unbuffered fix.
function Test-PythonUnbuffered {
    param([Parameter(Mandatory)][string]$Command, [string]$Cwd = '.')

    # Already unbuffered via inherited environment (any non-empty value is truthy)
    if ($env:PYTHONUNBUFFERED) { return $false }

    $hasPython = $Command -match '\b(python3?|uv\s+run)\b'
    $recipe = ''

    # Just invocation: resolve recipes to detect indirect python. Skip when
    # `just` isn't installed — no point spawning per-target lookups.
    if ($Command -match '\bjust\b' -and $null -ne (Get-Command just -ErrorAction SilentlyContinue)) {
        # Targets: words after 'just' that don't start with '-'
        $rest = [regex]::Replace($Command, '^.*\bjust\b', '')
        $targets = @($rest -split '\s+' | Where-Object { $_ -and -not $_.StartsWith('-') } | Select-Object -First 5)
        if ($targets.Count -eq 0) { $targets = @('_default') }

        foreach ($t in $targets) {
            $r = $null
            try {
                Push-Location $Cwd
                $r = just --show $t 2>$null
            } catch {
                $r = $null
            } finally {
                Pop-Location
            }
            if ($r) {
                $recipe += "$r`n"
                if ($r -match '\b(python3?|uv\s+run)\b') { $hasPython = $true }
            }
        }
    }

    if (-not $hasPython) { return $false }
    if ($Command.Contains('PYTHONUNBUFFERED')) { return $false }
    if ($recipe -and $recipe.Contains('PYTHONUNBUFFERED')) { return $false }
    if ($Command -match '\bpython3?\s+-u\b') { return $false }
    if ($recipe -and $recipe -match '\bpython3?\s+-u\b') { return $false }

    return $true
}

# ---------- command-position anchors (ports of lib/anchors.sh) ----------
# (?m) on CMD_ANCHOR_BASIC gives every anchor-based check bash's line-wise
# `^` semantics on multi-line commands. Inline options scope to the whole
# concatenated pattern, so (?i) from the caller and (?m) from here compose.
# Line-local gaps are [ \t], never \s (which matches \n in .NET).
$CMD_ANCHOR_BASIC = '(?m)(^|&&|;|\||\(|\{)[ \t]*((do|then|else)[ \t]+)?'
$CMD_ANCHOR_SUDO  = "${CMD_ANCHOR_BASIC}(sudo[ \t]+((-[CDghprtTuU][ \t]+\S+|-\S+)[ \t]+)*)?"
# CMD_WRAPPER adds pwsh/powershell -Command alongside bash/sh -c — the
# PowerShell-tool equivalents of the shell-evaluator escape hatch. Optional
# .exe suffix: `pwsh.exe -Command` is a real PowerShell-tool invocation form.
$CMD_WRAPPER = "${CMD_ANCHOR_SUDO}(((?:bash|sh|pwsh|powershell)(?:\.exe)?)[ \t]+(-\S+[ \t]+)*-c(?:ommand)?[ \t]+|eval[ \t]+|xargs[ \t]+(-\S+[ \t]+)*)['`"`']?(sudo[ \t]+)?"
# CMD_WRAPPER_SSH — ssh-wrapped invocation, for safety blocks where remote
# execution is as hazardous as local. Do NOT add to tool-suggestion hooks.
$CMD_WRAPPER_SSH = "${CMD_ANCHOR_SUDO}ssh[ \t]+((-[bBcDeEFIiJLlmOopQRSWw][ \t]+\S+|-\S+)[ \t]+)*\S+[ \t]+['`"`']?(sudo[ \t]+)?"
$CMD_TRAIL   = '(?=[ \t;&|''"]|$)'

# Trailing-pipeline truncation (one-shot hint + background-risky deny share
# these). Single `|` only (not `||`); `[^|]*$` anchors as the last stage of
# its line, so intermediate uses pass through — matching the .sh originals.
$BASH_TAIL_TRUNCATION = '(?m)(^|[^|])\|[ \t]*(head|tail)([ \t]|$)[^|]*$'
$PS_TAIL_TRUNCATION   = '(?mi)(^|[^|])\|[ \t]*(select(?:-object)?)\b[ \t]+(-\S+[ \t]+)*-(first|last|f|l)\b[^|]*$'

Export-ModuleMember -Function Read-StdinUtf8, Read-HookInput, Read-HookCommand,
    Test-BypassMarker, Exit-IfBypass,
    Emit-PreToolDeny, Emit-PreToolDenyBypassable, Emit-PreToolWarn, Emit-PostToolContext,
    Get-HookStateRoot, Reset-OnCompact, Test-SessionOneShotLock, Test-PythonUnbuffered `
    -Variable CMD_ANCHOR_BASIC, CMD_ANCHOR_SUDO, CMD_WRAPPER, CMD_WRAPPER_SSH, CMD_TRAIL,
    BASH_TAIL_TRUNCATION, PS_TAIL_TRUNCATION
