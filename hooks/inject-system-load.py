#!/usr/bin/env python3
"""UserPromptSubmit hook: inject system-load context only when resources are
actually elevated. Reminds the agent to review load before launching heavy
work (builds, training, parallel agents, babysit jobs) when the box is
already loaded. Python port of inject-system-load.sh — Linux-only: exits with
no output when platform.system() != "Linux" or when /proc/loadavg,
/proc/meminfo, GNU nproc/ps are unavailable.

Cooldown: time-based, per session_id, anchored to the last emit. Thresholds
are env-overridable (also lets tests force trip/silent paths):
  SYSLOAD_CPU_FACTOR   load5 / nproc threshold (default 0.7)
  SYSLOAD_MEM_PCT      memory %used threshold (default 80)
  SYSLOAD_DISK_PCT     disk %used threshold on / (default 90)
  SYSLOAD_GPU_UTIL     per-GPU %util threshold (default 70)
  SYSLOAD_GPU_MEM      per-GPU mem% threshold (default 80)
  SYSLOAD_COOLDOWN_SEC seconds to suppress repeat emits  (default 600)"""

import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

# Linux-only gate first: read nothing from stdin on other kernels.
if platform.system() != "Linux":
    sys.exit(0)

def _env_float(name: str, default: str) -> float:
    # Malformed override must degrade to the default, not crash the hook
    # (the .sh baseline degraded through awk; stay fail-open).
    try:
        return float(os.environ.get(name) or default)
    except ValueError:
        return float(default)


def _env_int(name: str, default: str) -> int:
    try:
        return int(os.environ.get(name) or default)
    except ValueError:
        return int(default)


CPU_FACTOR = _env_float("SYSLOAD_CPU_FACTOR", "0.7")
MEM_THRESH = _env_int("SYSLOAD_MEM_PCT", "80")
DISK_THRESH = _env_int("SYSLOAD_DISK_PCT", "90")
GPU_UTIL_THRESH = _env_int("SYSLOAD_GPU_UTIL", "70")
GPU_MEM_THRESH = _env_int("SYSLOAD_GPU_MEM", "80")
COOLDOWN_SEC = _env_int("SYSLOAD_COOLDOWN_SEC", "600")

# Read session_id from stdin (same pattern as inject-git-status).
hooklib.read_hook_input()
sid = hooklib.get_session_id()

WARN = []
load_tripped = False

# --- CPU 5-min load avg ---
# Match GNU nproc: honor sched_getaffinity (container/cpuset limited cores),
# falling back to the machine-wide count when affinity is unavailable.
try:
    nproc = len(os.sched_getaffinity(0))
except (AttributeError, OSError):
    nproc = os.cpu_count() or 1
load5 = 0.0
try:
    fields = Path("/proc/loadavg").read_text(encoding="utf-8", errors="replace").split()
    if len(fields) > 1:
        load5 = float(fields[1])
except (OSError, ValueError):
    load5 = 0.0
load_thresh = f"{nproc * CPU_FACTOR:.2f}"
if load5 > float(load_thresh):
    WARN.append(f"CPU: load5={load5} on {nproc} cores (warn>{load_thresh})")
    load_tripped = True

# --- Memory (locale-independent via /proc/meminfo) ---
# Swap intentionally not surfaced — saturated swap is paged-out cold data,
# not a constraint on new allocations as long as free RAM is plenty.
mem_total = 0
mem_avail = 0
try:
    for ln in Path("/proc/meminfo").read_text(encoding="utf-8", errors="replace").splitlines():
        if ln.startswith("MemTotal:"):
            mem_total = int(ln.split()[1])
        elif ln.startswith("MemAvailable:"):
            mem_avail = int(ln.split()[1])
except (OSError, ValueError):
    pass

if mem_total > 0:
    mem_used = mem_total - mem_avail
    mem_pct = mem_used * 100 // mem_total
    if mem_pct > MEM_THRESH:
        used_gb = f"{mem_used / 1048576:.1f}"
        tot_gb = f"{mem_total / 1048576:.1f}"
        WARN.append(f"MEM: {mem_pct}% used ({used_gb}/{tot_gb} GiB)")

# --- Disk on / ---
disk_pct = 0
try:
    du = shutil.disk_usage("/")
    disk_pct = du.used * 100 // du.total
except OSError:
    disk_pct = 0
if disk_pct > DISK_THRESH:
    WARN.append(f"DISK /: {disk_pct}% used")

# --- GPU (if nvidia-smi present) ---
if shutil.which("nvidia-smi"):
    gpu_info = ""
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5,
        )
        if r.returncode == 0:
            gpu_info = r.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        gpu_info = ""
    for row in gpu_info.splitlines():
        if not row.strip():
            continue
        idx, util, mused, mtotal = [c.strip() for c in row.split(",")[:4]] if len(row.split(",")) >= 4 else ["", "", "", ""]
        # Skip rows where any field is non-numeric — `nvidia-smi` returns
        # "[N/A]" or "[Not Supported]" when MIG, locked clocks, or driver
        # errors hide a metric.
        if not (re.fullmatch(r"\d+", util) and re.fullmatch(r"\d+", mused) and re.fullmatch(r"\d+", mtotal)):
            continue
        if int(mtotal) <= 0:
            continue
        mpct = int(mused) * 100 // int(mtotal)
        if int(util) > GPU_UTIL_THRESH or mpct > GPU_MEM_THRESH:
            WARN.append(f"GPU{idx}: {util}% util, mem {mpct}% ({mused}/{mtotal} MiB)")

# --- Long-running CPU hog (only when load5 already tripped, to skip
#     well-behaved services that don't actually saturate the box) ---
if load_tripped:
    hog_line = ""
    try:
        r = subprocess.run(
            ["ps", "-eo", "pid,pcpu,etimes,comm", "--no-headers", "--sort=-pcpu"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if r.returncode == 0:
            for ln in r.stdout.splitlines():
                f = ln.split()
                if len(f) >= 4 and float(f[1]) > 50 and float(f[2]) > 300 and not re.search(r"^(claude|codex|node)$", f[3]):
                    hog_line = " ".join(f)
                    break
    except (OSError, ValueError):
        hog_line = ""
    if hog_line:
        hp = hog_line.split()
        WARN.append(f"Hog: PID {hp[0]} {hp[3]} @ {hp[1]}% avg CPU for {hp[2]}s")

# Nothing tripped → silent, but leave the cache alone. A re-trip within the
# cooldown window is still suppressed (the prior emit's timestamp is what
# gates it). The point of NOT refreshing on clean ticks is to anchor the
# cooldown to the last *emit* (T_last_emit + COOLDOWN_SEC) rather than the
# last invocation — otherwise every clean prompt would push the next emit
# further out, effectively never re-emitting on a steadily-flapping box.
if not WARN:
    sys.exit(0)

# --- Cooldown: time-based. Suppress repeat emits within COOLDOWN_SEC of the
#     last one for this session, regardless of which metrics tripped. ---
cache_dir = hooklib.get_state_root() / "system-load"
cache_dir.mkdir(parents=True, exist_ok=True)
cache_file = cache_dir / sid
now = int(time.time())
try:
    if cache_file.exists():
        last = cache_file.read_text(encoding="utf-8").strip()
        if not re.fullmatch(r"\d+", last):
            last = "0"
        if now - int(last) < COOLDOWN_SEC:
            sys.exit(0)
except OSError:
    pass
tmp = cache_file.with_name(cache_file.name + f".tmp.{os.getpid()}")
try:
    tmp.write_text(str(now), encoding="utf-8")
    os.replace(tmp, cache_file)
except OSError:
    sys.exit(0)

ctx = "System load elevated — be careful before launching heavy work (builds, training, parallel agents):"
for line in WARN:
    ctx += f"\n  - {line}"
ctx += "\nWait for existing processes to complete before starting new heavy work. If DoA is high, periodically (~30m) re-check until system resources drop. Use /babysit to schedule heavy work and prevent overload."

hooklib.emit_user_prompt_context(ctx)
