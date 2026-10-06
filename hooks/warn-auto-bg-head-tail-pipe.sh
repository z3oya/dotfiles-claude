#!/usr/bin/bash
# PostToolUse hook: warn when a foreground Bash got auto-backgrounded by
# timeout AND ends with `| head` / `| tail`. The PreToolUse counterpart
# (no-bg-head-tail-pipe.sh) catches explicit run_in_background=true and
# timeout >= BASH_MAX_TIMEOUT_MS; this catches other implicit promotions.
set -euo pipefail

input=$(cat)

# Auto-backgrounded only — backgroundTaskId set in tool_response
bg_id=$(jq -r '.tool_response.backgroundTaskId // empty' <<< "$input")
[ -n "$bg_id" ] || exit 0

# Skip explicit run_in_background — PreToolUse hook owns that case
run_in_bg=$(jq -r '.tool_input.run_in_background // false' <<< "$input")
[ "$run_in_bg" != "true" ] || exit 0

command=$(jq -r '.tool_input.command // ""' <<< "$input")
[ -n "$command" ] || exit 0

if echo "$command" | grep -qE '(^|[^|])\|[[:space:]]*(head|tail)([[:space:]]|$)[^|]*$'; then
    source "$(dirname "$0")/lib/emit.sh"
    emit_post_tool_context 'This command was auto-backgrounded (timeout) and ends with `| head` / `| tail`. `head` exits after N lines and kills the producer; `tail` over a pipe buffers until EOF (the `-f` flag does not follow pipes) and never emits for a long-running task. The process will appear stuck in background and you will never be able to see the full log. Instead, consider re-run without the trailing `| head` / `| tail` — the harness will capture all the stdout into a text file (instead of feeding directly into context) on completion. You can freely rg/Read on it for analyzing the log, with no worry about context flood.'
fi

exit 0
