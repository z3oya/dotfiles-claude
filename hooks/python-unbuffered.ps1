#Requires -Version 7
# PreToolUse hook (PowerShell tool): block background python tasks without
# unbuffered output. Port of python-unbuffered.sh. Only checks explicit
# run_in_background=true (auto-backgrounding is caught by the PostToolUse
# counterpart). just recipes are resolved to detect indirect python.
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'lib\ps\HookLib.psm1') -Force -DisableNameChecking

Read-HookInput

# Only check explicit run_in_background
if ([string]$HookInput.tool_input.run_in_background -ne 'true') { exit 0 }

$command = [string]$HookInput.tool_input.command
if ([string]::IsNullOrEmpty($command)) { exit 0 }
$global:HookCommand = $command
Exit-IfBypass 'BYPASS_UNBUFFERED_CHECK'

$cwd = [string]$HookInput.cwd
if (Test-PythonUnbuffered $command $cwd) {
    Emit-PreToolDenyBypassable 'BYPASS_UNBUFFERED_CHECK' 'Background python task must use unbuffered output.
Claude launches processes with stdout as a pipe, causing Python to buffer output instead of flushing in real time — making it look stuck or empty.
Either: PYTHONUNBUFFERED=1 uv run python script.py
    or: uv run python -u script.py'
}
exit 0
