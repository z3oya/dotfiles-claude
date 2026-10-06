#!/usr/bin/bash
# PreToolUse hook: block bare python3, require uv run (bypassable)
# CLAUDE.md: "uv run not python3"
set -euo pipefail

source "$(dirname "$0")/lib/bypass.sh"
source "$(dirname "$0")/lib/emit.sh"
source "$(dirname "$0")/lib/read_input.sh"

read_bash_command
bypass_check BYPASS_UV_RUN_CHECK

# Skip if an active venv/conda env already scopes bare python3 correctly
if [ -n "${VIRTUAL_ENV:-}" ] || [ -n "${CONDA_PREFIX:-}" ]; then
    exit 0
fi

# Skip if command already uses uv run
if echo "$command" | grep -qP '\buv\s+run\b'; then
    exit 0
fi

# Skip if uv isn't installed — no point suggesting an unavailable alternative.
if ! command -v uv >/dev/null 2>&1; then
    exit 0
fi

# Detect bare python3/python at command position
if ! echo "$command" | grep -qP '(^|&&|;|\|)\s*python3?\s'; then
    exit 0
fi

# Skip common legitimate bare-python uses
if echo "$command" | grep -qP 'python3?\s+(-V|--version|--help|-c\s)'; then
    exit 0
fi

emit_pre_tool_deny_bypassable BYPASS_UV_RUN_CHECK 'Prefer uv run python instead of python3 directly.
  python3 script.py  →  uv run python script.py'
