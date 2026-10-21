#!/usr/bin/env python3
"""UserPromptSubmit hook: inject `git status -sb` as context, truncated to the
first 20 lines when longer. Skips when identical to the last emission for the
session. Python port of inject-git-status.sh."""

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

hooklib.read_hook_input()
sid = hooklib.get_session_id()

# Skip if not inside a git repo. timeout=3 keeps a hung git within the 5s
# hook budget.
try:
    probe = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=3,
    )
except (OSError, subprocess.TimeoutExpired):
    sys.exit(0)
if probe.returncode != 0:
    sys.exit(0)

MAX_LINES = 20
try:
    r = subprocess.run(
        ["git", "status", "-sb"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=3,
    )
except (OSError, subprocess.TimeoutExpired):
    sys.exit(0)
if r.returncode != 0:
    sys.exit(0)
status = r.stdout
lines = status.splitlines()
total = len(lines)

if total > MAX_LINES:
    remaining = total - MAX_LINES
    shown = "\n".join(lines[:MAX_LINES])
    ctx = (
        f"Git status (showing first {MAX_LINES} of {total} lines, "
        f"{remaining} more):\n{shown}"
    )
else:
    ctx = f"Git status:\n{status}"

# Skip if identical to last emission for this session — most turns repeat the
# same status, so re-injecting it costs uncached input tokens for no signal.
cache_dir = hooklib.get_state_root() / "git-status"
cache_dir.mkdir(parents=True, exist_ok=True)
cache_file = cache_dir / sid
try:
    if cache_file.exists() and cache_file.read_text(encoding="utf-8") == ctx:
        sys.exit(0)
except OSError:
    pass

# Persist atomically: temp file + rename, so a crashed hook never leaves a
# truncated cache that would mismatch and force a re-emit next turn.
tmp = cache_file.with_name(cache_file.name + f".tmp.{os.getpid()}")
try:
    tmp.write_text(ctx, encoding="utf-8")
    os.replace(tmp, cache_file)
except OSError:
    sys.exit(0)

hooklib.emit_user_prompt_context(ctx)
