#!/usr/bin/env python3
"""PostToolUse hook (Bash + PowerShell): hint about fork-first when this
session's cumulative investigation tool output crosses ~50 KB. Python port of
hint-fork-on-bloat.sh. One-shot per session, re-arms after compact.

The counter lives under claude-ps-state and tallies every matched tool's
tool_response (Bash/PowerShell/Read/Grep/Glob share this single counter and
the same 50 KB threshold and compact re-arm semantics)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

THRESHOLD_KB = 50

hook_input = hooklib.read_hook_input()

sid = str(hook_input.get("session_id") or "")
if not sid:
    sys.exit(0)

# Skip subagents — agent-* prefix on session_id. Short-lived by design.
if hooklib.skip_subagent():
    sys.exit(0)

cache_dir = hooklib.get_state_root() / "hint-fork-bloat"
counter = cache_dir / f"{sid}.counter"
fired = cache_dir / f"{sid}.fired"
cache_dir.mkdir(parents=True, exist_ok=True)
hooklib.reset_on_compact(sid, cache_dir, [str(fired), str(counter)])  # return ignored

# Already fired this (post-compact) session — cheapest exit.
if fired.exists():
    sys.exit(0)

# Estimate tool_response byte size (JSON text, like jq's tostring|length;
# escape inflation ~10-15% on both sides — threshold is approximate anyway).
resp_text = json.dumps(hook_input.get("tool_response"), separators=(",", ":"))
n_bytes = len(resp_text.encode("utf-8"))
if n_bytes <= 0:
    sys.exit(0)

# Read counter (default 0 on missing/corrupt).
current = 0
try:
    current = int(counter.read_text(encoding="utf-8").strip())
except (OSError, ValueError):
    current = 0
new_total = current + n_bytes
counter.write_text(str(new_total), encoding="utf-8")

if new_total < THRESHOLD_KB * 1024:
    sys.exit(0)

# Crossed the line — fire one-shot.
fired.touch()
kb = (new_total + 512) // 1024

hooklib.emit_post_tool_context(
    f"This session has spent ~{kb} KB on investigation tool output "
    "(Bash/PowerShell/Read/Grep/Glob). If you're surveying — count / breakdown / "
    "sweep / locate over a corpus, or smoke-testing with verbose output — consider forking "
    "the next batch via Agent (omit subagent_type to fork yourself). Intermediate fork "
    "output stays out of main context, so subsequent main turns re-read less. See "
    "CLAUDE.md 'Fork-first on Surveys'.\n"
    "(One-shot hint — will not fire again this session.)")
