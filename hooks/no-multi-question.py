#!/usr/bin/env python3
"""PreToolUse hook: AskUserQuestion accepts multiple questions per call, but
one-at-a-time questioning produces much better answers. Python port of
no-multi-question.sh — denies any call with more than one question."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

hook_input = hooklib.read_hook_input()
ti = hook_input.get("tool_input") or {}

questions = ti.get("questions")
n = len(questions) if isinstance(questions, list) else 0
if n <= 1:
    sys.exit(0)

hooklib.emit_pre_tool_deny(
    f"AskUserQuestion called with {n} questions in one call. Please ask one "
    "question at a time: split into sequential calls — present one decision, "
    "get an answer, then the next."
)
