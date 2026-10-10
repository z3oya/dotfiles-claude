#!/usr/bin/env python3
"""PostToolUse hook (WebSearch): hint WebSearch → tvly search. prefer-* series;
fires on every matching call (message is two short lines, no quota)."""

import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

# switch: USER_HOOKS_PREFER_TVLY, off = {0,false,off,no}.
if os.environ.get("USER_HOOKS_PREFER_TVLY", "").strip().lower() in {"0", "false", "off", "no"}:
    sys.exit(0)

MESSAGE = ("Prefer tvly search instead of WebSearch.\n"
           '  WebSearch "query"  →  tvly --json search "query"')

hook_input = hooklib.read_hook_input()

if not shutil.which("tvly"):
    sys.exit(0)

query = str((hook_input.get("tool_input") or {}).get("query") or "")
if not query:
    sys.exit(0)

hooklib.emit_post_tool_context(MESSAGE)
