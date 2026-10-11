#!/usr/bin/env python3
"""PreToolUse hook (Bash + PowerShell): asks the user on every `git commit`.
hint-git-commit-rules.py already denies the session's first attempt once."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

# switch: USER_HOOKS_ASK_GIT_COMMIT, off = {0,false,off,no}.
if os.environ.get("USER_HOOKS_ASK_GIT_COMMIT", "").strip().lower() in {"0", "false", "off", "no"}:
    sys.exit(0)

hook_input, command = hooklib.read_hook_command()

if "commit" not in command:
    sys.exit(0)

ANCHORS = f"({hooklib.CMD_ANCHOR_SUDO}|{hooklib.CMD_WRAPPER})"
# git [global opts] commit — superset of hint-git-commit-rules' pattern.
if not hooklib.compile_pattern(
    ANCHORS + r"git(?:\.exe)?[ \t]+(?:-{1,2}[\w.-]+(?:[ \t]+[\w./=-]+)?[ \t]+)*commit\b"
).search(command):
    sys.exit(0)

# no subagent skip: subagent commits must ask too.
hooklib.emit_pre_tool_ask(
    "git commit requires explicit user approval. "
    "Verify the message against COMMIT_RULES (~/.claude/hooks/COMMIT_RULES.zh.md) before approving."
)
