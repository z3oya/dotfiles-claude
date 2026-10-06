#!/usr/bin/env python3
"""PreToolUse hook (Bash + PowerShell): use Write tool instead of cat-heredoc
file writes (reachable via bash -c or Git Bash cat.exe). Python port of
no-cat-write.sh / no-cat-write.ps1."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

hook_input, command = hooklib.read_hook_command()
hooklib.exit_if_bypass(command, "BYPASS_CAT_WRITE")

ANCHORS = f"({hooklib.CMD_ANCHOR_SUDO}|{hooklib.CMD_WRAPPER})"
cat_heredoc = hooklib.compile_pattern(ANCHORS + r"cat\b.*<<", ignorecase=True)
cat_redirect = hooklib.compile_pattern(ANCHORS + r"cat\b.*(>\s*\S|>>\s*\S|\|\s*tee\b)", ignorecase=True)

if not cat_heredoc.search(command) or not cat_redirect.search(command):
    sys.exit(0)

# Implicit bypass for git commit (heredoc used for commit message)
if re.search(r"\bgit\s+commit\b", command):
    sys.exit(0)

# Skip when sudo precedes cat — Write cannot substitute elevated writes.
if re.search(r"\bsudo[ \t]+[^;&|\r\n]*?\bcat\b", command):
    sys.exit(0)

# Extract target file path (stop at first space, <, |, & or newline).
m = re.search(r">[ \t]*([^<>|&\r\n ]+)", command)
file = m.group(1).replace("'", "") if m else None

if file:
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_CAT_WRITE",
        f"Use Write tool instead of cat heredoc for file writes.\n  Write(\"{file}\", <content>)")
else:
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_CAT_WRITE",
        "Use Write tool instead of cat heredoc for file writes.")
