#!/usr/bin/env python3
"""PreToolUse hook: block isolation="worktree" combined with team_name —
silently broken (GitHub #33045). Python port of no-worktree-team.sh.
Workaround: pre-create worktrees, tell teammates to EnterWorktree(path:)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

hook_input = hooklib.read_hook_input()
ti = hook_input.get("tool_input") or {}

isolation = str(ti.get("isolation") or "")
team_name = str(ti.get("team_name") or "")
if isolation == "worktree" and team_name:
    hooklib.emit_pre_tool_deny(
        "isolation: worktree silently fails with team_name (#33045). Either use "
        "no team_name for regular subagents, or pre-create worktrees under "
        ".claude/worktrees/ and tell teammates to EnterWorktree(path:)."
    )
