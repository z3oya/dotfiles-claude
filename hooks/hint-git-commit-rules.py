#!/usr/bin/env python3
"""PreToolUse hook (Bash + PowerShell): denies the session's first
`git commit -m/--message` with a COMMIT_RULES reminder, so the rules land
before any commit is accepted; the retry passes silently. Bare `git commit`
(editor flow) does not trigger."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

# switch: USER_HOOKS_HINT_GIT_COMMIT_RULES, off = {0,false,off,no}.
if os.environ.get("USER_HOOKS_HINT_GIT_COMMIT_RULES", "").strip().lower() in {"0", "false", "off", "no"}:
    sys.exit(0)

MESSAGE = (
    "Blocked once per session so the rules land before any commit is accepted. "
    "Follow COMMIT_RULES for commit messages: `<type>[(<scope>)][!]: <subject>` — "
    "imperative subject ≤50 display columns, no trailing punctuation, blank line "
    "between sections. Full spec: ~/.claude/hooks/COMMIT_RULES.zh.md / .en.md. "
    "Re-check the message, then re-issue the command (retry passes silently)."
)

hook_input, command = hooklib.read_hook_command()

if "commit" not in command:
    sys.exit(0)

ANCHORS = f"({hooklib.CMD_ANCHOR_SUDO}|{hooklib.CMD_WRAPPER})"
if not hooklib.compile_pattern(
    ANCHORS + r"git[ \t]+commit\b[^;\r\n]*?(-m\b|--message\b)"
).search(command):
    sys.exit(0)

sid = hooklib.get_session_id()
if hooklib.skip_subagent():
    sys.exit(0)

if hooklib.test_session_one_shot_lock(sid, "git-commit-rules-hint"):
    hooklib.emit_pre_tool_deny(MESSAGE)
