#!/usr/bin/env python3
"""PreToolUse hook (single-track, Bash + PowerShell tools): block pip and npm
in favor of uv and pnpm. Python port of no-pip-npm.sh / no-pip-npm.ps1 — one
implementation serves both tools via the combined matcher."""

import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

hook_input, command = hooklib.read_hook_command()
hooklib.exit_if_bypass(command, "BYPASS_PACKAGE_MANAGER_CHECK")

ANCHORS = f"({hooklib.CMD_ANCHOR_SUDO}|{hooklib.CMD_WRAPPER})"
PIP_RE = hooklib.compile_pattern(ANCHORS + r"pip3?" + hooklib.CMD_TRAIL, ignorecase=True)
NPM_RE = hooklib.compile_pattern(ANCHORS + "npm" + hooklib.CMD_TRAIL, ignorecase=True)

# Skip inside an active conda env (checked before the PATH scan — conda users
# may need pip for conda-managed interpreters). Skip if uv isn't installed —
# no point suggesting an unavailable alternative.
if not os.environ.get("CONDA_PREFIX") and shutil.which("uv"):
    if PIP_RE.search(command):
        hooklib.emit_pre_tool_deny_bypassable("BYPASS_PACKAGE_MANAGER_CHECK",
            "Use uv instead of pip.\n"
            "  pip install pkg  →  uv add pkg (project) or uv pip install pkg (venv)\n"
            "  pip freeze       →  uv pip freeze")
        sys.exit(0)

# CMD_TRAIL ensures `pnpm` (substring `npm`) doesn't trigger.
if shutil.which("pnpm") and NPM_RE.search(command):
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_PACKAGE_MANAGER_CHECK",
        "Use pnpm instead of npm.\n"
        "  npm install  →  pnpm install\n"
        "  npm run      →  pnpm run")
    sys.exit(0)
