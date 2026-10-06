#!/usr/bin/env python3
"""PreToolUse hook (Bash + PowerShell): use Read tool with offset/limit instead
of `sed -n 'Np' file` / `sed -n 'N,Mp' file`. Python port of no-sed-print.sh /
no-sed-print.ps1."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

hook_input, command = hooklib.read_hook_command()
hooklib.exit_if_bypass(command, "BYPASS_SED_PRINT_CHECK")

# Skip when sudo precedes sed — Read cannot substitute elevated reads.
if re.search(r"\bsudo[ \t]+[^;&|\r\n]*?\bsed\b", command):
    sys.exit(0)

# Detect sed -n with numeric line printing on a file at command position.
# Catches '12p', 12p, '12,13p', '12,13!p' — not 's/foo/bar/p' (substitution)
# or '/pattern/p' (regex addresses).
m = hooklib.compile_pattern(
    r"(^|&&|;|\|)[ \t]*sed[ \t]+-n[ \t]+['\"]?(\d+[,.!]\d*p|\d+p)['\"]?[ \t]+([^\s|;&>]+)[ \t]*$"
).search(command)
if not m:
    sys.exit(0)
range_str, file = m.group(2), m.group(3)

# Parse range to offset/limit (1-indexed line → 0-indexed offset).
offset = limit = None
if m2 := re.match(r"^(\d+)p$", range_str):
    offset, limit = int(m2.group(1)) - 1, 1
elif m2 := re.match(r"^(\d+),(\d+)p$", range_str):
    offset = int(m2.group(1)) - 1
    limit = int(m2.group(2)) - int(m2.group(1)) + 1

if file and offset is not None:
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_SED_PRINT_CHECK",
        "Use Read tool with offset and limit instead of sed -n for reading specific lines.\n"
        f"  Read(file_path=\"{file}\", offset={offset}, limit={limit})")
else:
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_SED_PRINT_CHECK",
        "Use Read tool with offset and limit instead of sed -n for reading specific lines.\n"
        "  Read(file_path=\"<path>\", offset=<start_line-1>, limit=<num_lines>)")
