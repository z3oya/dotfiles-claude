#!/usr/bin/env python3
"""PreToolUse hook (Bash + PowerShell): deny background-risky commands with a
trailing truncation (`| head` / `| tail` / `| Select-Object -First/-Last`).
Python port of no-bg-head-tail-pipe.sh / no-bg-head-tail-pipe.ps1. Explicit
backgrounding and long timeouts can both land in background, where head kills
the producer and tail over a pipe buffers until EOF."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

hook_input = hooklib.read_hook_input()
ti = hook_input.get("tool_input") or {}

is_bg = hooklib.is_explicit_background(ti.get("run_in_background"))
try:
    timeout_ms = int(ti.get("timeout") or 0)
except (TypeError, ValueError):
    timeout_ms = 0
try:
    max_timeout_ms = int(os.environ.get("BASH_MAX_TIMEOUT_MS") or 600000)
except ValueError:
    max_timeout_ms = 600000
if max_timeout_ms <= 0:
    max_timeout_ms = 600000
if not is_bg and timeout_ms < max_timeout_ms:
    sys.exit(0)

command = str(ti.get("command") or "")
if not command:
    sys.exit(0)
hooklib.exit_if_bypass(command, "BYPASS_BACKGROUND_HEAD_TAIL")

# Trailing `| head` / `| tail` (bash tools via PS) or trailing
# `| Select-Object -First/-Last` (PS-native) — shared detector from hooklib.
if hooklib.tail_truncation_hit(command):
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_BACKGROUND_HEAD_TAIL",
        "Background-risky command (run_in_background=true or timeout >= max) with trailing "
        "`| head` / `| tail` / `| Select-Object -First/-Last` is rejected. `head` exits after "
        "N lines and kills the producer; `tail` over a pipe buffers until EOF (the `-f` flag "
        "does not follow pipes) and never emits for a long-running task. It would appear like "
        "the process stuck in background and you will never be able to see the full log again. "
        "Instead, drop the trailing truncation and start the bare command — the harness will "
        "capture all the stdout into a text file (instead of feeding directly into context) on "
        "completion. You can freely rg/Read on it for analyzing the log, with no worry about "
        "context flood.")
