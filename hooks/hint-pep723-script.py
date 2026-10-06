#!/usr/bin/env python3
"""PostToolUse hook: for .py files written with a shebang (scripts, not
modules), require the uv-run shebang check and a PEP 723 inline metadata block.
Python port of pep723-script.sh. Skips conda/venv environments where the
interpreter is managed by something other than uv scripts."""

import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

hook_input, file_path = hooklib.read_hook_file_path()

# Only check .py files
if not file_path.endswith(".py"):
    sys.exit(0)

content = str((hook_input.get("tool_input") or {}).get("content") or "")

# Only check files that have a shebang (scripts, not modules)
if not content.startswith("#!"):
    sys.exit(0)

# Only check when uv is available
if shutil.which("uv") is None:
    sys.exit(0)

# Skip inside an active conda env — the interpreter is managed by conda, not uv scripts.
if os.environ.get("CONDA_PREFIX"):
    sys.exit(0)

# Skip inside an active virtualenv — the interpreter is managed by the venv, not uv scripts.
if os.environ.get("VIRTUAL_ENV"):
    sys.exit(0)

expected_shebang = "#!/usr/bin/env -S uv run --script"
first_line = content.split("\n", 1)[0]

# Check 1: shebang must use uv run --script
if first_line != expected_shebang:
    hooklib.emit_post_tool_context(
        f"Fix shebang to `#!/usr/bin/env -S uv run --script` "
        f"(found: {first_line}) and add a PEP 723 metadata block."
    )
    sys.exit(0)

# Check 2: PEP 723 metadata block must exist
if "# /// script" not in content:
    hooklib.emit_post_tool_context(
        "Add PEP 723 inline metadata block after the shebang:\n"
        "# /// script\n"
        '# requires-python = ">=3.11"\n'
        "# dependencies = [\n"
        '#   "package-name",\n'
        "# ]\n"
        "# ///"
    )
sys.exit(0)
