#!/usr/bin/env python3
"""PreToolUse hook (Bash + PowerShell): block babysit commands until the
/babysit skill has been loaded. Python port of hint-skill-babysit.sh. Denies
once per session per compact, then allows through (one-shot guardrail).

Ordering mirrors the .sh original: the compact reset runs FIRST against BOTH
caches (each with its own gen-seen), then the marker decides. The skill-loaded
marker is written by track-babysit-skill-load.py into babysit-skill-loaded/ —
that hook also syncs the marker dir's gen-seen, so a skill loaded *after* a
compact survives the reset, while a pre-compact load is wiped and re-prompts."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

hook_input, command = hooklib.read_hook_command()

ANCHORS = f"({hooklib.CMD_ANCHOR_SUDO}|{hooklib.CMD_WRAPPER})"
if not hooklib.compile_pattern(ANCHORS + "babysit" + hooklib.CMD_TRAIL, ignorecase=True).search(command):
    sys.exit(0)

sid = hooklib.get_session_id()
if hooklib.skip_subagent():
    sys.exit(0)

state_root = hooklib.get_state_root()

# Compact reset first — hint lock and skill marker each with their own
# gen-seen (mirrors the .sh double reset_on_compact).
hint_dir = state_root / "babysit-skill-hint"
hint_lock = hint_dir / sid
hooklib.reset_on_compact(sid, hint_dir, [str(hint_lock)])
marker_dir = state_root / "babysit-skill-loaded"
marker = marker_dir / sid
hooklib.reset_on_compact(sid, marker_dir, [str(marker)])

if marker.exists():
    sys.exit(0)
if hint_lock.exists():
    sys.exit(0)
hint_lock.touch()

hooklib.emit_pre_tool_deny(
    "Load /babysit skill first — invoke Skill tool with skill='babysit' to get "
    "the standardised workflow and guardrails before running babysit commands. "
    "Ignore this hint if false positive trigger. (One-shot hint — will not fire again this session.)"
)
