#!/usr/bin/env python3
"""PostToolUse hook: after SendUserFile, write the latest delivered file as a
plain `file://user@ip/path` URL into a per-session state file that the Claude
Code statusline renderer reads. Python port of track-sent-file.sh. Netloc is
derived from SSH_CONNECTION so the local handler can ssh back."""

import getpass
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

hook_input = hooklib.read_hook_input()

if str(hook_input.get("tool_name") or "") != "SendUserFile":
    sys.exit(0)

files = (hook_input.get("tool_input") or {}).get("files")
if not isinstance(files, list) or not files:
    sys.exit(0)

session_id = str(hook_input.get("session_id") or "")
if not session_id:
    sys.exit(0)

cwd = str(hook_input.get("cwd") or "")

# Build a netloc the user's local machine can ssh back to: use the server IP
# the SSH client used to reach us (from SSH_CONNECTION), with our own username.
# When Claude runs on localhost (no SSH) or under loopback SSH (127.*, ::1) —
# i.e. the user is already on the same box — leave host empty so the URL is the
# hostless `file:///path` form and the local handler opens the file locally.
host = ""
ssh = os.environ.get("SSH_CONNECTION") or ""
if ssh:
    parts = ssh.split()
    server_ip = parts[2] if len(parts) >= 3 else ""
    if server_ip and not server_ip.startswith("127.") and server_ip not in ("::1", "0:0:0:0:0:0:0:1", "localhost"):
        host = f"{getpass.getuser()}@{server_ip}"

last_url = ""
for f in files:
    f = str(f)
    if not f:
        continue
    p = Path(f)
    if not p.is_absolute() and cwd:
        p = Path(cwd) / f
    try:
        p = p.resolve()
    except OSError:
        pass
    if not p.is_file():
        continue
    # Leading "/" is required: Windows as_posix() yields "C:/..." with no
    # leading slash — file://user@ipC:/... would be a malformed URL.
    last_url = f"file://{host}/{p.as_posix()}"

if not last_url:
    sys.exit(0)

state_dir = hooklib.get_state_root() / "last-file-url"
state_dir.mkdir(parents=True, exist_ok=True)
(state_dir / session_id).write_text(last_url + "\n", encoding="utf-8")
