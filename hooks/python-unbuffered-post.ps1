#Requires -Version 7
# PostToolUse hook (PowerShell tool): warn when an auto-backgrounded python
# task lacks unbuffered output. Port of python-unbuffered-post.sh. Catches the
# case PreToolUse can't: foreground python auto-backgrounded by timeout.
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'lib\ps\HookLib.psm1') -Force -DisableNameChecking

Read-HookInput

# Only fire when the command was backgrounded (explicit or auto)
$bgId = [string]$HookInput.tool_response.backgroundTaskId
if ([string]::IsNullOrEmpty($bgId)) { exit 0 }

# Skip explicit run_in_background — already caught by PreToolUse
if ([string]$HookInput.tool_input.run_in_background -eq 'true') { exit 0 }

$command = [string]$HookInput.tool_input.command
$cwd = [string]$HookInput.cwd

if (Test-PythonUnbuffered $command $cwd) {
    Emit-PostToolContext 'If this is a Python task, stdout is connected to a pipe, so Python buffers output instead of flushing in real time — making it look stuck or empty. Re-run with unbuffered output for easier real-time monitoring: PYTHONUNBUFFERED=1 uv run python script.py'
}
exit 0
