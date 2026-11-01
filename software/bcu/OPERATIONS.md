# BCU failure handling

The configured HDD filesystem UUID is
`bf117632-4982-44fd-a113-7b4fd682d9be` (ext4). `/dev/BACKUPHDD` is now
matched by that UUID, not the USB bridge. Reformatting or replacing the disk
requires updating both `config.yaml` and `setup/99-backupserver.rules`.

## Deployment

Repository changes do **not** install or reload system configuration. During a
maintenance window, with automatic backups stopped, install the updated
`setup/99-backupserver.rules` as `/etc/udev/rules.d/99-backupserver.rules` and
reload udev rules. The new rule takes effect on the next device add/change event
(normally the next docking cycle). Check that `/dev/BACKUPHDD` and
`/dev/disk/by-uuid/<configured UUID>` identify the same filesystem partition.
The existing `setup/fstab` entry can remain unchanged.

The destination must already exist. A `backups/current` symlink is supported,
but must resolve to a directory inside the verified HDD filesystem. rsync runs
with this directory pinned as its working directory and destination `.`; it
cannot fall back to writing into an unmounted `/media/BackupHDD` on the Pi.

BCU requires the existing passwordless `sudo` permission for rsync and shutdown;
it uses `sudo -n` so a password prompt cannot hang recovery. Mount/unmount use
the existing user-enabled fstab entry. No additional root Python permission is
needed. The `base` account must be able to list the destination for access and
sample selection; restoring protected files uses the existing rsync sudo permission.
Ensure `base` can read the system journal if kernel logs
are desired; diagnostic permission failures are logged but do not block cleanup.

## Runtime recovery

- rsync exit codes, mount results, UUID, read/write mount options, device instance,
  and directory accessibility are checked. A reconnect does not heal a stale mount.
- Transfer and checksum verification are monitored and have absolute timeouts.
  Filesystem probes run in separate disposable processes.
- After an error, bounded diagnostics are collected and rsync is stopped. BCU
  attempts unmount, power-off, and undocking. PCU acknowledgments and observable
  state are checked, with bounded retries.
- **If unmount fails, HDD power is cut anyway**, prioritizing physical isolation.
  This is logged as emergency/unclean, never as backup success. Filesystem damage
  is possible; inspect/repair the unmounted filesystem before trusting the backup.
- Undocking is attempted only after confirmed power-off and the spindown delay.
  If PCU communication is unavailable, isolation cannot be guaranteed in software.
- Up to two reboot-and-retry attempts are allowed by default. Cleanup is attempted
  before every reboot. The durable counter is stored on the Pi in
  `/home/base/.local/state/bcu/state.json`, atomically written and fsynced before
  requesting a reboot. It resets only after a complete clean cycle. An exhausted
  budget stays exhausted until a successful cycle; later scheduled cycles can
  still run backups, but cannot start another reboot loop while failures persist.
- Corrupt/unreadable/unwritable recovery state disables reboot retries rather than
  silently resetting the budget. Cleanup and final shutdown are still attempted.
- After exhaustion, BCU programs the next wakeup if possible and halts the Pi,
  even when PCU communication fails. There is no wait for operator intervention.
- `--no-shutdown` is a maintenance override: cleanup still runs, but neither
  reboot nor shutdown is requested. Failures return a nonzero exit status.

An uninterruptible kernel I/O wait may survive SIGKILL. BCU records this and
continues its bounded emergency recovery; independent PCU firmware recovery is
still required to guarantee isolation when the host cannot control it.

## Verification and logging

On the first transfer and every seven days afterward, BCU performs a **read-only
rsync checksum dry run** against the NAS, including detection of unexpected
destination files. Any reported difference or nonzero exit code fails verification.
Use a stable NAS source/snapshot: source changes between transfer and comparison
can legitimately cause differences.

BCU then restores up to five randomly selected regular files of at most 64 MiB
each to a temporary directory beside the Pi's state file, verifies content using
a local rsync checksum dry run, and removes its temporary copies. File paths and
restored-file SHA-256 checksums are logged. Sample selection traverses directories
readable by `base`; the full NAS checksum pass uses privileged rsync for all files.
No eligible files is a verification failure. These are content restore smoke
tests, not a substitute for application-level/full disaster-recovery exercises.
Full checksum passes can read the entire backup and NAS dataset; tune the
`backup.integrity` interval, timeouts, and sample limits for the available window.
Any failed cycle invalidates the verification timestamp.

Logs stay on the Pi (`logger.filename`) and distinguish transfer, verification,
clean isolation, emergency power-off, and overall cycle failures. Optional remote
log copying can be enabled with:

```yaml
debug:
  remote_ssh_connect_string: root@nas
  remote_logging_logfile_path: /path/to/base.log
```

Copy failures/timeouts do not prevent shutdown; local logs remain available.

## Hardware-free tests

From `software/bcu`, with pytest, pyserial, and PyYAML installed:

```sh
python3 -m pytest -q test
```

These tests mock the PCU, mount, power, reboot, and shutdown interfaces. Their
real subprocesses execute harmless Python programs and, when installed, an
unprivileged local rsync restore using temporary test files. No sudo, live backup,
or hardware-in-the-loop test is run.
