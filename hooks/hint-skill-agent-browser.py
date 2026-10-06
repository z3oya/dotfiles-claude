#!/usr/bin/env python3
"""PreToolUse hook (Bash + PowerShell): advertise the /agent-browser skill when
Claude is about to drive Chrome/Chromium headless by hand. Python port of
hint-skill-agent-browser.sh / hint-skill-agent-browser.ps1. Fires at most once
per session (re-arms after compact). Non-blocking by design."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

hook_input, command = hooklib.read_hook_command()

# Already using the skill's CLI — nothing to advertise.
if "agent-browser" in command:
    sys.exit(0)

# Fire if either: (a) an inherently-headless Chromium shell binary, or
# (b) a Chrome/Chromium-family binary WITH the --headless flag.
# Case-insensitive per the Windows baseline (.ps1 -match default).
shell_re = re.compile(r"\b(chromium-headless-shell|chrome-headless-shell|headless[-_]shell)\b", re.IGNORECASE)
chrome_re = re.compile(r"\b(chromium(-browser)?|google-chrome(-stable)?|chrome)\b", re.IGNORECASE)

if shell_re.search(command):
    hit = True
elif chrome_re.search(command) and re.search(r"--headless\b", command, re.IGNORECASE):
    hit = True
else:
    sys.exit(0)

sid = hooklib.get_session_id()
if hooklib.skip_subagent():
    sys.exit(0)

if hooklib.test_session_one_shot_lock(sid, "skill-hint-agent-browser"):
    hooklib.emit_pre_tool_warn(
        "About to drive Chrome/Chromium headless by hand. Consider the /agent-browser "
        "skill — it wraps Chrome/Chromium over CDP with snapshot/click/fill/screenshot "
        "verbs and a persistent daemon, instead of raw `chromium --headless` flag-juggling. "
        "Load via Skill tool (skill='agent-browser'). Raw `chromium --headless` is fine for "
        "a one-off where the skill is unavailable. (One-shot hint — will not fire again this session.)"
    )
