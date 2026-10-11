#!/usr/bin/env python3
"""PreToolUse hook (Bash + PowerShell): denies the session's first tag-creating
git tag with a Keep a Changelog reminder, so CHANGELOG.md gets updated before a
release is tagged; the retry passes silently. Listing and delete forms (bare
git tag, -l, -d, ...) do not trigger."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

# switch: USER_HOOKS_HINT_GIT_TAG_CHANGELOG, off = {0,false,off,no}.
if os.environ.get("USER_HOOKS_HINT_GIT_TAG_CHANGELOG", "").strip().lower() in {"0", "false", "off", "no"}:
    sys.exit(0)

MESSAGE = (
    "Blocked once per session so the changelog spec lands before any tag is created. "
    "Follow Keep a Changelog for CHANGELOG.md: keep a standing Unreleased section on top, "
    "cut releases as ## [X.Y.Z] - YYYY-MM-DD (newest first), group entries under "
    "Added / Changed / Deprecated / Removed / Fixed / Security, and convert Unreleased "
    "into the new version section before tagging. "
    "Full spec: ~/.claude/hooks/CHANGELOG_RULES.zh.md / .en.md. "
    "Re-check the changelog, then re-issue the command (retry passes silently)."
)

hook_input, command = hooklib.read_hook_command()

# Stage 1: locate a command-position `git tag`. The \b already keeps
# `git push --tags` and `git describe --tags` out.
ANCHORS = f"({hooklib.CMD_ANCHOR_SUDO}|{hooklib.CMD_WRAPPER})"
m = hooklib.compile_pattern(ANCHORS + r"git[ \t]+tag\b").search(command)
if not m:
    sys.exit(0)
# m.end() lands right after `tag`; the rest of this command decides
# query-vs-create. Cut at && / ; / | / newline to stay in-segment.
rest = hooklib.compile_pattern(r"&&|[;|\r\n]").split(command[m.end():])[0]

# Stage 2: query/delete modes never create a tag; exiting here keeps the
# one-shot lock unconsumed. Lookbehinds keep hyphenated tag names
# (release-l, v2-n5) from tripping the short-flag alternatives.
QUERY = (
    r"(?<![\w-])-[dlvi](?![\w-])"
    r"|(?<![\w-])-n(?:\b|\d)"
    r"|(?<![\w-])--(?:list|verify|contains|no-contains|merged|no-merged"
    r"|points-at|sort|format|color|ignore-case|column|omit-empty)\b"
)
if hooklib.compile_pattern(QUERY).search(rest):
    sys.exit(0)

# Stage 3: creation = a creation flag, or a bare lightweight form
# (git tag <name>). Anything else (bare git tag, --sort=... alone) is a
# listing: exit.
CREATE = (
    r"(?<![\w-])-[asfemuF](?![\w-])"
    r"|(?<![\w-])--(?:annotate|sign|force|message|file|edit|local-user"
    r"|cleanup|create-reflog)\b"
)
if not (
    hooklib.compile_pattern(CREATE).search(rest)
    or hooklib.compile_pattern(r"[ \t]+[^ \t-]").match(rest)
):
    sys.exit(0)

sid = hooklib.get_session_id()
if hooklib.skip_subagent():
    sys.exit(0)

if hooklib.test_session_one_shot_lock(sid, "git-tag-changelog-hint"):
    hooklib.emit_pre_tool_deny(MESSAGE)
