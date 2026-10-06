#!/usr/bin/env python3
"""PostToolUse hook (WebSearch): hint WebSearch → tvly search. prefer-* series;
fires on every matching call (message is two short lines, no quota)."""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

MESSAGE = ("Prefer tvly search instead of WebSearch.\n"
           '  WebSearch "query"  →  tvly --json search "query"')

hook_input = hooklib.read_hook_input()

if not shutil.which("tvly"):
    sys.exit(0)

query = str((hook_input.get("tool_input") or {}).get("query") or "")
if not query:
    sys.exit(0)

hooklib.emit_post_tool_context(MESSAGE)
