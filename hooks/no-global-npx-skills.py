#!/usr/bin/env python3
"""PreToolUse hook (single-track, Bash + PowerShell tools): block global
`npx skill` runs; require an explicit --scope. Bare/quoted/versioned and
flag-value-disguised invocations (npx -p pkg skill, npx -c "skill") are
denied; `npx skill --scope <value>` passes through."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

hook_input, command = hooklib.read_hook_command()
hooklib.exit_if_bypass(command, "BYPASS_NPX_SKILL_CHECK")

# NPX_START_RE only locates invocation starts — anchor/env work reused from
# hooklib. Flag parsing lives in the token walk below: value-taking flags
# are set membership there, not nested quantifiers with backtracking (under
# `Bash(*)` a missed spelling is silently allowed, and the walk keeps every
# branch legible and directly testable).
ENV_PREFIX = (r"(?:env(?:\.(?:exe|cmd))?[ \t]+(?:(?:-\S+[ \t]+)+(?:\S+[ \t]+)?)*"  # env wrapper, flags may take values
              r"|[A-Za-z_]\w*=(?:\"[^\"]*\"|'[^']*'|\S*)[ \t]+)*")                 # var=value prefix
NPX_START_RE = hooklib.compile_pattern(
    f"({hooklib.CMD_ANCHOR_SUDO}|{hooklib.CMD_WRAPPER})" + ENV_PREFIX
    + r"npx(?:\.(?:exe|cmd))?[ \t]+",
    ignorecase=True)
OPS = {"&&", "||", ";", "|", "|&", "&", ")"}
VALUE_FLAGS = {"-p", "--package", "--prefix", "--registry", "--userconfig",
               "--cache", "--node-options", "--node-gyp-def", "--ssh-command"}
CALL_FLAGS = {"-c", "--call", "--shell"}
# Last path segment decides the bin npx runs: `skill`, `skill@2`, and the
# scoped-package spelling `@org/skill` all land on a `skill` binary.
SPEC_RE = re.compile(r"(?:@\S+?/)?skill(?:@\S+)?", re.IGNORECASE)
DENY = ("Global `npx skill` is blocked; pass an explicit scope:\n"
        "  npx skill --scope <value>")


def _tokens(text: str) -> list[str]:
    # Shell-ish tokenization: quoted strings stay whole, and `;&|()<>` split
    # even without spaces (`npx skill; echo hi` must not yield `skill;`).
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c in " \t\r\n":
            i += 1
        elif c in "\"'":
            j = text.find(c, i + 1)
            if j == -1:
                j = n - 1
            out.append(text[i:j + 1])
            i = j + 1
        elif c in ";&|()<>":
            two = text[i:i + 2]
            if two in ("&&", "||", "|&", ">&", "&>"):
                out.append(two)
                i += 2
            else:
                out.append(c)
                i += 1
        else:
            j = i
            while j < n and text[j] not in " \t\r\n\"';&|()<>":
                j += 1
            out.append(text[i:j])
            i = j
    return out


def _unquote(tok: str) -> str:
    # Wrappers (bash -c "...") eat the opening quote, so a closing quote can
    # stick to tokens; strip any quote run (incl. backticks) from both ends.
    return tok.strip("\"'`")


def _has_scope(tokens: list[str]) -> bool:
    # Tokens arrive quote-wrapped when the shell passed them that way; npx
    # sees the unquoted flag, so strip before matching.
    for t in tokens:
        s = _unquote(t)
        if s == "--scope" or s.startswith("--scope="):
            return True
    return False


def deny_reason(command: str) -> str | None:
    """Deny reason for `command`, or None when it may pass."""
    for m in NPX_START_RE.finditer(command):
        seg = []                                   # this subcommand's tokens
        for tok in _tokens(command[m.end():]):
            if tok in OPS:
                break
            seg.append(tok)
        i = 0
        while i < len(seg):
            t = _unquote(seg[i])
            base, eq, _ = t.partition("=")
            if not t.startswith("-"):              # first bare token = package
                if SPEC_RE.fullmatch(t) and not _has_scope(seg[i + 1:]):
                    return DENY
                break                              # later tokens are its args
            if base in CALL_FLAGS:
                body = _unquote(t[len(base) + 1:]) if eq else (
                    _unquote(seg[i + 1]) if i + 1 < len(seg) else "")
                words = [_unquote(w) for w in _tokens(body)]
                if words and SPEC_RE.fullmatch(words[0]) \
                        and not _has_scope(words[1:]):
                    return DENY
                i += 1 if eq else 2
                continue
            if base in VALUE_FLAGS or t.startswith("--"):
                # Any long flag's value — after `=` or as the next bare token —
                # could itself be the package (npx --package skill has no
                # command and runs the package; npx --loglevel info skill).
                # Both readings deny on a spec; --scope before the package is
                # an npm config, not the sanctioned form.
                if eq:
                    cand, rest = t[len(base) + 1:], i + 1
                elif i + 1 < len(seg) and not _unquote(seg[i + 1]).startswith("-"):
                    cand, rest = seg[i + 1], i + 2
                else:
                    cand, rest = "", i + 1
                if SPEC_RE.fullmatch(_unquote(cand)) \
                        and not _has_scope(seg[rest:]):
                    return DENY
                i = rest
                continue
            i += 1                                 # bare short/boolean flag
    return None


if (reason := deny_reason(command)) is not None:
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_NPX_SKILL_CHECK", reason)
