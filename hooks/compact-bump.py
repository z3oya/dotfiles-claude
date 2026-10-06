#!/usr/bin/env python3
"""PostCompact hook: bump a per-session generation counter that one-shot hint
hooks read to detect "did compaction happen since I last fired?". Python port
of compact-bump.sh — writes the shared-path copy under the state root that
hooklib.reset_on_compact reads (the bash /tmp tree has no consumers left)."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

raw = hooklib.read_stdin_utf8()
sid = None
if raw.strip():
    try:
        payload = json.loads(raw)
        sid = payload.get("session_id") if isinstance(payload, dict) else None
    except json.JSONDecodeError:
        sid = None
if not sid:
    sys.exit(0)

d = hooklib.get_state_root() / "compact-events"
d.mkdir(parents=True, exist_ok=True)
f = d / f"{sid}.gen"
try:
    gen = int(f.read_text(encoding="utf-8").strip())
except (OSError, ValueError):
    gen = 0
# Atomic tmp+rename: a torn gen file would be read as 0 by consumers and
# silently skip one re-arm (self-heals next bump, but free to prevent).
tmp = f.with_name(f"{sid}.gen.tmp.{os.getpid()}")
tmp.write_text(str(gen + 1), encoding="utf-8")
os.replace(tmp, f)
