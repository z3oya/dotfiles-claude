#!/usr/bin/env python3
"""PreToolUse hook (Bash + PowerShell): no shell-level backgrounding —
trailing `&` (bash idiom; PS syntax error, still flagged) or Start-Job (the
PowerShell-native background primitive). Python port of
no-background-ampersand.sh / no-background-ampersand.ps1."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

hook_input, command = hooklib.read_hook_command()
hooklib.exit_if_bypass(command, "BYPASS_BACKGROUND_CHECK")

if re.search(r"(?m)[^&]&[ \t]*$", command) or re.search(r"(?i)\bstart-job\b", command):
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_BACKGROUND_CHECK",
        "Do not background by shell. Use the tool parameter instead:\n"
        "  Bash(command=\"...\", run_in_background=true)  /  "
        "PowerShell(command=\"...\", run_in_background=true)")
