#Requires -Version 7
# PreToolUse hook (PowerShell tool): block pip and npm in favor of uv and pnpm.
# PowerShell port of no-pip-npm.sh — serves the PowerShell tool via the
# "PowerShell" matcher; the .sh original keeps serving the Bash tool.
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'lib\ps\HookLib.psm1') -Force -DisableNameChecking

Read-HookCommand
Exit-IfBypass 'BYPASS_PACKAGE_MANAGER_CHECK'

# Anchors as alternation, mirroring no-pip-npm.sh's ANCHORS="(SUDO|WRAPPER)":
# SUDO branch covers direct command position; WRAPPER covers bash -c/eval/
# xargs/pwsh -Command wrapped invocations.
$ANCHORS = '(' + $CMD_ANCHOR_SUDO + '|' + $CMD_WRAPPER + ')'

# Skip inside an active conda env (checked before the PATH scan — conda users
# may need pip for conda-managed interpreters). Skip if uv isn't installed —
# no point suggesting an unavailable alternative.
$hasUv = $env:CONDA_PREFIX ? $false : ($null -ne (Get-Command uv -ErrorAction SilentlyContinue))
if ($hasUv) {
    if ($HookCommand -match ('(?i)' + $ANCHORS + 'pip3?' + $CMD_TRAIL)) {
        Emit-PreToolDenyBypassable 'BYPASS_PACKAGE_MANAGER_CHECK' @'
Use uv instead of pip.
  pip install pkg  →  uv add pkg (project) or uv pip install pkg (venv)
  pip freeze       →  uv pip freeze
'@
        exit 0
    }
}

# Detect npm usage; CMD_TRAIL ensures `pnpm` (substring `npm`) doesn't trigger.
# Skip if pnpm isn't installed.
$hasPnpm = $null -ne (Get-Command pnpm -ErrorAction SilentlyContinue)
if ($hasPnpm -and $HookCommand -match ('(?i)' + $ANCHORS + 'npm' + $CMD_TRAIL)) {
    Emit-PreToolDenyBypassable 'BYPASS_PACKAGE_MANAGER_CHECK' @'
Use pnpm instead of npm.
  npm install  →  pnpm install
  npm run      →  pnpm run
'@
    exit 0
}

exit 0
