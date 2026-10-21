#!/usr/bin/env python3
"""PreToolUse hook (Bash + PowerShell): block destructive git operations that
destroy work without prompting. Python port of no-destructive-git.sh /
no-destructive-git.ps1. Each check carries its own bypass marker so unrelated
chained commands don't silence each other."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

hook_input, command = hooklib.read_hook_command()

ANCHORS = f"({hooklib.CMD_ANCHOR_SUDO}|{hooklib.CMD_WRAPPER}|{hooklib.CMD_WRAPPER_SSH})"
A = lambda s: hooklib.compile_pattern(s, ignorecase=True).search(command)

# git reset --hard
if A(ANCHORS + r"git\s+reset\b[^|;&]*\s--hard\b") and not hooklib.test_bypass_marker(command, "BYPASS_RESET_HARD_CHECK"):
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_RESET_HARD_CHECK",
        "Do not use git reset --hard. It permanently discards working-tree and index changes.")
    sys.exit(0)

# git clean -f (matches combined flags like -fd, -fx, -dfx)
if A(ANCHORS + r"git\s+clean\b[^|;&]*\s-[a-zA-Z]*f[a-zA-Z]*\b") \
        and not hooklib.test_bypass_marker(command, "BYPASS_GIT_CLEAN_CHECK"):
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_GIT_CLEAN_CHECK",
        "Do not use git clean -f. It deletes untracked files which may include the user's "
        "in-progress work.")
    sys.exit(0)

# git branch -D (force-delete; -d alone is non-destructive — it refuses unmerged)
if A(ANCHORS + r"git\s+branch\b[^|;&]*\s-D\b") \
        and not hooklib.test_bypass_marker(command, "BYPASS_BRANCH_DELETE_CHECK"):
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_BRANCH_DELETE_CHECK",
        "Do not use git branch -D. It force-deletes branches with unmerged commits, losing work.")
    sys.exit(0)

# git checkout -- <path>  or  git checkout .  (discard working-tree changes)
if A(ANCHORS + r"git\s+checkout\b[^|;&]*(\s--(\s|$)|\s\.(\s|$))") \
        and not hooklib.test_bypass_marker(command, "BYPASS_CHECKOUT_DISCARD_CHECK"):
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_CHECKOUT_DISCARD_CHECK",
        "Do not use git checkout -- / git checkout . — these discard local working-tree changes.")
    sys.exit(0)

# git restore <path> WITHOUT --staged / -S (default form discards working-tree)
if A(ANCHORS + r"git\s+restore\b") \
        and not hooklib.compile_pattern(r"git\s+restore\b[^|;&]*\s(--staged|-S)\b", ignorecase=True).search(command) \
        and not hooklib.test_bypass_marker(command, "BYPASS_RESTORE_CHECK"):
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_RESTORE_CHECK",
        "Do not use git restore <path> without --staged. It discards working-tree changes.")
    sys.exit(0)

# git rm -f / --force (overrides safety check on uncommitted changes);
# --cached is exempt (unstages only, never touches the filesystem).
if A(ANCHORS + r"git\s+rm\b[^|;&]*\s(-[a-zA-Z]*f[a-zA-Z]*|--force)\b") \
        and not hooklib.compile_pattern(r"git\s+rm\b[^|;&]*\s--cached\b", ignorecase=True).search(command) \
        and not hooklib.test_bypass_marker(command, "BYPASS_GIT_RM_FORCE_CHECK"):
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_GIT_RM_FORCE_CHECK",
        "Do not use git rm -f / --force. It overrides git's safety check and deletes files with "
        "uncommitted modifications — those changes are then unrecoverable (git only has the last "
        "committed version).\n"
        "Plain `git rm <file>` refuses uncommitted changes (safe). If you intend to discard those "
        "modifications, commit / stash them first, then `git rm`.")
    sys.exit(0)

# git stash — pop conflicts and drop/clear discard diffs irreversibly. The
# permission layer denies the bare form; this adds wrapper forms
# (bash -c / eval / xargs / ssh / ...).
if A(ANCHORS + r"git\s+stash\b") and not hooklib.test_bypass_marker(command, "BYPASS_STASH_CHECK"):
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_STASH_CHECK",
        "Do not use git stash. Stash pop conflicts and stash drop/clear discard changes with "
        "no recovery path. Commit or branch instead; `git stash list` / `show` are read-only "
        "— bypass with `# BYPASS_STASH_CHECK` for those.")
    sys.exit(0)
