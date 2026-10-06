#!/usr/bin/env python3
"""PreToolUse hook (Bash + PowerShell): use Read tool with limit instead of
`head -N file`. Python port of no-head-read.sh / no-head-read.ps1."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

hook_input, command = hooklib.read_hook_command()
hooklib.exit_if_bypass(command, "BYPASS_HEAD_READ_CHECK")

# Skip when sudo precedes head — Read runs without elevated privileges so
# cannot substitute for `sudo head -3 /etc/shadow`.
if re.search(r"\bsudo[ \t]+[^;&|\r\n]*?\bhead\b", command):
    sys.exit(0)

FLAGS = r"-\d+|-n[ \t]*\d+|--lines[= ][ \t]*\d+"
detect = hooklib.compile_pattern(rf"(^|&&|;|\|)[ \t]*head[ \t]+({FLAGS})[ \t]+[^\s|;&>]+[ \t]*$")
if not detect.search(command):
    sys.exit(0)

m = re.search(rf"\bhead[ \t]+(?:{FLAGS})[ \t]+([^\s|;&>]+)", command)
mf = re.search(rf"\bhead[ \t]+({FLAGS})", command)
num_m = re.search(r"(\d+)", mf.group(1)) if mf else None
num = num_m.group(1) if num_m else None
file = m.group(1) if m else None

if file and num:
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_HEAD_READ_CHECK",
        f"Use Read tool with limit instead of head for reading file lines.\n"
        f"  Read(file_path=\"{file}\", limit={num})")
else:
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_HEAD_READ_CHECK",
        "Use Read tool with limit instead of head for reading file lines.\n"
        "  Read(file_path=\"<path>\", limit=<num_lines>)")
