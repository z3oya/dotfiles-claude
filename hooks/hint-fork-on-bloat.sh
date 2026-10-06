#!/usr/bin/bash
# PostToolUse hook: hint about fork-first when this session's cumulative
# investigation tool output (Bash/Read/Grep/Glob) crosses ~50 KB.
#
# Threshold calibrated from 3-day session history (107 sessions):
#   p80 ≈ 54 KB; top 22% of sessions account for 80% of investigation
#   bytes (Pareto knee). Rounded to 50 KB so the hint fires on the
#   bloat-prone tail without nagging typical sessions.
#
# One-shot per session (matches no-head-tail-pipe.sh pattern) to avoid
# nag spam — after the first hint, the session has been reminded and
# repeats are silently allowed.
set -euo pipefail

source "$(dirname "$0")/lib/emit.sh"
source "$(dirname "$0")/lib/session_lock.sh"

THRESHOLD_KB=50
CACHE_DIR=/tmp/claude-${UID}-state/hint-fork-bloat

input=$(cat)
SID=$(jq -r '.session_id // empty' <<< "$input")
[ -n "$SID" ] || exit 0

# Skip subagents — their session_id is prefixed `agent-` (e.g.
# `agent-a932b584c6cf7c6a3`), distinct from main-agent UUID session_ids.
# Subagents are short-lived by design and the fork hint doesn't apply to
# them; main agent gets the hint via its own counter.
case "$SID" in agent-*) exit 0 ;; esac

mkdir -p -m 700 "$CACHE_DIR"
COUNTER="$CACHE_DIR/$SID.counter"
FIRED="$CACHE_DIR/$SID.fired"

# Re-arm post-compact: if auto-compact bumped the shared gen counter, wipe
# the counter+fired files so the hint can fire again for the new post-compact
# session. See lib/session_lock.sh.
reset_on_compact "$SID" "$CACHE_DIR" "$FIRED" "$COUNTER"

# Already fired this (post-compact) session — cheapest exit.
[ -f "$FIRED" ] && exit 0

# Estimate tool_response byte size. tostring on whatever shape it has
# captures all content bytes; JSON escapes inflate by ~10-15% but the
# threshold is approximate anyway.
bytes=$(jq -r '.tool_response | tostring | length' <<< "$input")
case "$bytes" in *[!0-9]*|"") exit 0 ;; esac
[ "$bytes" -gt 0 ] || exit 0

# Read counter (default 0 on missing/corrupt).
current=0
if [ -f "$COUNTER" ]; then
    current=$(cat "$COUNTER")
    case "$current" in *[!0-9]*|"") current=0 ;; esac
fi

new=$((current + bytes))
echo "$new" > "$COUNTER"

threshold_bytes=$((THRESHOLD_KB * 1024))
[ "$new" -ge "$threshold_bytes" ] || exit 0

# Cross-the-line, fire one-shot.
touch "$FIRED"
kb=$(( (new + 512) / 1024 ))

emit_post_tool_context "This session has spent ~${kb} KB on investigation tool output (Bash/Read/Grep/Glob). If you're surveying — count / breakdown / sweep / locate over a corpus, or smoke-testing with verbose output — consider forking the next batch via Agent (omit subagent_type to fork yourself). Intermediate fork output stays out of main context, so subsequent main turns re-read less. See CLAUDE.md 'Fork-first on Surveys'.
(One-shot hint — will not fire again this session.)"
