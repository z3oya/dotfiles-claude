#!/usr/bin/env python3
"""PreToolUse hook (Bash + PowerShell): no output discarding into the void —
`> /dev/null` (bash) and the PS-native `> $null` (any stream redirect) both
blocked. Python port of no-devnull-redirect.sh / no-devnull-redirect.ps1."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

hook_input, command = hooklib.read_hook_command()
hooklib.exit_if_bypass(command, "BYPASS_DEVNULL_CHECK")

# `>` + optional whitespace + /dev/null — or the PS-native $null equivalent.
if re.search(r">\s*/dev/null\b", command) or re.search(r"(?i)>\s*\$null\b", command):
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_DEVNULL_CHECK",
        "Do not redirect to /dev/null — noise is cheaper than blindness.\n"
        "Remove the `>/dev/null` / `2>/dev/null` / `>$null` so output reaches the agent.")
