#Requires -Version 7
# PreToolUse hook (PowerShell tool): deny background-risky PowerShell with a
# trailing `| head` / `| tail` (or the PS-equivalent trailing Select-Object
# -First/-Last). Port of no-bg-head-tail-pipe.sh. Explicit backgrounding and
# long timeouts can both land in background, where head kills the producer and
# tail over a pipe buffers until EOF.
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'lib\ps\HookLib.psm1') -Force -DisableNameChecking

Read-HookInput

$runInBg = [string]$HookInput.tool_input.run_in_background
$timeoutMs = 0
[void][int]::TryParse([string]$HookInput.tool_input.timeout, [ref]$timeoutMs)
$maxTimeoutMs = 600000
[void][int]::TryParse($env:BASH_MAX_TIMEOUT_MS, [ref]$maxTimeoutMs)
if ($maxTimeoutMs -le 0) { $maxTimeoutMs = 600000 }
if ($runInBg -ne 'true' -and $timeoutMs -lt $maxTimeoutMs) { exit 0 }

$command = [string]$HookInput.tool_input.command
if ([string]::IsNullOrEmpty($command)) { exit 0 }
$global:HookCommand = $command
Exit-IfBypass 'BYPASS_BACKGROUND_HEAD_TAIL'

# Trailing `| head` / `| tail` (bash tools via PS) or trailing
# `| Select-Object -First/-Last` (PS-native) — the last pipeline stage.
# Shared patterns from HookLib (?m line-wise, single `|`, trailing stage only).
if ($command -match $BASH_TAIL_TRUNCATION -or $command -match $PS_TAIL_TRUNCATION) {
    Emit-PreToolDenyBypassable 'BYPASS_BACKGROUND_HEAD_TAIL' 'Background-risky command (run_in_background=true or timeout >= max) with trailing `| head` / `| tail` / `| Select-Object -First/-Last` is rejected. `head` exits after N lines and kills the producer; `tail` over a pipe buffers until EOF (the `-f` flag does not follow pipes) and never emits for a long-running task. It would appear like the process stuck in background and you will never be able to see the full log again. Instead, drop the trailing truncation and start the bare command — the harness will capture all the stdout into a text file (instead of feeding directly into context) on completion. You can freely rg/Read on it for analyzing the log, with no worry about context flood.'
}
exit 0
