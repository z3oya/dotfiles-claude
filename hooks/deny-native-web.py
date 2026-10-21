#!/usr/bin/env python3
"""PreToolUse hook (WebSearch|WebFetch): deny native web tools and route to the
selected web CLI. Mode selector: USER_HOOKS_WEB_TOOL_USE_DEEPSEEK beats
USER_HOOKS_WEB_TOOL_USE_TVLY when both are on; with neither on the hook idles.
USER_HOOKS_ALLOW_NATIVE_WEB in {1,true,on,yes} lets native tools through."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

ALTERNATIVES = {
    "WebSearch": {
        "deepseek": '  ds-web search "{v}"\n'
        "  flags: --count N (1-50), --content, --ori-question S, --localization IP,\n"
        '         operators site: -site: -term "phrase" lang: after: before:; --json for raw output.',
        "tvly": '  tvly --json search "{v}"',
    },
    "WebFetch": {
        "deepseek": '  ds-web fetch "{v}"\n'
        "  returns the page title and Markdown content; --json for raw output.",
        "tvly": '  tvly --json extract "{v}"',
    },
}

hook_input = hooklib.read_hook_input()
tool = str(hook_input.get("tool_name") or "")
if tool not in ALTERNATIVES or hooklib.env_flag_on("USER_HOOKS_ALLOW_NATIVE_WEB"):
    sys.exit(0)

if hooklib.env_flag_on("USER_HOOKS_WEB_TOOL_USE_DEEPSEEK"):
    mode = "deepseek"
elif hooklib.env_flag_on("USER_HOOKS_WEB_TOOL_USE_TVLY"):
    mode = "tvly"
else:
    sys.exit(0)

tool_input = hook_input.get("tool_input") or {}
value = str(tool_input.get("query" if tool == "WebSearch" else "url") or "")
reason = (
    f"Native {tool} is denied by user hooks; run the command below instead.\n"
    f"{ALTERNATIVES[tool][mode].format(v=value)}"
)

hooklib.emit_pre_tool_deny(reason)
