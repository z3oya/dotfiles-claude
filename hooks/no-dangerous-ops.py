#!/usr/bin/env python3
"""PreToolUse hook (Bash + PowerShell): block dangerous system operations —
11 checks, each with its own bypass marker so a bypass on one chained
operation does not silence another. Python port of no-dangerous-ops.sh /
no-dangerous-ops.ps1."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "py"))
import hooklib

hook_input, command = hooklib.read_hook_command()

# Fast-path bailout: union of trigger tokens across all checks below —
# false negatives would silently disarm, so keep it a superset.
FASTPATH = re.compile(
    r"\b(mkfs|parted|fdisk|gdisk|sgdisk|cfdisk|wipefs|cryptsetup|shred|srm|wipe"
    r"|shutdown|reboot|poweroff|halt|init|telinit|systemctl|chmod|chown|docker"
    r"|iptables|ip6tables|nft|ufw|crontab|killall|kill|tee|cp|mv|install|dd)\b"
    r"|/dev/|/etc/|/proc/|/sys/|/boot/|>"
)
if not FASTPATH.search(command):
    sys.exit(0)

ANCHORS = f"({hooklib.CMD_ANCHOR_SUDO}|{hooklib.CMD_WRAPPER}|{hooklib.CMD_WRAPPER_SSH})"
# Every tool-name check is anchored to command position (direct/sudo/wrapped/
# ssh) — without ANCHORS a literal mention in echo/comments would deny. The
# target-shape checks below are the only unanchored ones (the .sh source has
# them unanchored too: the hazard is the target path, not the tool).
A = lambda s: hooklib.compile_pattern(ANCHORS + s, ignorecase=True).search(command)
B = lambda m: hooklib.test_bypass_marker(command, m)

# --- Disk format / partition tools (allow --dry-run) -----------------------
if A(r"(mkfs(\.[a-zA-Z0-9]+)?|parted|fdisk|gdisk|sgdisk|cfdisk|wipefs)\b") \
        and not re.search(r"--dry-run\b", command) and not B("BYPASS_DISK_FORMAT_CHECK"):
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_DISK_FORMAT_CHECK",
        "Do not run disk-format / partition-edit tools (mkfs, parted, fdisk, gdisk, "
        "sgdisk, cfdisk, wipefs) — formatting or rewriting a partition table is "
        "irrecoverable on the wrong target.\n"
        "Run with `--dry-run` first to preview, and verify the device with `lsblk -f` "
        "(confirm size matches the user's expected disk and no partition is mounted).")
    sys.exit(0)

if A(r"cryptsetup\b[^|;&]*\b(luksFormat|erase|reencrypt)\b") \
        and not re.search(r"--dry-run\b", command) and not B("BYPASS_DISK_FORMAT_CHECK"):
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_DISK_FORMAT_CHECK",
        "Do not run cryptsetup luksFormat / erase / reencrypt — these destroy the LUKS "
        "header; lost headers are unrecoverable without an external backup.\n"
        "Back up the header first (`cryptsetup luksHeaderBackup`) and verify the device "
        "with `lsblk -f`.")
    sys.exit(0)

# --- Writes to /dev/<device> and /etc|/proc|/sys|/boot (target-based) ------
SAFE_DEV = (r"(?!(null|zero|random|urandom|full|console|stderr|stdout|stdin|ptmx)"
            r"(?![/.\w])|tty\w*(?![/.\w])|fd/\w+(?![/.\w])|pts/\w+(?![/.\w]))")
SYS_PATH = r"(/etc|/proc|/sys|/boot)/"
TARGET_SHAPES = [
    r"\bof=(%s)\S", r">>?\s*(%s)\S", r"\btee\b[^|;&]*\s(%s)\S",
    # 4th shape: path as the LAST argument (line-end anchor). The .sh source
    # matched a literal `$` there (bash quoting bug) and thus never fired —
    # deliberate deviation, keep.
    r"\b(cp|mv|install)\b[^|;&]*\s(%s)\S+[ \t]*($|[|;&])",
]
dev_hit = any(re.search(s % ("/dev/" + SAFE_DEV), command) for s in TARGET_SHAPES)
sys_hit = any(re.search(s % SYS_PATH, command) for s in TARGET_SHAPES)
if dev_hit and not B("BYPASS_BLOCKDEV_WRITE_CHECK"):
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_BLOCKDEV_WRITE_CHECK",
        "Do not write to a /dev/<device> — the hazard is the target, not the tool. "
        "`dd of=`, `> /dev/X`, `tee /dev/X` share one failure mode: one wrong letter "
        "overwrites a live disk. Verify with `lsblk -f` before bypassing.")
    sys.exit(0)
if sys_hit and not B("BYPASS_SYSPATH_WRITE_CHECK"):
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_SYSPATH_WRITE_CHECK",
        "Do not write to /etc, /proc, /sys, or /boot — one bad write can break boot, "
        "networking, login, or kernel params. Prefer `sudoedit` for /etc, `sysctl -w` "
        "for kernel params. Confirm the exact path before bypassing.")
    sys.exit(0)

# --- Secure-delete tools ---------------------------------------------------
if A(r"(shred|srm|wipe)" + hooklib.CMD_TRAIL) and not B("BYPASS_SECURE_DELETE_CHECK"):
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_SECURE_DELETE_CHECK",
        "Do not use shred / srm / wipe — secure-erase tools destroy data with no "
        "recovery path. Plain `rm` is reversible from snapshots/backups; only use "
        "secure-erase with a documented compliance requirement.")
    sys.exit(0)

# --- Power-state operations ------------------------------------------------
if (A(r"(shutdown|reboot|poweroff|halt)\b")
        or A(r"(tel)?init\s+[016]\b")
        or A(r"systemctl\s+(poweroff|reboot|halt|kexec|hibernate|suspend)\b")
        or A(r"kill\s+(-9|-KILL|-SIGKILL)\s+-?1\b")) and not B("BYPASS_POWER_STATE_CHECK"):
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_POWER_STATE_CHECK",
        "Do not change the host power state — these terminate the host and on remote "
        "machines you may have no way back in. For service restarts prefer "
        "`systemctl restart <unit>` instead.")
    sys.exit(0)

# --- Recursive permission/ownership change ---------------------------------
if A(r"(chmod|chown)\b[^|;&]*\s-[a-zA-Z]*R[a-zA-Z]*\b") \
        and not B("BYPASS_RECURSIVE_PERMS_CHECK"):
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_RECURSIVE_PERMS_CHECK",
        "Do not use chmod -R / chown -R — one wrong path can lock out a user or "
        "break system services. Test on a single file first; never recurse from `/`.")
    sys.exit(0)

# --- Docker prune ----------------------------------------------------------
if A(r"docker\s+(system|volume|image|container|network)\s+prune\b") \
        and not B("BYPASS_DOCKER_PRUNE_CHECK"):
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_DOCKER_PRUNE_CHECK",
        "Do not run docker {system,volume,image,container,network} prune — volume "
        "prune discards data volumes that may be the only copy. List candidates "
        "first and remove specific items by name.")
    sys.exit(0)

# --- Firewall wipe ---------------------------------------------------------
if (A(r"ip6?tables\b[^|;&]*\s(-[a-zA-Z]*[FX][a-zA-Z]*\b|--flush\b|--delete-chain\b)")
        or A(r"nft\s+flush\s+ruleset\b")
        or A(r"ufw\s+(--force\s+)?reset\b")) and not B("BYPASS_FIREWALL_WIPE_CHECK"):
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_FIREWALL_WIPE_CHECK",
        "Do not flush firewall rules — can lock you out of remote machines instantly "
        "(SSH itself relies on those rules). Save rules first and schedule a revert.")
    sys.exit(0)

# --- crontab -r ------------------------------------------------------------
if A(r"crontab\b[^|;&]*\s(-[a-zA-Z]*r[a-zA-Z]*|--remove)\b") \
        and not B("BYPASS_CRONTAB_REMOVE_CHECK"):
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_CRONTAB_REMOVE_CHECK",
        "Do not run `crontab -r` — deletes the whole crontab with no backup. "
        "Run `crontab -l > backup.cron` first, then `crontab -e` for single entries.")
    sys.exit(0)

# --- killall ---------------------------------------------------------------
if A(r"killall\b") and not B("BYPASS_KILLALL_CHECK"):
    hooklib.emit_pre_tool_deny_bypassable("BYPASS_KILLALL_CHECK",
        "Do not use `killall` — kills every matching process system-wide. Safer: "
        "`pgrep -af <pattern>` then `kill <PID>`, or `pkill -f <pattern>`.")
