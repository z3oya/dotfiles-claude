#!/usr/bin/env python3
"""PreToolUse hook (Bash + PowerShell): block bare python3, require uv run.
Python port of prefer-uv-run.sh / prefer-uv-run.ps1."""

import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

hook_input, command = hooklib.read_hook_command()
hooklib.exit_if_bypass(command, "BYPASS_UV_RUN_CHECK")

# Skip if an active venv/conda env already scopes bare python3 correctly
if os.environ.get("VIRTUAL_ENV") or os.environ.get("CONDA_PREFIX"):
    sys.exit(0)

# Skip if command already uses uv run
if re.search(r"\buv\s+run\b", command):
    sys.exit(0)

# Skip if uv isn't installed — no point suggesting an unavailable alternative.
if not shutil.which("uv"):
    sys.exit(0)

# Detect bare python3/python at command position. Anchor adds `&` — the
# PowerShell call operator. Case-insensitive per the Windows baseline;
# [ \t] gaps so a pattern never straddles lines.
ANCHOR = r"(^|&&|;|\||&)[ \t]*python3?[ \t]"
if not hooklib.compile_pattern(ANCHOR, ignorecase=True).search(command):
    sys.exit(0)

# Skip common legitimate bare-python uses. Case-SENSITIVE: `-V` is version,
# lowercase `-v` is Python's verbose flag — a real script run.
if re.search(r"python3?[ \t]+(-V|--version|--help|-c[ \t])", command):
    sys.exit(0)

hooklib.emit_pre_tool_deny_bypassable("BYPASS_UV_RUN_CHECK",
    "Prefer uv run python instead of python3 directly.\n"
    "  python3 script.py  →  uv run python script.py")
