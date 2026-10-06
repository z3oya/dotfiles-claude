#Requires -Version 7
# PreToolUse hook (PowerShell tool): block git commit --amend, push --force,
# push --delete. Port of no-git-amend.sh. Each check carries its own bypass
# marker so a bypass on one chained operation does not silence another.
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'lib\ps\HookLib.psm1') -Force -DisableNameChecking

Read-HookCommand

$ANCHORS = '(' + $CMD_ANCHOR_SUDO + '|' + $CMD_WRAPPER + '|' + $CMD_WRAPPER_SSH + ')'

if ($HookCommand -match ('(?i)' + $ANCHORS + 'git\s+commit\b.*--amend') -and -not (Test-BypassMarker 'BYPASS_AMEND_CHECK')) {
    Emit-PreToolDenyBypassable 'BYPASS_AMEND_CHECK' 'Do not use git commit --amend. Always create new commits instead.'
    exit 0
}

# git push --force / -f / --force-with-lease / --force-if-includes
if ($HookCommand -match ('(?i)' + $ANCHORS + 'git\s+push\b[^|;&]*(\s--force(-with-lease|-if-includes)?\b|\s-[a-zA-Z]*f\b)') -and -not (Test-BypassMarker 'BYPASS_FORCE_PUSH_CHECK')) {
    Emit-PreToolDenyBypassable 'BYPASS_FORCE_PUSH_CHECK' "Do not use git push --force (or -f). Force-push rewrites remote history and can destroy others' work."
    exit 0
}

# git push --delete / -d <remote> <branch>, or refspec `git push <remote> :<branch>`
if ($HookCommand -match ('(?i)' + $ANCHORS + 'git\s+push\b[^|;&]*(\s--delete\b|\s-[a-zA-Z]*d\b|\s:[\w./-]+)') -and -not (Test-BypassMarker 'BYPASS_PUSH_DELETE_CHECK')) {
    Emit-PreToolDenyBypassable 'BYPASS_PUSH_DELETE_CHECK' 'Do not use git push --delete (or `git push <remote> :<branch>`). Deleting a remote branch erases history that collaborators may share, and some workflows treat branch refs as a permanent record.
Confirm the branch is fully merged and not protected; prefer letting the remote''s branch-cleanup workflow handle it after the PR merges.'
    exit 0
}

exit 0
