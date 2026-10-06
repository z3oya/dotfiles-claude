#!/usr/bin/bash
# PostCompact hook: bump a per-session generation counter that other hooks
# read to detect "did compaction happen since I last fired?" Avoids each
# downstream hook having to scan the transcript on every fire.
#
# Generation file: /tmp/claude-${UID}-state/compact-events/<session_id>.gen — single
# monotonic integer, incremented on every compaction (auto or manual).
# Consumer hooks store the gen value at their last fire and compare:
# if it grew, compaction happened in the interval and the consumer
# should reset its own state.
set -euo pipefail

DIR=/tmp/claude-${UID}-state/compact-events
mkdir -p -m 700 "$DIR"

input=$(cat)
SID=$(jq -r '.session_id // empty' <<< "$input")
[ -n "$SID" ] || exit 0

FILE="$DIR/$SID.gen"
gen=0
if [ -f "$FILE" ]; then
    gen=$(cat "$FILE")
    case "$gen" in *[!0-9]*|"") gen=0 ;; esac
fi

echo $((gen + 1)) > "$FILE"

# Windows-path copy for PowerShell-side hooks (HookLib Reset-OnCompact reads
# this; /tmp's MSYS UID is not predictable from pwsh). cygpath converts
# $LOCALAPPDATA from its backslash form to an MSYS path. No -m 700: chmod
# emulation fails on NTFS for existing dirs and set -e would abort the bump.
# Fail loudly if cygpath is missing — a silently empty PS_DIR would break the
# PS-side compact re-arm with no error anywhere.
CYG="$(command -v cygpath || true)"
[ -n "$CYG" ] || { echo "compact-bump: cygpath not found; cannot write PS-side gen mirror" >&2; exit 0; }
PS_DIR="$(cygpath "$LOCALAPPDATA")/Temp/claude-ps-state/compact-events"
mkdir -p "$PS_DIR"
echo $((gen + 1)) > "$PS_DIR/$SID.gen"
