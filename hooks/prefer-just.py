#!/usr/bin/env python3
"""PostToolUse hook (Bash + PowerShell): hint make → just. prefer-* series;
fires on every matching command (message is two short lines, no quota)."""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

ANCHORS = "(" + hooklib.CMD_ANCHOR_SUDO + "|" + hooklib.CMD_WRAPPER + ")"
PATTERN = ANCHORS + "make" + hooklib.CMD_TRAIL
MESSAGE = ("Prefer just instead of make.\n"
           "  make build  →  just build")

hook_input, command = hooklib.read_hook_command()


def has_justfile(cwd: str) -> bool:
    # just searches ancestor directories for the justfile, so a make call in a
    # subdirectory of a just-managed project still has a `just` substitute.
    # A pure-Makefile project has none anywhere → make is legitimate there.
    root = Path(cwd).resolve()
    for d in (root, *root.parents):
        if any((d / n).is_file() for n in ("justfile", "Justfile", ".justfile")) \
                or any(d.glob("*.just")):
            return True
    return False


if shutil.which("just") \
        and hooklib.compile_pattern(PATTERN, ignorecase=True).search(command) \
        and has_justfile(str(hook_input.get("cwd") or ".")):
    hooklib.emit_post_tool_context(MESSAGE)
