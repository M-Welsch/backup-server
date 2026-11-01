"""Potentially blocking filesystem access runs in a disposable process.

Transfer execs rsync with a pinned cwd. Its destination is '.', never an absolute
path that could fall through to the root filesystem after an unmount.
"""

import hashlib
import json
import os
import random
import stat
import subprocess
import sys
import tempfile
from pathlib import Path


def enter_destination(mountpoint, destination, major_minor):
    root = Path(mountpoint).resolve(strict=True)
    target = (root / destination).resolve(strict=True)
    target.relative_to(root)  # Support current -> snapshot, but never escape the mount.
    if target == root:
        raise RuntimeError("Backup destination must be below the mount root")
    fd = os.open(str(target), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if "{}:{}".format(os.major(info.st_dev), os.minor(info.st_dev)) != major_minor:
            raise RuntimeError("Destination is not on the verified backup device")
        os.fchdir(fd)
    finally:
        os.close(fd)


def checksum(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def restore_command(command):
    try:
        return subprocess.run(command, capture_output=True, check=True, timeout=60)
    except subprocess.SubprocessError as error:
        print("Restore command failed: {!r}; stdout={!r}; stderr={!r}".format(
            command, getattr(error, "stdout", None), getattr(error, "stderr", None)
        ), file=sys.stderr)
        raise


def restore_samples(directory, count, max_bytes):
    restored = []
    # Restores live on the Pi, never inside the backup. TemporaryDirectory only
    # deletes its own generated files, including on verification failure.
    with tempfile.TemporaryDirectory(prefix="bcu-restore-", dir=directory) as temporary:
        for root, dirs, files in os.walk(".", followlinks=False):
            random.shuffle(dirs)
            random.shuffle(files)
            for name in files:
                source = Path(root) / name
                info = source.lstat()
                if not stat.S_ISREG(info.st_mode) or info.st_size > max_bytes:
                    continue
                target = Path(temporary) / str(len(restored))
                source_argument = "./" + str(source)  # A colon in a filename is not a remote rsync host.
                # Use the same restricted-to-rsync sudo permission as backup:
                # archived files may legitimately be unreadable by user base.
                common = ["sudo", "-n", "rsync", "-t", "--no-motd"]
                copied = restore_command(
                    common + ["--perms", "--owner", "--group",
                              "--chown={}:{}".format(os.getuid(), os.getgid()), "--chmod=F600",
                              "--", source_argument, str(target)],
                )
                verified = restore_command(
                    common + ["--checksum", "--dry-run", "--itemize-changes", "--", source_argument, str(target)],
                )
                if verified.stdout:
                    raise RuntimeError("Restore checksum mismatch: {}".format(source))
                if copied.stderr or verified.stderr:
                    print("Restore rsync diagnostics: {!r} {!r}".format(copied.stderr, verified.stderr), file=sys.stderr)
                restored.append({"path": str(source), "sha256": checksum(target), "bytes": info.st_size})
                if len(restored) >= count:
                    return restored
    if not restored:
        raise RuntimeError("No eligible regular files for restore verification")
    return restored


def main():
    operation, mountpoint, destination, major_minor, *args = sys.argv[1:]
    enter_destination(mountpoint, destination, major_minor)
    if operation == "probe":
        with os.scandir(".") as entries:
            next(entries, None)
        print("Backup filesystem accessible")
    elif operation == "transfer":
        os.execvp(args[0], args)
    elif operation == "restore":
        directory, count, max_bytes = args
        print(json.dumps(restore_samples(directory, int(count), int(max_bytes))))
    else:
        raise ValueError("Unknown storage operation: {}".format(operation))


if __name__ == "__main__":
    main()
