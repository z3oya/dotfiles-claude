#!/usr/bin/env python3
"""PreToolUse hook (Bash + PowerShell): block git commit --amend, push --force,
push --delete. Python port of no-git-amend.sh / no-git-amend.ps1. Each check
carries its own bypass marker so a bypass on one chained operation does not
silence another."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

hook_input, command = hooklib.read_hook_command()

ANCHORS = f"({hooklib.CMD_ANCHOR_SUDO}|{hooklib.CMD_WRAPPER}|{hooklib.CMD_WRAPPER_SSH})"
A = lambda s: hooklib.compile_pattern(s, ignorecase=True).search(command)

if A(ANCHORS + r"git\s+commit\b.*--amend") and not hooklib.test_bypass_marker(command, "BYPASS_AMEND_CHECK"):
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_AMEND_CHECK",
        "Do not use git commit --amend. Always create new commits instead.")
    sys.exit(0)

# git push --force / -f / --force-with-lease / --force-if-includes
if A(ANCHORS + r"git\s+push\b[^|;&]*(\s--force(-with-lease|-if-includes)?\b|\s-[a-zA-Z]*f\b)") \
        and not hooklib.test_bypass_marker(command, "BYPASS_FORCE_PUSH_CHECK"):
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_FORCE_PUSH_CHECK",
        "Do not use git push --force (or -f). Force-push rewrites remote history "
        "and can destroy others' work.")
    sys.exit(0)

# git push --delete / -d <remote> <branch>, or refspec `git push <remote> :<branch>`
if A(ANCHORS + r"git\s+push\b[^|;&]*(\s--delete\b|\s-[a-zA-Z]*d\b|\s:[\w./-]+)") \
        and not hooklib.test_bypass_marker(command, "BYPASS_PUSH_DELETE_CHECK"):
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_PUSH_DELETE_CHECK",
        "Do not use git push --delete (or `git push <remote> :<branch>`). Deleting a remote "
        "branch erases history that collaborators may share, and some workflows treat branch "
        "refs as a permanent record.\n"
        "Confirm the branch is fully merged and not protected; prefer letting the remote's "
        "branch-cleanup workflow handle it after the PR merges.")
    sys.exit(0)
