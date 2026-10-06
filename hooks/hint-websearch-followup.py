#!/usr/bin/env python3
"""PostToolUse hook: after WebSearch, remind to fetch interesting links —
search results are titles + URLs + a synthesized summary, not full page
content. Python port of websearch-followup-hint.sh."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

hook_input = hooklib.read_hook_input()

# Skip subagents — agent-* prefix on session_id. The WebFetch fallback chain
# advice targets main-agent investigation; subagents typically perform a
# single search and return.
if hooklib.skip_subagent():
    sys.exit(0)

# Skip if the search returned no results — nothing to follow up on.
results = (hook_input.get("tool_response") or {}).get("results")
result_count = len(results) if isinstance(results, list) else 0
if result_count <= 0:
    sys.exit(0)

hooklib.emit_post_tool_context(
    "WebSearch returns result titles and URLs plus a short synthesized "
    "summary — not the full page content. To actually read a result that "
    "matters, use WebFetch; if WebFetch is truncated or refused, fall back "
    "to the /read-url skill. Never cite a WebSearch result as a source "
    "without reading it."
)
