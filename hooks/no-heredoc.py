#!/usr/bin/env python3
"""PreToolUse hook (Bash + PowerShell): block oversized inline scripts —
heredoc, PS here-strings, and multi-line -c payloads above 80 lines; use the
Write tool + a temp file instead. Python port of no-heredoc.sh /
no-heredoc.ps1."""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

MAX_LINES = 80

hook_input, command = hooklib.read_hook_command()
hooklib.exit_if_bypass(command, "BYPASS_HEREDOC_RESTRICTION")
hooklib.exit_if_bypass(command, "BYPASS_INLINE_SCRIPT_RESTRICTION")

cmd_lines = command.splitlines()

# Heredoc (<<, not <<<) — bash idiom reachable via bash -c / Git Bash tools.
has_heredoc = re.search(r"<<[^<]", command) is not None

# PS here-string opener: @' / @" at end of line (closed by '@ / "@).
has_here_string = re.search(r"@['\"]\s*$", command, re.MULTILINE) is not None

# Multi-line -c payload: lines from the line containing -c to the end
# (approximation of the bash awk quote-matcher; feeds only the 80-line gate).
has_inline_c = False
inline_c_lines = 0
if re.search(r"-c\s+['\"]", command):
    for i, line in enumerate(cmd_lines):
        if re.search(r"-c\s+['\"]", line):
            inline_c_lines = len(cmd_lines) - i
            break
    if inline_c_lines > MAX_LINES:
        has_inline_c = True

if not (has_heredoc or has_here_string or has_inline_c):
    sys.exit(0)

# Implicit bypass for git commit (heredoc used for commit message)
if re.search(r"\bgit\s+commit\b", command):
    sys.exit(0)

script_lines = 0
if has_heredoc:
    mm = re.search(r"<<[-'\" ]*([A-Za-z_][A-Za-z0-9_]*)", command)
    if not mm:
        sys.exit(0)
    marker = mm.group(1)
    inside = False
    for line in cmd_lines:
        if not inside:
            if "<<" in line and marker in line:
                inside = True
            continue
        if line.strip() == marker:
            inside = False
        else:
            script_lines += 1
    detection_type = "Heredoc"
    bypass_marker = "BYPASS_HEREDOC_RESTRICTION"
elif has_here_string:
    inside = False
    for line in cmd_lines:
        if not inside:
            if re.search(r"@['\"]\s*$", line):
                inside = True
            continue
        if re.match(r"\s*['\"]@", line):
            inside = False
        else:
            script_lines += 1
    detection_type = "Here-string"
    bypass_marker = "BYPASS_HEREDOC_RESTRICTION"
else:
    script_lines = inline_c_lines
    detection_type = "Inline -c script"
    bypass_marker = "BYPASS_INLINE_SCRIPT_RESTRICTION"

if script_lines <= MAX_LINES:
    sys.exit(0)

# Interpreter — order matters: uv run before python
if re.search(r"\buv\s+run\b", command):
    interpreter, ext = "uv run", "py"
elif re.search(r"\bpython3?\b", command):
    interpreter, ext = "python3", "py"
elif re.search(r"\b(bash|sh|pwsh|powershell)\b", command):
    interpreter, ext = "pwsh", "ps1"
else:
    sys.exit(0)

project_temp = Path(os.environ.get("CLAUDE_PROJECT_DIR") or "") / "temp"
if project_temp.exists():
    tmp_dir = project_temp
else:
    tmp_dir = Path(os.environ.get("TEMP") or ".")
tmp_file = tmp_dir / f"script_{os.getpid()}.{ext}"
hooklib.emit_pre_tool_deny_bypassable(bypass_marker,
    f"{detection_type} >{MAX_LINES} lines detected for {interpreter}. "
    f"Use Write tool + temp file instead:\n"
    f"  Write(\"{tmp_file}\", <script>)  →  run: {interpreter} \"{tmp_file}\"")
