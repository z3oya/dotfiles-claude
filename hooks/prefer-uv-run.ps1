#Requires -Version 7
# PreToolUse hook (PowerShell tool): block bare python3, require uv run.
# PowerShell port of prefer-uv-run.sh — serves the PowerShell tool via the
# "PowerShell" matcher; the .sh original keeps serving the Bash tool.
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'lib\ps\HookLib.psm1') -Force -DisableNameChecking

Read-HookCommand
Exit-IfBypass 'BYPASS_UV_RUN_CHECK'

# Skip if an active venv/conda env already scopes bare python3 correctly
if ($env:VIRTUAL_ENV -or $env:CONDA_PREFIX) {
    exit 0
}

# Skip if command already uses uv run
if ($HookCommand -match '\buv\s+run\b') {
    exit 0
}

# Skip if uv isn't installed — no point suggesting an unavailable alternative.
if ($null -eq (Get-Command uv -ErrorAction SilentlyContinue)) {
    exit 0
}

# Detect bare python3/python at command position. Anchor adds `&` — the
# PowerShell call operator (`& python script.py` is a common PS idiom).
# (?im) for bash's line-wise anchoring; [ \t] gaps so a pattern never
# straddles lines the way bash's line-wise grep cannot.
if ($HookCommand -notmatch '(?im)(^|&&|;|\||&)[ \t]*python3?[ \t]') {
    exit 0
}

# Skip common legitimate bare-python uses. Case-SENSITIVE (-cmatch): `-V` is
# version, but lowercase `-v` is Python's verbose flag — a real script run.
if ($HookCommand -cmatch 'python3?[ \t]+(-V|--version|--help|-c[ \t])') {
    exit 0
}

Emit-PreToolDenyBypassable 'BYPASS_UV_RUN_CHECK' @'
Prefer uv run python instead of python3 directly.
  python3 script.py  →  uv run python script.py
'@
exit 0
