#Requires -Version 7
# PreToolUse hook (PowerShell tool): block babysit commands until the /babysit
# skill has been loaded. Port of hint-skill-babysit.sh. Denies once per session
# per compact, then allows through (one-shot guardrail).
#
# The skill-loaded marker is written by track-babysit-skill-load.sh under the
# bash-side /tmp/claude-<uid>-state tree, whose UID is not predictable from
# pwsh — resolve it with a bounded glob. Ordering matches the .sh original:
# the compact reset runs FIRST (clearing this hook's lock and the bash-side
# marker together), then the marker decides — so a post-compact session
# re-prompts when the skill was loaded only pre-compact.
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'lib\ps\HookLib.psm1') -Force -DisableNameChecking

Read-HookCommand

if ($HookCommand -notmatch ('(' + $CMD_ANCHOR_SUDO + '|' + $CMD_WRAPPER + ')babysit' + $CMD_TRAIL)) { exit 0 }

$sid = [string]$HookInput.session_id
if (-not $sid) { $sid = 'unknown' }
# Skip subagents — agent-* prefix on session_id.
if ($sid -like 'agent-*') { exit 0 }

# Resolve the bash-side marker path (needed as a compact-reset target).
$bashMarkerGlob = Join-Path $env:TEMP 'claude-*-state\babysit-skill-loaded'
$found = @(Get-ChildItem $bashMarkerGlob -Filter $sid -File -ErrorAction SilentlyContinue)
$markerPath = $found.Count -gt 0 ? $found[0].FullName : $null

# One-shot hint lock; compaction also clears the bash-side marker.
$hintDir = Join-Path (Get-HookStateRoot) 'babysit-skill-hint'
$hintLock = Join-Path $hintDir $sid
New-Item -ItemType Directory -Force -Path $hintDir | Out-Null
$alsoReset = @($hintLock)
if ($markerPath) { $alsoReset += $markerPath }
Reset-OnCompact $sid $hintDir $alsoReset

# Post-reset state of the marker decides (it may have just been cleared).
$skillLoaded = @(Get-ChildItem $bashMarkerGlob -Filter $sid -File -ErrorAction SilentlyContinue).Count -gt 0
if ($skillLoaded) { exit 0 }
if (Test-Path -LiteralPath $hintLock) { exit 0 }
New-Item -ItemType File -Force -Path $hintLock | Out-Null

Emit-PreToolDeny "Load /babysit skill first — invoke Skill tool with skill='babysit' to get the standardised workflow and guardrails before running babysit commands. Ignore this hint if false positive trigger. (One-shot hint — will not fire again this session.)"
exit 0
