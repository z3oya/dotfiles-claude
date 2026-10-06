"""Shared helpers for single-track Python hooks.

One implementation serves both the Bash and PowerShell tools via a combined
"Bash|PowerShell" matcher: a hook check reads the tool_input.command string,
which is tool-agnostic. Python equivalents of lib/*.sh and lib/ps/HookLib.psm1
— interface names are kept aligned so ported hook bodies read the same.

Porting semantics (same as HookLib.psm1, see that file's header):
- bash grep matches line-by-line: every ^ / $ in a ported pattern carries (?m).
- line-local whitespace is [ \\t], never \\s (Python \\s also matches \\n).
- the bypass footer names the tool dynamically from tool_name — the same
  marker lands in a Bash or PowerShell command depending on which tool ran.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

_hook_input: dict | None = None


# ---------- stdin ----------

def read_stdin_utf8() -> str:
    # Byte-level read + explicit UTF-8 decode: text-mode stdin follows the
    # console code page (CJK locale would GBK-decode the harness's UTF-8).
    return sys.stdin.buffer.read().decode("utf-8", errors="replace")


def _load_stdin_json() -> dict:
    raw = read_stdin_utf8()
    if not raw.strip():
        sys.exit(0)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit(0)
    # Valid JSON but not an object (array/scalar) would AttributeError later
    # on .get(); the bash/jq baseline quietly allowed such input through.
    if not isinstance(payload, dict):
        sys.exit(0)
    return payload


def read_hook_input() -> dict:
    """Parse stdin JSON without command extraction; exit 0 on empty/bad input."""
    global _hook_input
    _hook_input = _load_stdin_json()
    return _hook_input


def read_hook_command() -> tuple[dict, str]:
    """Mirror of read_bash_command: returns (hook_input, command); exits 0
    (allowing the tool call) on empty/unparseable stdin or empty command."""
    global _hook_input
    _hook_input = _load_stdin_json()
    command = str((_hook_input.get("tool_input") or {}).get("command") or "")
    if not command:
        sys.exit(0)
    return _hook_input, command


def read_hook_file_path() -> tuple[dict, str]:
    """Mirror of read_file_path: returns (hook_input, file_path) from
    .tool_input.file_path (falling back to legacy .tool_input.file); exits 0
    when neither is set."""
    global _hook_input
    _hook_input = _load_stdin_json()
    ti = _hook_input.get("tool_input") or {}
    file_path = str(ti.get("file_path") or ti.get("file") or "")
    if not file_path:
        sys.exit(0)
    return _hook_input, file_path


def get_session_id(default: str = "unknown") -> str:
    return str((_hook_input or {}).get("session_id") or default)


def skip_subagent() -> bool:
    """True when this payload belongs to a subagent (agent-* session prefix)."""
    return get_session_id().startswith("agent-")


def is_explicit_background(value) -> bool:
    """run_in_background may be a JSON boolean or a string flag. The .ps1
    baseline's `-eq 'true'` was case-insensitive and matched both, so must
    this — str(True) == "True" != "true" would silently miss booleans."""
    return value is True or str(value or "").lower() == "true"


# ---------- bypass ----------

def test_bypass_marker(command: str, marker: str) -> bool:
    return marker in command


def exit_if_bypass(command: str, marker: str) -> None:
    if test_bypass_marker(command, marker):
        sys.exit(0)


# ---------- emit ----------

def emit_pre_tool_deny(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }, separators=(",", ":")))


def emit_pre_tool_deny_bypassable(marker: str, reason: str, tool_name: str | None = None) -> None:
    # Two-branch wording per lib/README.md; tool name follows the tool that
    # actually issued the call.
    tool = tool_name or (_hook_input or {}).get("tool_name") or "PowerShell"
    emit_pre_tool_deny(
        f"{reason}\nIf legitimate or false-positive, append `# {marker}` to the {tool} command."
    )


def emit_pre_tool_warn(hint: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": hint}
    }, separators=(",", ":")))


def emit_post_tool_context(message: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": message}
    }, separators=(",", ":")))


def emit_user_prompt_context(ctx: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": ctx}
    }, separators=(",", ":")))


def emit_block(reason: str) -> None:
    # block-note style: block the prompt/response with a reason message.
    print(json.dumps({"decision": "block", "reason": reason}, separators=(",", ":")))


def emit_pre_tool_allow_updated(updated_input: dict) -> None:
    # explore-model-sonnet style: allow with a modified tool_input.
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": updated_input,
        }
    }, separators=(",", ":")))


def last_assistant_model(transcript_path: str) -> str:
    """Model name from the transcript's most recent assistant turn ('' if
    unreadable) — PreToolUse payloads carry no model field, so callers read
    the transcript JSONL instead."""
    try:
        model = ""
        with open(transcript_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("type") == "assistant":
                    m = (rec.get("message") or {}).get("model") or ""
                    if m and m != "<synthetic>":
                        model = m
        return model
    except OSError:
        return ""


# ---------- session state ----------

def get_state_root() -> Path:
    # Single root for Python-side hook state (locks, counters, compact gen
    # mirror). LOCALAPPDATA is the normal anchor; the TEMP fallback must NOT
    # append another "Temp" segment — TEMP already ends in ...\Temp, and
    # Temp\Temp would fork the whole state tree.
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "Temp" / "claude-ps-state"
    return Path(os.environ["TEMP"]) / "claude-ps-state"


def reset_on_compact(sid: str, cache_dir: Path, files: list[str]) -> bool:
    """Mirror of reset_on_compact: clear `files` when the shared per-session
    generation counter (Windows-path copy written by compact-bump.sh) has
    grown since our last fire. Returns True when a reset happened."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    gen_seen = cache_dir / f"{sid}.gen-seen"
    compact_gen = get_state_root() / "compact-events" / f"{sid}.gen"

    def _read_int(p: Path) -> int:
        try:
            return int(p.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return 0

    current = _read_int(compact_gen) if compact_gen.exists() else 0
    prev = _read_int(gen_seen) if gen_seen.exists() else 0
    if current > prev:
        for f in files:
            try:
                os.remove(f)
            except OSError:
                pass
        try:
            gen_seen.write_text(str(current), encoding="utf-8")
        except OSError:
            pass
        return True
    return False


def test_session_one_shot_lock(sid: str, hint_name: str, also_reset: list[str] | None = None) -> bool:
    """Shared one-shot hint lock: returns True exactly when this call is the
    first fire of the (post-compact) session — the lock is created as a side
    effect, so True means "emit the hint now". agent-* filtering stays in the
    caller (not every hint hook skips subagents)."""
    cache_dir = get_state_root() / hint_name
    cache_dir.mkdir(parents=True, exist_ok=True)
    lock = cache_dir / sid
    reset_on_compact(sid, cache_dir, [str(lock), *(also_reset or [])])
    if lock.exists():
        return False
    lock.touch()
    return True


# ---------- command-position anchors (ports of lib/anchors.sh) ----------
# Python 3.11+ forbids global inline flags mid-pattern, and these constants
# get concatenated after the caller's case flag — so flags are NOT baked into
# the constants. Compile through compile_pattern(), which applies
# re.MULTILINE (bash's line-wise ^ / $ semantics) and optional IGNORECASE.
# Line-local gaps are [ \t].

def compile_pattern(pattern: str, ignorecase: bool = False) -> re.Pattern:
    return re.compile(pattern, re.MULTILINE | (re.IGNORECASE if ignorecase else 0))


CMD_ANCHOR_BASIC = r"(^|&&|;|\||\(|\{)[ \t]*((do|then|else)[ \t]+)?"
CMD_ANCHOR_SUDO = CMD_ANCHOR_BASIC + r"(sudo[ \t]+((-[CDghprtTuU][ \t]+\S+|-\S+)[ \t]+)*)?"
CMD_WRAPPER = CMD_ANCHOR_SUDO + (
    r"(((?:bash|sh|pwsh|powershell)(?:\.exe)?)[ \t]+(-\S+[ \t]+)*-c(?:ommand)?[ \t]+|eval[ \t]+"
    r"|xargs[ \t]+(-\S+[ \t]+)*)['\"`]?(sudo[ \t]+)?"
)
CMD_WRAPPER_SSH = CMD_ANCHOR_SUDO + (
    r"ssh[ \t]+((-[bBcDeEFIiJLlmOopQRSWw][ \t]+\S+|-\S+)[ \t]+)*\S+[ \t]+['\"`]?(sudo[ \t]+)?"
)
CMD_TRAIL = r"(?=[ \t;&|'\"]|$)"

# Trailing-pipeline truncation, shared by the one-shot hint and the
# background-risky deny. Single `|` only (not `||`); `[^|]*$` anchors as the
# last stage of its line, so intermediate uses pass through. Compile via
# compile_pattern() (PS variant needs ignorecase=True).
BASH_TAIL_TRUNCATION = r"(^|[^|])\|[ \t]*(head|tail)([ \t]|$)[^|]*$"
PS_TAIL_TRUNCATION = r"(^|[^|])\|[ \t]*(select(?:-object)?)\b[ \t]+(-\S+[ \t]+)*-(first|last|f|l)\b[^|]*$"

_TAIL_CACHE = {}


def tail_truncation_hit(command: str) -> bool:
    """True when the command's trailing pipeline stage truncates — `| head` /
    `| tail` (bash) or `| Select-Object -First/-Last` (PowerShell). Shared by
    the one-shot hint and the background-risky deny."""
    if "tail_hit" not in _TAIL_CACHE:
        _TAIL_CACHE["tail_hit"] = (
            compile_pattern(BASH_TAIL_TRUNCATION),
            compile_pattern(PS_TAIL_TRUNCATION, ignorecase=True),
        )
    bash_re, ps_re = _TAIL_CACHE["tail_hit"]
    return bool(bash_re.search(command) or ps_re.search(command))


# ---------- shared detection ----------

def test_python_unbuffered(command: str, cwd: str = ".") -> bool:
    """Mirror of lib/check-python-unbuffered.sh: True when python is invoked
    (directly or via a just recipe) without PYTHONUNBUFFERED / -u."""
    import subprocess

    if os.environ.get("PYTHONUNBUFFERED"):
        return False

    has_python = re.search(r"\b(python3?|uv\s+run)\b", command) is not None
    recipe = ""

    if re.search(r"\bjust\b", command) and shutil.which("just"):
        rest = re.sub(r"^.*\bjust\b", "", command)
        targets = [t for t in rest.split() if not t.startswith("-")][:5] or ["_default"]
        for t in targets:
            try:
                r = subprocess.run(["just", "--show", t], cwd=cwd, capture_output=True,
                                   text=True, timeout=5)
                out = r.stdout.strip() if r.returncode == 0 else ""
            except (OSError, subprocess.TimeoutExpired):
                out = ""
            if out:
                recipe += out + "\n"
                if re.search(r"\b(python3?|uv\s+run)\b", out):
                    has_python = True

    if not has_python:
        return False
    if "PYTHONUNBUFFERED" in command or "PYTHONUNBUFFERED" in recipe:
        return False
    if re.search(r"\bpython3?\s+-u\b", command) or re.search(r"\bpython3?\s+-u\b", recipe):
        return False
    return True
