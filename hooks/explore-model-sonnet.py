#!/usr/bin/env python3
"""PreToolUse hook: default model "sonnet" for research subagents
(Explore, claude-code-guide) when the caller omits a model — but only when the
calling (main) agent is itself running on opus, so Sonnet/Haiku parents are
left alone (no haiku → sonnet downgrade). Python port of explore-model-sonnet.sh."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

hook_input = hooklib.read_hook_input()
ti = hook_input.get("tool_input") or {}

subagent_type = str(ti.get("subagent_type") or "")
if subagent_type not in ("Explore", "claude-code-guide"):
    sys.exit(0)

# Caller picked a model explicitly — leave it alone.
if str(ti.get("model") or ""):
    sys.exit(0)

# Determine the main agent's model from the transcript's most recent assistant
# turn. PreToolUse payloads don't include a `model` field, so we read
# transcript_path and pull `.message.model` from the last assistant line.
transcript_path = str(hook_input.get("transcript_path") or "")
if not transcript_path:
    sys.exit(0)

main_model = hooklib.last_assistant_model(transcript_path)
if "opus" not in main_model:
    sys.exit(0)

# Merge model: "sonnet" into the full tool_input and return as updatedInput
updated = dict(ti)
updated["model"] = "sonnet"
hooklib.emit_pre_tool_allow_updated(updated)
