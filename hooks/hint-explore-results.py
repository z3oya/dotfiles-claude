#!/usr/bin/env python3
"""PostToolUse hook: remind to verify research-subagent results before acting
on them. Covers Explore (codebase claims) and claude-code-guide (docs/schema
claims) — both produce factual verdicts the parent treats as ground truth
unless reminded otherwise. Python port of verify-explore-results.sh."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

hook_input = hooklib.read_hook_input()
ti = hook_input.get("tool_input") or {}

subagent_type = str(ti.get("subagent_type") or "")
if subagent_type not in ("Explore", "claude-code-guide"):
    sys.exit(0)

hooklib.emit_post_tool_context(
    'Verify subagent results before acting: spot-check key claims (file '
    'paths, line numbers, doc URLs, schema fields) via Read/Grep/curl. '
    'Negative claims ("not documented", "doesn\'t exist", "not supported") '
    'are highest risk — the miss is invisible. On conflict with a primary '
    'source, primary source wins.'
)
