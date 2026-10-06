#!/usr/bin/env python3
"""PostToolUse hook (Bash + PowerShell): hint ls → eza. prefer-* series;
fires on every matching command (message is two short lines, no quota)."""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

ANCHORS = "(" + hooklib.CMD_ANCHOR_SUDO + "|" + hooklib.CMD_WRAPPER + ")"
PATTERN = ANCHORS + "ls" + hooklib.CMD_TRAIL
MESSAGE = ("Prefer eza instead of ls.\n"
           "  ls -la  →  eza -la")

hook_input, command = hooklib.read_hook_command()

if shutil.which("eza") \
        and hooklib.compile_pattern(PATTERN, ignorecase=True).search(command):
    hooklib.emit_post_tool_context(MESSAGE)
