#!/usr/bin/env python3
"""PostToolUse hook (Bash + PowerShell): warn when a foreground command got
auto-backgrounded by timeout AND ends with `| head` / `| tail` / trailing
Select-Object -First/-Last. Python port of warn-auto-bg-head-tail-pipe.ps1.
The PreToolUse counterpart owns explicit run_in_background=true and long
timeouts; this catches other implicit promotions."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

hook_input = hooklib.read_hook_input()

# Auto-backgrounded only — backgroundTaskId set in tool_response
resp = hook_input.get("tool_response") or {}
if not str(resp.get("backgroundTaskId") or ""):
    sys.exit(0)

# Skip explicit run_in_background — PreToolUse hook owns that case
ti = hook_input.get("tool_input") or {}
if hooklib.is_explicit_background(ti.get("run_in_background")):
    sys.exit(0)

command = str(ti.get("command") or "")
if not command:
    sys.exit(0)

# Shared truncation detector from hooklib (?m line-wise, trailing stage only)
if hooklib.tail_truncation_hit(command):
    hooklib.emit_post_tool_context(
        "This command was auto-backgrounded (timeout) and ends with `| head` / `| tail` / "
        "`| Select-Object -First/-Last`. `head` exits after N lines and kills the producer; "
        "`tail` over a pipe buffers until EOF (the `-f` flag does not follow pipes) and never "
        "emits for a long-running task. The process will appear stuck in background and you "
        "will never be able to see the full log. Instead, consider re-run without the trailing "
        "truncation — the harness will capture all the stdout into a text file (instead of "
        "feeding directly into context) on completion. You can freely rg/Read on it for "
        "analyzing the log, with no worry about context flood.")
