#!/usr/bin/env python3
"""PreToolUse hook (single-track, Bash + PowerShell tools): nudge once per
session when a command pipes its trailing stage into a truncation — `| head` /
`| tail` (bash) or `| Select-Object -First/-Last` (PowerShell). Python port of
no-head-tail-pipe.sh / no-head-tail-pipe.ps1 — one implementation detects both
idioms and serves both tools. Soft advisory, not a block. One hint per
session; re-arms after compact via the shared generation counter."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

hook_input, command = hooklib.read_hook_command()

if not hooklib.tail_truncation_hit(command):
    sys.exit(0)

sid = str(hook_input.get("session_id") or "unknown")
if hooklib.test_session_one_shot_lock(sid, "hint-no-head-tail-pipe"):
    hooklib.emit_pre_tool_warn(
        "Trailing `| head` / `| tail` / `| Select-Object -First/-Last` truncates by position "
        "and discards the rest (irrecoverable if the producer was expensive or non-idempotent: "
        "the truncation happens before the harness sees the output). The harness already saves "
        "large output to a file and shows a head preview, so plain `cmd` gives you the same "
        "visible head AND the rest for rg/Read.\n\n"
        "Prefer the producer's native limit (semantic — short-circuits work):\n"
        "  rg           →  -m N\n"
        "  Get-Content  →  -TotalCount N\n"
        "  git log      →  -n N\n\n"
        "(One-shot hint — will not fire again this session.)"
    )
