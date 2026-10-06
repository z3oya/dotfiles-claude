#!/usr/bin/env python3
"""UserPromptSubmit hook: implement /note as a session notes taker — blocks
the prompt and either stores the note or echoes the accumulated list, via the
block-with-reason output. Python port of block-note-prompt.sh."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

hook_input = hooklib.read_hook_input()
prompt = str(hook_input.get("prompt") or "")

if not (prompt == "/note" or prompt.startswith("/note ")):
    sys.exit(0)

sid = hooklib.get_session_id()
notes_dir = hooklib.get_state_root() / "notes"
notes_dir.mkdir(parents=True, exist_ok=True)
notes_file = notes_dir / sid

if prompt == "/note":
    if notes_file.exists() and notes_file.stat().st_size > 0:
        lines = notes_file.read_text(encoding="utf-8", errors="replace").splitlines()
        notes = "\n".join(f"{i}. {line}" for i, line in enumerate(lines, 1))
        msg = f"Notes this session:\n{notes}"
    else:
        msg = "No notes yet this session."
else:
    text = prompt[len("/note "):]
    with open(notes_file, "a", encoding="utf-8") as fh:
        fh.write(text + "\n")
    count = len(notes_file.read_text(encoding="utf-8", errors="replace").splitlines())
    msg = f"Note #{count} saved: {text}"

hooklib.emit_block(msg)
