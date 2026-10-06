#!/usr/bin/env python3
"""PreToolUse hook: when Claude is about to Write/Edit a Claude Code schema
file under any `.claude/` directory (user-global ~/.claude/... or project-local
<repo>/.claude/...), nudge it to consult the `claude-code-guide` subagent for
current official docs BEFORE committing to a change. Python port of
hint-agent-claude-code-guide.sh. Scoped to settings.json / settings.local.json
and the agents/, hooks/, skills/ subtrees; fires at most once per session per
compact (one-shot lock).

Why: these schemas evolve quickly. Claude's training data lags the live docs,
so editing them from prior knowledge often produces stale or invalid
configurations. The claude-code-guide subagent fetches current Anthropic docs
on demand."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

hook_input, file_path = hooklib.read_hook_file_path()

# Require a `.claude/` directory segment in the path. A leading-segment
# `.claudeignore` or `foo.claude/bar` does not match because the `.claude`
# component must be bracketed by `/` on both sides (or be the leading segment
# in a relative path). Backslashes normalized so Windows-style paths match.
norm = file_path.replace("\\", "/")
if "/.claude/" not in norm and not norm.startswith(".claude/"):
    sys.exit(0)

# Restrict to settings files and the agents/, hooks/, skills/ subtrees.
is_settings = norm.endswith("/settings.json") or norm.endswith("/settings.local.json")
in_subtree = ("/agents/" in norm or "/hooks/" in norm or "/skills/" in norm)
if not (is_settings or in_subtree):
    sys.exit(0)

# Skip subagents — agent-* prefix on session_id. The hint asks Claude to spawn
# the claude-code-guide subagent via the Agent tool, but most subagents don't
# have the Agent tool and can't act on this advice.
if hooklib.skip_subagent():
    sys.exit(0)

sid = hooklib.get_session_id()
if hooklib.test_session_one_shot_lock(sid, "hint-agent-claude-code-guide"):
    hooklib.emit_pre_tool_warn(
        "About to edit a Claude config file under `.claude/` (settings.json, "
        "settings.local.json, agent, hook, or skill). Before committing to a "
        "change, spawn the `claude-code-guide` subagent via the Agent tool to "
        "fetch the current official Claude Code / Agent SDK / API docs for "
        "whatever schema or feature you are touching — formats and field names "
        "may have shifted since training. Skip only if the edit is a pure "
        "rename, typo fix, or value tweak that does not depend on schema."
    )
