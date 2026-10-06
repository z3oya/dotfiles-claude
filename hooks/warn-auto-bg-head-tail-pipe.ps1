#Requires -Version 7
# PostToolUse hook (PowerShell tool): warn when a foreground command got
# auto-backgrounded by timeout AND ends with `| head` / `| tail` / trailing
# Select-Object -First/-Last. Port of warn-auto-bg-head-tail-pipe.sh. The
# PreToolUse counterpart owns explicit run_in_background=true and long timeouts;
# this catches other implicit promotions.
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'lib\ps\HookLib.psm1') -Force -DisableNameChecking

Read-HookInput

# Auto-backgrounded only — backgroundTaskId set in tool_response
$bgId = [string]$HookInput.tool_response.backgroundTaskId
if ([string]::IsNullOrEmpty($bgId)) { exit 0 }

# Skip explicit run_in_background — PreToolUse hook owns that case
if ([string]$HookInput.tool_input.run_in_background -eq 'true') { exit 0 }

$command = [string]$HookInput.tool_input.command
if ([string]::IsNullOrEmpty($command)) { exit 0 }

# Shared truncation patterns from HookLib (?m line-wise, trailing stage only).
if ($command -match $BASH_TAIL_TRUNCATION -or $command -match $PS_TAIL_TRUNCATION) {
    Emit-PostToolContext 'This command was auto-backgrounded (timeout) and ends with `| head` / `| tail` / `| Select-Object -First/-Last`. `head` exits after N lines and kills the producer; `tail` over a pipe buffers until EOF (the `-f` flag does not follow pipes) and never emits for a long-running task. The process will appear stuck in background and you will never be able to see the full log. Instead, consider re-run without the trailing truncation — the harness will capture all the stdout into a text file (instead of feeding directly into context) on completion. You can freely rg/Read on it for analyzing the log, with no worry about context flood.'
}
exit 0
