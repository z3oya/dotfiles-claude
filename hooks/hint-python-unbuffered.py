#!/usr/bin/env python3
"""PostToolUse hook (Bash + PowerShell): warn when an auto-backgrounded python
task lacks unbuffered output. Python port of python-unbuffered-post.ps1.
Catches the case PreToolUse can't: foreground python auto-backgrounded by
timeout."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

hook_input = hooklib.read_hook_input()

# Only fire when the command was backgrounded (explicit or auto)
resp = hook_input.get("tool_response") or {}
if not str(resp.get("backgroundTaskId") or ""):
    sys.exit(0)

# Skip explicit run_in_background — already caught by PreToolUse
ti = hook_input.get("tool_input") or {}
if hooklib.is_explicit_background(ti.get("run_in_background")):
    sys.exit(0)

command = str(ti.get("command") or "")
cwd = str(hook_input.get("cwd") or ".")

if hooklib.test_python_unbuffered(command, cwd):
    hooklib.emit_post_tool_context(
        "If this is a Python task, stdout is connected to a pipe, so Python buffers "
        "output instead of flushing in real time — making it look stuck or empty. "
        "Re-run with unbuffered output for easier real-time monitoring: "
        "PYTHONUNBUFFERED=1 uv run python script.py")
