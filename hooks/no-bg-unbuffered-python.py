#!/usr/bin/env python3
"""PreToolUse hook (Bash + PowerShell): block background python tasks without
unbuffered output. Python port of python-unbuffered.sh / python-unbuffered.ps1.
Only checks explicit run_in_background=true (auto-backgrounding is caught by
the PostToolUse counterpart). just recipes are resolved to detect indirect
python invocations."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

hook_input = hooklib.read_hook_input()
ti = hook_input.get("tool_input") or {}

# Only check explicit run_in_background
if not hooklib.is_explicit_background(ti.get("run_in_background")):
    sys.exit(0)

command = str(ti.get("command") or "")
if not command:
    sys.exit(0)
hooklib.exit_if_bypass(command, "BYPASS_UNBUFFERED_CHECK")

cwd = str(hook_input.get("cwd") or ".")
if hooklib.test_python_unbuffered(command, cwd):
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_UNBUFFERED_CHECK",
        "Background python task must use unbuffered output.\n"
        "Claude launches processes with stdout as a pipe, causing Python to buffer "
        "output instead of flushing in real time — making it look stuck or empty.\n"
        "Either: PYTHONUNBUFFERED=1 uv run python script.py\n"
        "    or: uv run python -u script.py")
