#Requires -Version 7
# PreToolUse hook (PowerShell tool): block dangerous system operations. Port of
# no-dangerous-ops.sh — 11 checks, each with its own bypass marker so a bypass
# on one chained operation does not silence another. Anchored via
# (SUDO|WRAPPER|WRAPPER_SSH) so literal mentions don't false-positive.
#
#   - disk format / partition tools (allowed with --dry-run)
#   - writes to /dev/<device> (target-based; safe pseudo-devices exempt)
#   - writes to /etc, /proc, /sys, /boot
#   - secure-delete tools (shred, srm, wipe)
#   - power-state / kill init
#   - recursive perm/owner change (chmod -R, chown -R)
#   - docker prune
#   - firewall wipe (iptables -F, nft flush ruleset, ufw reset)
#   - crontab -r
#   - killall
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'lib\ps\HookLib.psm1') -Force -DisableNameChecking

Read-HookCommand

# Fast-path bailout: union of trigger tokens across all checks. Must remain a
# superset of every check below — false negatives would silently disarm.
$FASTPATH = '\b(mkfs|parted|fdisk|gdisk|sgdisk|cfdisk|wipefs|cryptsetup|shred|srm|wipe|shutdown|reboot|poweroff|halt|init|telinit|systemctl|chmod|chown|docker|iptables|ip6tables|nft|ufw|crontab|killall|kill|tee|cp|mv|install|dd)\b|/dev/|/etc/|/proc/|/sys/|/boot/|>'
if ($HookCommand -notmatch $FASTPATH) { exit 0 }

$ANCHORS = '(' + $CMD_ANCHOR_SUDO + '|' + $CMD_WRAPPER + '|' + $CMD_WRAPPER_SSH + ')'

# --- Disk format / partition tools (allow --dry-run) -----------------------
if ($HookCommand -match ('(?i)' + $ANCHORS + '(mkfs(\.[a-zA-Z0-9]+)?|parted|fdisk|gdisk|sgdisk|cfdisk|wipefs)\b') `
    -and $HookCommand -notmatch '--dry-run\b' `
    -and -not (Test-BypassMarker 'BYPASS_DISK_FORMAT_CHECK')) {
    Emit-PreToolDenyBypassable 'BYPASS_DISK_FORMAT_CHECK' "Do not run disk-format / partition-edit tools (mkfs, parted, fdisk, gdisk, sgdisk, cfdisk, wipefs) — formatting or rewriting a partition table is irrecoverable on the wrong target.
Run with ``--dry-run`` first to preview, and verify the device with ``lsblk -f`` (confirm size matches the user's expected disk and no partition is mounted)."
    exit 0
}

if ($HookCommand -match ('(?i)' + $ANCHORS + 'cryptsetup\b[^|;&]*\b(luksFormat|erase|reencrypt)\b') `
    -and $HookCommand -notmatch '--dry-run\b' `
    -and -not (Test-BypassMarker 'BYPASS_DISK_FORMAT_CHECK')) {
    Emit-PreToolDenyBypassable 'BYPASS_DISK_FORMAT_CHECK' 'Do not run cryptsetup luksFormat / erase / reencrypt — these destroy the LUKS header or rewrite the encrypted volume; lost headers are unrecoverable without an external backup.
Back up the header first (`cryptsetup luksHeaderBackup`) and verify the device with `lsblk -f`.'
    exit 0
}

# --- Write to /dev/<device> (target-based; safe pseudo-devices exempt) -----
# `(?![/.\w])` after each safe name rejects /dev/null/../sda, /dev/null2, etc.
$SAFE_DEV = '(?!(null|zero|random|urandom|full|console|stderr|stdout|stdin|ptmx)(?![/.\w])|tty\w*(?![/.\w])|fd/\w+(?![/.\w])|pts/\w+(?![/.\w]))'
if (($HookCommand -match "\bof=/dev/${SAFE_DEV}\S" `
        -or $HookCommand -match ">>?\s*/dev/${SAFE_DEV}\S" `
        -or $HookCommand -match "\btee\b[^|;&]*\s/dev/${SAFE_DEV}\S" `
        -or $HookCommand -match "\b(cp|mv|install)\b[^|;&]*\s/dev/${SAFE_DEV}\S+\s*(\$|[|;&])") `
    -and -not (Test-BypassMarker 'BYPASS_BLOCKDEV_WRITE_CHECK')) {
    Emit-PreToolDenyBypassable 'BYPASS_BLOCKDEV_WRITE_CHECK' "Do not write to a /dev/<device>. The hazard is the target, not the tool — ``dd of=``, ``> /dev/X``, ``tee /dev/X``, and ``cp/mv/install … /dev/X`` all share the same failure mode: one wrong letter overwrites a live disk. Switching tools does not make it safer.
Verify with ``lsblk -f`` that the device path is correct and no partition is mounted; confirm the size matches the user's expected disk before bypassing."
    exit 0
}

# --- Write to /etc, /proc, /sys, /boot -------------------------------------
$SYS_PATH = '(/etc|/proc|/sys|/boot)/'
if (($HookCommand -match "\bof=${SYS_PATH}\S" `
        -or $HookCommand -match ">>?\s*${SYS_PATH}\S" `
        -or $HookCommand -match "\btee\b[^|;&]*\s${SYS_PATH}\S" `
        -or $HookCommand -match "\b(cp|mv|install)\b[^|;&]*\s${SYS_PATH}\S+\s*(\$|[|;&])") `
    -and -not (Test-BypassMarker 'BYPASS_SYSPATH_WRITE_CHECK')) {
    Emit-PreToolDenyBypassable 'BYPASS_SYSPATH_WRITE_CHECK' 'Do not write to /etc, /proc, /sys, or /boot. These paths control system/kernel state — one bad write can break boot, networking, login, or kernel parameters. The hazard is the target, not the tool.
For /etc edits prefer `sudoedit`. For kernel params prefer `sysctl -w net.foo=bar` over raw `> /proc/sys/...`. Confirm the exact path with `ls -l` and the change with the user before bypassing.'
    exit 0
}

# --- Secure-delete tools ---------------------------------------------------
if ($HookCommand -match ('(?i)' + $ANCHORS + '(shred|srm|wipe)' + $CMD_TRAIL) `
    -and -not (Test-BypassMarker 'BYPASS_SECURE_DELETE_CHECK')) {
    Emit-PreToolDenyBypassable 'BYPASS_SECURE_DELETE_CHECK' 'Do not use shred / srm / wipe — secure-erase tools destroy data with no recovery path. Filesystem-level snapshots, journals, and backups cannot recover what these tools overwrite.
Plain `rm` (or `trash`) is reversible from snapshots/backups in most environments. Only use secure-erase when you have a documented compliance requirement.'
    exit 0
}

# --- Power-state operations ------------------------------------------------
if (($HookCommand -match ('(?i)' + $ANCHORS + '(shutdown|reboot|poweroff|halt)\b') `
        -or $HookCommand -match ('(?i)' + $ANCHORS + '(tel)?init\s+[016]\b') `
        -or $HookCommand -match ('(?i)' + $ANCHORS + 'systemctl\s+(poweroff|reboot|halt|kexec|hibernate|suspend)\b') `
        -or $HookCommand -match ('(?i)' + $ANCHORS + 'kill\s+(-9|-KILL|-SIGKILL)\s+-?1\b')) `
    -and -not (Test-BypassMarker 'BYPASS_POWER_STATE_CHECK')) {
    Emit-PreToolDenyBypassable 'BYPASS_POWER_STATE_CHECK' 'Do not change the host power state (shutdown / reboot / poweroff / halt / init 0|1|6 / systemctl poweroff|reboot|halt|kexec / kill -9 1) — these terminate the host and on remote/shared machines you may have no way back in.
Confirm hostname with `hostname` and `who` for other logged-in users before bypassing; for service restarts prefer `systemctl restart <unit>` instead.'
    exit 0
}

# --- Recursive permission/ownership change ---------------------------------
if ($HookCommand -match ('(?i)' + $ANCHORS + '(chmod|chown)\b[^|;&]*\s-[a-zA-Z]*R[a-zA-Z]*\b') `
    -and -not (Test-BypassMarker 'BYPASS_RECURSIVE_PERMS_CHECK')) {
    Emit-PreToolDenyBypassable 'BYPASS_RECURSIVE_PERMS_CHECK' 'Do not use chmod -R / chown -R. Recursive permission or ownership changes silently rewrite metadata for every file in the tree — one wrong path can lock out a user, break system services, or corrupt package-manager invariants.
Test on a single file first, scope the recursion to the smallest possible subtree, and never recurse from `/` or `$HOME`. Consider `find <dir> -type f -exec chmod 644 {} +` for filtered changes.'
    exit 0
}

# --- Docker prune ----------------------------------------------------------
if ($HookCommand -match ('(?i)' + $ANCHORS + 'docker\s+(system|volume|image|container|network)\s+prune\b') `
    -and -not (Test-BypassMarker 'BYPASS_DOCKER_PRUNE_CHECK')) {
    Emit-PreToolDenyBypassable 'BYPASS_DOCKER_PRUNE_CHECK' 'Do not run docker {system,volume,image,container,network} prune. Pruning removes resources without confirmation; volume prune discards data volumes that may be the only copy of stateful container data.
List candidates first (`docker volume ls -f dangling=true`, `docker ps -a --filter status=exited`) and remove specific items by name.'
    exit 0
}

# --- Firewall wipe ---------------------------------------------------------
if (($HookCommand -match ('(?i)' + $ANCHORS + 'ip6?tables\b[^|;&]*\s(-[a-zA-Z]*[FX][a-zA-Z]*\b|--flush\b|--delete-chain\b)') `
        -or $HookCommand -match ('(?i)' + $ANCHORS + 'nft\s+flush\s+ruleset\b') `
        -or $HookCommand -match ('(?i)' + $ANCHORS + 'ufw\s+(--force\s+)?reset\b')) `
    -and -not (Test-BypassMarker 'BYPASS_FIREWALL_WIPE_CHECK')) {
    Emit-PreToolDenyBypassable 'BYPASS_FIREWALL_WIPE_CHECK' 'Do not flush firewall rules. `iptables -F`, `nft flush ruleset`, and `ufw reset` can lock you out of remote machines instantly — the SSH session itself relies on the rules you are about to remove.
Save current rules first (`iptables-save > /tmp/rules.bak`) and schedule a revert (`echo iptables-restore < /tmp/rules.bak | at now+5min`) before flushing.'
    exit 0
}

# --- crontab -r ------------------------------------------------------------
if ($HookCommand -match ('(?i)' + $ANCHORS + 'crontab\b[^|;&]*\s(-[a-zA-Z]*r[a-zA-Z]*|--remove)\b') `
    -and -not (Test-BypassMarker 'BYPASS_CRONTAB_REMOVE_CHECK')) {
    Emit-PreToolDenyBypassable 'BYPASS_CRONTAB_REMOVE_CHECK' 'Do not run `crontab -r`. It deletes the entire user crontab with no confirmation and no backup.
Run `crontab -l > backup.cron` first, then `crontab -e` to remove specific entries.'
    exit 0
}

# --- killall ---------------------------------------------------------------
if ($HookCommand -match ('(?i)' + $ANCHORS + 'killall\b') `
    -and -not (Test-BypassMarker 'BYPASS_KILLALL_CHECK')) {
    Emit-PreToolDenyBypassable 'BYPASS_KILLALL_CHECK' 'Do not use `killall` — it kills every matching process system-wide, including unrelated ones from other users or sessions.
Safer: `pgrep -af <pattern>` first to see exactly which PIDs match, then `kill <PID>` for the specific target. Or `pkill -f <pattern>` when the full command-line pattern is unique.'
    exit 0
}

exit 0
