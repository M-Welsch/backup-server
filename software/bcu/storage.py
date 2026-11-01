"""Identify the mounted filesystem AND its original kernel device instance."""

import json
import logging
import os
import stat
import sys
from pathlib import Path

from process_ops import run_checked

WORKER = str(Path(__file__).with_name("storage_worker.py"))
LOG = logging.getLogger(__name__)


class Storage:
    def __init__(self, cfg):
        self.uuid = cfg.get("filesystem_uuid")
        self.mountpoint = Path(cfg.get("mountpoint", "/media/BackupHDD"))
        self.destination = cfg.get("destination", "backups/current")
        self.timeout = cfg.get("storage_timeout_seconds", 15)
        self.identity = None
        self._validation_logged = False

    async def mounted(self):
        # /proc mountinfo inspection avoids probing a possibly dead filesystem.
        output = await run_checked(
            "findmnt", "--json", "--list", "--output", "TARGET", timeout=self.timeout, log_success=False,
        )
        return any(item["target"] == str(self.mountpoint) for item in json.loads(output)["filesystems"])

    async def verify(self, access=False):
        if not self.uuid:
            raise RuntimeError("backup.filesystem_uuid must be configured")
        output = await run_checked(
            "findmnt", "--json", "--mountpoint", str(self.mountpoint),
            "--output", "TARGET,UUID,MAJ:MIN,OPTIONS", timeout=self.timeout, log_success=False,
        )
        mounts = json.loads(output)["filesystems"]
        if len(mounts) != 1:
            raise RuntimeError("Expected exactly one backup filesystem mount")
        mount = mounts[0]
        if mount["uuid"] != self.uuid or "rw" not in mount["options"].split(","):
            raise RuntimeError("Backup mount UUID/options mismatch: {!r}".format(mount))
        device = Path("/dev/disk/by-uuid") / self.uuid
        info = device.stat()
        major_minor = "{}:{}".format(os.major(info.st_rdev), os.minor(info.st_rdev))
        if not stat.S_ISBLK(info.st_mode) or major_minor != mount["maj:min"]:
            raise RuntimeError("Expected HDD is missing or no longer backs the mount")
        node = Path("/sys/dev/block") / major_minor
        resolved = node.resolve(strict=True)
        # sysfs inode + disk sequence distinguish a re-enumerated/reused device.
        disk = resolved.parent if (resolved / "partition").exists() else resolved
        sequence = (disk / "diskseq").read_text().strip() if (disk / "diskseq").exists() else None
        identity = (major_minor, str(resolved), node.stat().st_ino, sequence)
        if self.identity is not None and self.identity != identity:
            raise RuntimeError("Backup HDD device instance changed during the operation")
        self.identity = identity
        if access:
            await run_checked(*self.worker_command("probe"), timeout=self.timeout, log_success=False)
        if not self._validation_logged:
            LOG.info("Backup storage verified: mountpoint=%s uuid=%s device=%s mode=rw",
                     self.mountpoint, self.uuid, major_minor)
            self._validation_logged = True
        return identity

    def worker_command(self, operation, *args):
        if self.identity is None:
            raise RuntimeError("Storage has not been verified")
        return [sys.executable, WORKER, operation, str(self.mountpoint), self.destination,
                self.identity[0], *args]
