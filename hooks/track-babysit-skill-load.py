#!/usr/bin/env python3
"""PostToolUse hook: mark /babysit skill as loaded so hint-skill-babysit.py
allows subsequent babysit commands. Python port of track-babysit-skill-load.sh.
Also syncs gen-seen so a post-compact skill load isn't wiped by the pre-bash
hook's reset_on_compact call."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

hook_input = hooklib.read_hook_input()
ti = hook_input.get("tool_input") or {}

skill = str(ti.get("skill") or "")
if "babysit" not in skill:
    sys.exit(0)

sid = hooklib.get_session_id()
skill_cache_dir = hooklib.get_state_root() / "babysit-skill-loaded"
skill_cache_dir.mkdir(parents=True, exist_ok=True)

# Copy the compact generation counter into the skill cache so the pre-bash
# hook's reset_on_compact sees our marker as already post-compact.
compact_gen = hooklib.get_state_root() / "compact-events" / f"{sid}.gen"
if compact_gen.exists():
    (skill_cache_dir / f"{sid}.gen-seen").write_bytes(compact_gen.read_bytes())

(skill_cache_dir / sid).touch()
