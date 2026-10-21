#!/usr/bin/env python3
"""PostToolUse hook (WebSearch): hint WebSearch → tvly search. prefer-* series;
fires only while USER_HOOKS_WEB_TOOL_USE_TVLY is on ({1,true,on,yes}), so the
tvly hint and the ds-web deny hook never steer at the same time."""

import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

# switch: USER_HOOKS_WEB_TOOL_USE_TVLY, on = {1,true,on,yes}.
if not hooklib.env_flag_on("USER_HOOKS_WEB_TOOL_USE_TVLY"):
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
