#Requires -Version 7
# PreToolUse hook (PowerShell tool): advertise the /agent-browser skill when
# Claude is about to drive Chrome/Chromium headless by hand. Port of
# hint-skill-agent-browser.sh. Fires at most once per session (re-arms after
# compact). Non-blocking by design — emits additionalContext and lets the
# command run.
#
# Discriminator: the --headless flag carries the specificity, so binary
# matching is deliberately lenient (path prefixes and wrappers fire too). The
# residual FP is harmless: a one-shot, non-blocking nudge.
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'lib\ps\HookLib.psm1') -Force -DisableNameChecking

Read-HookCommand

# Already using the skill's CLI — nothing to advertise.
if ($HookCommand -match 'agent-browser') { exit 0 }

# Fire if either: (a) an inherently-headless Chromium shell binary, or
# (b) a Chrome/Chromium-family binary WITH the --headless flag.
$shellRe = '\b(chromium-headless-shell|chrome-headless-shell|headless[-_]shell)\b'
$chromeRe = '\b(chromium(-browser)?|google-chrome(-stable)?|chrome)\b'

if ($HookCommand -match $shellRe) {
    # headless shell binary — fire
} elseif ($HookCommand -match $chromeRe -and $HookCommand -match '--headless\b') {
    # chrome family + headless flag — fire
} else {
    exit 0
}

$sid = [string]$HookInput.session_id
if (-not $sid) { $sid = 'unknown' }
if ($sid -like 'agent-*') { exit 0 }

if (Test-SessionOneShotLock $sid 'skill-hint-agent-browser') {
    Emit-PreToolWarn 'About to drive Chrome/Chromium headless by hand. Consider the /agent-browser skill — it wraps Chrome/Chromium over CDP with snapshot/click/fill/screenshot verbs and a persistent daemon, instead of raw `chromium --headless` flag-juggling. Load via Skill tool (skill=''agent-browser''). Raw `chromium --headless` is fine for a one-off where the skill is unavailable. (One-shot hint — will not fire again this session.)'
}
exit 0
