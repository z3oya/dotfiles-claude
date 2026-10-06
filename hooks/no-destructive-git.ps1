#Requires -Version 7
# PreToolUse hook (PowerShell tool): block destructive git operations that can
# silently destroy work. Port of no-destructive-git.sh. Each check carries its
# own bypass marker so unrelated chained commands don't silence each other.
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'lib\ps\HookLib.psm1') -Force -DisableNameChecking

Read-HookCommand

$ANCHORS = '(' + $CMD_ANCHOR_SUDO + '|' + $CMD_WRAPPER + '|' + $CMD_WRAPPER_SSH + ')'

# git reset --hard
if ($HookCommand -match ('(?i)' + $ANCHORS + 'git\s+reset\b[^|;&]*\s--hard\b') -and -not (Test-BypassMarker 'BYPASS_RESET_HARD_CHECK')) {
    Emit-PreToolDenyBypassable 'BYPASS_RESET_HARD_CHECK' 'Do not use git reset --hard. It permanently discards working-tree and index changes.'
    exit 0
}

# git clean -f (matches combined flags like -fd, -fx, -dfx)
if ($HookCommand -match ('(?i)' + $ANCHORS + 'git\s+clean\b[^|;&]*\s-[a-zA-Z]*f[a-zA-Z]*\b') -and -not (Test-BypassMarker 'BYPASS_GIT_CLEAN_CHECK')) {
    Emit-PreToolDenyBypassable 'BYPASS_GIT_CLEAN_CHECK' "Do not use git clean -f. It deletes untracked files which may include the user's in-progress work."
    exit 0
}

# git branch -D (force-delete; -d alone is non-destructive — it refuses unmerged)
if ($HookCommand -match ('(?i)' + $ANCHORS + 'git\s+branch\b[^|;&]*\s-D\b') -and -not (Test-BypassMarker 'BYPASS_BRANCH_DELETE_CHECK')) {
    Emit-PreToolDenyBypassable 'BYPASS_BRANCH_DELETE_CHECK' 'Do not use git branch -D. It force-deletes branches with unmerged commits, losing work.'
    exit 0
}

# git checkout -- <path>  or  git checkout .  (discard working-tree changes)
if ($HookCommand -match ('(?i)' + $ANCHORS + 'git\s+checkout\b[^|;&]*(\s--(\s|$)|\s\.(\s|$))') -and -not (Test-BypassMarker 'BYPASS_CHECKOUT_DISCARD_CHECK')) {
    Emit-PreToolDenyBypassable 'BYPASS_CHECKOUT_DISCARD_CHECK' 'Do not use git checkout -- / git checkout . — these discard local working-tree changes.'
    exit 0
}

# git restore <path> WITHOUT --staged / -S (default form discards working-tree)
if ($HookCommand -match ('(?i)' + $ANCHORS + 'git\s+restore\b') `
    -and $HookCommand -notmatch '(?i)git\s+restore\b[^|;&]*\s(--staged|-S)\b' `
    -and -not (Test-BypassMarker 'BYPASS_RESTORE_CHECK')) {
    Emit-PreToolDenyBypassable 'BYPASS_RESTORE_CHECK' 'Do not use git restore <path> without --staged. It discards working-tree changes.'
    exit 0
}

# git rm -f / --force (overrides safety check on uncommitted changes);
# --cached is exempt (unstages only, never touches the filesystem).
if ($HookCommand -match ('(?i)' + $ANCHORS + 'git\s+rm\b[^|;&]*\s(-[a-zA-Z]*f[a-zA-Z]*|--force)\b') `
    -and $HookCommand -notmatch '(?i)git\s+rm\b[^|;&]*\s--cached\b' `
    -and -not (Test-BypassMarker 'BYPASS_GIT_RM_FORCE_CHECK')) {
    Emit-PreToolDenyBypassable 'BYPASS_GIT_RM_FORCE_CHECK' "Do not use git rm -f / --force. It overrides git's safety check and deletes files with uncommitted modifications — those changes are then unrecoverable (git only has the last committed version).
Plain ``git rm <file>`` refuses uncommitted changes (safe). If you intend to discard those modifications, commit / stash them first, then ``git rm``."
    exit 0
}

exit 0
